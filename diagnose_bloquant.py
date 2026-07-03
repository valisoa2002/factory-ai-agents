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

    # Liste actionnable : couples Produit x Machine avec cadence théorique
    # suspecte, à transmettre à l'équipe méthodes/production.
    suspects = []
    for r in rows:
        if not r.quality_details:
            continue
        anomalies = json.loads(r.quality_details)
        has_ceiling_issue = any(
            a["rule"] == "percentage_ceiling_exceeded" and a["severity"] == "BLOQUANT" for a in anomalies
        )
        if has_ceiling_issue:
            suspects.append(
                {
                    "code_of": r.code_of,
                    "produit": r.produit,
                    "machine": r.machine,
                    "cadence_theorique_saisie": r.cadence_theorique,
                    "cadence_reelle_observee": r.cadence_reelle,
                }
            )

    if suspects:
        print(f"\n--- {len(suspects)} ligne(s) à cadence théorique probablement erronée ---")
        print(f"{'Code OF':20s} | {'Produit':45s} | {'Machine':30s} | {'Théo. saisie':>12s} | {'Réelle obs.':>12s}")
        for s in suspects:
            print(
                f"{s['code_of']:20s} | {s['produit'][:45]:45s} | {s['machine'][:30]:30s} | "
                f"{s['cadence_theorique_saisie']:12.2f} | {s['cadence_reelle_observee'] or 0:12.2f}"
            )

        report_path = config.paths.reports_dir / "cadence_theorique_a_corriger.csv"
        import csv
        with open(report_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(suspects[0].keys()))
            writer.writeheader()
            writer.writerows(suspects)
        print(f"\n📄 Liste exportée pour l'atelier : {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())