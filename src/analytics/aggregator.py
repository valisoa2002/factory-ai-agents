"""
Calcul des indicateurs agrégés par couple Produit × Machine.

Règle de conception centrale : les lignes de sévérité BLOQUANT sont
exclues du calcul des moyennes par défaut (configurable via
config.analytics.exclude_bloquant) — une valeur physiquement impossible
(ex. TRS=1870%) fausserait toute la moyenne du couple. Le nombre de
lignes exclues est conservé et affiché, jamais caché.
"""

from __future__ import annotations

import pandas as pd

from src.analytics.insights import generate_conclusions
from src.analytics.models import ProductMachineMetrics
from src.utils.config import AnalyticsConfig


def compute_metrics(df: pd.DataFrame, config: AnalyticsConfig) -> list[ProductMachineMetrics]:
    if df.empty:
        return []

    df = df.copy()

    # Compte les exclusions AVANT de filtrer, par couple
    excluded_counts = (
        df[df["quality_severity"] == "BLOQUANT"]
        .groupby(["produit", "machine"])
        .size()
        .to_dict()
    )

    working_df = df
    if config.exclude_bloquant:
        working_df = df[df["quality_severity"] != "BLOQUANT"]

    results: list[ProductMachineMetrics] = []

    for (produit, machine), group in working_df.groupby(["produit", "machine"]):
        n_of = len(group)
        n_excluded = int(excluded_counts.get((produit, machine), 0))

        cadence_reelle = group["cadence_reelle"].dropna()
        stabilite_cv = None
        if len(cadence_reelle) >= 2 and cadence_reelle.mean() != 0:
            stabilite_cv = float(cadence_reelle.std() / cadence_reelle.mean() * 100)

        trs_moy = _safe_mean(group["trs_pct"])

        conclusions = generate_conclusions(
            n_of=n_of,
            n_excluded_bloquant=n_excluded,
            trs_moy=trs_moy,
            stabilite_cv=stabilite_cv,
            config=config,
        )

        results.append(
            ProductMachineMetrics(
                produit=produit,
                machine=machine,
                n_of=n_of,
                n_excluded_bloquant=n_excluded,
                cadence_theorique_moy=_safe_mean(group["cadence_theorique"]),
                cadence_reelle_moy=_safe_mean(cadence_reelle),
                cadence_reelle_min=float(cadence_reelle.min()) if len(cadence_reelle) else None,
                cadence_reelle_max=float(cadence_reelle.max()) if len(cadence_reelle) else None,
                ecart_moy=_safe_mean(group["ecart_pct"]),
                trs_moy=trs_moy,
                performance_moy=_safe_mean(group["performance_pct"]),
                disponibilite_moy=_safe_mean(group["disponibilite_pct"]),
                qualite_moy=_safe_mean(group["qualite_pct"]),
                stabilite_cv=stabilite_cv,
                conclusions=conclusions,
            )
        )

    # Tri par TRS croissant : les couples les plus problématiques en premier
    results.sort(key=lambda m: (m.trs_moy is None, m.trs_moy))
    return results


def _safe_mean(series: pd.Series) -> float | None:
    series = series.dropna()
    if series.empty:
        return None
    return float(series.mean())
