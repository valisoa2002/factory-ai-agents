"""
Modèle d'une anomalie statistique détectée au niveau d'un OF individuel,
par comparaison à l'historique de son propre couple Produit × Machine.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RowAnomaly:
    code_of: str
    produit: str
    machine: str
    metric: str          # ex. "cadence_reelle", "trs_pct"
    value: float
    group_mean: float
    group_std: float
    z_score: float
    message: str

    def to_dict(self) -> dict:
        return {
            "code_of": self.code_of,
            "produit": self.produit,
            "machine": self.machine,
            "metric": self.metric,
            "value": round(self.value, 2),
            "group_mean": round(self.group_mean, 2),
            "group_std": round(self.group_std, 2),
            "z_score": round(self.z_score, 2),
            "message": self.message,
        }


@dataclass
class InsufficientHistory:
    produit: str
    machine: str
    n_of: int
    min_required: int
