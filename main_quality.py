"""
Point d'entrée : extraction + contrôle qualité (Phase 2 + Phase 3).

Usage :
    python main_quality.py data/raw/export_production.xlsx

Produit :
    reports/quality_report_<timestamp>.md    (lisible par un humain)
    reports/quality_report_<timestamp>.json  (consommable par la Phase 4)

Code de sortie :
    0 si aucune anomalie BLOQUANTE
    1 si au moins une anomalie BLOQUANTE (utile pour une future intégration
      dans un pipeline automatisé / CI)
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.extract.excel_extractor import ExcelExtractor
from src.extract.exceptions import ExtractionError
from src.quality.quality_engine import QualityEngine
from src.utils.config import load_config
from src.utils.logger import setup_logger


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage : python main_quality.py <chemin_vers_export.xlsx>")
        return 1

    config = load_config("config/settings.yaml")
    logger = setup_logger(config)

    try:
        extractor = ExcelExtractor(config, logger=logger)
        result = extractor.extract(sys.argv[1])
    except ExtractionError as exc:
        logger.error(f"Échec de l'extraction : {exc}")
        return 1

    engine = QualityEngine(config, logger=logger)
    report = engine.run(result.dataframe, source_file=result.source_file.name)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path, json_path = report.save(config.paths.reports_dir, f"quality_report_{timestamp}")

    counts = report.count_by_severity()
    print(f"\n=== Rapport de qualité — {result.source_file.name} ===")
    print(f"🔴 Bloquant       : {counts['BLOQUANT']}")
    print(f"🟠 Avertissement  : {counts['AVERTISSEMENT']}")
    print(f"🔵 Info           : {counts['INFO']}")
    print(f"\nRapport détaillé : {md_path}")
    print(f"Rapport JSON      : {json_path}")

    if report.has_blocking_issues():
        print("\n⚠️  Anomalie(s) bloquante(s) détectée(s) — revue humaine requise avant historisation.")
        return 1

    print("\n✅ Aucune anomalie bloquante.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
