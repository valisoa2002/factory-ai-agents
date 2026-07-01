"""
Règles de cohérence : les colonnes calculées respectent-elles leur formule ?

Les trois formules ci-dessous ont été validées empiriquement le 2026-07-01
sur un export réel de 38 lignes (voir validate_formulas.py et
src/quality/schema.py pour le détail). Un écart signalé ici ne veut pas
dire "la formule est fausse" — dans notre cas réel, il a révélé une valeur
source aberrante (Cadence Théorique = 0.03), pas une erreur de calcul.
C'est pour ça que la sévérité par défaut est AVERTISSEMENT et non BLOQUANT :
la ligne mérite une revue humaine, pas un rejet automatique aveugle.
"""

from __future__ import annotations

import pandas as pd

from src.quality.models import Anomaly, Severity
from src.quality.schema import (
    COL_CADENCE_REELLE,
    COL_CADENCE_THEORIQUE,
    COL_CODE_OF,
    COL_DISPONIBILITE,
    COL_DUREE_ARRETS,
    COL_DUREE_TOTALE,
    COL_ECART,
    COL_MACHINE,
    COL_PERFORMANCE,
    COL_QUALITE,
    COL_TEMPS_NET,
    COL_TRS,
)


def _check_formula(
    df: pd.DataFrame,
    rule_name: str,
    computed: pd.Series,
    actual_column: str,
    tolerance: float,
) -> list[Anomaly]:
    diff = (computed - df.loc[computed.index, actual_column]).abs()
    bad = diff[diff > tolerance]

    anomalies: list[Anomaly] = []
    for idx in bad.index:
        row = df.loc[idx]
        anomalies.append(
            Anomaly(
                rule=rule_name,
                severity=Severity.AVERTISSEMENT,
                message=(
                    f"'{actual_column}' = {row[actual_column]} ne correspond pas à la "
                    f"valeur calculée ({computed.loc[idx]:.2f}), écart = {diff.loc[idx]:.2f}"
                ),
                row_index=int(idx),
                code_of=row.get(COL_CODE_OF),
                machine=row.get(COL_MACHINE),
                column=actual_column,
            )
        )
    return anomalies


def check_temps_net(df: pd.DataFrame, tolerance: float = 0.5) -> list[Anomaly]:
    """Temps Net (min) = Durée Totale (min) - Durée Arrêts (min)"""
    required = {COL_DUREE_TOTALE, COL_DUREE_ARRETS, COL_TEMPS_NET}
    if not required <= set(df.columns):
        return []
    computed = df[COL_DUREE_TOTALE] - df[COL_DUREE_ARRETS]
    return _check_formula(df, "temps_net_formula", computed, COL_TEMPS_NET, tolerance)


def check_ecart(df: pd.DataFrame, tolerance: float = 1.0) -> list[Anomaly]:
    """Écart (%) = (Cadence Réelle - Cadence Théorique) / Cadence Théorique * 100"""
    required = {COL_CADENCE_REELLE, COL_CADENCE_THEORIQUE, COL_ECART}
    if not required <= set(df.columns):
        return []
    valid = df[COL_CADENCE_THEORIQUE] != 0
    subset = df.loc[valid]
    computed = (
        (subset[COL_CADENCE_REELLE] - subset[COL_CADENCE_THEORIQUE])
        / subset[COL_CADENCE_THEORIQUE]
        * 100
    )
    return _check_formula(subset, "ecart_formula", computed, COL_ECART, tolerance)


def check_trs(df: pd.DataFrame, tolerance: float = 1.0) -> list[Anomaly]:
    """TRS (%) = Disponibilité (%) * Performance (%) * Qualité (%) / 10000"""
    required = {COL_DISPONIBILITE, COL_PERFORMANCE, COL_QUALITE, COL_TRS}
    if not required <= set(df.columns):
        return []
    computed = df[COL_DISPONIBILITE] * df[COL_PERFORMANCE] * df[COL_QUALITE] / 10000
    return _check_formula(df, "trs_formula", computed, COL_TRS, tolerance)
