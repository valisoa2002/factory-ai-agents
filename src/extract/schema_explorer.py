"""
Exploration de la structure réelle d'un export Excel.

Ce module ne fait pas partie du pipeline de production : c'est un OUTIL
D'INVESTIGATION. Il répond à la Phase 1 (compréhension des données) que
nous n'avons pas encore faite formellement faute d'avoir un export réel
sous la main.

Il produit un rapport Markdown listant, pour la feuille "Détails Cadences" :
- les feuilles disponibles dans le classeur
- les colonnes détectées, leur type pandas, leur taux de valeurs manquantes
- un échantillon de lignes
- les colonnes à faible cardinalité (candidates à devenir des catégories /
  clés d'agrégation Produit, Machine, etc.)

Le rapport généré doit ensuite être relu et annoté à la main : c'est ce
travail conjoint qui deviendra le dictionnaire de données officiel utilisé
pour coder les règles de qualité de la Phase 3.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.extract.excel_extractor import ExcelExtractor
from src.utils.config import AppConfig

LOW_CARDINALITY_THRESHOLD = 50  # au-delà, une colonne n'est plus considérée catégorielle


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    n_missing: int
    pct_missing: float
    n_unique: int
    sample_values: list


class SchemaExplorer:
    """Génère un rapport d'exploration structurelle d'un export Excel."""

    def __init__(self, config: AppConfig, logger: logging.Logger | None = None):
        self.config = config
        self.logger = logger or logging.getLogger("cadence_pipeline")
        self.extractor = ExcelExtractor(config, logger=self.logger)

    def explore(self, file_path: str | Path) -> Path:
        """
        Explore le fichier donné et écrit un rapport Markdown dans
        config.paths.reports_dir. Retourne le chemin du rapport généré.
        """
        file_path = Path(file_path)
        all_sheets = self.extractor.list_sheets(file_path)
        result = self.extractor.extract(file_path)  # valide déjà la feuille cible
        df = result.dataframe

        profiles = [self._profile_column(df, col) for col in df.columns]

        report_path = self._write_report(file_path, all_sheets, result, profiles)
        self.logger.info(f"Rapport d'exploration généré : {report_path}")
        return report_path

    # ------------------------------------------------------------------

    def _profile_column(self, df: pd.DataFrame, column: str) -> ColumnProfile:
        series = df[column]
        n_missing = int(series.isna().sum())
        n_total = len(series)
        n_unique = int(series.nunique(dropna=True))
        sample = series.dropna().unique()[:5].tolist()
        return ColumnProfile(
            name=column,
            dtype=str(series.dtype),
            n_missing=n_missing,
            pct_missing=round(100 * n_missing / n_total, 2) if n_total else 0.0,
            n_unique=n_unique,
            sample_values=sample,
        )

    def _write_report(
        self,
        file_path: Path,
        all_sheets: list[str],
        result,
        profiles: list[ColumnProfile],
    ) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.config.paths.reports_dir / f"schema_report_{timestamp}.md"

        lines: list[str] = []
        lines.append(f"# Rapport d'exploration — {file_path.name}")
        lines.append(f"\nGénéré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        lines.append("## Feuilles disponibles dans le classeur\n")
        for sheet in all_sheets:
            marker = " ← analysée" if sheet == result.sheet_name else ""
            lines.append(f"- {sheet}{marker}")

        lines.append(f"\n## Feuille '{result.sheet_name}'\n")
        lines.append(f"- Lignes : {result.n_rows}")
        lines.append(f"- Colonnes : {result.n_columns}")

        lines.append("\n## Profil des colonnes\n")
        lines.append("| Colonne | Type pandas | % manquant | Valeurs uniques | Exemples |")
        lines.append("|---|---|---|---|---|")
        for p in profiles:
            examples = ", ".join(str(v) for v in p.sample_values)
            lines.append(
                f"| {p.name} | {p.dtype} | {p.pct_missing}% | {p.n_unique} | {examples} |"
            )

        lines.append("\n## Colonnes candidates à une dimension catégorielle\n")
        lines.append(
            "(faible cardinalité — potentiels axes Produit / Machine / Poste / Équipe)\n"
        )
        for p in profiles:
            if 0 < p.n_unique <= LOW_CARDINALITY_THRESHOLD:
                lines.append(f"- **{p.name}** ({p.n_unique} valeurs distinctes)")

        lines.append("\n## À compléter manuellement\n")
        lines.append("| Colonne | Signification métier | Unité | Colonne clé ? | Notes |")
        lines.append("|---|---|---|---|---|")
        for p in profiles:
            lines.append(f"| {p.name} |  |  |  |  |")

        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path
