"""
Vérification rapide : la base PostgreSQL (Docker ou autre) est-elle
accessible avec la configuration actuelle (config/settings.yaml + .env) ?

Usage :
    python check_db.py

Ne modifie rien en base — se contente d'ouvrir une connexion et de la fermer.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text

from src.load.db import get_engine
from src.utils.config import load_config


def main() -> int:
    config = load_config("config/settings.yaml")

    print(f"Connexion à postgresql://{config.database.user}@{config.database.host}:"
          f"{config.database.port}/{config.database.name} ...")

    try:
        engine = get_engine(config)
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version();")).scalar()
    except RuntimeError as exc:
        print(f"\n❌ {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\n❌ Connexion impossible : {exc}")
        print("\nVérifications possibles :")
        print("  - Le conteneur Docker tourne-t-il ? -> docker compose ps")
        print("  - Le port 5432 est-il bien exposé et libre sur votre machine ?")
        print("  - DB_PASSWORD dans .env correspond-il à celui de docker-compose.yml ?")
        return 1

    print(f"\n✅ Connexion réussie.")
    print(f"   {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())