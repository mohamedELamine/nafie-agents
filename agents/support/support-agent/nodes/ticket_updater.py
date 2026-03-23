from typing import TypedDict
from datetime import datetime
from models import SupportTicket, SupportAnswer, EscalationRecord


class TicketUpdaterNode:
    def __init__(self, helpscout_client, redis_bus):
        self.helpscout = helpscout_client
        self.redis = redis_bus

    def __call__(self, state: "SupportState") -> "SupportState":
        ticket = state["ticket"]
        answer = state.get("support_answer")
        overall_risk = state.get("overall_risk_level")

        if not answer:
            self.helpscout.add_note(
                ticket_id=ticket["ticket_id"], note="لا يوجد إجابة متاحة للسؤال"
            )
            return state

        self.helpscout.reply(ticket_id=ticket["ticket_id"], body=answer["answer_text"])

        state["ticket"]["updated"] = True

        return state
