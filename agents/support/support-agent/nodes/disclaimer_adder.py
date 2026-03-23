from typing import Any, Dict

from ..logging_config import get_logger

logger = get_logger("nodes.disclaimer_adder")

_DISCLAIMER = (
    "\n\n**ملاحظة هامة:**\n"
    "هذا رد آلي — إن لم يحل مشكلتك، سيتولى فريقنا الأمر\n"
    "يرجى التواصل معنا عبر الهاتف أو الدردشة المباشرة."
)


def make_disclaimer_adder_node() -> callable:
    """Create the disclaimer adder node."""

    def disclaimer_adder_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Append disclaimer to support answer without mutating existing state."""
        try:
            answer = state.get("support_answer")

            if not answer:
                return state

            new_answer = {
                **answer,
                "answer_text": answer.get("answer_text", "") + _DISCLAIMER,
            }

            return {**state, "support_answer": new_answer}

        except Exception as e:
            logger.error(f"Error in disclaimer_adder_node: {e}")
            return state

    return disclaimer_adder_node
