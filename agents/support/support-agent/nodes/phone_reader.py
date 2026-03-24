from datetime import datetime, timezone


class PhoneReaderNode:
    def __init__(self, redis_bus):
        self.redis = redis_bus

    def __call__(self, state: "SupportState") -> "SupportState":
        message = self.redis.consume_message("phone:incoming")

        if not message:
            return state

        state["ticket"] = {
            "ticket_id": message.get("id"),
            "platform": "phone",
            "body": message.get("transcript", ""),
            "subject": message.get("subject", "Phone Call"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated": False,
        }

        state["intent_classification"] = None
        state["risk_flags"] = []
        state["retrieval_results"] = []
        state["support_answer"] = None
        state["escalation_record"] = None

        return state
