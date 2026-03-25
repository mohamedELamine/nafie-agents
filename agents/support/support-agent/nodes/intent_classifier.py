from typing import Any, Dict, Literal, TypedDict


class IntentClassification(TypedDict):
    intent_category: Literal["billing", "technical", "general"]
    confidence: float
    reasoning: str


def _build_identity(ticket: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "email": ticket.get("customer_email"),
        "order_id": ticket.get("order_id"),
        "license_key": ticket.get("license_key"),
        "customer_name": ticket.get("customer_name"),
    }


def make_intent_classifier_node(claude_client) -> callable:
    """Create the intent classifier node."""

    def intent_classifier_node(state: Dict[str, Any]) -> Dict[str, Any]:
        ticket = state.get("ticket", {})
        ticket_text = ticket.get("message") or ticket.get("body", "")
        if not ticket_text:
            return {
                **state,
                "intent_classification": None,
                "risk_flags": [],
                "overall_risk_level": "low",
            }

        intent, risk = claude_client.classify_intent_and_risk(
            ticket_text=ticket_text,
            identity=_build_identity(ticket),
        )
        return {
            **state,
            "intent_classification": intent or None,
            "risk_flags": risk.get("flags", []),
            "overall_risk_level": risk.get("risk_level", "low"),
        }

    return intent_classifier_node
