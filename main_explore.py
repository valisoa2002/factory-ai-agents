"""
Point d'entrée : exploration d'un export Excel.

Usage :
    python main_explore.py data/raw/export_production.xlsx

Ce script ne fait PAS partie du pipeline final — c'est l'outil qu'on
utilise une seule fois (ou à chaque nouveau type d'export) pour construire
le dictionnaire de données avant d'écrire les règles de qualité (Phase 3).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.extract.exceptions import ExtractionError
from src.extract.schema_explorer import SchemaExplorer
from src.utils.config import load_config
from src.utils.logger import setup_logger


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage : python main_explore.py <chemin_vers_export.xlsx>")
        return 1

    file_path = sys.argv[1]

    config = load_config("config/settings.yaml")
    logger = setup_logger(config)

    try:
        explorer = SchemaExplorer(config, logger=logger)
        report_path = explorer.explore(file_path)
    except ExtractionError as exc:
        logger.error(f"Échec de l'exploration : {exc}")
        return 1

    print(f"\n✅ Rapport généré : {report_path}")
    print("→ Ouvrez-le, complétez la colonne 'Signification métier', et partagez-le")
    print("  moi pour qu'on construise ensemble le dictionnaire de données officiel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
