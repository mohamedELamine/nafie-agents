import os
import logging
import asyncio
from typing import Optional

from models import SupportState
from qdrant_client import QdrantClient
from helpscout_client import HelpScoutClient
from claude_client import ClaudeClient
from redis_bus import RedisBus
from helpscout_client import HelpScoutClient
from db import DB
from resend_client import ResendClient
from state import create_initial_state
from nodes import SupportGraph, should_escalate

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class SupportAgent:
    def __init__(
        self,
        helpscout_client: HelpScoutClient,
        claude_client: ClaudeClient,
        qdrant_client: QdrantClient,
        redis_bus: RedisBus,
        db: DB,
        resend_client: ResendClient,
    ):
        self.helpscout = helpscout_client
        self.claude = claude_client
        self.qdrant = qdrant_client
        self.redis = redis_bus
        self.db = db
        self.resend = resend_client

        self.graph: Optional[SupportGraph] = None

    async def initialize(self):
        self.graph = self._build_graph()
        logger.info("Support agent initialized successfully")

    def _build_graph(self) -> SupportGraph:
        from agent import SupportAgentGraph

        agent_graph = SupportAgentGraph(
            helpscout_client=self.helpscout,
            claude_client=self.claude,
            qdrant_client=self.qdrant,
            redis_bus=self.redis,
            db=self.db,
            resend_client=self.resend,
        )

        return agent_graph.build_graph()

    async def process_ticket(self, ticket_data: dict) -> SupportState:
        logger.info(f"Processing ticket: {ticket_data.get('ticket_id')}")

        state = create_initial_state(ticket_data)

        graph = self.graph

        if not graph:
            await self.initialize()
            graph = self.graph

        await graph.intent_classifier(state)
        await graph.knowledge_retriever(state)
        await graph.disclaimer_adder(state)
        await graph.ticket_updater(state)
        await graph.escalation_handler(state)

        logger.info(f"Processed ticket {ticket_data.get('ticket_id')}")
        return state

    async def process_facebook_comment(self, comment_data: dict) -> SupportState:
        logger.info(f"Processing Facebook comment: {comment_data.get('id')}")

        state = create_initial_state(comment_data)

        graph = self.graph

        if not graph:
            await self.initialize()
            graph = self.graph

        await graph.facebook_comment_processor(state)
        await graph.intent_classifier(state)
        await graph.knowledge_retriever(state)
        await graph.disclaimer_adder(state)
        await graph.post_classifier(state)
        await graph.ticket_updater(state)

        logger.info(f"Processed Facebook comment {comment_data.get('id')}")
        return state

    async def process_webhook(self, webhook_data: dict) -> dict:
        if webhook_data.get("event") == "conversation.created":
            return await self.process_ticket(webhook_data.get("data", {}))
        elif webhook_data.get("event") == "conversation.note.added":
            return await self.process_ticket(webhook_data.get("data", {}))
        else:
            return {"status": "ignored"}

    def get_pending_tickets(self) -> list[dict]:
        return self.redis.get_messages("ticket:pending")

    def get_ticket_answer(self, ticket_id: str) -> Optional[str]:
        return self.redis.get_value(f"ticket:answer:{ticket_id}")


async def main():
    from dotenv import load_dotenv

    load_dotenv()

    helpscout_client = HelpScoutClient(
        api_key=os.getenv("HELPSCOUT_API_KEY"), app_id=os.getenv("HELPSCOUT_APP_ID")
    )

    claude_client = ClaudeClient(api_key=os.getenv("OPENAI_API_KEY"))

    qdrant_client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333)),
    )

    redis_bus = RedisBus(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
    )

    db = DB(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        database=os.getenv("POSTGRES_DB", "support_agent"),
    )

    resend_client = ResendClient(
        api_key=os.getenv("RESEND_API_KEY"),
        owner_email=os.getenv("OWNER_EMAIL", ""),
    )

    agent = SupportAgent(
        helpscout_client=helpscout_client,
        claude_client=claude_client,
        qdrant_client=qdrant_client,
        redis_bus=redis_bus,
        db=db,
        resend_client=resend_client,
    )

    await agent.initialize()

    logger.info("Support agent is running")

    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
