"""
Chargement et validation de la configuration du pipeline.

Pourquoi un module dédié plutôt qu'un simple yaml.safe_load() dispersé
dans le code ?
- Un seul point d'accès à la configuration (pas de chemins codés en dur).
- Typage fort via des dataclasses : les erreurs de config (clé manquante,
  mauvais type) sont détectées au démarrage, pas au milieu d'un traitement.
- Facilite les tests (on peut injecter une AppConfig factice).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ExcelConfig:
    required_sheet: str
    header_row: int = 0


@dataclass(frozen=True)
class PathsConfig:
    raw_data_dir: Path
    processed_data_dir: Path
    reports_dir: Path
    logs_dir: Path


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    format: str
    file_name: str


@dataclass(frozen=True)
class ExtractionConfig:
    add_technical_columns: bool = True


@dataclass(frozen=True)
class QualityConfig:
    formula_tolerance: dict  # {"temps_net": 0.5, "ecart": 1.0, "trs": 1.0}
    percentage_tolerance: float = 1.0
    min_plausible_cadence_theorique: float = 0.5
    performance_ceiling: dict = field(default_factory=lambda: {"warning_max": 100, "blocking_max": 120})
    trs_ceiling: dict = field(default_factory=lambda: {"warning_max": 100, "blocking_max": 120})


@dataclass(frozen=True)
class AppConfig:
    excel: ExcelConfig
    paths: PathsConfig
    logging: LoggingConfig
    extraction: ExtractionConfig
    quality: QualityConfig
    project_root: Path

    def ensure_directories(self) -> None:
        """Crée les dossiers nécessaires (idempotent)."""
        for directory in (
            self.paths.raw_data_dir,
            self.paths.processed_data_dir,
            self.paths.reports_dir,
            self.paths.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def load_config(config_path: str | Path = "config/settings.yaml") -> AppConfig:
    """
    Charge settings.yaml et retourne un objet AppConfig typé.

    Les chemins relatifs du YAML sont résolus par rapport à la racine du
    projet (dossier parent de config/), pour que le pipeline fonctionne
    quel que soit le répertoire courant depuis lequel il est lancé.
    """
    config_path = Path(config_path).resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Fichier de configuration introuvable : {config_path}")

    project_root = config_path.parent.parent

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    excel = ExcelConfig(**raw["excel"])

    paths_raw = raw["paths"]
    paths = PathsConfig(
        raw_data_dir=project_root / paths_raw["raw_data_dir"],
        processed_data_dir=project_root / paths_raw["processed_data_dir"],
        reports_dir=project_root / paths_raw["reports_dir"],
        logs_dir=project_root / paths_raw["logs_dir"],
    )

    logging_cfg = LoggingConfig(**raw["logging"])
    extraction_cfg = ExtractionConfig(**raw.get("extraction", {}))
    quality_cfg = QualityConfig(**raw.get("quality", {"formula_tolerance": {}}))

    config = AppConfig(
        excel=excel,
        paths=paths,
        logging=logging_cfg,
        extraction=extraction_cfg,
        quality=quality_cfg,
        project_root=project_root,
    )
    config.ensure_directories()
    return config