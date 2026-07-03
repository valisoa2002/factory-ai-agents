"""
Diagnostic : quelles règles de qualité génèrent le plus d'anomalies
BLOQUANT dans l'historique ? Aide à distinguer un vrai problème de
saisie récurrent d'un seuil de la Phase 3 mal calibré.

Usage :
    python diagnose_bloquant.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.console import setup_console_encoding

setup_console_encoding()

from src.load.db import open_session
from src.load.models import ProductionRecord
from src.utils.config import load_config


def main() -> int:
    config = load_config("config/settings.yaml")

    try:
        engine, session = open_session(config)
    except RuntimeError as exc:
        print(f"❌ {exc}")
        return 1

    rows = (
        session.query(ProductionRecord)
        .filter(ProductionRecord.quality_severity == "BLOQUANT")
        .all()
    )
    session.close()

    print(f"=== {len(rows)} ligne(s) BLOQUANT trouvée(s) ===\n")

    rule_counter: Counter[str] = Counter()
    column_counter: Counter[str] = Counter()
    examples: dict[str, dict] = {}

    for r in rows:
        if not r.quality_details:
            continue
        anomalies = json.loads(r.quality_details)
        for a in anomalies:
            if a["severity"] != "BLOQUANT":
                continue
            rule_counter[a["rule"]] += 1
            if a.get("column"):
                column_counter[a["column"]] += 1
            if a["rule"] not in examples:
                examples[a["rule"]] = {
                    "code_of": r.code_of,
                    "machine": r.machine,
                    "produit": r.produit,
                    "message": a["message"],
                }

    print("--- Répartition par règle déclenchée ---")
    for rule, count in rule_counter.most_common():
        pct = round(100 * count / len(rows), 1)
        print(f"  {rule:35s} : {count:4d} occurrence(s) ({pct}%)")
        ex = examples[rule]
        print(f"    Exemple : OF={ex['code_of']} | {ex['produit'][:40]} | {ex['machine']}")
        print(f"    -> {ex['message']}")
        print()

    print("--- Répartition par colonne concernée ---")
    for col, count in column_counter.most_common():
        print(f"  {col:35s} : {count:4d} occurrence(s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())