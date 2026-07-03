"""
Correctif d'encodage console pour Windows.

PowerShell utilise souvent l'encodage cp1252 par défaut, incapable
d'afficher les emojis (✅, ❌, 🔴, 🟠, 🔵) utilisés dans les messages du
pipeline. Sans ce correctif, un print() contenant un emoji fait planter
le script avec UnicodeEncodeError — ce qui, pire, écrase le message
qu'on cherchait justement à afficher (c'est ce qui s'est produit avec
check_connection.py : l'erreur PostgreSQL réelle était masquée par ce
crash d'encodage).

À appeler en tout premier, avant le moindre print(), dans chaque script
d'entrée (main_*.py, check_db.py).
"""

from __future__ import annotations

import sys


def setup_console_encoding() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass  # environnement où reconfigure() n'est pas supporté : on continue sans planter