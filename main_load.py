"""
Point d'entrée : chaîne complète Extraction -> Qualité -> Historisation.

Usage :
    python main_load.py data/raw/export_production.xlsx

Prérequis :
    1. PostgreSQL démarré et accessible avec les paramètres de
       config/settings.yaml (section database:).
    2. Un fichier .env à la racine (copié depuis .env.example) contenant
       DB_PASSWORD=votre_mot_de_passe

Ce script est idempotent : le relancer sur le même fichier ne duplique
rien (déduplication sur la clé Code OF + Machine).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.console import setup_console_encoding

setup_console_encoding()

from src.extract.excel_extractor import ExcelExtractor
from src.extract.exceptions import ExtractionError
from src.load.db import open_session
from src.load.history_loader import HistoryLoader
from src.load.models import Base
from src.quality.quality_engine import QualityEngine
from src.utils.config import load_config
from src.utils.logger import setup_logger


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage : python main_load.py <chemin_vers_export.xlsx>")
        return 1

    config = load_config("config/settings.yaml")
    logger = setup_logger(config)

    # 1. Extraction
    try:
        extractor = ExcelExtractor(config, logger=logger)
        result = extractor.extract(sys.argv[1])
    except ExtractionError as exc:
        logger.error(f"Échec de l'extraction : {exc}")
        return 1

    # 2. Qualité
    engine_quality = QualityEngine(config, logger=logger)
    quality_report = engine_quality.run(result.dataframe, source_file=result.source_file.name)

    # 3. Historisation
    try:
        engine, session = open_session(config)
    except RuntimeError as exc:
        logger.error(str(exc))
        return 1

    try:
        Base.metadata.create_all(engine)  # idempotent : ne recrée rien si déjà présent
        loader = HistoryLoader(logger=logger)
        load_result = loader.load(
            session, result.dataframe, quality_report, source_file=result.source_file.name
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Échec du chargement en base : {exc}")
        session.rollback()
        return 1
    finally:
        session.close()

    counts = quality_report.count_by_severity()
    print(f"\n=== Résumé — {result.source_file.name} ===")
    print(f"Extraites   : {load_result.n_rows_extracted}")
    print(f"Insérées    : {load_result.n_rows_inserted}")
    print(f"Ignorées (déjà en base) : {load_result.n_rows_skipped_duplicate}")
    print(f"\nQualité — 🔴 {counts['BLOQUANT']}  🟠 {counts['AVERTISSEMENT']}  🔵 {counts['INFO']}")
    print("\n✅ Historisation terminée.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())