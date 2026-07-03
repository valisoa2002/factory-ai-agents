"""
Détection d'anomalies statistiques : un OF s'écarte-t-il significativement
du comportement habituel de SON PROPRE couple Produit × Machine ?

Différence avec la Phase 3 (quality) : la Phase 3 vérifie si une valeur
est structurellement/physiquement valide dans l'absolu (ex. TRS ≤ 100%).
Cette Phase 6 vérifie si une valeur, bien que valide, est statistiquement
inhabituelle PAR RAPPORT à l'historique de ce couple précis — une cadence
de 40 pcs/min peut être parfaitement normale pour un couple et anormale
pour un autre.

Règle de transparence : un couple avec moins de
`min_of_for_stat_detection` OF ne peut pas avoir de détection fiable
(écart-type non significatif sur trop peu de points). Il est listé à part
en tant qu'InsufficientHistory, jamais silencieusement ignoré ni analysé
avec de fausses certitudes.
"""

from __future__ import annotations

import pandas as pd

from src.anomalies.models import InsufficientHistory, RowAnomaly
from src.utils.config import AnomalyConfig

# Métriques sur lesquelles on cherche des OF statistiquement déviants.
_METRICS_TO_CHECK = ["cadence_reelle", "trs_pct"]


def detect_anomalies(
    df: pd.DataFrame,
    config: AnomalyConfig,
    exclude_bloquant: bool = True,
) -> tuple[list[RowAnomaly], list[InsufficientHistory]]:
    if df.empty:
        return [], []

    working_df = df
    if exclude_bloquant:
        working_df = df[df["quality_severity"] != "BLOQUANT"]

    anomalies: list[RowAnomaly] = []
    insufficient: list[InsufficientHistory] = []

    for (produit, machine), group in working_df.groupby(["produit", "machine"]):
        n_of = len(group)

        if n_of < config.min_of_for_stat_detection:
            insufficient.append(
                InsufficientHistory(
                    produit=produit,
                    machine=machine,
                    n_of=n_of,
                    min_required=config.min_of_for_stat_detection,
                )
            )
            continue

        for metric in _METRICS_TO_CHECK:
            anomalies += _detect_outliers_in_group(group, produit, machine, metric, config)

    return anomalies, insufficient


def _detect_outliers_in_group(
    group: pd.DataFrame,
    produit: str,
    machine: str,
    metric: str,
    config: AnomalyConfig,
) -> list[RowAnomaly]:
    series = group[metric].dropna()
    if len(series) < config.min_of_for_stat_detection:
        return []  # trop de valeurs manquantes sur cette métrique précise

    mean = series.mean()
    std = series.std()
    if std == 0 or pd.isna(std):
        return []  # aucune variation -> rien à détecter (tout le monde est identique)

    anomalies: list[RowAnomaly] = []
    for idx, row in group.iterrows():
        value = row[metric]
        if pd.isna(value):
            continue
        z = (value - mean) / std
        if abs(z) > config.z_score_threshold:
            direction = "au-dessus" if z > 0 else "en-dessous"
            anomalies.append(
                RowAnomaly(
                    code_of=row.get("code_of"),
                    produit=produit,
                    machine=machine,
                    metric=metric,
                    value=float(value),
                    group_mean=float(mean),
                    group_std=float(std),
                    z_score=float(z),
                    message=(
                        f"'{metric}' = {value:.2f} est {abs(z):.1f} écarts-types {direction} "
                        f"de la moyenne habituelle de ce couple ({mean:.2f}) — à investiguer."
                    ),
                )
            )
    return anomalies
