import resend
from datetime import datetime
from typing import Any, Dict, Optional

from ..logging_config import get_logger

logger = get_logger("services.resend_client")


class ResendClient:
    """Client for Resend API for sending emails."""

    def __init__(self, api_key: str, owner_email: str):
        self.api_key = api_key
        self.owner_email = owner_email
        resend.api_key = api_key

    def send_escalation_alert(
        self,
        escalation_id: str,
        ticket_id: str,
        reason: str,
        original_message: str,
        customer_identity: Dict[str, Any],
        current_agent_context: str,
        retry: int = 3,
    ) -> bool:
        """Send escalation alert to owner."""
        try:
            email = self.owner_email
            
            subject = f"🔴 صعود تصعيد جديد: {escalation_id}"
            body = f"""
            <h1>escalation</h1>
            <p><strong>escalation_id:</strong> {escalation_id}</p>
            <p><strong>ticket_id:</strong> {ticket_id}</p>
            <p><strong>reason:</strong> {reason}</p>
            <p><strong>customer_identity:</strong> {customer_identity}</p>
            <p><strong>current_agent_context:</strong> {current_agent_context}</p>
            """
            
            for attempt in range(retry):
                try:
                    response = resend.Emails.send({
                        "from": "onboarding@resend.dev",
                        "to": [email],
                        "subject": subject,
                        "html": body,
                    })

                    if response.id:
                        logger.info(f"Sent escalation alert: {response.id}")
                        return True
                    else:
                        logger.error(f"Failed to send escalation alert: {response}")
                        return False

                except Exception as e:
                    logger.error(f"Error sending escalation alert (attempt {attempt + 1}): {e}")
                    if attempt == retry - 1:
                        return False

        except Exception as e:
            logger.error(f"Error in send_escalation_alert: {e}")
            return False

    def send_recurring_issue_alert(
        self,
        issue_type: str,
        issue_count: int,
        evidence_contract: str,
        retry: int = 3,
    ) -> bool:
        """Send recurring issue alert."""
        try:
            email = self.owner_email
            
            subject = f"⚠️ مشكلة متكررة: {issue_type} ({issue_count} occurrences)"
            body = f"""
            <h1>recurring_issue</h1>
            <p><strong>issue_type:</strong> {issue_type}</p>
            <p><strong>issue_count:</strong> {issue_count}</p>
            <p><strong>evidence_contract:</strong> {evidence_contract}</p>
            """
            
            for attempt in range(retry):
                try:
                    response = resend.Emails.send({
                        "from": "onboarding@resend.dev",
                        "to": [email],
                        "subject": subject,
                        "html": body,
                    })

                    if response.id:
                        logger.info(f"Sent recurring issue alert: {response.id}")
                        return True
                    else:
                        logger.error(f"Failed to send recurring issue alert: {response}")
                        return False

                except Exception as e:
                    logger.error(f"Error sending recurring issue alert (attempt {attempt + 1}): {e}")
                    if attempt == retry - 1:
                        return False

        except Exception as e:
            logger.error(f"Error in send_recurring_issue_alert: {e}")
            return False


def send_escalation_alert(
    api_key: str,
    owner_email: str,
    escalation_id: str,
    ticket_id: str,
    reason: str,
    original_message: str,
    customer_identity: Dict[str, Any],
    current_agent_context: str,
) -> bool:
    """Send escalation alert."""
    client = ResendClient(api_key, owner_email)
    return client.send_escalation_alert(
        escalation_id,
        ticket_id,
        reason,
        original_message,
        customer_identity,
        current_agent_context,
    )


def send_recurring_issue_alert(
    api_key: str,
    owner_email: str,
    issue_type: str,
    issue_count: int,
    evidence_contract: str,
) -> bool:
    """Send recurring issue alert."""
    client = ResendClient(api_key, owner_email)
    return client.send_recurring_issue_alert(
        issue_type,
        issue_count,
        evidence_contract,
    )