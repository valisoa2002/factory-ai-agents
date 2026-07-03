"""
Export du rapport d'entraînement du modèle ML.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.ml.model import TrainingResult


def to_markdown(
    result: TrainingResult,
    feature_importance: list[tuple[str, float]],
    example_explanations: list[dict],
) -> str:
    lines = [
        "# Rapport d'entraînement — modèle de prédiction de cadence",
        f"\nGénéré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"\n## Fiabilité du modèle (validation croisée, {result.n_folds} folds)\n",
        f"- Lignes utilisées : {result.n_rows_used}",
        f"- R² moyen : {result.cv_r2_mean:.3f} (± {result.cv_r2_std:.3f})",
        f"- Erreur absolue moyenne (MAE) : {result.cv_mae_mean:.2f} pcs/min (± {result.cv_mae_std:.2f})",
        "\n*R² proche de 1 = bonnes prédictions ; proche de 0 ou négatif = le modèle ne fait pas "
        "mieux qu'une moyenne. Un écart-type élevé entre folds signale un modèle encore instable "
        "faute de données suffisantes par couple Produit x Machine.*",
        "\n## Importance des variables (moyenne SHAP)\n",
        "| Variable | Importance moyenne |",
        "|---|---|",
    ]
    for name, importance in feature_importance:
        lines.append(f"| {name} | {importance:.3f} |")

    if example_explanations:
        lines.append("\n## Exemples de prédictions expliquées\n")
        for ex in example_explanations:
            lines.append(f"### {ex['produit']} — {ex['machine']}")
            lines.append(f"- Cadence prédite : {ex['prediction']:.2f} pcs/min "
                          f"(intervalle 95% : {ex['ci_low']:.2f} – {ex['ci_high']:.2f})")
            lines.append("- Facteurs déterminants :")
            for e in ex["explanations"]:
                lines.append(f"  - {e}")
            lines.append("")

    return "\n".join(lines)


def to_dict(result: TrainingResult, feature_importance: list[tuple[str, float]], example_explanations: list[dict]) -> dict:
    return {
        "generated_at": datetime.now().isoformat(),
        "n_rows_used": result.n_rows_used,
        "n_folds": result.n_folds,
        "cv_r2_mean": result.cv_r2_mean,
        "cv_r2_std": result.cv_r2_std,
        "cv_mae_mean": result.cv_mae_mean,
        "cv_mae_std": result.cv_mae_std,
        "feature_importance": [{"feature": n, "importance": float(i)} for n, i in feature_importance],
        "example_explanations": example_explanations,
    }


def save(
    result: TrainingResult,
    feature_importance: list[tuple[str, float]],
    example_explanations: list[dict],
    reports_dir: Path,
    basename: str,
) -> tuple[Path, Path]:
    md_path = reports_dir / f"{basename}.md"
    json_path = reports_dir / f"{basename}.json"
    md_path.write_text(to_markdown(result, feature_importance, example_explanations), encoding="utf-8")
    json_path.write_text(
        json.dumps(to_dict(result, feature_importance, example_explanations), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return md_path, json_path
