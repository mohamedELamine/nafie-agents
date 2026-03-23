from typing import TypedDict, Literal
from datetime import datetime


class IntentClassification(TypedDict):
    intent_category: Literal["billing", "technical", "general"]
    confidence: float
    reasoning: str


class TicketReceiverNode:
    def __init__(self, helpscout_client, redis_bus):
        self.helpscout = helpscout_client
        self.redis = redis_bus

    def __call__(self, state: "SupportState") -> "SupportState":
        ticket = state["ticket"]
        ticket_id = ticket["ticket_id"]

        if ticket["platform"] == "helpscout":
            conversation = self.helpscout.get_conversation(ticket_id)
            ticket["subject"] = conversation.get("subject", "No subject")
            ticket["body"] = conversation.get("body", "")

        state["intent_classification"] = None
        state["risk_flags"] = []
        state["retrieval_results"] = []
        state["support_answer"] = None
        state["escalation_record"] = None

        return state
