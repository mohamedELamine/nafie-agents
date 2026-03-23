from typing import TypedDict, Literal
from datetime import datetime


class RiskFlag:
    pass


class RiskFlags(TypedDict):
    flags: list[RiskFlag]
    overall_risk_level: Literal["low", "medium", "high"]


class RiskFlaggerNode:
    def __init__(self, claude_client):
        self.claude = claude_client

    def __call__(self, state: "SupportState") -> "SupportState":
        ticket = state["ticket"]
        intent = state["intent_classification"]
        answer = state["support_answer"]

        if not intent or not answer:
            return state

        risk_flags, overall_level = self.claude.classify_risk(
            ticket=ticket, intent=intent, answer=answer
        )

        state["risk_flags"] = risk_flags
        state["overall_risk_level"] = overall_level

        return state
