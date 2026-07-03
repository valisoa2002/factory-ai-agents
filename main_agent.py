"""
Point d'entrée : agent conversationnel interactif (Phase 9).

Usage :
    python main_agent.py

Tapez vos questions, "quit" ou "exit" pour arrêter.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.console import setup_console_encoding

setup_console_encoding()

from src.agent.agent import CadenceAgent
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
        print("Aucune donnée en base. Lancez d'abord main_load.py ou main_load_batch.py.")
        return 1

    print(f"Agent Cadence/TRS prêt — {len(df)} lignes en historique, "
          f"{df['produit'].nunique()} produit(s), {df['machine'].nunique()} machine(s).")
    print("Posez vos questions (tapez 'quit' pour arrêter).\n")

    agent = CadenceAgent(df, config)

    while True:
        try:
            question = input("Vous > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nFin de la session.")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Fin de la session.")
            break

        answer = agent.answer(question)
        print(f"\nAgent > {answer}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
