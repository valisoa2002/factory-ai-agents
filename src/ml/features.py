"""
Préparation de la matrice de features pour le modèle prédictif.

RÈGLE ANTI-FUITE DE DONNÉES (critique) : la cible est `cadence_reelle`.
Les colonnes `performance_pct`, `disponibilite_pct`, `qualite_pct`,
`trs_pct`, `ecart_pct` sont calculées À PARTIR de `cadence_reelle` (ou
directement corrélées par construction). Les inclure comme features
donnerait au modèle un accès indirect à sa propre cible — il apprendrait
une formule algébrique triviale plutôt qu'un vrai pattern prédictif.
Elles sont donc explicitement exclues.

Features utilisées : produit, machine, atelier (catégorielles, connues
avant production), cadence_theorique et qte_produite (numériques,
connues avant ou indépendamment du résultat réel).
"""

from __future__ import annotations

import pandas as pd

TARGET_COLUMN = "cadence_reelle"

CATEGORICAL_FEATURES = ["produit", "machine", "atelier"]
NUMERIC_FEATURES = ["cadence_theorique", "qte_produite"]

# Colonnes explicitement exclues car dérivées de la cible (fuite de données)
_LEAKY_COLUMNS = ["performance_pct", "disponibilite_pct", "qualite_pct", "trs_pct", "ecart_pct"]


def prepare_training_data(df: pd.DataFrame, exclude_bloquant: bool = True) -> tuple[pd.DataFrame, pd.Series]:
    """
    Retourne (X, y) prêts pour l'entraînement.

    Filtre : exclut les lignes BLOQUANT (qualité non fiable) et les lignes
    où la cible ou une feature obligatoire est manquante.
    """
    working = df.copy()
    if exclude_bloquant:
        working = working[working["quality_severity"] != "BLOQUANT"]

    required_columns = CATEGORICAL_FEATURES + NUMERIC_FEATURES + [TARGET_COLUMN]
    working = working.dropna(subset=required_columns)

    X = working[CATEGORICAL_FEATURES + NUMERIC_FEATURES].copy()
    y = working[TARGET_COLUMN].copy()
    return X, y
