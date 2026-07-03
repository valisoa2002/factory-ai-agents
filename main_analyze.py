"""
Point d'entrée : analyse des cadences par couple Produit × Machine
(Phase 5), à partir de l'historique déjà chargé en base (Phase 4).

Usage :
    python main_analyze.py

Ne prend pas de fichier Excel en argument : contrairement aux phases
précédentes, celle-ci lit TOUT l'historique en base, pas un seul export.
C'est tout l'intérêt de l'avoir historisé.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.console import setup_console_encoding

setup_console_encoding()

from src.analytics.aggregator import compute_metrics
from src.analytics.analytics_report import save
from src.analytics.db_reader import load_history_dataframe
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

    metrics = compute_metrics(df, config.analytics)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path, json_path = save(metrics, config.paths.reports_dir, f"analytics_report_{timestamp}")

    print(f"\n=== Analyse des cadences — {len(metrics)} couple(s) Produit x Machine ===\n")

    # Aperçu console : les 5 couples les plus problématiques (déjà triés par TRS croissant)
    for m in metrics[:5]:
        trs = f"{m.trs_moy:.1f}%" if m.trs_moy is not None else "N/A"
        print(f"  {m.produit[:40]:40s} | {m.machine[:30]:30s} | TRS={trs:>8s} | {m.n_of} OF")

    print(f"\nRapport complet : {md_path}")
    print(f"Rapport JSON     : {json_path}")
    print("\n✅ Analyse terminée.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
