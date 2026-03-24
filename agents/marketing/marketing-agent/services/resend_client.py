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

    def send_campaign_launched(
        self,
        campaign_id: str,
        campaign_title: str,
        channels: List[str],
        scheduled_time: datetime,
        owner_email: Optional[str] = None,
        retry: int = 3,
    ) -> bool:
        """Send campaign launched notification."""
        try:
            email = owner_email or self.owner_email
            
            subject = f"🚀 Campaign Launched: {campaign_title}"
            body = f"""
            <h1>Campaign Launched Successfully</h1>
            <p><strong>Campaign:</strong> {campaign_title}</p>
            <p><strong>ID:</strong> {campaign_id}</p>
            <p><strong>Scheduled Time:</strong> {scheduled_time.isoformat()}</p>
            <p><strong>Channels:</strong> {', '.join(channels)}</p>
            <p>Your campaign has been scheduled and will be published automatically.</p>
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
                        logger.info(f"Sent campaign launched email: {response.id}")
                        return True
                    else:
                        logger.error(f"Failed to send campaign launched email: {response}")
                        return False

                except Exception as e:
                    logger.error(f"Error sending campaign launched email (attempt {attempt + 1}): {e}")
                    if attempt == retry - 1:
                        return False

        except Exception as e:
            logger.error(f"Error in send_campaign_launched: {e}")
            return False

    def send_publish_failed(
        self,
        post_id: str,
        campaign_id: str,
        channel: str,
        error: str,
        owner_email: Optional[str] = None,
        retry: int = 3,
    ) -> bool:
        """Send publish failed notification."""
        try:
            email = owner_email or self.owner_email
            
            subject = f"⚠️ Publish Failed: {channel} - {post_id}"
            body = f"""
            <h1>Publish Failed</h1>
            <p><strong>Post ID:</strong> {post_id}</p>
            <p><strong>Campaign:</strong> {campaign_id}</p>
            <p><strong>Channel:</strong> {channel}</p>
            <p><strong>Error:</strong> {error}</p>
            <p>The post failed to publish. The agent will retry automatically.</p>
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
                        logger.info(f"Sent publish failed email: {response.id}")
                        return True
                    else:
                        logger.error(f"Failed to send publish failed email: {response}")
                        return False

                except Exception as e:
                    logger.error(f"Error sending publish failed email (attempt {attempt + 1}): {e}")
                    if attempt == retry - 1:
                        return False

        except Exception as e:
            logger.error(f"Error in send_publish_failed: {e}")
            return False

    def send_paid_channel_suggestion(
        self,
        channel: str,
        reason: str,
        suggested_time: datetime,
        owner_email: Optional[str] = None,
        retry: int = 3,
    ) -> bool:
        """Send paid channel suggestion."""
        try:
            email = owner_email or self.owner_email
            
            subject = f"💰 Suggested: {channel} Paid Ad"
            body = f"""
            <h1>Paid Channel Suggestion</h1>
            <p><strong>Channel:</strong> {channel}</p>
            <p><strong>Reason:</strong> {reason}</p>
            <p><strong>Suggested Time:</strong> {suggested_time.isoformat()}</p>
            <p><strong>Note:</strong> This is a suggestion only. Please review and approve before enabling.</p>
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
                        logger.info(f"Sent paid channel suggestion email: {response.id}")
                        return True
                    else:
                        logger.error(f"Failed to send paid channel suggestion email: {response}")
                        return False

                except Exception as e:
                    logger.error(f"Error sending paid channel suggestion email (attempt {attempt + 1}): {e}")
                    if attempt == retry - 1:
                        return False

        except Exception as e:
            logger.error(f"Error in send_paid_channel_suggestion: {e}")
            return False


def send_campaign_launched(
    api_key: str,
    owner_email: str,
    campaign_id: str,
    campaign_title: str,
    channels: List[str],
    scheduled_time: datetime,
) -> bool:
    """Send campaign launched notification."""
    client = ResendClient(api_key, owner_email)
    return client.send_campaign_launched(
        campaign_id, campaign_title, channels, scheduled_time
    )


def send_publish_failed(
    api_key: str,
    owner_email: str,
    post_id: str,
    campaign_id: str,
    channel: str,
    error: str,
) -> bool:
    """Send publish failed notification."""
    client = ResendClient(api_key, owner_email)
    return client.send_publish_failed(post_id, campaign_id, channel, error)


def send_paid_channel_suggestion(
    api_key: str,
    owner_email: str,
    channel: str,
    reason: str,
    suggested_time: datetime,
) -> bool:
    """Send paid channel suggestion."""
    client = ResendClient(api_key, owner_email)
    return client.send_paid_channel_suggestion(channel, reason, suggested_time)