from typing import Dict, Any
from ..models import AssetType


class AssetSelectorNode:
    def __call__(self, approved_assets: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Select best candidate for each asset type"""
        # Get minimum viable set: hero_image + product_card + 3 screenshots
        required_types = [
            AssetType.HERO_IMAGE,
            AssetType.PRODUCT_CARD,
            AssetType.SCREENSHOT_HOME,
            AssetType.SCREENSHOT_INNER,
        ]

        selected_assets = {}
        found_minimum = False

        for asset_type in required_types:
            if asset_type in approved_assets:
                selected_assets[asset_type] = approved_assets[asset_type]
                logger.info(f"Selected {asset_type}")
            else:
                logger.warning(f"Missing required asset: {asset_type}")

            if len(selected_assets) == 4:
                found_minimum = True
                break

        is_complete = len(selected_assets) == 4

        logger.info(f"Asset selection: {len(selected_assets)}/4 complete ({found_minimum=})")

        return {
            "selected": selected_assets,
            "complete": is_complete,
            "missing": [t for t in required_types if t not in selected_assets],
        }


asset_selector_node = AssetSelectorNode()
