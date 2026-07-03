"""
Modèle d'une recommandation de cadence pour un couple Produit × Machine.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CadenceRecommendation:
    produit: str
    machine: str

    fiable: bool                       # False si historique insuffisant
    n_of_disponibles: int
    n_of_utilises: int                  # après exclusion BLOQUANT + anomalies
    n_of_reference: int                  # nombre d'OF utilisés pour la moyenne finale

    cadence_theorique_actuelle: float | None
    cadence_recommandee: float | None
    trs_moyen_reference: float | None    # TRS moyen des OF de référence utilisés

    ecart_vs_theorique_pct: float | None

    justification: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "produit": self.produit,
            "machine": self.machine,
            "fiable": self.fiable,
            "n_of_disponibles": self.n_of_disponibles,
            "n_of_utilises": self.n_of_utilises,
            "n_of_reference": self.n_of_reference,
            "cadence_theorique_actuelle": self.cadence_theorique_actuelle,
            "cadence_recommandee": self.cadence_recommandee,
            "trs_moyen_reference": self.trs_moyen_reference,
            "ecart_vs_theorique_pct": self.ecart_vs_theorique_pct,
            "justification": self.justification,
        }
