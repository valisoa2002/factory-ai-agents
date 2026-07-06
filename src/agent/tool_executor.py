"""
Exécution locale des outils appelés par le LLM.

Chaque fonction retourne un dict JSON-sérialisable de données RÉELLEMENT
CALCULÉES par les modules des Phases 5-8. Le LLM ne voit jamais que ce
dict — il ne peut pas halluciner un chiffre qui n'y figure pas.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from src.agent.entities import match_machine, match_produit
from src.analytics.models import ProductMachineMetrics
from src.ml.explain import compute_shap_values, explain_single_prediction
from src.ml.predict import predict_with_confidence
from src.recommend.models import CadenceRecommendation
from src.utils.config import AppConfig


class ToolExecutor:
    def __init__(
        self,
        df: pd.DataFrame,
        produits: list[str],
        machines: list[str],
        code_index: dict[str, str],
        metrics: list[ProductMachineMetrics],
        recommendations: list[CadenceRecommendation],
        config: AppConfig,
    ):
        self.df = df
        self.produits = produits
        self.machines = machines
        self.code_index = code_index
        self.metrics = metrics
        self.recommendations = recommendations
        self.config = config
        self._ml_pipeline = None  # chargé paresseusement

    def execute(self, tool_name: str, arguments: dict) -> dict:
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is None:
            return {"error": f"Outil inconnu : {tool_name}"}
        return handler(arguments)

    # ------------------------------------------------------------------

    def _resolve(self, arguments: dict) -> tuple[str | None, str | None]:
        produit_query = arguments.get("produit") or ""
        machine_query = arguments.get("machine") or ""
        produit = match_produit(produit_query, self.produits, self.code_index) if produit_query else None
        machine = match_machine(machine_query, self.machines) if machine_query else None
        return produit, machine

    def _tool_get_cadence_recommendation(self, arguments: dict) -> dict:
        produit, machine = self._resolve(arguments)
        if not produit and not machine:
            return {"error": "Aucun produit ou machine identifié dans la question."}

        if produit and machine:
            matches = [r for r in self.recommendations if r.produit == produit and r.machine == machine]
        elif produit:
            matches = [r for r in self.recommendations if r.produit == produit]
        else:
            matches = [r for r in self.recommendations if r.machine == machine]

        if not matches:
            return {"error": f"Aucune donnée en historique pour produit={produit}, machine={machine}."}

        fiables = [r for r in matches if r.fiable]
        if not fiables:
            r = matches[0]
            return {
                "fiable": False,
                "produit": r.produit,
                "machine": r.machine,
                "n_of_utilises": r.n_of_utilises,
                "min_of_requis": self.config.recommendation.min_of_for_recommendation,
                "message": "Historique insuffisant pour une recommandation fiable.",
            }

        r = max(fiables, key=lambda x: x.n_of_reference)
        return {
            "fiable": True,
            "produit": r.produit,
            "machine": r.machine,
            "cadence_theorique_actuelle": r.cadence_theorique_actuelle,
            "cadence_recommandee": r.cadence_recommandee,
            "ecart_vs_theorique_pct": r.ecart_vs_theorique_pct,
            "trs_moyen_reference": r.trs_moyen_reference,
            "n_of_reference": r.n_of_reference,
            "justification": r.justification,
        }

    def _tool_get_performance_analysis(self, arguments: dict) -> dict:
        produit, machine = self._resolve(arguments)
        if not produit and not machine:
            return {"error": "Aucun produit ou machine identifié dans la question."}

        if produit and machine:
            candidates = [m for m in self.metrics if m.produit == produit and m.machine == machine]
        elif machine:
            candidates = [m for m in self.metrics if m.machine == machine]
        else:
            candidates = [m for m in self.metrics if m.produit == produit]

        candidates = [m for m in candidates if m.trs_moy is not None]
        if not candidates:
            return {"error": f"Aucune donnée exploitable pour produit={produit}, machine={machine}."}

        worst = min(candidates, key=lambda m: m.trs_moy)
        return {
            "produit": worst.produit,
            "machine": worst.machine,
            "n_of": worst.n_of,
            "trs_moyen": round(worst.trs_moy, 1),
            "stabilite_cv": round(worst.stabilite_cv, 1) if worst.stabilite_cv is not None else None,
            "conclusions": worst.conclusions,
            "n_couples_analyses": len(candidates),
        }

    def _tool_get_stability_ranking(self, arguments: dict) -> dict:
        min_of = self.config.anomalies.min_of_for_stat_detection
        working = self.df[self.df["quality_severity"] != "BLOQUANT"].dropna(subset=["cadence_reelle"])

        stats = []
        for machine, group in working.groupby("machine"):
            n = len(group)
            if n < min_of:
                continue
            mean = group["cadence_reelle"].mean()
            std = group["cadence_reelle"].std()
            if mean and mean != 0 and not pd.isna(std):
                stats.append({"machine": machine, "coefficient_variation_pct": round(float(std / mean * 100), 1), "n_of": n})

        if not stats:
            return {"error": f"Aucune machine avec au moins {min_of} OF pour évaluer la stabilité."}

        stats.sort(key=lambda x: x["coefficient_variation_pct"])
        n_excluded = self.df["machine"].nunique() - len(stats)
        return {"machines_classees_par_stabilite": stats, "n_machines_non_evaluees": n_excluded, "min_of_requis": min_of}

    def _tool_get_trend_analysis(self, arguments: dict) -> dict:
        return {
            "disponible": False,
            "raison": (
                "Les exports 'Détails Cadences' ne contiennent pas de date de "
                "production exploitable. Une analyse de tendance temporelle "
                "nécessiterait d'intégrer la feuille 'Détails Progressions' ou "
                "d'ajouter un champ date."
            ),
        }

    def _tool_get_ml_prediction(self, arguments: dict) -> dict:
        produit, machine = self._resolve(arguments)
        if not produit or not machine:
            return {"error": "Produit et machine sont tous les deux nécessaires pour une prédiction ML."}

        pipeline = self._load_ml_pipeline()
        if pipeline is None:
            return {"error": "Aucun modèle ML entraîné disponible. Lancez main_train_model.py d'abord."}

        cadence_theorique = arguments.get("cadence_theorique")
        if cadence_theorique is None:
            couple_rows = self.df[(self.df["produit"] == produit) & (self.df["machine"] == machine)]
            if not couple_rows.empty:
                cadence_theorique = couple_rows["cadence_theorique"].dropna().mean()
            else:
                cadence_theorique = self.df["cadence_theorique"].dropna().mean()

        atelier_rows = self.df[self.df["machine"] == machine]["atelier"].dropna()
        atelier = atelier_rows.iloc[0] if not atelier_rows.empty else self.df["atelier"].dropna().iloc[0]
        qte_moyenne = self.df["qte_produite"].dropna().mean()

        X = pd.DataFrame([{
            "produit": produit, "machine": machine, "atelier": atelier,
            "cadence_theorique": cadence_theorique, "qte_produite": qte_moyenne,
        }])

        preds = predict_with_confidence(pipeline, X)
        pred = preds[0]

        shap_values, feature_names = compute_shap_values(pipeline, X)
        explanations = explain_single_prediction(shap_values, feature_names, 0)

        return {
            "produit": produit,
            "machine": machine,
            "cadence_predite": round(pred.prediction, 2),
            "intervalle_confiance_95": [round(pred.confidence_interval_95[0], 2), round(pred.confidence_interval_95[1], 2)],
            "facteurs_explicatifs": explanations,
        }

    def _load_ml_pipeline(self):
        if self._ml_pipeline is not None:
            return self._ml_pipeline
        model_path = self.config.project_root / self.config.ml.model_output_path
        if not Path(model_path).exists():
            return None
        self._ml_pipeline = joblib.load(model_path)
        return self._ml_pipeline
