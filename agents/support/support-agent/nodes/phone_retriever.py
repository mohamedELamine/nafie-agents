from typing import list
from models import SupportAnswer


class PhoneRetrieverNode:
    def __init__(self, qdrant_client):
        self.qdrant = qdrant_client

    def __call__(self, state: "SupportState") -> "SupportState":
        ticket = state["ticket"]
        intent = state.get("intent_classification")

        if not intent:
            state["retrieval_results"] = []
            return state

        query_text = ticket["body"]
        intent_category = intent["intent_category"]

        results = self.qdrant.retrieve_knowledge(
            query=query_text, category=intent_category, limit=5
        )

        state["retrieval_results"] = results

        if results:
            state["support_answer"] = self._build_support_answer(results)
        else:
            state["support_answer"] = None

        return state

    def _build_support_answer(self, results: list[dict]) -> SupportAnswer:
        best_result = results[0]
        return {
            "answer_text": best_result.get("answer", ""),
            "confidence": best_result.get("score", 1.0),
            "sources": [best_result.get("source", "unknown")],
        }
