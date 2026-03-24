class TicketUpdaterNode:
    def __init__(self, helpscout_client, redis_bus, facebook_client=None):
        self.helpscout = helpscout_client
        self.redis = redis_bus
        self.facebook = facebook_client

    def __call__(self, state: "SupportState") -> "SupportState":
        ticket = state["ticket"]
        answer = state.get("support_answer")
        platform = ticket.get("platform", "helpscout")
        ticket_id = ticket.get("ticket_id")

        if not answer:
            if platform == "helpscout":
                self.helpscout.add_note(
                    conversation_id=ticket_id,
                    body="لا يوجد إجابة متاحة للسؤال",
                )
            self.redis.publish_message(
                "support:ticket_updates",
                {
                    "ticket_id": ticket_id,
                    "platform": platform,
                    "status": "no_answer",
                },
            )
            return state

        if platform == "facebook" and self.facebook:
            self.facebook.reply_comment(
                comment_id=ticket_id,
                message=answer["answer_text"],
                page_id=ticket.get("page_id", ""),
            )
        else:
            self.helpscout.reply(
                conversation_id=ticket_id,
                body=answer["answer_text"],
            )

        state["ticket"]["updated"] = True
        self.redis.publish_message(
            "support:ticket_updates",
            {
                "ticket_id": ticket_id,
                "platform": platform,
                "status": "answered",
                "answer": answer["answer_text"],
            },
        )

        return state
