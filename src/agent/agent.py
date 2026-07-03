"""
L'agent : reçoit une question en langage naturel, route vers le bon
module métier (Phases 5, 6, 7), retourne une réponse ancrée dans les
données réelles.
"""

from __future__ import annotations

import pandas as pd

from src.agent import responder
from src.agent.entities import build_produit_index
from src.agent.intents import Intent, classify_intent
from src.analytics.aggregator import compute_metrics
from src.anomalies.detector import detect_anomalies
from src.recommend.recommender import recommend_cadences
from src.utils.config import AppConfig


class CadenceAgent:
    """
    Charge une fois les données et les calculs (analytics, anomalies,
    recommandations), puis répond à autant de questions que nécessaire
    sans tout recalculer à chaque fois.
    """

    def __init__(self, df: pd.DataFrame, config: AppConfig):
        self.df = df
        self.config = config

        self.produits = sorted(df["produit"].dropna().unique().tolist())
        self.machines = sorted(df["machine"].dropna().unique().tolist())
        self.code_index = build_produit_index(self.produits)

        self.metrics = compute_metrics(df, config.analytics)
        self.statistical_anomalies, _ = detect_anomalies(
            df, config.anomalies, exclude_bloquant=config.analytics.exclude_bloquant
        )
        self.recommendations = recommend_cadences(
            df, self.statistical_anomalies, config.recommendation, exclude_bloquant=config.analytics.exclude_bloquant
        )

    def answer(self, question: str) -> str:
        intent = classify_intent(question)

        if intent == Intent.RECOMMEND_CADENCE:
            return responder.respond_recommend_cadence(
                question,
                self.df,
                self.produits,
                self.machines,
                self.code_index,
                self.recommendations,
                self.config.recommendation.min_of_for_recommendation,
            )
        if intent == Intent.WHY_LOW_PERFORMANCE:
            return responder.respond_why_low_performance(
                question, self.df, self.produits, self.machines, self.code_index, self.metrics
            )
        if intent == Intent.STABLE_MACHINES:
            return responder.respond_stable_machines(self.df, min_of=self.config.anomalies.min_of_for_stat_detection)
        if intent == Intent.TRS_TREND:
            return responder.respond_trs_trend()

        return responder.respond_unknown()
