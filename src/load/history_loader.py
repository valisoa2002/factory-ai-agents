"""
Chargement des données extraites et contrôlées en base d'historisation.

Règle de déduplication : la clé (Code OF, Machine) est unique en base
(contrainte SQL). Une ligne déjà présente n'est jamais réécrite ni
dupliquée — rejouer le même export est donc sans danger (idempotent).

Règle de conservation qualité : une ligne BLOQUANT est quand même
historisée, avec son statut et le détail de ses anomalies en JSON. La
décision de l'exclure d'une analyse se prend au moment de la requête
(Phase 5+), pas au moment du chargement — on ne perd jamais de donnée
silencieusement.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.load.models import ImportLog, ProductionRecord
from src.quality import schema
from src.quality.models import Anomaly, Severity
from src.quality.quality_report import QualityReport

_SEVERITY_ORDER = {Severity.BLOQUANT: 3, Severity.AVERTISSEMENT: 2, Severity.INFO: 1}


@dataclass
class LoadResult:
    source_file: str
    n_rows_extracted: int
    n_rows_inserted: int
    n_rows_skipped_duplicate: int

    def summary(self) -> str:
        return (
            f"Chargement de '{self.source_file}' : {self.n_rows_inserted} insérée(s), "
            f"{self.n_rows_skipped_duplicate} déjà présente(s) (ignorée(s))."
        )


class HistoryLoader:
    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger("cadence_pipeline")

    def load(
        self,
        session: Session,
        df: pd.DataFrame,
        quality_report: QualityReport,
        source_file: str,
    ) -> LoadResult:
        anomalies_by_row = self._group_anomalies_by_row(quality_report.anomalies)

        existing_keys = self._fetch_existing_keys(session)

        n_inserted = 0
        n_skipped = 0

        for row_index, row in df.iterrows():
            key = (str(row.get(schema.COL_CODE_OF)), str(row.get(schema.COL_MACHINE)))
            if key in existing_keys:
                n_skipped += 1
                continue

            row_anomalies = anomalies_by_row.get(row_index, [])
            severity = self._worst_severity(row_anomalies)

            record = self._row_to_record(row, severity, row_anomalies, source_file)
            session.add(record)
            existing_keys.add(key)  # évite les doublons DANS le même import aussi
            n_inserted += 1

        session.add(
            ImportLog(
                source_file=source_file,
                n_rows_extracted=len(df),
                n_rows_inserted=n_inserted,
                n_rows_skipped_duplicate=n_skipped,
                n_bloquant=quality_report.count_by_severity()["BLOQUANT"],
                n_avertissement=quality_report.count_by_severity()["AVERTISSEMENT"],
                n_info=quality_report.count_by_severity()["INFO"],
            )
        )
        session.commit()

        result = LoadResult(
            source_file=source_file,
            n_rows_extracted=len(df),
            n_rows_inserted=n_inserted,
            n_rows_skipped_duplicate=n_skipped,
        )
        self.logger.info(result.summary())
        return result

    # ------------------------------------------------------------------

    def _fetch_existing_keys(self, session: Session) -> set[tuple[str, str]]:
        rows = session.execute(select(ProductionRecord.code_of, ProductionRecord.machine)).all()
        return {(r[0], r[1]) for r in rows}

    def _group_anomalies_by_row(self, anomalies: list[Anomaly]) -> dict[int, list[Anomaly]]:
        grouped: dict[int, list[Anomaly]] = defaultdict(list)
        for a in anomalies:
            if a.row_index is not None:
                grouped[a.row_index].append(a)
        return grouped

    def _worst_severity(self, anomalies: list[Anomaly]) -> Severity | None:
        if not anomalies:
            return None
        return max((a.severity for a in anomalies), key=lambda s: _SEVERITY_ORDER[s])

    def _row_to_record(
        self,
        row: pd.Series,
        severity: Severity | None,
        row_anomalies: list[Anomaly],
        source_file: str,
    ) -> ProductionRecord:
        def safe(col: str):
            val = row.get(col)
            return None if pd.isna(val) else val

        extracted_at_raw = safe(schema.COL_EXTRACTED_AT)
        extracted_at = pd.to_datetime(extracted_at_raw).to_pydatetime() if extracted_at_raw else None

        return ProductionRecord(
            code_of=str(safe(schema.COL_CODE_OF)),
            machine=str(safe(schema.COL_MACHINE)),
            produit=safe(schema.COL_PRODUIT),
            atelier=safe(schema.COL_ATELIER),
            qte_produite=safe(schema.COL_QTE_PRODUITE),
            duree_totale_min=safe(schema.COL_DUREE_TOTALE),
            duree_arrets_min=safe(schema.COL_DUREE_ARRETS),
            temps_net_min=safe(schema.COL_TEMPS_NET),
            cadence_reelle=safe(schema.COL_CADENCE_REELLE),
            cadence_theorique=safe(schema.COL_CADENCE_THEORIQUE),
            ecart_pct=safe(schema.COL_ECART),
            disponibilite_pct=safe(schema.COL_DISPONIBILITE),
            performance_pct=safe(schema.COL_PERFORMANCE),
            qualite_pct=safe(schema.COL_QUALITE),
            trs_pct=safe(schema.COL_TRS),
            quality_severity=severity.value if severity else None,
            quality_details=json.dumps([a.to_dict() for a in row_anomalies], ensure_ascii=False)
            if row_anomalies
            else None,
            source_file=source_file,
            extracted_at=extracted_at,
        )
