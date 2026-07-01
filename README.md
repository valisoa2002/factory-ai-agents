# Agent IA d'Analyse et d'Optimisation des Cadences — Phase 2

## État actuel

**Phase 2 : Pipeline ETL — module d'extraction** ✅ codé et testé.

Ce qui existe et fonctionne :
- `src/extract/excel_extractor.py` — extrait la feuille "Détails Cadences"
  d'un export Excel, valide sa présence, gère les erreurs (fichier absent,
  feuille absente, fichier corrompu, feuille vide), ajoute des colonnes
  techniques de traçabilité (`_source_file`, `_extracted_at`).
- `src/extract/schema_explorer.py` + `main_explore.py` — outil d'exploration
  qui génère un rapport Markdown (colonnes, types, % manquants,
  cardinalité) pour construire le dictionnaire de données réel.
- `src/utils/config.py` — configuration centralisée et typée
  (`config/settings.yaml`), aucun chemin ni nom de feuille codé en dur.
- `src/utils/logger.py` — logging structuré (console + fichier).

Ce qui n'existe pas encore (volontairement) :
- Contrôle qualité (Phase 3) — **ne peut pas être écrit sérieusement tant
  qu'on n'a pas un vrai dictionnaire de données**, sinon les règles seront
  inventées et fausses.
- Historisation, analyse, anomalies, recommandation, ML, agent — Phases 4 à 9.

## Pourquoi commencer par l'exploration et pas directement par les règles métier

Le cahier des charges liste des colonnes attendues (cadence théorique,
cadence réelle, TRS, disponibilité, performance, qualité...) mais je n'ai
pas vu un export réel. Écrire les règles de contrôle qualité (Phase 3)
maintenant reviendrait à deviner les noms de colonnes exacts, leurs unités,
et leurs plages de valeurs valides — ça casserait au premier fichier réel.

## Comment tester dès maintenant

```bash
pip install -r requirements.txt

# 1. Déposez un export réel dans data/raw/, par exemple :
#    data/raw/export_production_2026_06.xlsx

# 2. Lancez l'exploration :
python main_explore.py data/raw/export_production_2026_06.xlsx

# 3. Ouvrez le rapport généré dans reports/, remplissez la colonne
#    "Signification métier", et partagez-le pour qu'on verrouille
#    ensemble le dictionnaire de données.
```

## Structure du projet

```
src/
├── extract/       # Phase 2 — lecture des exports Excel (fait)
├── quality/        # Phase 3 — contrôle qualité (à venir, après exploration)
├── transform/       # Phase 3-4 — nettoyage, normalisation
├── load/            # Phase 4 — écriture en base / historisation
├── analytics/        # Phase 5 — moteur d'analyse des cadences
├── ml/               # Phase 8 — modèles prédictifs
├── agents/           # Phase 9 — agent conversationnel
├── reporting/        # Power BI / exports de reporting
└── utils/            # config, logger, helpers transverses
```

## Prochaine étape proposée

Dès que vous avez un export réel (même anonymisé/partiel), on :
1. lance `main_explore.py` dessus ;
2. remplit ensemble le dictionnaire de données (signification, unité,
   colonne clé Produit/Machine, plages valides) ;
3. seulement à ce moment-là, on code la Phase 3 (contrôle qualité) avec
   des règles réelles et testables, pas inventées.

Si vous n'avez pas de fichier réel disponible tout de suite, on peut aussi
avancer sur l'**architecture de la Phase 3** (squelette des règles,
génération du rapport de qualité) en paramétrant les noms de colonnes
plutôt qu'en les codant en dur — dites-moi ce que vous préférez.
