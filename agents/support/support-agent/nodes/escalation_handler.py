import os
from datetime import datetime
from typing import Any, Dict

from .. import db
from ..db.connection import get_conn
from ..logging_config import get_logger

logger = get_logger("nodes.escalation_handler")


def make_escalation_handler_node(helpscout_client, resend_client, redis_bus) -> callable:
    """Create the escalation handler node."""

    def escalation_handler_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ticket escalation for medium/high risk tickets."""
        try:
            ticket = state.get("ticket", {})
            risk_flags = state.get("risk_flags", [])
            overall_level = state.get("overall_risk_level", "low")

            if overall_level == "low":
                return {**state, "escalation_record": None}

            ticket_id = ticket.get("ticket_id", "unknown")
            escalation = {
                "escalation_id": f"esc_{ticket_id}_{int(datetime.utcnow().timestamp())}",
                "ticket_id": ticket_id,
                "ticket_platform": ticket.get("platform", "helpscout"),
                "escalation_reason": overall_level,
                "original_message": ticket.get("message") or ticket.get("body", ""),
                "customer_identity": {
                    "email": ticket.get("customer_email"),
                    "name": ticket.get("customer_name"),
                    "order_id": ticket.get("order_id"),
                },
                "current_agent_context": f"risk_flags={risk_flags}",
                "escalation_time": datetime.utcnow(),
            }

            with get_conn() as conn:
                db.save_escalation(conn, escalation)

            helpscout_client.add_note(
                ticket_id=ticket_id,
                note=(
                    f"تم رفع هذا السؤال إلى الإدارة.\n"
                    f"التقييم: {overall_level}\n"
                    f"الأسباب: {risk_flags}"
                ),
            )

            admin_email = os.environ.get("SUPPORT_ADMIN_EMAIL", "admin@example.com")
            resend_client.send(
                to=admin_email,
                subject=f"Escalation: {ticket_id}",
                text=_format_escalation_email(escalation),
            )

            logger.info(f"Escalated ticket {ticket_id} — level: {overall_level}")

            return {**state, "escalation_record": escalation}

        except Exception as e:
            logger.error(f"Error in escalation_handler_node: {e}")
            return {**state, "escalation_record": None}

    return escalation_handler_node


def _format_escalation_email(escalation: Dict[str, Any]) -> str:
    """Format escalation email body."""
    identity = escalation.get("customer_identity", {})
    return (
        f"Escalation Alert\n"
        f"Ticket ID: {escalation['ticket_id']}\n"
        f"Risk Level: {escalation['escalation_reason']}\n"
        f"Timestamp: {escalation['escalation_time'].isoformat()}\n\n"
        f"Customer:\n"
        f"  Email: {identity.get('email')}\n"
        f"  Name: {identity.get('name')}\n"
        f"  Order ID: {identity.get('order_id')}\n\n"
        f"Original Message:\n{escalation['original_message']}\n"
    )
