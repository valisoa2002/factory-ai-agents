"""
Règles de plausibilité : les valeurs sont-elles physiquement/métier possibles ?

C'est ici qu'on attrape le cas réel découvert le 2026-07-01 :
TRS = 1870.91% sur la ligne WH/MO/53958_FARDELEUSE. Un TRS ne peut
mathématiquement pas dépasser 100% — c'est donc BLOQUANT, contrairement
aux règles de cohérence (consistency.py) qui elles restent en
AVERTISSEMENT.
"""

from __future__ import annotations

import pandas as pd

from src.quality.models import Anomaly, Severity
from src.quality.schema import COL_CODE_OF, COL_MACHINE


def check_percentage_bounds(
    df: pd.DataFrame,
    columns: list[str],
    tolerance: float = 1.0,
) -> list[Anomaly]:
    """
    Vérifie que les colonnes en % restent dans [0 - tolerance, 100 + tolerance].

    Un dépassement au-delà de la tolérance d'arrondi est physiquement
    impossible (ex. TRS > 100%) : BLOQUANT. En pratique, ça révèle presque
    toujours une valeur source aberrante en amont (voir check_consistency).
    """
    anomalies: list[Anomaly] = []
    for column in columns:
        if column not in df.columns:
            continue
        out_of_bounds = df[(df[column] < -tolerance) | (df[column] > 100 + tolerance)]
        for idx, row in out_of_bounds.iterrows():
            anomalies.append(
                Anomaly(
                    rule="percentage_out_of_bounds",
                    severity=Severity.BLOQUANT,
                    message=f"'{column}' = {row[column]}% hors plage [0, 100] — valeur impossible",
                    row_index=int(idx),
                    code_of=row.get(COL_CODE_OF),
                    machine=row.get(COL_MACHINE),
                    column=column,
                )
            )
    return anomalies


def check_non_negative(df: pd.DataFrame, columns: list[str]) -> list[Anomaly]:
    """Vérifie qu'aucune colonne de quantité/durée/cadence n'est négative."""
    anomalies: list[Anomaly] = []
    for column in columns:
        if column not in df.columns:
            continue
        negative = df[df[column] < 0]
        for idx, row in negative.iterrows():
            anomalies.append(
                Anomaly(
                    rule="negative_value",
                    severity=Severity.BLOQUANT,
                    message=f"'{column}' = {row[column]} : valeur négative impossible",
                    row_index=int(idx),
                    code_of=row.get(COL_CODE_OF),
                    machine=row.get(COL_MACHINE),
                    column=column,
                )
            )
    return anomalies


def check_suspiciously_low_cadence_theorique(
    df: pd.DataFrame,
    column: str,
    min_plausible: float = 0.5,
) -> list[Anomaly]:
    """
    Signale une Cadence Théorique anormalement basse — cas réel rencontré :
    0.03 pcs/min sur une fardeleuse automatique, probable erreur de virgule.

    AVERTISSEMENT et non BLOQUANT car on n'a pas encore, à ce stade du
    projet, de plage de référence par Produit × Machine (ça viendra en
    Phase 5 avec l'historique) — on demande une revue humaine plutôt que
    de rejeter automatiquement une valeur qui pourrait être légitime pour
    un produit réellement très lent.
    """
    if column not in df.columns:
        return []

    suspicious = df[(df[column] > 0) & (df[column] < min_plausible)]
    anomalies: list[Anomaly] = []
    for idx, row in suspicious.iterrows():
        anomalies.append(
            Anomaly(
                rule="suspicious_low_cadence_theorique",
                severity=Severity.AVERTISSEMENT,
                message=(
                    f"'{column}' = {row[column]} pcs/min, anormalement bas "
                    f"(seuil {min_plausible}) — vérifier une possible erreur de saisie"
                ),
                row_index=int(idx),
                code_of=row.get(COL_CODE_OF),
                machine=row.get(COL_MACHINE),
                column=column,
            )
        )
    return anomalies
