

class WebhookHandlerNode:
    def __init__(self, helpscout_client):
        self.helpscout = helpscout_client

    def __call__(self, state: "SupportState") -> "SupportState":
        ticket = state["ticket"]
        ticket_id = ticket["ticket_id"]

        if ticket["platform"] != "helpscout":
            return state

        conversation = self.helpscout.get_conversation(ticket_id)
        ticket["subject"] = conversation.get("subject", "No subject")
        ticket["body"] = conversation.get("body", "")

        state["intent_classification"] = None
        state["risk_flags"] = []
        state["retrieval_results"] = []
        state["support_answer"] = None
        state["escalation_record"] = None

        return state
