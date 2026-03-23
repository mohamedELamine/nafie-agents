from typing import Any, Dict, List

from ..models import MarketingChannel
from ..logging_config import get_logger

logger = get_logger("nodes.channel_router")


def make_channel_router_node() -> callable:
    """Create the channel router node."""

    AUTONOMOUS_CHANNELS = [
        MarketingChannel.FACEBOOK_PAGE.value,
        MarketingChannel.INSTAGRAM.value,
        MarketingChannel.TIKTOK.value,
        MarketingChannel.WHATSAPP_BUSINESS.value,
    ]

    PAID_CHANNELS = [
        MarketingChannel.GOOGLE_ADS.value,
        MarketingChannel.META_PAID_ADS.value,
    ]

    def channel_router_node(state: Any) -> Dict[str, Any]:
        """Route channels between autonomous and paid suggestions."""
        try:
            if not state.current_campaign:
                logger.warning("No current campaign, returning empty channels")
                return {
                    "autonomous_channels": [],
                    "paid_channels": [],
                    "route_after_channel": "paid_only",
                }

            # Start with no channels
            autonomous_channels = []
            paid_channels = []

            # Try to use user's primary channel if it's autonomous
            if (
                state.user_primary_channel
                and state.user_primary_channel in AUTONOMOUS_CHANNELS
            ):
                autonomous_channels.append(state.user_primary_channel)
                logger.info(
                    f"Using user's primary autonomous channel: {state.user_primary_channel}"
                )
            else:
                # If no user channel, use default autonomous channels
                autonomous_channels = AUTONOMOUS_CHANNELS[
                    :2
                ]  # Use first 2 autonomous channels

            # Add other autonomous channels if needed
            for channel in AUTONOMOUS_CHANNELS:
                if channel not in autonomous_channels and len(autonomous_channels) < 4:
                    autonomous_channels.append(channel)

            # Add paid channels as suggestions
            paid_channels = PAID_CHANNELS

            logger.info(
                f"Channel routing for campaign {state.current_campaign.campaign_id}: "
                f"autonomous={autonomous_channels}, paid={paid_channels}"
            )

            return {
                "autonomous_channels": autonomous_channels,
                "paid_channels": paid_channels,
                "route_after_channel": "paid_only",  # Always route to paid_only after autonomous
            }

        except Exception as e:
            logger.error(f"Error in channel_router_node: {e}")
            return {
                "autonomous_channels": [],
                "paid_channels": [],
                "route_after_channel": "paid_only",
            }

    return channel_router_node
