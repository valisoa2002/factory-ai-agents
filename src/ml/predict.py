"""
Prédiction avec mesure de confiance.

Astuce méthodologique : une RandomForest est un ensemble d'arbres. Plutôt
que de rajouter une infrastructure de calcul d'incertitude séparée, on
utilise directement la variance des prédictions individuelles de chaque
arbre — un ensemble d'arbres unanimes indique une prédiction fiable, un
ensemble dispersé indique une zone où le modèle est incertain (souvent
un couple Produit x Machine peu représenté dans les données d'entraînement).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline


@dataclass
class PredictionWithConfidence:
    prediction: float
    std: float             # écart-type entre les arbres -> proxy de confiance
    confidence_interval_95: tuple[float, float]


def predict_with_confidence(pipeline: Pipeline, X: pd.DataFrame) -> list[PredictionWithConfidence]:
    preprocessor = pipeline.named_steps["preprocess"]
    model = pipeline.named_steps["model"]

    X_transformed = preprocessor.transform(X)

    # Prédiction de chaque arbre individuellement
    tree_predictions = np.stack([tree.predict(X_transformed) for tree in model.estimators_], axis=1)

    means = tree_predictions.mean(axis=1)
    stds = tree_predictions.std(axis=1)

    results = []
    for mean, std in zip(means, stds):
        ci = (float(mean - 1.96 * std), float(mean + 1.96 * std))
        results.append(PredictionWithConfidence(prediction=float(mean), std=float(std), confidence_interval_95=ci))
    return results
