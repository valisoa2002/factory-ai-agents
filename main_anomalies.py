"""
Point d'entrée : détection d'anomalies statistiques (Phase 6), à partir
de l'historique en base.

Usage :
    python main_anomalies.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.console import setup_console_encoding

setup_console_encoding()

from src.analytics.db_reader import load_history_dataframe
from src.anomalies.anomaly_report import save
from src.anomalies.detector import detect_anomalies
from src.load.db import open_session
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
        print("Aucune donnée en base. Lancez d'abord main_load.py sur au moins un export.")
        return 1

    anomalies, insufficient = detect_anomalies(df, config.anomalies, exclude_bloquant=config.analytics.exclude_bloquant)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path, json_path = save(anomalies, insufficient, config.paths.reports_dir, f"anomaly_report_{timestamp}")

    print(f"\n=== Détection d'anomalies statistiques ===")
    print(f"🔍 {len(anomalies)} anomalie(s) détectée(s)")
    print(f"⚪ {len(insufficient)} couple(s) avec historique insuffisant (< "
          f"{config.anomalies.min_of_for_stat_detection} OF)")

    for a in sorted(anomalies, key=lambda x: -abs(x.z_score))[:5]:
        print(f"  {a.code_of} | {a.produit[:35]:35s} | {a.machine[:25]:25s} | {a.message}")

    print(f"\nRapport complet : {md_path}")
    print(f"Rapport JSON     : {json_path}")
    print("\n✅ Détection terminée.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
