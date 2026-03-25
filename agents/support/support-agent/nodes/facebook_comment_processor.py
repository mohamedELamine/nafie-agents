

class FacebookCommentProcessorNode:
    def __init__(self, facebook_client, helpscout_client, redis_bus):
        self.facebook = facebook_client
        self.helpscout = helpscout_client
        self.redis = redis_bus

    def __call__(self, state: "SupportState") -> "SupportState":
        comment = state["ticket"]
        comment_id = comment.get("id")

        if not comment_id:
            return state

        helpscout_ticket = self.helpscout.get_conversation(comment_id)

        if not helpscout_ticket:
            return state

        helpscout_ticket["platform"] = "facebook"
        helpscout_ticket["ticket_id"] = comment_id
        helpscout_ticket["body"] = comment.get("text", "")
        helpscout_ticket["subject"] = "Facebook Comment"

        state["ticket"] = helpscout_ticket

        return state
