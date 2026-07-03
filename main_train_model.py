"""
Point d'entrée : entraînement du modèle prédictif de cadence (Phase 8),
à partir de l'historique en base.

Usage :
    python main_train_model.py

Refuse d'entraîner si l'historique total est en-dessous du seuil
configuré (config.ml.min_total_rows_for_training) — un modèle entraîné
sur trop peu de données donnerait une fausse impression de fiabilité.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.console import setup_console_encoding

setup_console_encoding()

import joblib

from src.analytics.db_reader import load_history_dataframe
from src.load.db import open_session
from src.ml.explain import compute_shap_values, explain_single_prediction, global_feature_importance
from src.ml.features import prepare_training_data
from src.ml.ml_report import save
from src.ml.model import train_with_cross_validation
from src.ml.predict import predict_with_confidence
from src.utils.config import load_config
from src.utils.logger import setup_logger


def main() -> int:
    config = load_config("config/settings.yaml")
    logger = setup_logger(config)

    try:
        engine, session = open_session(config)
    except RuntimeError as exc:
        logger.error(str(exc))
        return 1

    try:
        df = load_history_dataframe(session)
    finally:
        session.close()

    X, y = prepare_training_data(df, exclude_bloquant=True)

    if len(X) < config.ml.min_total_rows_for_training:
        print(
            f"❌ Historique insuffisant pour l'entraînement : {len(X)} lignes exploitables, "
            f"minimum requis {config.ml.min_total_rows_for_training}.\n"
            "Chargez d'autres exports avec main_load_batch.py avant de réessayer."
        )
        return 1

    logger.info(f"Entraînement sur {len(X)} lignes exploitables (sur {len(df)} en base).")

    result = train_with_cross_validation(X, y, config.ml)
    logger.info(f"Résultat validation croisée : {result.summary()}")

    # Sauvegarde du modèle
    model_path = config.project_root / config.ml.model_output_path
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(result.pipeline, model_path)
    logger.info(f"Modèle sauvegardé : {model_path}")

    # Explicabilité SHAP sur un échantillon (jusqu'à 50 lignes, pour rester rapide)
    sample_X = X.head(min(50, len(X))).reset_index(drop=True)
    shap_values, feature_names = compute_shap_values(result.pipeline, sample_X)
    importance = global_feature_importance(shap_values, feature_names)

    # Quelques exemples de prédictions expliquées
    predictions = predict_with_confidence(result.pipeline, sample_X.head(3))
    example_explanations = []
    for i, pred in enumerate(predictions):
        explanations = explain_single_prediction(shap_values, feature_names, i)
        example_explanations.append(
            {
                "produit": sample_X.iloc[i]["produit"],
                "machine": sample_X.iloc[i]["machine"],
                "prediction": pred.prediction,
                "ci_low": pred.confidence_interval_95[0],
                "ci_high": pred.confidence_interval_95[1],
                "explanations": explanations,
            }
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path, json_path = save(result, importance, example_explanations, config.paths.reports_dir, f"ml_report_{timestamp}")

    print(f"\n=== Entraînement du modèle de cadence ===")
    print(result.summary())
    print(f"\nModèle sauvegardé : {model_path}")
    print(f"Rapport complet   : {md_path}")
    print(f"Rapport JSON      : {json_path}")
    print("\n✅ Entraînement terminé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
