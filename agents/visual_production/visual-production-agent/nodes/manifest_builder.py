import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger("visual_production.manifest_builder")


class ManifestBuilderNode:
    def __init__(self, redis_bus):
        self.redis = redis_bus

    async def __call__(
        self, batch_id: str, theme_slug: str, approved_assets: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build final JSON manifest + publish event"""
        processed = approved_assets.get("processed", {})

        # Build manifest
        manifest = {
            "batch_id": batch_id,
            "theme_slug": theme_slug,
            "version": "1.0",
            "assets": [],
            "total_cost": 0.0,
            "status": "published",
            "published_at": datetime.utcnow().isoformat(),
        }

        for asset_type, asset in processed.items():
            asset_id = f"{batch_id}_{asset_type}"
            manifest["assets"].append(
                {
                    "asset_id": asset_id,
                    "type": asset_type,
                    "url": f"/assets/{asset_type}/{asset_id}.webp",
                    "dimensions": asset["dimensions"],
                    "size_kb": asset["size_kb"],
                    "quality_score": asset["quality_score"],
                }
            )

        # Build event
        event = await self.redis.build_event(
            event_type="THEME_ASSETS_READY",
            data={"batch_id": batch_id, "theme_slug": theme_slug, "assets": manifest["assets"]},
            source="visual_production_agent",
        )

        # Publish event
        await self.redis.publish(channel="product-events", message=event)

        logger.info(f"Published THEME_ASSETS_READY for batch {batch_id}")

        return {
            "batch_id": batch_id,
            "status": "published",
            "assets_count": len(manifest["assets"]),
            "event_published": True,
        }


manifest_builder_node = ManifestBuilderNode(redis_bus=None)
