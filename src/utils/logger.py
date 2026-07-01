"""
Configuration centralisée du logging.

Pourquoi ne pas utiliser print() ?
- Un pipeline industriel doit produire des traces exploitables : niveau de
  gravité, horodatage, module d'origine.
- Les logs sont écrits à la fois en console (suivi en direct) et dans un
  fichier (audit, debug a posteriori, alimentation future d'un monitoring).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from src.utils.config import AppConfig


def setup_logger(config: AppConfig, name: str = "cadence_pipeline") -> logging.Logger:
    """
    Configure et retourne un logger prêt à l'emploi.

    Idempotent : appeler cette fonction plusieurs fois (ex. depuis
    différents modules) n'ajoute pas de handlers en double.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # déjà configuré

    logger.setLevel(config.logging.level)
    formatter = logging.Formatter(config.logging.format)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_file = Path(config.paths.logs_dir) / config.logging.file_name
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger
