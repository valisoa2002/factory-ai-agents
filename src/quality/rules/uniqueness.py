"""
Règle d'unicité.

Découverte métier appliquée ici : la clé unique d'une ligne est
(Code OF, Machine), pas Code OF seul — un même OF peut être décomposé par
étape/machine (ex. "WH/MO/53956_FARDELEUSE" et "WH/MO/53956_REMPLISSEUSE").
Vérifier l'unicité sur Code OF seul aurait généré de faux doublons.
"""

from __future__ import annotations

import pandas as pd

from src.quality.models import Anomaly, Severity


def check_duplicate_keys(
    df: pd.DataFrame,
    key_columns: list[str],
) -> list[Anomaly]:
    """
    Détecte les lignes dupliquées sur la clé métier composite.

    BLOQUANT : un doublon de clé signifie soit un problème d'export,
    soit une double saisie — dans les deux cas, historiser ces lignes
    telles quelles fausserait tous les calculs agrégés de la Phase 5.
    """
    if not all(c in df.columns for c in key_columns):
        return []  # déjà signalé par check_required_columns

    duplicated_mask = df.duplicated(subset=key_columns, keep=False)
    if not duplicated_mask.any():
        return []

    anomalies: list[Anomaly] = []
    for idx, row in df[duplicated_mask].iterrows():
        key_desc = ", ".join(f"{c}={row[c]}" for c in key_columns)
        anomalies.append(
            Anomaly(
                rule="duplicate_key",
                severity=Severity.BLOQUANT,
                message=f"Ligne dupliquée sur la clé ({key_desc})",
                row_index=int(idx),
                code_of=row.get(key_columns[0]),
                machine=row.get(key_columns[1]) if len(key_columns) > 1 else None,
            )
        )
    return anomalies
