from typing import TypedDict
from datetime import datetime
from models import RetrievalResult, SupportAnswer


class TwitterConsumerNode:
    def __init__(self, redis_bus):
        self.redis = redis_bus

    def __call__(self, state: "SupportState") -> "SupportState":
        message = self.redis.consume_message("twitter:incoming")

        if not message:
            return state

        state["ticket"] = {
            "ticket_id": message.get("id"),
            "platform": "twitter",
            "body": message.get("text", ""),
            "subject": message.get("text", ""),
            "created_at": datetime.utcnow().isoformat(),
            "updated": False,
        }

        state["intent_classification"] = None
        state["risk_flags"] = []
        state["retrieval_results"] = []
        state["support_answer"] = None
        state["escalation_record"] = None

        return state
