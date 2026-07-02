"""
Modèles SQLAlchemy de la base d'historisation.

Deux tables :
    production_history : une ligne par (Code OF, Machine), avec son statut
                          de qualité conservé (pas de perte d'information —
                          une ligne BLOQUANT est historisée avec son flag,
                          pas silencieusement supprimée).
    import_log          : trace chaque exécution du pipeline de chargement,
                           pour audit (quel fichier, quand, combien inséré/
                           ignoré/rejeté).
"""

from __future__ import annotations

import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ProductionRecord(Base):
    """Une ligne historisée de la feuille 'Détails Cadences'."""

    __tablename__ = "production_history"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Clé métier (voir découverte Phase 1 : OF peut être décomposé par machine)
    code_of = Column(String, nullable=False)
    machine = Column(String, nullable=False)

    # Dimensions
    produit = Column(String)
    atelier = Column(String)

    # Mesures
    qte_produite = Column(Integer)
    duree_totale_min = Column(Float)
    duree_arrets_min = Column(Float)
    temps_net_min = Column(Float)
    cadence_reelle = Column(Float, nullable=True)  # peut être NULL si Qté Produite = 0
    cadence_theorique = Column(Float)
    ecart_pct = Column(Float)
    disponibilite_pct = Column(Float)
    performance_pct = Column(Float)
    qualite_pct = Column(Float)
    trs_pct = Column(Float)

    # Traçabilité qualité — la ligne est CONSERVÉE même si BLOQUANT ;
    # c'est aux requêtes d'analyse (Phase 5+) de filtrer si besoin.
    quality_severity = Column(String, nullable=True)  # "BLOQUANT" | "AVERTISSEMENT" | "INFO" | None
    quality_details = Column(Text, nullable=True)       # JSON des anomalies de cette ligne

    # Traçabilité d'origine
    source_file = Column(String, nullable=False)
    extracted_at = Column(DateTime)
    loaded_at = Column(DateTime, default=datetime.datetime.now)

    __table_args__ = (
        UniqueConstraint("code_of", "machine", name="uq_production_history_code_of_machine"),
    )


class ImportLog(Base):
    """Journal d'audit de chaque exécution du chargement."""

    __tablename__ = "import_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_file = Column(String, nullable=False)
    imported_at = Column(DateTime, default=datetime.datetime.now)

    n_rows_extracted = Column(Integer)
    n_rows_inserted = Column(Integer)
    n_rows_skipped_duplicate = Column(Integer)

    n_bloquant = Column(Integer)
    n_avertissement = Column(Integer)
    n_info = Column(Integer)
