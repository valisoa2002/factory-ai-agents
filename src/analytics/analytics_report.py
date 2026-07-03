"""
Export des indicateurs calculés en rapport Markdown (lecture humaine) et
JSON (consommable par Power BI, un futur agent IA, ou tout autre outil).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.analytics.models import ProductMachineMetrics


def to_markdown(metrics: list[ProductMachineMetrics]) -> str:
    lines = [
        "# Rapport d'analyse des cadences — Produit x Machine",
        f"\nGénéré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"\n{len(metrics)} couple(s) Produit x Machine analysé(s).",
        "\nTriés par TRS moyen croissant (les plus problématiques en premier).\n",
    ]

    for m in metrics:
        lines.append(f"## {m.produit} — {m.machine}")
        lines.append(f"\n- OF analysés : {m.n_of}"
                      + (f" ({m.n_excluded_bloquant} exclu(s) pour qualité bloquante)" if m.n_excluded_bloquant else ""))
        lines.append(f"- Cadence théorique moyenne : {_fmt(m.cadence_theorique_moy)} pcs/min")
        lines.append(f"- Cadence réelle moyenne : {_fmt(m.cadence_reelle_moy)} pcs/min "
                      f"(min {_fmt(m.cadence_reelle_min)} / max {_fmt(m.cadence_reelle_max)})")
        lines.append(f"- Écart moyen : {_fmt(m.ecart_moy)}%")
        lines.append(f"- TRS moyen : {_fmt(m.trs_moy)}%")
        lines.append(f"- Performance moyenne : {_fmt(m.performance_moy)}%")
        lines.append(f"- Disponibilité moyenne : {_fmt(m.disponibilite_moy)}%")
        lines.append(f"- Qualité moyenne : {_fmt(m.qualite_moy)}%")
        lines.append(f"- Stabilité (coefficient de variation) : "
                      f"{_fmt(m.stabilite_cv) + '%' if m.stabilite_cv is not None else 'insuffisant (< 2 OF)'}")
        lines.append("\n**Conclusions automatiques :**")
        for c in m.conclusions:
            lines.append(f"- {c}")
        lines.append("")

    return "\n".join(lines)


def to_dict(metrics: list[ProductMachineMetrics]) -> dict:
    return {
        "generated_at": datetime.now().isoformat(),
        "n_couples": len(metrics),
        "metrics": [m.to_dict() for m in metrics],
    }


def save(metrics: list[ProductMachineMetrics], reports_dir: Path, basename: str) -> tuple[Path, Path]:
    md_path = reports_dir / f"{basename}.md"
    json_path = reports_dir / f"{basename}.json"
    md_path.write_text(to_markdown(metrics), encoding="utf-8")
    json_path.write_text(json.dumps(to_dict(metrics), ensure_ascii=False, indent=2), encoding="utf-8")
    return md_path, json_path


def _fmt(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "N/A"
