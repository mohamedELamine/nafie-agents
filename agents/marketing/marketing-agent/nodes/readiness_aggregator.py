from datetime import datetime, timezone
from typing import Any, Dict

from ..logging_config import get_logger
from ..state import MarketingState

logger = get_logger("nodes.readiness_aggregator")


def make_readiness_aggregator_node(redis) -> callable:
    """Create the readiness aggregator node."""

    def readiness_aggregator_node(state: MarketingState) -> Dict[str, Any]:
        """Aggregate readiness status."""
        try:
            if not state.current_campaign:
                logger.warning("No current campaign, returning pending status")
                return {
                    "readiness_status": "pending",
                    "reason": "no_campaign",
                    "has_content_ready": False,
                    "has_assets_ready": False,
                }

            has_content = state.has_content_ready
            has_assets = state.has_assets_ready

            # Check product launch date
            product_live = False
            if state.product_launch_date:
                hours_since_launch = (
                    datetime.now(timezone.utc) - state.product_launch_date
                ).total_seconds() / 3600
                product_live = hours_since_launch <= 48  # 48 hours timeout

            # Evaluate readiness
            if has_content and has_assets and product_live:
                status = "ready"
                reason = "all_requirements_met"
            elif product_live and not has_content and not has_assets:
                # Product live but no content/assets yet
                status = "waiting"
                reason = "waiting_for_content_and_assets"
            elif not product_live:
                status = "pending"
                reason = "waiting_for_product_launch"
            else:
                status = "partial"
                reason = "partial_requirements"

            logger.info(
                f"Readiness check for campaign {state.current_campaign.campaign_id}: "
                f"status={status}, content={has_content}, assets={has_assets}, product={product_live}"
            )

            return {
                "readiness_status": status,
                "reason": reason,
                "has_content_ready": has_content,
                "has_assets_ready": has_assets,
                "product_launch_date": state.product_launch_date.isoformat()
                if state.product_launch_date
                else None,
                "time_since_launch": (
                    (datetime.now(timezone.utc) - state.product_launch_date).total_seconds()
                    / 3600
                    if state.product_launch_date
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Error in readiness_aggregator_node: {e}")
            return {
                "readiness_status": "error",
                "reason": f"error: {str(e)}",
            }

    return readiness_aggregator_node
