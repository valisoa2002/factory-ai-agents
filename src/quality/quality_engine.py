"""
Orchestrateur de la Phase 3 : exécute toutes les règles de qualité sur un
DataFrame extrait et compile un QualityReport unique.

Ajouter une nouvelle règle = l'écrire dans rules/, puis l'ajouter à la
liste dans `run()`. Aucune règle ne dépend d'une autre : elles sont
appelées indépendamment et leurs résultats simplement concaténés.
"""

from __future__ import annotations

import logging

import pandas as pd

from src.quality import schema
from src.quality.models import Anomaly
from src.quality.quality_report import QualityReport
from src.quality.rules import completeness, consistency, plausibility, uniqueness
from src.utils.config import AppConfig


class QualityEngine:
    def __init__(self, config: AppConfig, logger: logging.Logger | None = None):
        self.config = config
        self.logger = logger or logging.getLogger("cadence_pipeline")

    def run(self, df: pd.DataFrame, source_file: str) -> QualityReport:
        anomalies: list[Anomaly] = []

        # 1. Structure — si des colonnes manquent, tout le reste est peu fiable
        anomalies += completeness.check_required_columns(df, schema.REQUIRED_COLUMNS)

        # 2. Complétude des valeurs obligatoires
        anomalies += completeness.check_missing_values(
            df,
            column=schema.COL_CADENCE_REELLE,
            code_of_column=schema.COL_CODE_OF,
            machine_column=schema.COL_MACHINE,
            allowed_if_zero_column=schema.COL_QTE_PRODUITE,
        )

        # 3. Unicité de la clé métier (Code OF, Machine)
        anomalies += uniqueness.check_duplicate_keys(df, schema.KEY_COLUMNS)

        # 4. Cohérence des formules calculées
        tol = self.config.quality.formula_tolerance
        anomalies += consistency.check_temps_net(df, tolerance=tol.get("temps_net", 0.5))
        anomalies += consistency.check_ecart(df, tolerance=tol.get("ecart", 1.0))
        anomalies += consistency.check_trs(df, tolerance=tol.get("trs", 1.0))

        # 5. Plausibilité métier
        # Disponibilité / Qualité : ne peuvent mathématiquement pas dépasser 100%
        anomalies += plausibility.check_percentage_bounds(
            df, schema.STRICT_PERCENTAGE_COLUMNS, tolerance=self.config.quality.percentage_tolerance
        )
        # Performance / TRS : peuvent légitimement dépasser 100% si la
        # cadence théorique est sous-évaluée -> plafond à deux paliers
        anomalies += plausibility.check_percentage_ceiling(
            df,
            column=schema.COL_PERFORMANCE,
            warning_max=self.config.quality.performance_ceiling.get("warning_max", 100),
            blocking_max=self.config.quality.performance_ceiling.get("blocking_max", 120),
        )
        anomalies += plausibility.check_percentage_ceiling(
            df,
            column=schema.COL_TRS,
            warning_max=self.config.quality.trs_ceiling.get("warning_max", 100),
            blocking_max=self.config.quality.trs_ceiling.get("blocking_max", 120),
        )
        anomalies += plausibility.check_non_negative(df, schema.NON_NEGATIVE_COLUMNS)
        anomalies += plausibility.check_suspiciously_low_cadence_theorique(
            df,
            column=schema.COL_CADENCE_THEORIQUE,
            min_plausible=self.config.quality.min_plausible_cadence_theorique,
        )

        report = QualityReport(
            source_file=source_file,
            n_rows_analyzed=len(df),
            anomalies=anomalies,
        )

        self.logger.info(
            f"Contrôle qualité terminé : {len(anomalies)} anomalie(s) "
            f"détectée(s) — {report.count_by_severity()}"
        )
        return report