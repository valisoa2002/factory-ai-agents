"""
Export du rapport de détection d'anomalies statistiques.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.anomalies.models import InsufficientHistory, RowAnomaly


def to_markdown(anomalies: list[RowAnomaly], insufficient: list[InsufficientHistory]) -> str:
    lines = [
        "# Rapport de détection d'anomalies statistiques",
        f"\nGénéré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"\n{len(anomalies)} anomalie(s) statistique(s) détectée(s) sur "
        f"{len({(a.produit, a.machine) for a in anomalies})} couple(s) concerné(s).",
        f"\n{len(insufficient)} couple(s) avec historique insuffisant pour une détection fiable.",
    ]

    if anomalies:
        lines.append("\n## Anomalies détectées\n")
        lines.append("| Code OF | Produit | Machine | Métrique | Valeur | Moyenne du couple | Z-score | Message |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for a in sorted(anomalies, key=lambda x: -abs(x.z_score)):
            lines.append(
                f"| {a.code_of} | {a.produit} | {a.machine} | {a.metric} | {a.value:.2f} | "
                f"{a.group_mean:.2f} | {a.z_score:.2f} | {a.message} |"
            )

    if insufficient:
        lines.append("\n## Couples avec historique insuffisant (non analysés statistiquement)\n")
        lines.append("| Produit | Machine | OF disponibles | Minimum requis |")
        lines.append("|---|---|---|---|")
        for i in insufficient:
            lines.append(f"| {i.produit} | {i.machine} | {i.n_of} | {i.min_required} |")

    if not anomalies and not insufficient:
        lines.append("\n✅ Aucune anomalie statistique détectée, historique suffisant partout.")

    return "\n".join(lines)


def to_dict(anomalies: list[RowAnomaly], insufficient: list[InsufficientHistory]) -> dict:
    return {
        "generated_at": datetime.now().isoformat(),
        "n_anomalies": len(anomalies),
        "n_insufficient_history": len(insufficient),
        "anomalies": [a.to_dict() for a in anomalies],
        "insufficient_history": [
            {"produit": i.produit, "machine": i.machine, "n_of": i.n_of, "min_required": i.min_required}
            for i in insufficient
        ],
    }


def save(
    anomalies: list[RowAnomaly],
    insufficient: list[InsufficientHistory],
    reports_dir: Path,
    basename: str,
) -> tuple[Path, Path]:
    md_path = reports_dir / f"{basename}.md"
    json_path = reports_dir / f"{basename}.json"
    md_path.write_text(to_markdown(anomalies, insufficient), encoding="utf-8")
    json_path.write_text(
        json.dumps(to_dict(anomalies, insufficient), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return md_path, json_path
