import logging
from typing import Dict, Any

logger = logging.getLogger("visual_production.asset_publisher")


class AssetPublisherNode:
    def __init__(self, storage_client):
        self.storage = storage_client

    async def __call__(self, processed_assets: Dict[str, Any], batch_id: str) -> Dict[str, Any]:
        """Upload assets to storage and record URLs in manifest"""
        assets_with_urls = []

        processed = processed_assets.get("processed", {})

        for asset_type, asset in processed.items():
            image_bytes = asset.get("image_bytes", b"")
            asset_id = f"{batch_id}_{asset_type}"

            # Determine dimensions
            width, height = asset.get("dimensions", (1920, 1080))

            # Save to storage
            url = await self.storage.save_asset(
                asset_bytes=image_bytes,
                asset_id=asset_id,
                asset_type=asset_type,
                dimensions=(width, height),
            )

            asset_with_url = {
                "asset_id": asset_id,
                "type": asset_type,
                "url": url,
                "size_kb": asset.get("size_kb", 0),
                "quality_score": asset.get("quality_score", 0.5),
            }

            assets_with_urls.append(asset_with_url)

            logger.info(f"Published {asset_type} to {url}")

        return {"assets": assets_with_urls, "count": len(assets_with_urls)}


asset_publisher_node = AssetPublisherNode(storage_client=None)
