"""
Point d'entrée : recommandation de cadence optimale par couple
Produit × Machine (Phase 7), à partir de l'historique en base.

Usage :
    python main_recommend.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.console import setup_console_encoding

setup_console_encoding()

from src.analytics.db_reader import load_history_dataframe
from src.anomalies.detector import detect_anomalies
from src.load.db import open_session
from src.recommend.recommendation_report import save
from src.recommend.recommender import recommend_cadences
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

    if df.empty:
        print("Aucune donnée en base. Lancez d'abord main_load.py ou main_load_batch.py.")
        return 1

    # Réutilise le détecteur d'anomalies de la Phase 6 pour exclure les OF
    # aberrants de la base de référence des recommandations.
    statistical_anomalies, _ = detect_anomalies(
        df, config.anomalies, exclude_bloquant=config.analytics.exclude_bloquant
    )

    recommendations = recommend_cadences(
        df, statistical_anomalies, config.recommendation, exclude_bloquant=config.analytics.exclude_bloquant
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path, json_path = save(recommendations, config.paths.reports_dir, f"recommendation_report_{timestamp}")

    n_fiables = sum(1 for r in recommendations if r.fiable)
    print(f"\n=== Recommandation de cadence — {len(recommendations)} couple(s) ===")
    print(f"✅ {n_fiables} recommandation(s) fiable(s)")
    print(f"⚪ {len(recommendations) - n_fiables} couple(s) avec historique insuffisant")

    for r in [r for r in recommendations if r.fiable][:5]:
        ecart = f"{r.ecart_vs_theorique_pct:+.1f}%" if r.ecart_vs_theorique_pct is not None else "N/A"
        print(f"  {r.produit[:35]:35s} | {r.machine[:25]:25s} | recommandé={r.cadence_recommandee:6.2f} "
              f"| théorique={_fmt(r.cadence_theorique_actuelle):>6s} | écart={ecart}")

    print(f"\nRapport complet : {md_path}")
    print(f"Rapport JSON     : {json_path}")
    print("\n✅ Recommandation terminée.")
    return 0


def _fmt(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "N/A"


if __name__ == "__main__":
    raise SystemExit(main())
