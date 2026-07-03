"""
Entraînement du modèle prédictif de cadence réelle, avec validation
croisée pour mesurer honnêtement sa fiabilité (pas un simple split
train/test, plus instable sur un volume encore modeste de données).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.ml.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES
from src.utils.config import MLConfig


@dataclass
class TrainingResult:
    pipeline: Pipeline
    cv_r2_mean: float
    cv_r2_std: float
    cv_mae_mean: float
    cv_mae_std: float
    n_rows_used: int
    n_folds: int

    def summary(self) -> str:
        return (
            f"R² = {self.cv_r2_mean:.2f} (± {self.cv_r2_std:.2f}) | "
            f"MAE = {self.cv_mae_mean:.2f} (± {self.cv_mae_std:.2f}) pcs/min "
            f"sur {self.n_folds} folds ({self.n_rows_used} lignes)"
        )


def build_pipeline(config: MLConfig) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
            ("num", "passthrough", NUMERIC_FEATURES),
        ]
    )
    model = RandomForestRegressor(
        n_estimators=config.n_estimators,
        random_state=config.random_state,
        n_jobs=-1,
    )
    return Pipeline(steps=[("preprocess", preprocessor), ("model", model)])


def train_with_cross_validation(X: pd.DataFrame, y: pd.Series, config: MLConfig) -> TrainingResult:
    """
    Entraîne le modèle final sur toutes les données, ET mesure sa
    fiabilité par validation croisée (K-fold) — deux choses distinctes :
    le modèle livré utilise tout l'historique disponible, mais les
    métriques de confiance reportées viennent de folds jamais vus par
    le modèle qui les a produits.
    """
    kf = KFold(n_splits=config.cv_folds, shuffle=True, random_state=config.random_state)

    r2_scores: list[float] = []
    mae_scores: list[float] = []

    for train_idx, test_idx in kf.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        fold_pipeline = build_pipeline(config)
        fold_pipeline.fit(X_train, y_train)
        preds = fold_pipeline.predict(X_test)

        r2_scores.append(r2_score(y_test, preds))
        mae_scores.append(mean_absolute_error(y_test, preds))

    # Modèle final : entraîné sur 100% des données, c'est celui qu'on livre
    final_pipeline = build_pipeline(config)
    final_pipeline.fit(X, y)

    return TrainingResult(
        pipeline=final_pipeline,
        cv_r2_mean=float(np.mean(r2_scores)),
        cv_r2_std=float(np.std(r2_scores)),
        cv_mae_mean=float(np.mean(mae_scores)),
        cv_mae_std=float(np.std(mae_scores)),
        n_rows_used=len(X),
        n_folds=config.cv_folds,
    )
