"""
Modèle de données commun à toutes les règles de qualité.

Chaque règle (completeness, uniqueness, consistency, plausibility) retourne
une liste d'objets `Anomaly`. C'est ce contrat commun qui permet à
`quality_engine.py` d'agréger les résultats de règles complètement
indépendantes sans qu'elles aient besoin de se connaître entre elles.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    """
    Gravité d'une anomalie.

    BLOQUANT      : la ligne ne doit pas être historisée/utilisée en l'état
                    (ex. TRS > 100%, valeur négative, doublon de clé).
    AVERTISSEMENT : la ligne est utilisable mais mérite une revue humaine
                    (ex. cadence théorique suspecte, écart de formule).
    INFO          : cas normal identifié mais notable (ex. Cadence Réelle
                    manquante parce que Qté Produite = 0).
    """

    BLOQUANT = "BLOQUANT"
    AVERTISSEMENT = "AVERTISSEMENT"
    INFO = "INFO"


@dataclass
class Anomaly:
    rule: str                  # nom technique de la règle, ex. "trs_out_of_bounds"
    severity: Severity
    message: str                # message lisible par un humain
    row_index: int | None = None
    code_of: str | None = None
    machine: str | None = None
    column: str | None = None

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": self.severity.value,
            "message": self.message,
            "row_index": self.row_index,
            "code_of": self.code_of,
            "machine": self.machine,
            "column": self.column,
        }
