"""
Modèle des indicateurs agrégés par couple Produit × Machine.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProductMachineMetrics:
    produit: str
    machine: str

    n_of: int                          # nombre d'ordres de fabrication considérés (hors BLOQUANT exclus)
    n_excluded_bloquant: int             # nombre d'OF exclus car BLOQUANT

    cadence_theorique_moy: float | None
    cadence_reelle_moy: float | None
    cadence_reelle_min: float | None
    cadence_reelle_max: float | None
    ecart_moy: float | None

    trs_moy: float | None
    performance_moy: float | None
    disponibilite_moy: float | None
    qualite_moy: float | None

    stabilite_cv: float | None          # coefficient de variation (%) de la cadence réelle, None si n_of < 2

    conclusions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "produit": self.produit,
            "machine": self.machine,
            "n_of": self.n_of,
            "n_excluded_bloquant": self.n_excluded_bloquant,
            "cadence_theorique_moy": self.cadence_theorique_moy,
            "cadence_reelle_moy": self.cadence_reelle_moy,
            "cadence_reelle_min": self.cadence_reelle_min,
            "cadence_reelle_max": self.cadence_reelle_max,
            "ecart_moy": self.ecart_moy,
            "trs_moy": self.trs_moy,
            "performance_moy": self.performance_moy,
            "disponibilite_moy": self.disponibilite_moy,
            "qualite_moy": self.qualite_moy,
            "stabilite_cv": self.stabilite_cv,
            "conclusions": self.conclusions,
        }
