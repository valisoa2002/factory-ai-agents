"""
Schéma de données de la feuille "Détails Cadences" — VERROUILLÉ.

Ce module est la traduction en code du dictionnaire de données validé le
2026-07-01 sur l'export réel `Rapport_Production_1782880266815.xlsx`
(38 lignes × 17 colonnes) via `validate_formulas.py`.

Toute règle de qualité (Phase 3) DOIT référencer les colonnes via ces
constantes plutôt que ré-écrire les chaînes littérales — ça centralise
le seul endroit à modifier si un futur export renomme une colonne.

Formules confirmées empiriquement (voir validate_formulas.py) :
    Temps Net (min)  = Durée Totale (min) - Durée Arrêts (min)     [exact, 38/38]
    Écart (%)        = (Cadence Réelle - Cadence Théorique)
                        / Cadence Théorique * 100                  [37/38, 1 anomalie source]
    TRS (%)          = Disponibilité (%) * Performance (%)
                        * Qualité (%) / 10000                      [exact, 38/38]

Particularités métier découvertes sur données réelles :
    - La clé unique d'une ligne est (Code OF, Machine), PAS Code OF seul :
      un même OF peut être décomposé par étape (ex. "_FARDELEUSE",
      "_REMPLISSEUSE") quand plusieurs machines interviennent.
    - Cadence Réelle peut être manquante (NaN) sans que ce soit une erreur,
      SI Qté Produite = 0 (rien n'a été produit sur cet OF).
"""

from __future__ import annotations

# --- Noms de colonnes exacts de l'export -----------------------------------

COL_CODE_OF = "Code OF"
COL_PRODUIT = "Produit"
COL_ATELIER = "Atelier"
COL_MACHINE = "Machine"
COL_QTE_PRODUITE = "Qté Produite"
COL_DUREE_TOTALE = "Durée Totale (min)"
COL_DUREE_ARRETS = "Durée Arrêts (min)"
COL_TEMPS_NET = "Temps Net (min)"
COL_CADENCE_REELLE = "Cadence Réelle (pcs/min)"
COL_CADENCE_THEORIQUE = "Cadence Théorique (pcs/min)"
COL_ECART = "Écart (%)"
COL_DISPONIBILITE = "Disponibilité (%)"
COL_PERFORMANCE = "Performance (%)"
COL_QUALITE = "Qualité (%)"
COL_TRS = "TRS (%)"

# Colonnes techniques ajoutées par notre propre ExcelExtractor
# (jamais issues de l'export lui-même — jamais soumises aux règles métier)
COL_SOURCE_FILE = "_source_file"
COL_EXTRACTED_AT = "_extracted_at"

# --- Regroupements utilisés par le moteur de qualité ------------------------

REQUIRED_COLUMNS: list[str] = [
    COL_CODE_OF,
    COL_PRODUIT,
    COL_ATELIER,
    COL_MACHINE,
    COL_QTE_PRODUITE,
    COL_DUREE_TOTALE,
    COL_DUREE_ARRETS,
    COL_TEMPS_NET,
    COL_CADENCE_REELLE,
    COL_CADENCE_THEORIQUE,
    COL_ECART,
    COL_DISPONIBILITE,
    COL_PERFORMANCE,
    COL_QUALITE,
    COL_TRS,
]

# Clé métier réelle d'une ligne (voir découverte ci-dessus)
KEY_COLUMNS: list[str] = [COL_CODE_OF, COL_MACHINE]

# Colonnes exprimées en pourcentage, bornées [0, 100] par construction
PERCENTAGE_COLUMNS: list[str] = [
    COL_DISPONIBILITE,
    COL_PERFORMANCE,
    COL_QUALITE,
    COL_TRS,
]

# Colonnes qui doivent être strictement positives ou nulles
NON_NEGATIVE_COLUMNS: list[str] = [
    COL_QTE_PRODUITE,
    COL_DUREE_TOTALE,
    COL_DUREE_ARRETS,
    COL_TEMPS_NET,
    COL_CADENCE_THEORIQUE,
]

# Colonnes catégorielles / dimensions d'analyse (Phase 5)
DIMENSION_COLUMNS: list[str] = [COL_PRODUIT, COL_ATELIER, COL_MACHINE]
