"""
Agrégation des anomalies en un rapport exploitable par un humain (Markdown)
et par les phases suivantes du pipeline (JSON).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.quality.models import Anomaly, Severity


@dataclass
class QualityReport:
    source_file: str
    n_rows_analyzed: int
    anomalies: list[Anomaly] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def count_by_severity(self) -> dict[str, int]:
        counts = {s.value: 0 for s in Severity}
        for a in self.anomalies:
            counts[a.severity.value] += 1
        return counts

    def has_blocking_issues(self) -> bool:
        return any(a.severity == Severity.BLOQUANT for a in self.anomalies)

    def to_markdown(self) -> str:
        counts = self.count_by_severity()
        lines = [
            f"# Rapport de qualité — {self.source_file}",
            f"\nGénéré le {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"\nLignes analysées : {self.n_rows_analyzed}",
            "\n## Résumé\n",
            "| Sévérité | Nombre |",
            "|---|---|",
            f"| 🔴 BLOQUANT | {counts['BLOQUANT']} |",
            f"| 🟠 AVERTISSEMENT | {counts['AVERTISSEMENT']} |",
            f"| 🔵 INFO | {counts['INFO']} |",
        ]

        if not self.anomalies:
            lines.append("\n✅ Aucune anomalie détectée.")
            return "\n".join(lines)

        for severity in (Severity.BLOQUANT, Severity.AVERTISSEMENT, Severity.INFO):
            group = [a for a in self.anomalies if a.severity == severity]
            if not group:
                continue
            icon = {"BLOQUANT": "🔴", "AVERTISSEMENT": "🟠", "INFO": "🔵"}[severity.value]
            lines.append(f"\n## {icon} {severity.value} ({len(group)})\n")
            lines.append("| Ligne | Code OF | Machine | Colonne | Règle | Message |")
            lines.append("|---|---|---|---|---|---|")
            for a in group:
                lines.append(
                    f"| {a.row_index} | {a.code_of or ''} | {a.machine or ''} | "
                    f"{a.column or ''} | {a.rule} | {a.message} |"
                )

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "source_file": self.source_file,
            "n_rows_analyzed": self.n_rows_analyzed,
            "generated_at": self.generated_at.isoformat(),
            "counts_by_severity": self.count_by_severity(),
            "anomalies": [a.to_dict() for a in self.anomalies],
        }

    def save(self, reports_dir: Path, basename: str) -> tuple[Path, Path]:
        """Écrit le rapport en .md et .json, retourne les deux chemins."""
        md_path = reports_dir / f"{basename}.md"
        json_path = reports_dir / f"{basename}.json"
        md_path.write_text(self.to_markdown(), encoding="utf-8")
        json_path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return md_path, json_path
