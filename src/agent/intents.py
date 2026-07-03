"""
Classification de l'intention d'une question en langage naturel.

Approche par mots-clés, volontairement simple et transparente : on
préfère un agent qui répond "je ne comprends pas" plutôt qu'un agent qui
devine mal silencieusement.
"""

from __future__ import annotations

from enum import Enum


class Intent(str, Enum):
    RECOMMEND_CADENCE = "RECOMMEND_CADENCE"
    WHY_LOW_PERFORMANCE = "WHY_LOW_PERFORMANCE"
    STABLE_MACHINES = "STABLE_MACHINES"
    TRS_TREND = "TRS_TREND"
    UNKNOWN = "UNKNOWN"


# Ordre de vérification important : du plus spécifique au plus général.
_RULES: list[tuple[Intent, list[str]]] = [
    (Intent.TRS_TREND, ["baisse", "évolution du trs", "tendance", "évolue"]),
    (Intent.STABLE_MACHINES, ["stable", "stables", "instable", "instables"]),
    (
        Intent.RECOMMEND_CADENCE,
        ["cadence recommand", "quelle cadence", "cadence optimale", "meilleure cadence", "recommandes-tu", "recommande"],
    ),
    (Intent.WHY_LOW_PERFORMANCE, ["pourquoi", "performant", "performance"]),
]


def classify_intent(question: str) -> Intent:
    q_lower = question.lower()
    for intent, keywords in _RULES:
        if any(kw in q_lower for kw in keywords):
            return intent
    return Intent.UNKNOWN
