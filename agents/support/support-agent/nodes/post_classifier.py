from typing import TypedDict
from models import RetrievalResult, SupportAnswer
from typing import Literal


class PostClassifierNode:
    def __init__(self, claude_client):
        self.claude = claude_client

    def __call__(self, state: "SupportState") -> "SupportState":
        ticket = state["ticket"]
        answer = state.get("support_answer")

        if not answer:
            return state

        post_category, confidence = self.claude.classify_post(
            ticket=ticket, answer=answer
        )

        state["post_classification"] = {
            "category": post_category,
            "confidence": confidence,
        }

        return state
