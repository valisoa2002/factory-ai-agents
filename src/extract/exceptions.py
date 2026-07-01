"""
Exceptions métier du module d'extraction.

Pourquoi des exceptions custom plutôt que des Exception génériques ?
- Elles rendent explicite la cause métier de l'échec (fichier absent,
  feuille absente, fichier corrompu) au lieu d'un simple KeyError/ValueError
  générique difficile à interpréter en production.
- Elles permettront, en Phase 3, de router chaque type d'erreur vers une
  entrée précise du rapport de qualité.
"""


class ExtractionError(Exception):
    """Erreur générique levée pendant l'extraction d'un fichier Excel."""


class FileNotFoundExtractionError(ExtractionError):
    """Le fichier Excel source est introuvable sur le disque."""


class SheetNotFoundError(ExtractionError):
    """La feuille attendue (ex. 'Détails Cadences') est absente du classeur."""


class CorruptedFileError(ExtractionError):
    """Le fichier existe mais ne peut pas être lu par openpyxl/pandas."""


class EmptySheetError(ExtractionError):
    """La feuille attendue existe mais ne contient aucune donnée exploitable."""
