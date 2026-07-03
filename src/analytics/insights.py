"""
Génération de conclusions automatiques en langage naturel à partir des
indicateurs calculés — c'est la première brique du futur "agent IA"
(Phase 9) : traduire des chiffres en phrases compréhensibles par un
responsable production.

Chaque règle est indépendante et documente sa propre condition — facilite
l'ajout de nouvelles règles sans toucher aux existantes.
"""

from __future__ import annotations

from src.utils.config import AnalyticsConfig


def generate_conclusions(
    n_of: int,
    n_excluded_bloquant: int,
    trs_moy: float | None,
    stabilite_cv: float | None,
    config: AnalyticsConfig,
) -> list[str]:
    conclusions: list[str] = []

    # Fiabilité de l'historique — toujours en premier, ça conditionne la
    # confiance à accorder aux conclusions suivantes.
    if n_of < config.min_of_for_confidence:
        conclusions.append(
            f"Historique limité ({n_of} OF) — conclusions à confirmer avec plus de données."
        )

    if n_excluded_bloquant > 0:
        conclusions.append(
            f"{n_excluded_bloquant} OF exclu(s) du calcul car données bloquantes en qualité "
            "(voir rapport de qualité pour le détail)."
        )

    # Niveau de TRS
    if trs_moy is not None:
        if trs_moy < config.trs_low_threshold:
            conclusions.append(
                f"TRS moyen faible ({trs_moy:.1f}%) — ce couple Produit x Machine mérite "
                "une investigation prioritaire."
            )
        elif trs_moy < config.trs_good_threshold:
            conclusions.append(f"TRS moyen modéré ({trs_moy:.1f}%) — marge de progression identifiée.")
        else:
            conclusions.append(f"Bon TRS moyen ({trs_moy:.1f}%).")

    # Stabilité de la cadence
    if stabilite_cv is not None:
        if stabilite_cv > config.stability_cv_threshold:
            conclusions.append(
                f"Cadence instable (variation de {stabilite_cv:.1f}% autour de la moyenne) — "
                "possible irrégularité machine, produit, ou cadence théorique mal calibrée."
            )
        else:
            conclusions.append(f"Cadence stable d'un OF à l'autre (variation de {stabilite_cv:.1f}%).")

    if not conclusions:
        conclusions.append("Aucune anomalie notable détectée sur ce couple.")

    return conclusions
