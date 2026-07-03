"""
Connexion à la base PostgreSQL.

Le mot de passe n'est JAMAIS lu depuis settings.yaml : il vient de la
variable d'environnement DB_PASSWORD, chargée depuis un fichier .env
(voir .env.example). C'est la seule donnée sensible du projet — elle ne
doit jamais être committée dans Git (déjà exclue par .gitignore).
"""

from __future__ import annotations

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.utils.config import AppConfig


def build_connection_url(config: AppConfig) -> str:
    load_dotenv(config.project_root / ".env")  # silencieux si le fichier n'existe pas
    password = os.getenv("DB_PASSWORD")
    if not password:
        raise RuntimeError(
            "Variable d'environnement DB_PASSWORD manquante. "
            "Copiez .env.example vers .env et renseignez votre mot de passe PostgreSQL."
        )
    db = config.database
    # quote_plus échappe les caractères spéciaux (@, :, /, %, #...) qui
    # casseraient sinon le format de l'URL de connexion.
    safe_password = quote_plus(password)
    # Pilote pg8000 : 100% Python, sans DLL compilée. Choisi après un bug
    # récurrent de psycopg2-binary sous Windows (messages d'erreur vides
    # dus à un conflit de DLL OpenSSL — voir diagnose_pg.py de la Phase 4).
    return f"postgresql+pg8000://{db.user}:{safe_password}@{db.host}:{db.port}/{db.name}"


def get_engine(config: AppConfig) -> Engine:
    return create_engine(build_connection_url(config), pool_pre_ping=True)


def get_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine)


def open_session(config: AppConfig) -> tuple[Engine, Session]:
    """Raccourci : crée l'engine et ouvre une session en un appel."""
    engine = get_engine(config)
    session_factory = get_session_factory(engine)
    return engine, session_factory()