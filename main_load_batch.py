"""
Chargement en lot : traite tous les fichiers .xlsx d'un dossier en une
seule commande (extraction -> qualité -> historisation pour chacun).

Usage :
    python main_load_batch.py data/raw/

Idempotent comme main_load.py : relancer sur des fichiers déjà chargés
ne duplique rien.
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
        print("Usage : python main_load_batch.py <dossier_contenant_les_xlsx>")
        return 1

    folder = Path(sys.argv[1])
    if not folder.is_dir():
        print(f"'{folder}' n'est pas un dossier valide.")
        return 1

    excel_files = sorted(folder.glob("*.xlsx"))
    if not excel_files:
        print(f"Aucun fichier .xlsx trouvé dans '{folder}'.")
        return 1

    config = load_config("config/settings.yaml")
    logger = setup_logger(config)

    try:
        engine, session = open_session(config)
    except RuntimeError as exc:
        logger.error(str(exc))
        return 1

    Base.metadata.create_all(engine)

    extractor = ExcelExtractor(config, logger=logger)
    quality_engine = QualityEngine(config, logger=logger)
    loader = HistoryLoader(logger=logger)

    total_extracted = total_inserted = total_skipped = total_errors = 0

    print(f"=== Chargement en lot de {len(excel_files)} fichier(s) ===\n")

    for file_path in excel_files:
        try:
            result = extractor.extract(file_path)
        except ExtractionError as exc:
            logger.error(f"[{file_path.name}] Échec extraction : {exc}")
            total_errors += 1
            continue

        quality_report = quality_engine.run(result.dataframe, source_file=result.source_file.name)

        try:
            load_result = loader.load(
                session, result.dataframe, quality_report, source_file=result.source_file.name
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[{file_path.name}] Échec chargement : {exc}")
            session.rollback()
            total_errors += 1
            continue

        counts = quality_report.count_by_severity()
        print(
            f"  {file_path.name:50s} | +{load_result.n_rows_inserted:3d} inséré(s) | "
            f"{load_result.n_rows_skipped_duplicate:3d} ignoré(s) | "
            f"qualité 🔴{counts['BLOQUANT']} 🟠{counts['AVERTISSEMENT']} 🔵{counts['INFO']}"
        )

        total_extracted += load_result.n_rows_extracted
        total_inserted += load_result.n_rows_inserted
        total_skipped += load_result.n_rows_skipped_duplicate

    session.close()

    print(f"\n=== Résumé global ===")
    print(f"Fichiers traités  : {len(excel_files) - total_errors}/{len(excel_files)}")
    print(f"Lignes extraites  : {total_extracted}")
    print(f"Lignes insérées   : {total_inserted}")
    print(f"Lignes ignorées   : {total_skipped} (déjà en base)")
    if total_errors:
        print(f"⚠️  {total_errors} fichier(s) en échec — voir logs/pipeline.log")

    print("\n✅ Chargement en lot terminé.")
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
