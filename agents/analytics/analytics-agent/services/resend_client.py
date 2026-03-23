import resend
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..logging_config import get_logger

logger = get_logger("services.resend_client")


class ResendClient:
    """Client for Resend API for sending emails."""

    def __init__(self, api_key: str, owner_email: str):
        self.api_key = api_key
        self.owner_email = owner_email
        resend.api_key = api_key

    def send_owner_alert(
        self,
        subject: str,
        body: str,
        template_data: Optional[Dict[str, Any]] = None,
        retry: int = 3,
    ) -> bool:
        """Send critical alert to owner with retry."""
        for attempt in range(retry):
            try:
                response = resend.Emails.send(
                    from="onboarding@resend.dev",
                    to=[self.owner_email],
                    subject=subject,
                    html=body,
                    template_data=template_data,
                )

                if response.id:
                    logger.info(f"Sent owner alert: {response.id}")
                    return True
                else:
                    logger.error(f"Failed to send owner alert: {response}")
                    return False

            except Exception as e:
                logger.error(f"Error sending owner alert (attempt {attempt + 1}): {e}")
                if attempt == retry - 1:
                    return False

        return False

    def send_weekly_report(
        self,
        subject: str,
        html_content: str,
        template_data: Optional[Dict[str, Any]] = None,
        retry: int = 3,
    ) -> bool:
        """Send weekly report to owner with retry."""
        for attempt in range(retry):
            try:
                response = resend.Emails.send(
                    from="onboarding@resend.dev",
                    to=[self.owner_email],
                    subject=subject,
                    html=html_content,
                    template_data=template_data,
                )

                if response.id:
                    logger.info(f"Sent weekly report: {response.id}")
                    return True
                else:
                    logger.error(f"Failed to send weekly report: {response}")
                    return False

            except Exception as e:
                logger.error(f"Error sending weekly report (attempt {attempt + 1}): {e}")
                if attempt == retry - 1:
                    return False

        return False


def send_owner_alert(
    api_key: str,
    owner_email: str,
    subject: str,
    body: str,
    template_data: Optional[Dict[str, Any]] = None,
    retry: int = 3,
) -> bool:
    """Send critical alert to owner."""
    client = ResendClient(api_key, owner_email)
    return client.send_owner_alert(subject, body, template_data, retry)


def send_weekly_report(
    api_key: str,
    owner_email: str,
    subject: str,
    html_content: str,
    template_data: Optional[Dict[str, Any]] = None,
    retry: int = 3,
) -> bool:
    """Send weekly report."""
    client = ResendClient(api_key, owner_email)
    return client.send_weekly_report(subject, html_content, template_data, retry)