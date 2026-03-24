"""
Support agent — LangGraph StateGraph pipeline.
Routing: HelpScout/Facebook tickets → classify → retrieve → answer / escalate.
"""
import asyncio
import os
import sys
from typing import Any, Dict, List, Optional

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from core.base_agent import BaseAgent
from core.state import AgentName, BusinessEvent, EventType

from .logging_config import get_logger
from .nodes.ticket_receiver import make_ticket_receiver_node
from .nodes.knowledge_retriever import make_knowledge_retriever_node
from .nodes.escalation_handler import make_escalation_handler_node
from .nodes.disclaimer_adder import make_disclaimer_adder_node

logger = get_logger("agent")


# ---------------------------------------------------------------------------
# State definition
# ---------------------------------------------------------------------------

class SupportState(TypedDict, total=False):
    """Shared state threaded through every node in the pipeline."""

    # Inbound ticket (raw dict from webhook)
    ticket: Dict[str, Any]
    platform: str

    # Classification
    intent_classification: Optional[Dict[str, Any]]

    # Risk assessment
    risk_flags: List[Any]
    overall_risk_level: str  # "low" | "medium" | "high" | "critical"

    # Knowledge retrieval
    retrieval_results: List[Dict[str, Any]]
    support_answer: Optional[Dict[str, Any]]

    # Escalation
    escalation_record: Optional[Dict[str, Any]]

    # Flow control
    success: bool
    error: Optional[str]


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------

def _route_by_platform(state: SupportState) -> str:
    """Route incoming ticket by platform."""
    platform = state.get("platform", "helpscout")
    if platform == "facebook":
        return "facebook_flow"
    return "helpscout_flow"


def _route_after_risk(state: SupportState) -> str:
    """Escalate for medium/high/critical risk, otherwise update ticket."""
    level = state.get("overall_risk_level", "low")
    if level in ("medium", "high", "critical"):
        return "escalation_handler"
    return "ticket_updater"


# ---------------------------------------------------------------------------
# Placeholder nodes for class-based nodes not yet refactored
# (they implement __call__ so LangGraph can invoke them directly)
# ---------------------------------------------------------------------------

def _make_noop_node(name: str):
    """Return a no-op node that passes state through unchanged."""
    def noop(state: SupportState) -> SupportState:
        logger.debug(f"noop node: {name}")
        return state
    noop.__name__ = name
    return noop


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_support_graph(
    helpscout_client,
    claude_client,
    qdrant_client,
    resend_client,
    redis_bus,
    facebook_client=None,
) -> StateGraph:
    """Build and return the compiled support LangGraph."""

    # --- instantiate nodes ---------------------------------------------------
    ticket_receiver    = make_ticket_receiver_node()
    knowledge_retriever = make_knowledge_retriever_node(qdrant_client)
    disclaimer_adder   = make_disclaimer_adder_node()
    escalation_handler = make_escalation_handler_node(
        helpscout_client, resend_client, redis_bus
    )

    # Class-based nodes (implement __call__) — used directly
    # These will be replaced with factory functions in future refactors
    from .nodes.intent_classifier import TicketReceiverNode as _IntentDummy
    from .nodes.risk_flagger import RiskFlaggerNode
    from .nodes.ticket_updater import TicketUpdaterNode

    intent_classifier_node = RiskFlaggerNode(claude_client)   # wraps claude for risk+intent
    risk_flagger_node      = RiskFlaggerNode(claude_client)
    ticket_updater_node    = TicketUpdaterNode(helpscout_client, redis_bus)

    # --- build graph ---------------------------------------------------------
    graph = StateGraph(SupportState)

    # Entry point: receive & normalise the raw webhook payload
    graph.add_node("ticket_receiver", ticket_receiver)

    # HelpScout flow
    graph.add_node("intent_classifier", risk_flagger_node)   # classifies intent via claude
    graph.add_node("risk_flagger", risk_flagger_node)
    graph.add_node("knowledge_retriever", knowledge_retriever)
    graph.add_node("disclaimer_adder", disclaimer_adder)
    graph.add_node("escalation_handler", escalation_handler)
    graph.add_node("ticket_updater", ticket_updater_node)

    # Facebook flow (no-op placeholder — replace when facebook nodes are refactored)
    graph.add_node("facebook_flow", _make_noop_node("facebook_flow"))

    # --- edges ---------------------------------------------------------------
    graph.add_edge(START, "ticket_receiver")

    # Route after receiving ticket
    graph.add_conditional_edges(
        "ticket_receiver",
        _route_by_platform,
        {
            "helpscout_flow": "intent_classifier",
            "facebook_flow":  "facebook_flow",
        },
    )

    # HelpScout linear flow: classify → flag → retrieve → disclaimer → route
    graph.add_edge("intent_classifier", "risk_flagger")
    graph.add_edge("risk_flagger",      "knowledge_retriever")
    graph.add_edge("knowledge_retriever", "disclaimer_adder")

    # Branch after disclaimer: escalate or reply
    graph.add_conditional_edges(
        "disclaimer_adder",
        _route_after_risk,
        {
            "escalation_handler": "escalation_handler",
            "ticket_updater":     "ticket_updater",
        },
    )

    graph.add_edge("escalation_handler", END)
    graph.add_edge("ticket_updater",     END)
    graph.add_edge("facebook_flow",      END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public run helper
# ---------------------------------------------------------------------------

def run_support_pipeline(
    ticket_data: Dict[str, Any],
    helpscout_client,
    claude_client,
    qdrant_client,
    resend_client,
    redis_bus,
    facebook_client=None,
) -> Dict[str, Any]:
    """Build the graph and run a single ticket through the pipeline."""
    try:
        app = build_support_graph(
            helpscout_client=helpscout_client,
            claude_client=claude_client,
            qdrant_client=qdrant_client,
            resend_client=resend_client,
            redis_bus=redis_bus,
            facebook_client=facebook_client,
        )

        initial_state: SupportState = {
            "ticket":              ticket_data,
            "platform":            ticket_data.get("platform", "helpscout"),
            "intent_classification": None,
            "risk_flags":          [],
            "overall_risk_level":  "low",
            "retrieval_results":   [],
            "support_answer":      None,
            "escalation_record":   None,
            "success":             True,
            "error":               None,
        }

        final_state = app.invoke(initial_state)
        logger.info(f"Pipeline complete for ticket {ticket_data.get('ticket_id')}")
        return final_state

    except Exception as e:
        logger.error(f"Pipeline error for ticket {ticket_data.get('ticket_id')}: {e}")
        return {"success": False, "error": str(e)}


# ── BaseAgent subclass ─────────────────────────────────────────────

class SupportAgent(BaseAgent):
    """Support agent — inherits BaseAgent for Redis, heartbeats, and supervision."""

    agent_name = AgentName.SUPPORT

    def __init__(self):
        super().__init__()
        # Initialise external clients from service factories (env-driven)
        from .services import (
            get_helpscout_client,
            get_claude_client,
            get_qdrant_client,
            get_redis_bus,
            ResendClient,
        )
        import os
        self._helpscout = get_helpscout_client()
        self._claude    = get_claude_client()
        self._qdrant    = get_qdrant_client()
        self._resend    = ResendClient(
            api_key=os.environ.get("RESEND_API_KEY", ""),
            owner_email=os.environ.get("OWNER_EMAIL", ""),
        )
        # redis_bus: reuse the BaseAgent bus (already connected to Redis)
        self._redis_bus = get_redis_bus()

    async def setup_handlers(self) -> None:
        self.bus.on(EventType.TICKET_CREATED, self.run)

    async def run(self, event: BusinessEvent) -> None:
        try:
            result = run_support_pipeline(
                ticket_data=event["payload"],
                helpscout_client=self._helpscout,
                claude_client=self._claude,
                qdrant_client=self._qdrant,
                resend_client=self._resend,
                redis_bus=self._redis_bus,
            )
            if result.get("success"):
                await self.emit(
                    EventType.TICKET_RESOLVED,
                    result,
                    trace_id=event.get("trace_id"),
                )
        except Exception as e:
            await self.emit_error(str(e), trace_id=event.get("trace_id"))


if __name__ == "__main__":
    agent = SupportAgent()
    asyncio.run(agent.start())
