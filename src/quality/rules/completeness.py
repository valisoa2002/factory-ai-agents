"""
Règles de complétude : colonnes attendues présentes, valeurs obligatoires non vides.

Découverte métier appliquée ici : `Cadence Réelle` peut légitimement être
manquante quand `Qté Produite = 0` (rien n'a été produit sur cet OF). Dans
ce cas précis, l'absence de valeur est un fait normal (INFO), pas une
anomalie (AVERTISSEMENT).
"""

from __future__ import annotations

import pandas as pd

from src.quality.models import Anomaly, Severity


def check_required_columns(df: pd.DataFrame, required_columns: list[str]) -> list[Anomaly]:
    """
    Vérifie que toutes les colonnes attendues sont présentes.

    Anomalie structurelle : si une colonne manque, la feuille source a
    probablement changé de format. C'est BLOQUANT car aucune règle
    suivante ne peut s'exécuter correctement.
    """
    missing = [c for c in required_columns if c not in df.columns]
    if not missing:
        return []
    return [
        Anomaly(
            rule="required_columns_missing",
            severity=Severity.BLOQUANT,
            message=f"Colonne(s) obligatoire(s) absente(s) de l'export : {missing}",
            column=", ".join(missing),
        )
    ]


def check_missing_values(
    df: pd.DataFrame,
    column: str,
    code_of_column: str,
    machine_column: str,
    allowed_if_zero_column: str | None = None,
) -> list[Anomaly]:
    """
    Détecte les valeurs manquantes sur une colonne obligatoire.

    Si `allowed_if_zero_column` est fourni, une valeur manquante sur
    `column` est reclassée en INFO (cas normal) plutôt qu'AVERTISSEMENT
    lorsque la colonne de référence vaut 0 sur la même ligne — ex.
    Cadence Réelle vide parce que Qté Produite = 0.
    """
    if column not in df.columns:
        return []  # déjà signalé par check_required_columns

    anomalies: list[Anomaly] = []
    missing_rows = df[df[column].isna()]

    for idx, row in missing_rows.iterrows():
        is_expected = (
            allowed_if_zero_column is not None
            and allowed_if_zero_column in df.columns
            and row[allowed_if_zero_column] == 0
        )
        severity = Severity.INFO if is_expected else Severity.AVERTISSEMENT
        reason = (
            f"(attendu car {allowed_if_zero_column} = 0)"
            if is_expected
            else "(cause non identifiée — à vérifier)"
        )
        anomalies.append(
            Anomaly(
                rule="missing_value",
                severity=severity,
                message=f"Valeur manquante sur '{column}' {reason}",
                row_index=int(idx),
                code_of=row.get(code_of_column),
                machine=row.get(machine_column),
                column=column,
            )
        )
    return anomalies
