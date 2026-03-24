from typing import Any, Dict

from ..logging_config import get_logger

logger = get_logger("nodes.paid_channel_gate")


def make_paid_channel_gate_node(resend_client) -> callable:
    """Create the paid channel gate node."""

    def paid_channel_gate_node(state: Any) -> Dict[str, Any]:
        """Build paid channel suggestion report."""
        try:
            if not state.current_campaign:
                logger.warning("No current campaign, returning empty suggestions")
                return {
                    "has_paid_suggestions": False,
                    "suggested_channels": [],
                    "needs_user_approval": True,
                    "route_after_channel": "campaign_recorder",
                }

            # Get the route_after_channel value from state
            route_after_channel = getattr(
                state, "route_after_channel", "campaign_recorder"
            )

            # Build suggestion report
            suggested_channels = getattr(state, "paid_channels", [])

            if not suggested_channels:
                logger.info(
                    f"No paid channels suggested for campaign {state.current_campaign.campaign_id}"
                )
                return {
                    "has_paid_suggestions": False,
                    "suggested_channels": [],
                    "needs_user_approval": False,
                    "route_after_channel": route_after_channel,
                }

            logger.info(
                f"Paid channel gate for campaign {state.current_campaign.campaign_id}: "
                f"suggested {len(suggested_channels)} channels, needs approval=True"
            )

            return {
                "has_paid_suggestions": True,
                "suggested_channels": suggested_channels,
                "needs_user_approval": True,
                "route_after_channel": route_after_channel,
            }

        except Exception as e:
            logger.error(f"Error in paid_channel_gate_node: {e}")
            return {
                "has_paid_suggestions": False,
                "suggested_channels": [],
                "needs_user_approval": False,
                "route_after_channel": "campaign_recorder",
            }

    return paid_channel_gate_node
