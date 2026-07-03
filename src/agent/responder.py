"""
Génération des réponses de l'agent — chaque réponse est construite à
partir des modules déjà codés (Phases 5, 6, 7), jamais inventée. Si les
données manquent pour répondre correctement, l'agent le dit plutôt que
de deviner.
"""

from __future__ import annotations

import pandas as pd

from src.agent.entities import match_machine, match_produit
from src.analytics.models import ProductMachineMetrics
from src.recommend.models import CadenceRecommendation


def respond_recommend_cadence(
    question: str,
    df: pd.DataFrame,
    produits: list[str],
    machines: list[str],
    code_index: dict[str, str],
    recommendations: list[CadenceRecommendation],
    min_of_for_recommendation: int,
) -> str:
    produit = match_produit(question, produits, code_index)
    machine = match_machine(question, machines)

    if not produit and not machine:
        return (
            "Je n'ai pas identifié de produit ou de machine dans votre question. "
            "Pouvez-vous préciser, par exemple : \"Quelle cadence recommandes-tu pour "
            "le produit FL016 sur la Souffleuse automatique ?\""
        )

    if produit and machine:
        matches = [r for r in recommendations if r.produit == produit and r.machine == machine]
    elif produit:
        matches = [r for r in recommendations if r.produit == produit]
    else:
        matches = [r for r in recommendations if r.machine == machine]

    if not matches:
        return f"Je n'ai aucune donnée en historique pour {produit or ''} {machine or ''}.".strip()

    fiables = [r for r in matches if r.fiable]
    if not fiables:
        r = matches[0]
        return (
            f"Pour {r.produit} sur {r.machine}, l'historique est encore insuffisant "
            f"({r.n_of_utilises} OF exploitable(s), {min_of_for_recommendation} minimum requis) "
            "pour une recommandation fiable. Chargez plus d'exports pour affiner."
        )

    r = max(fiables, key=lambda x: x.n_of_reference)
    lines = [
        f"Pour {r.produit} sur {r.machine}, je recommande une cadence de "
        f"**{r.cadence_recommandee:.2f} pcs/min** (cadence théorique actuelle : "
        f"{r.cadence_theorique_actuelle:.2f} pcs/min)."
    ]
    lines.extend(r.justification)
    return "\n".join(lines)


def respond_why_low_performance(
    question: str,
    df: pd.DataFrame,
    produits: list[str],
    machines: list[str],
    code_index: dict[str, str],
    metrics: list[ProductMachineMetrics],
) -> str:
    produit = match_produit(question, produits, code_index)
    machine = match_machine(question, machines)

    if not produit and not machine:
        return (
            "Je n'ai pas identifié de produit ou de machine dans votre question. "
            "Pouvez-vous préciser lequel vous intéresse ?"
        )

    if produit and machine:
        candidates = [m for m in metrics if m.produit == produit and m.machine == machine]
    elif machine:
        candidates = [m for m in metrics if m.machine == machine]
    else:
        candidates = [m for m in metrics if m.produit == produit]

    if not candidates:
        return f"Aucune donnée disponible pour {produit or ''} {machine or ''}.".strip()

    candidates_with_trs = [m for m in candidates if m.trs_moy is not None]
    if not candidates_with_trs:
        return "Historique insuffisant pour évaluer la performance de cet ensemble."

    worst = min(candidates_with_trs, key=lambda m: m.trs_moy)
    lines = [
        f"Pour {worst.produit} sur {worst.machine} : TRS moyen de {worst.trs_moy:.1f}% "
        f"sur {worst.n_of} OF analysé(s)."
    ]
    lines.extend(worst.conclusions)

    if len(candidates_with_trs) > 1:
        avg_trs = sum(m.trs_moy for m in candidates_with_trs) / len(candidates_with_trs)
        lines.append(
            f"\n(Sur l'ensemble des {len(candidates_with_trs)} couples correspondants, "
            f"TRS moyen global : {avg_trs:.1f}%.)"
        )
    return "\n".join(lines)


def respond_stable_machines(df: pd.DataFrame, min_of: int, top_n: int = 3) -> str:
    working = df[df["quality_severity"] != "BLOQUANT"].dropna(subset=["cadence_reelle"])

    stats = []
    for machine, group in working.groupby("machine"):
        n = len(group)
        if n < min_of:
            continue
        mean = group["cadence_reelle"].mean()
        std = group["cadence_reelle"].std()
        if mean and mean != 0 and not pd.isna(std):
            cv = float(std / mean * 100)
            stats.append((machine, cv, n))

    if not stats:
        return (
            f"Aucune machine n'a assez d'historique (minimum {min_of} OF) pour évaluer "
            "sa stabilité de façon fiable pour l'instant."
        )

    stats.sort(key=lambda x: x[1])
    top = stats[:top_n]

    lines = [f"Les {len(top)} machine(s) les plus stables (plus faible variation de cadence réelle) :"]
    for machine, cv, n in top:
        lines.append(f"  - {machine} : variation de {cv:.1f}% sur {n} OF")

    n_excluded = len({m for m in df['machine'].unique()}) - len(stats)
    if n_excluded > 0:
        lines.append(f"\n({n_excluded} machine(s) non évaluée(s), historique < {min_of} OF)")

    return "\n".join(lines)


def respond_trs_trend() -> str:
    return (
        "Je ne peux pas répondre de façon fiable à cette question pour l'instant : "
        "les exports actuels ('Détails Cadences') ne contiennent pas de date de production "
        "exploitable, donc je ne peux pas mesurer une évolution dans le temps. "
        "Il faudrait exploiter la feuille 'Détails Progressions' de vos exports (non "
        "encore intégrée à ce pipeline) ou ajouter un champ date pour permettre ce type "
        "d'analyse temporelle."
    )


def respond_unknown() -> str:
    return (
        "Je n'ai pas compris votre question. Je peux répondre à des questions comme :\n"
        "  - \"Quelle est la meilleure cadence pour le produit FL016 ?\"\n"
        "  - \"Pourquoi cette machine est-elle moins performante ?\"\n"
        "  - \"Quelles machines sont les plus stables ?\"\n"
        "  - \"Quelle cadence recommandes-tu pour ce couple produit/machine ?\""
    )
