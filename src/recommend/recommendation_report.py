"""
Export du rapport de recommandation de cadence.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.recommend.models import CadenceRecommendation


def to_markdown(recommendations: list[CadenceRecommendation]) -> str:
    fiables = [r for r in recommendations if r.fiable]
    non_fiables = [r for r in recommendations if not r.fiable]

    lines = [
        "# Rapport de recommandation de cadence — Produit x Machine",
        f"\nGénéré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"\n{len(fiables)} recommandation(s) fiable(s), {len(non_fiables)} couple(s) avec "
        "historique insuffisant.\n",
    ]

    if fiables:
        lines.append("## Recommandations\n")
        for r in fiables:
            lines.append(f"### {r.produit} — {r.machine}")
            lines.append(f"\n- Cadence théorique actuelle : {_fmt(r.cadence_theorique_actuelle)} pcs/min")
            lines.append(f"- **Cadence recommandée : {_fmt(r.cadence_recommandee)} pcs/min**")
            if r.ecart_vs_theorique_pct is not None:
                lines.append(f"- Écart vs théorique : {r.ecart_vs_theorique_pct:+.1f}%")
            lines.append(f"- Basée sur {r.n_of_reference} OF de référence (sur {r.n_of_utilises} exploitables, "
                          f"{r.n_of_disponibles} disponibles au total)")
            lines.append("\n**Justification :**")
            for j in r.justification:
                lines.append(f"- {j}")
            lines.append("")

    if non_fiables:
        lines.append("## Couples avec historique insuffisant (aucune recommandation)\n")
        lines.append("| Produit | Machine | OF exploitables | OF disponibles |")
        lines.append("|---|---|---|---|")
        for r in non_fiables:
            lines.append(f"| {r.produit} | {r.machine} | {r.n_of_utilises} | {r.n_of_disponibles} |")

    return "\n".join(lines)


def to_dict(recommendations: list[CadenceRecommendation]) -> dict:
    return {
        "generated_at": datetime.now().isoformat(),
        "n_couples": len(recommendations),
        "n_fiables": sum(1 for r in recommendations if r.fiable),
        "recommendations": [r.to_dict() for r in recommendations],
    }


def save(recommendations: list[CadenceRecommendation], reports_dir: Path, basename: str) -> tuple[Path, Path]:
    md_path = reports_dir / f"{basename}.md"
    json_path = reports_dir / f"{basename}.json"
    md_path.write_text(to_markdown(recommendations), encoding="utf-8")
    json_path.write_text(
        json.dumps(to_dict(recommendations), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return md_path, json_path


def _fmt(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "N/A"
