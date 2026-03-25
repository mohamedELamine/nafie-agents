from datetime import datetime, timezone
from typing import Any, Dict

from ..models import AssetSnapshot
from ..state import MarketingState, update_state_with_assets
from ..logging_config import get_logger

logger = get_logger("nodes.asset_collector")


def make_asset_collector_node() -> callable:
    """Create the asset collector node."""

    def asset_collector_node(state: MarketingState) -> Dict[str, Any]:
        """Collect and freeze assets for the campaign."""
        try:
            if not state.current_campaign:
                logger.warning("No current campaign, returning error")
                return {
                    "success": False,
                    "reason": "no_campaign",
                }

            # Check if we already have assets
            if state.assets_snapshot:
                logger.info(
                    f"Assets already collected for campaign {state.current_campaign.campaign_id}"
                )
                return {
                    "success": True,
                    "message": "assets_already_frozen",
                }

            # Create asset snapshot
            assets_snapshot = AssetSnapshot(
                asset_id=f"assets_{state.current_campaign.campaign_id}_{int(datetime.now(timezone.utc).timestamp())}",
                campaign_id=state.current_campaign.campaign_id,
                asset_data={
                    "campaign_id": state.current_campaign.campaign_id,
                    "theme_slug": state.current_campaign.theme_slug,
                    "frozen_at": datetime.now(timezone.utc).isoformat(),
                    "data": {},
                },
                snapshot_date=datetime.now(timezone.utc),
            )

            # Update state
            new_state = update_state_with_assets(state, assets_snapshot)

            logger.info(
                f"Assets frozen for campaign {state.current_campaign.campaign_id}"
            )
            return {
                "success": True,
                "assets_snapshot_id": assets_snapshot.asset_id,
            }

        except Exception as e:
            logger.error(f"Error in asset_collector_node: {e}")
            return {
                "success": False,
                "reason": f"error: {str(e)}",
            }

    return asset_collector_node
