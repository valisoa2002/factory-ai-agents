"""
Explicabilité du modèle via SHAP — traduit "pourquoi le modèle prédit
cette cadence" en contributions par feature, base de la future Phase 9
(l'agent devra pouvoir dire "parce que c'est cette machine" ou "parce
que la cadence théorique est élevée").
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import shap
from sklearn.pipeline import Pipeline


def compute_shap_values(pipeline: Pipeline, X: pd.DataFrame):
    preprocessor = pipeline.named_steps["preprocess"]
    model = pipeline.named_steps["model"]

    X_transformed = preprocessor.transform(X)
    feature_names = preprocessor.get_feature_names_out()

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_transformed)

    return shap_values, feature_names


def global_feature_importance(shap_values, feature_names, top_n: int = 10) -> list[tuple[str, float]]:
    """Importance moyenne (valeur absolue) de chaque feature sur tout le jeu de données."""
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    ranked = sorted(zip(feature_names, mean_abs_shap), key=lambda x: -x[1])
    return ranked[:top_n]


def explain_single_prediction(shap_values, feature_names, row_index: int, top_n: int = 3) -> list[str]:
    """
    Explication textuelle des N features qui ont le plus contribué à UNE
    prédiction précise — écarte le jargon, formule en langage naturel.
    """
    row_shap = shap_values[row_index]
    ranked_idx = np.argsort(-np.abs(row_shap))[:top_n]

    explanations = []
    for i in ranked_idx:
        name = _clean_feature_name(feature_names[i])
        contribution = row_shap[i]
        direction = "augmente" if contribution > 0 else "diminue"
        explanations.append(f"{name} {direction} la cadence prédite (impact : {contribution:+.2f} pcs/min)")
    return explanations


def _clean_feature_name(raw_name: str) -> str:
    """Transforme 'cat__machine_Souffleuse 1' en 'Machine = Souffleuse 1'."""
    name = raw_name.split("__", 1)[-1]
    for prefix, label in (("produit_", "Produit"), ("machine_", "Machine"), ("atelier_", "Atelier")):
        if name.startswith(prefix):
            return f"{label} = {name[len(prefix):]}"
    return {"cadence_theorique": "Cadence théorique", "qte_produite": "Quantité produite"}.get(name, name)
