"""
Définitions des outils exposés au LLM (function calling / tool use).

Principe non négociable : le LLM ne fait QUE choisir quel outil appeler et
avec quels arguments (produit/machine mentionnés) ; c'est TOUJOURS le
code Python de ces outils qui calcule le vrai chiffre, à partir des
modules déjà validés (Phases 5, 6, 7, 8). Le LLM reformule ensuite le
résultat en langage naturel, mais ne peut jamais inventer un chiffre —
il n'a accès qu'à ce que l'outil lui retourne.
"""

from __future__ import annotations

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_cadence_recommendation",
            "description": (
                "Retourne la cadence de production recommandée pour un couple "
                "produit/machine, basée sur l'historique réel de fabrication "
                "(pas une estimation théorique). Utiliser pour toute question "
                "sur la 'meilleure cadence', la 'cadence optimale', ou "
                "'quelle cadence recommandes-tu'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "produit": {
                        "type": "string",
                        "description": "Nom, mot-clé ou code du produit mentionné dans la question (laisser vide si non mentionné).",
                    },
                    "machine": {
                        "type": "string",
                        "description": "Nom ou mot-clé de la machine mentionnée dans la question (laisser vide si non mentionnée).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_performance_analysis",
            "description": (
                "Retourne le TRS moyen, la stabilité et les conclusions d'analyse "
                "pour un produit et/ou une machine. Utiliser pour toute question du "
                "type 'pourquoi cette machine/ce produit est-elle/il moins performant(e)', "
                "'quel est le TRS de...', ou pour comparer des performances."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "produit": {
                        "type": "string",
                        "description": "Nom, mot-clé ou code du produit mentionné (laisser vide si non mentionné).",
                    },
                    "machine": {
                        "type": "string",
                        "description": "Nom ou mot-clé de la machine mentionnée (laisser vide si non mentionnée).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stability_ranking",
            "description": (
                "Retourne le classement des machines par stabilité de cadence "
                "(du plus stable au moins stable). Utiliser pour toute question sur "
                "quelles machines sont stables/instables, régulières/irrégulières."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ml_prediction",
            "description": (
                "Retourne une prédiction de cadence réelle par Machine Learning pour "
                "un couple produit/machine, avec un intervalle de confiance et les "
                "facteurs explicatifs (SHAP). Utiliser en complément de "
                "get_cadence_recommendation quand l'utilisateur demande explicitement "
                "une prédiction, une estimation par IA, ou 'que prédit le modèle'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "produit": {"type": "string", "description": "Produit concerné."},
                    "machine": {"type": "string", "description": "Machine concernée."},
                    "cadence_theorique": {
                        "type": "number",
                        "description": "Cadence théorique à utiliser pour la prédiction, si mentionnée.",
                    },
                },
                "required": ["produit", "machine"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trend_analysis",
            "description": (
                "Tente une analyse de tendance temporelle (ex. évolution du TRS dans "
                "le temps). Utiliser pour toute question contenant 'évolution', "
                "'tendance', 'baisse', 'augmente au fil du temps'."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]
