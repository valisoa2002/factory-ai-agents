"""
Recommandation d'une cadence optimale par couple Produit × Machine.

Principe : ne pas recommander "la cadence la plus rapide observée" (ça
pousserait vers la vitesse au détriment de la qualité), mais s'appuyer
sur le TRS — qui équilibre déjà disponibilité, performance et qualité
(TRS = Dispo x Perf x Qualité / 10000). On prend la cadence réelle moyenne
des OF où le TRS a été le meilleur : c'est le meilleur compromis
observé dans l'historique réel, pas un optimum théorique inventé.

Garde-fous :
    - OF BLOQUANT exclus (comme en Phase 5/6).
    - OF signalés comme anomalie statistique (Phase 6) exclus aussi : un
      OF avec un excellent TRS ne doit pas servir de référence s'il est
      lui-même une valeur aberrante.
    - Historique insuffisant -> recommandation explicitement marquée non
      fiable, aucun chiffre inventé.
"""

from __future__ import annotations

import pandas as pd

from src.anomalies.models import RowAnomaly
from src.recommend.models import CadenceRecommendation
from src.utils.config import RecommendationConfig


def recommend_cadences(
    df: pd.DataFrame,
    statistical_anomalies: list[RowAnomaly],
    config: RecommendationConfig,
    exclude_bloquant: bool = True,
) -> list[CadenceRecommendation]:
    if df.empty:
        return []

    anomalous_of_codes = {a.code_of for a in statistical_anomalies}

    df = df.copy()
    df["_is_anomalous"] = df["code_of"].isin(anomalous_of_codes)

    recommendations: list[CadenceRecommendation] = []

    for (produit, machine), group in df.groupby(["produit", "machine"]):
        n_of_disponibles = len(group)

        usable = group
        if exclude_bloquant:
            usable = usable[usable["quality_severity"] != "BLOQUANT"]
        usable = usable[~usable["_is_anomalous"]]

        n_of_utilises = len(usable)
        cadence_theorique = _safe_mean(group["cadence_theorique"])

        if n_of_utilises < config.min_of_for_recommendation:
            recommendations.append(
                CadenceRecommendation(
                    produit=produit,
                    machine=machine,
                    fiable=False,
                    n_of_disponibles=n_of_disponibles,
                    n_of_utilises=n_of_utilises,
                    n_of_reference=0,
                    cadence_theorique_actuelle=cadence_theorique,
                    cadence_recommandee=None,
                    trs_moyen_reference=None,
                    ecart_vs_theorique_pct=None,
                    justification=[
                        f"Historique insuffisant ({n_of_utilises} OF exploitable(s) sur "
                        f"{n_of_disponibles} disponible(s), minimum requis : "
                        f"{config.min_of_for_recommendation}) — pas de recommandation fiable possible."
                    ],
                )
            )
            continue

        usable_with_trs = usable.dropna(subset=["trs_pct", "cadence_reelle"])
        n_reference = min(config.top_n_reference, len(usable_with_trs))
        top_of = usable_with_trs.nlargest(n_reference, "trs_pct")

        cadence_recommandee = float(top_of["cadence_reelle"].mean())
        trs_moyen_reference = float(top_of["trs_pct"].mean())

        ecart_pct = None
        if cadence_theorique:
            ecart_pct = round((cadence_recommandee - cadence_theorique) / cadence_theorique * 100, 1)

        justification = _build_justification(
            n_reference, trs_moyen_reference, cadence_recommandee, cadence_theorique, ecart_pct
        )

        recommendations.append(
            CadenceRecommendation(
                produit=produit,
                machine=machine,
                fiable=True,
                n_of_disponibles=n_of_disponibles,
                n_of_utilises=n_of_utilises,
                n_of_reference=n_reference,
                cadence_theorique_actuelle=cadence_theorique,
                cadence_recommandee=round(cadence_recommandee, 2),
                trs_moyen_reference=round(trs_moyen_reference, 2),
                ecart_vs_theorique_pct=ecart_pct,
                justification=justification,
            )
        )

    recommendations.sort(key=lambda r: (r.fiable, r.produit, r.machine))
    return recommendations


def _build_justification(
    n_reference: int,
    trs_moyen_reference: float,
    cadence_recommandee: float,
    cadence_theorique: float | None,
    ecart_pct: float | None,
) -> list[str]:
    lines = [
        f"Recommandation basée sur les {n_reference} OF au meilleur TRS observé "
        f"(TRS moyen de référence : {trs_moyen_reference:.1f}%)."
    ]

    if cadence_theorique is None or ecart_pct is None:
        lines.append("Cadence théorique de référence indisponible pour comparaison.")
        return lines

    if ecart_pct > 5:
        lines.append(
            f"Cadence recommandée ({cadence_recommandee:.2f} pcs/min) supérieure de {ecart_pct:.1f}% "
            f"à la cadence théorique actuelle ({cadence_theorique:.2f} pcs/min) — le référentiel "
            "théorique est probablement sous-évalué, à recalibrer avec l'atelier."
        )
    elif ecart_pct < -5:
        lines.append(
            f"Cadence recommandée ({cadence_recommandee:.2f} pcs/min) inférieure de {abs(ecart_pct):.1f}% "
            f"à la cadence théorique actuelle ({cadence_theorique:.2f} pcs/min) — même dans les "
            "meilleurs OF, la cadence théorique actuelle n'est pas atteinte ; à réévaluer."
        )
    else:
        lines.append(
            f"Cadence recommandée ({cadence_recommandee:.2f} pcs/min) proche de la cadence théorique "
            f"actuelle ({cadence_theorique:.2f} pcs/min) — référentiel cohérent avec la réalité observée."
        )

    return lines


def _safe_mean(series: pd.Series) -> float | None:
    series = series.dropna()
    if series.empty:
        return None
    return float(series.mean())
