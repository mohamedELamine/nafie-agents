from typing import Any, Dict, List

from ..logging_config import get_logger
from ..models import SupportAnswer

logger = get_logger("nodes.knowledge_retriever")


def make_knowledge_retriever_node(qdrant_client) -> callable:
    """Create the knowledge retriever node."""

    def knowledge_retriever_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve relevant knowledge and build support answer."""
        try:
            ticket = state.get("ticket", {})
            intent = state.get("intent_classification")

            if not intent:
                return {**state, "retrieval_results": [], "support_answer": None}

            query_text = ticket.get("message") or ticket.get("body", "")
            intent_category = intent.get("category") or intent.get("intent_category")

            results = qdrant_client.retrieve_knowledge(
                query=query_text, category=intent_category, limit=5
            )

            support_answer = _build_support_answer(results) if results else None

            logger.info(
                f"Retrieved {len(results)} results for ticket {ticket.get('ticket_id')}"
            )

            return {
                **state,
                "retrieval_results": results,
                "support_answer": support_answer,
            }

        except Exception as e:
            logger.error(f"Error in knowledge_retriever_node: {e}")
            return {**state, "retrieval_results": [], "support_answer": None}

    return knowledge_retriever_node


def _build_support_answer(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build support answer dict from retrieval results."""
    best_result = results[0]
    return {
        "answer_text": best_result.get("answer", ""),
        "confidence": best_result.get("score", 1.0),
        "sources": [best_result.get("source", "unknown")],
    }
