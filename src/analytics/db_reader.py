"""
Lecture de production_history en DataFrame pandas, prête pour l'analyse.

Séparé du reste de src/load/ volontairement : ce module est en LECTURE
SEULE, alors que src/load/ est dédié à l'ÉCRITURE (Phase 4). Mélanger les
deux romprait la responsabilité unique de chaque module.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy.orm import Session

from src.load.models import ProductionRecord


def load_history_dataframe(session: Session) -> pd.DataFrame:
    """Charge toute la table production_history en DataFrame pandas."""
    rows = session.query(ProductionRecord).all()

    records = [
        {
            "produit": r.produit,
            "machine": r.machine,
            "atelier": r.atelier,
            "qte_produite": r.qte_produite,
            "cadence_theorique": r.cadence_theorique,
            "cadence_reelle": r.cadence_reelle,
            "ecart_pct": r.ecart_pct,
            "disponibilite_pct": r.disponibilite_pct,
            "performance_pct": r.performance_pct,
            "qualite_pct": r.qualite_pct,
            "trs_pct": r.trs_pct,
            "quality_severity": r.quality_severity,
            "code_of": r.code_of,
        }
        for r in rows
    ]
    return pd.DataFrame.from_records(records)
