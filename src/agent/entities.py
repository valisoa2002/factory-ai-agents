"""
Extraction d'entités : quel produit ou quelle machine l'utilisateur
mentionne-t-il dans sa question en langage naturel ?

Approche volontairement simple (mots-clés + correspondance approximative),
pas un vrai NLU par LLM — suffisant pour un premier agent, amélioration
possible plus tard si le besoin s'en fait sentir.
"""

from __future__ import annotations

import difflib
import re

_CODE_PATTERN = re.compile(r"\[([^\]]+)\]")


def build_produit_index(produits: list[str]) -> dict[str, str]:
    """Associe chaque code produit (ex. 'FL016') à son libellé complet."""
    index = {}
    for p in produits:
        match = _CODE_PATTERN.search(p)
        if match:
            index[match.group(1).upper()] = p
    return index


def match_produit(question: str, produits: list[str], code_index: dict[str, str]) -> str | None:
    q_upper = question.upper()

    # 1. Correspondance par code produit explicite (ex. "FL016")
    for code, full in code_index.items():
        if code in q_upper:
            return full

    # 2. Correspondance par mot du libellé (ex. "shampooing", "vaisselle")
    q_lower = question.lower()
    for p in produits:
        description = _CODE_PATTERN.sub("", p).strip(" -").lower()
        words = [w for w in description.split() if len(w) > 4]
        if any(w in q_lower for w in words):
            return p

    # 3. Correspondance approximative en dernier recours
    close = difflib.get_close_matches(q_lower, [p.lower() for p in produits], n=1, cutoff=0.4)
    if close:
        idx = [p.lower() for p in produits].index(close[0])
        return produits[idx]

    return None


def match_machine(question: str, machines: list[str]) -> str | None:
    q_lower = question.lower()

    # Les noms de machine les plus longs d'abord, pour éviter qu'un nom
    # court ("Souffleuse") ne matche avant un nom plus précis.
    for m in sorted(machines, key=len, reverse=True):
        if m.lower() in q_lower:
            return m

    close = difflib.get_close_matches(q_lower, [m.lower() for m in machines], n=1, cutoff=0.4)
    if close:
        idx = [m.lower() for m in machines].index(close[0])
        return machines[idx]

    return None
