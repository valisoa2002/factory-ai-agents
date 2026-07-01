"""
Validation des hypothèses de formules métier sur un export réel.

Usage :
    python validate_formulas.py data/raw/Rapport_Production_XXXX.xlsx

Ce script vérifie, ligne par ligne, si les formules supposées tiennent :
    - Temps Net       = Durée Totale - Durée Arrêts
    - Écart (%)       = (Cadence Réelle - Cadence Théorique) / Cadence Théorique * 100
    - TRS (%)         = Disponibilité * Performance * Qualité / 10000
    - Code OF unique  = unicité de (Code OF, Machine), pas Code OF seul

Il ne modifie rien : c'est un outil de diagnostic pour valider (ou invalider)
le dictionnaire de données avant d'écrire les règles de la Phase 3.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.extract.excel_extractor import ExcelExtractor
from src.extract.exceptions import ExtractionError
from src.utils.config import load_config
from src.utils.logger import setup_logger

TOLERANCE = 0.5  # tolérance d'arrondi acceptée (en unité de la colonne)


def check_formula(df, name, computed, actual, tolerance=TOLERANCE):
    diff = (computed - actual).abs()
    n_bad = int((diff > tolerance).sum())
    n_total = len(df)
    print(f"\n[{name}]")
    if n_bad == 0:
        print(f"  ✅ Formule vérifiée sur {n_total}/{n_total} lignes (tolérance ±{tolerance}).")
    else:
        pct = round(100 * n_bad / n_total, 1)
        print(f"  ⚠️  {n_bad}/{n_total} lignes ({pct}%) s'écartent de plus de {tolerance}.")
        bad_rows = df.loc[diff > tolerance]
        cols_to_show = [c for c in df.columns if not c.startswith("_")]
        print("  Exemples de lignes en écart :")
        print(bad_rows[cols_to_show].head(5).to_string(index=False))


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage : python validate_formulas.py <chemin_vers_export.xlsx>")
        return 1

    config = load_config("config/settings.yaml")
    logger = setup_logger(config)

    try:
        extractor = ExcelExtractor(config, logger=logger)
        result = extractor.extract(sys.argv[1])
    except ExtractionError as exc:
        logger.error(f"Échec de l'extraction : {exc}")
        return 1

    df = result.dataframe.copy()
    print(f"\n=== Validation des formules sur {result.n_rows} lignes ===")

    # 1. Temps Net = Durée Totale - Durée Arrêts
    if {"Durée Totale (min)", "Durée Arrêts (min)", "Temps Net (min)"} <= set(df.columns):
        computed = df["Durée Totale (min)"] - df["Durée Arrêts (min)"]
        check_formula(df, "Temps Net (min) = Durée Totale - Durée Arrêts", computed, df["Temps Net (min)"])

    # 2. Écart (%) = (Réelle - Théorique) / Théorique * 100
    if {"Cadence Réelle (pcs/min)", "Cadence Théorique (pcs/min)", "Écart (%)"} <= set(df.columns):
        valid = df["Cadence Théorique (pcs/min)"] != 0
        computed = (
            (df.loc[valid, "Cadence Réelle (pcs/min)"] - df.loc[valid, "Cadence Théorique (pcs/min)"])
            / df.loc[valid, "Cadence Théorique (pcs/min)"] * 100
        )
        check_formula(df.loc[valid], "Écart (%) = (Réelle - Théorique) / Théorique * 100", computed, df.loc[valid, "Écart (%)"], tolerance=1.0)

    # 3. TRS (%) = Disponibilité * Performance * Qualité / 10000
    if {"Disponibilité (%)", "Performance (%)", "Qualité (%)", "TRS (%)"} <= set(df.columns):
        computed = df["Disponibilité (%)"] * df["Performance (%)"] * df["Qualité (%)"] / 10000
        check_formula(df, "TRS (%) = Disponibilité * Performance * Qualité / 10000", computed, df["TRS (%)"], tolerance=1.0)

    # 4. Unicité de la clé (Code OF, Machine)
    if {"Code OF", "Machine"} <= set(df.columns):
        n_dup = int(df.duplicated(subset=["Code OF", "Machine"]).sum())
        print(f"\n[Unicité (Code OF, Machine)]")
        if n_dup == 0:
            print(f"  ✅ Aucune ligne dupliquée sur la clé (Code OF, Machine).")
        else:
            print(f"  ⚠️  {n_dup} ligne(s) dupliquée(s) sur (Code OF, Machine).")

    # 5. Valeurs manquantes en Cadence Réelle
    if "Cadence Réelle (pcs/min)" in df.columns:
        missing = df[df["Cadence Réelle (pcs/min)"].isna()]
        print(f"\n[Cadence Réelle manquante]")
        if missing.empty:
            print("  ✅ Aucune valeur manquante.")
        else:
            cols_to_show = [c for c in df.columns if not c.startswith("_")]
            print(f"  ⚠️  {len(missing)} ligne(s) sans Cadence Réelle :")
            print(missing[cols_to_show].to_string(index=False))

    print("\n=== Fin de la validation ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())