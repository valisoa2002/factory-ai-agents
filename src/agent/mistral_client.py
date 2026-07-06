"""
Client Mistral pour l'agent conversationnel.

⚠️ Non testé bout-en-bout dans l'environnement de développement (pas
d'accès réseau à api.mistral.ai) : cette implémentation suit la
documentation officielle du SDK `mistralai` (client.chat.complete avec
`tools`/`tool_choice`). À valider en conditions réelles — si la
signature d'appel diffère, le message d'erreur exact permettra de
corriger rapidement.

Garde-fou anti-hallucination : le system prompt interdit explicitement
au modèle d'inventer un chiffre ; toute donnée numérique DOIT provenir
d'un résultat d'outil. Si aucun outil ne peut répondre, le modèle doit
le dire plutôt que d'improviser.
"""

from __future__ import annotations

import json
import os

from mistralai.client import Mistral

from src.agent.tool_executor import ToolExecutor
from src.agent.tools import TOOLS
from src.utils.config import LLMConfig

_SYSTEM_PROMPT = """Tu es un assistant d'aide à la décision pour une équipe de production industrielle, \
spécialisé dans l'analyse du TRS (Taux de Rendement Synthétique) et des cadences de fabrication.

RÈGLES STRICTES :
1. Tu ne dois JAMAIS inventer un chiffre (cadence, TRS, pourcentage). Chaque chiffre que tu donnes \
DOIT provenir du résultat d'un outil que tu as appelé.
2. Si aucun outil ne peut répondre à la question, dis-le clairement plutôt que d'improviser.
3. Si un outil retourne un champ "error" ou "disponible": false, explique cette limite à l'utilisateur \
au lieu de contourner le problème.
4. Réponds en français, de façon concise et actionnable pour un responsable de production.
5. Si la question mentionne un produit ou une machine, transmets-le tel quel en argument à l'outil \
(l'outil se charge de retrouver la correspondance exacte dans les données)."""


class MistralAgent:
    def __init__(self, tool_executor: ToolExecutor, config: LLMConfig):
        api_key = os.getenv("CADENCE_TRS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Variable d'environnement CADENCE_TRS_API_KEY manquante dans .env "
                "(votre clé API Mistral)."
            )
        self.client = Mistral(api_key=api_key)
        self.model = config.model
        self.temperature = config.temperature
        self.tool_executor = tool_executor
        self.history: list[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]

    def ask(self, question: str) -> str:
        self.history.append({"role": "user", "content": question})

        response = self.client.chat.complete(
            model=self.model,
            messages=self.history,
            tools=TOOLS,
            tool_choice="auto",
            temperature=self.temperature,
        )
        message = response.choices[0].message

        # Le modèle peut enchaîner plusieurs appels d'outils avant de répondre
        max_tool_rounds = 4
        rounds = 0
        while getattr(message, "tool_calls", None) and rounds < max_tool_rounds:
            self.history.append(message)

            for tool_call in message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                result = self.tool_executor.execute(tool_call.function.name, args)
                self.history.append(
                    {
                        "role": "tool",
                        "name": tool_call.function.name,
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )

            response = self.client.chat.complete(
                model=self.model,
                messages=self.history,
                tools=TOOLS,
                tool_choice="auto",
                temperature=self.temperature,
            )
            message = response.choices[0].message
            rounds += 1

        self.history.append(message)
        return message.content or "(réponse vide du modèle)"
