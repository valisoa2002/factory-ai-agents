"""
Diagnostic bas niveau : connexion psycopg2 directe, sans SQLAlchemy,
pour isoler un éventuel problème de négociation SSL (bug connu de
psycopg2-binary sur Windows produisant un message d'erreur vide).

Usage :
    python diagnose_pg.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.console import setup_console_encoding

setup_console_encoding()

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import psycopg2

password = os.getenv("DB_PASSWORD")
if not password:
    print("DB_PASSWORD manquant dans .env")
    sys.exit(1)

for sslmode in ("disable", "prefer", "require"):
    print(f"\n--- Tentative avec sslmode={sslmode} ---")
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname="cadence_trs",
            user="postgres",
            password=password,
            sslmode=sslmode,
            connect_timeout=5,
        )
        print(f"OK : connexion réussie avec sslmode={sslmode}")
        conn.close()
    except Exception as exc:  # noqa: BLE001
        print(f"ECHEC avec sslmode={sslmode}")
        print(f"  type       : {type(exc).__name__}")
        print(f"  repr       : {exc!r}")
        print(f"  args       : {exc.args}")
        print(f"  str        : '{exc}'")