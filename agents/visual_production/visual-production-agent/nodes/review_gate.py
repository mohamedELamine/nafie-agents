import logging
from datetime import datetime
from typing import Any, Dict

from ..db import save_manifest
from ..db.connection import get_conn

logger = logging.getLogger("visual_production.review_gate")


class ReviewGateNode:
    def __init__(self, resend, redis_bus):
        self.resend = resend
        self.redis = redis_bus

    async def __call__(
        self,
        processed_assets: Dict[str, Any],
        batch_id: str,
        theme_slug: str,
        version: str,
        owner_email: str,
    ) -> Dict[str, Any]:
        """Save checkpoint + send review request"""
        # Save checkpoint in Redis
        await self.redis.checkpoint_save(
            key=f"visual_review:{batch_id}",
            data={
                "batch_id": batch_id,
                "theme_slug": theme_slug,
                "version": version,
                "assets": processed_assets.get("processed", {}),
                "total_size_kb": processed_assets.get("total_size_kb", 0),
            },
            ttl=48 * 3600,
        )

        assets = processed_assets.get("processed", {})

        manifest = {
            "batch_id": batch_id,
            "theme_slug": theme_slug,
            "version": version,
            "assets": [],
            "total_cost": 0.0,
            "status": "review_pending",
            "created_at": datetime.utcnow().isoformat(),
            "notes": "Waiting for human review",
        }

        for asset_type, asset in assets.items():
            manifest["assets"].append(
                {
                    "asset_id": f"{batch_id}_{asset_type}",
                    "type": asset_type,
                    "url": f"/assets/{asset_type}/{batch_id}_{asset_type}.webp",
                    "dimensions": asset["dimensions"],
                    "size_kb": asset["size_kb"],
                    "quality_score": asset["quality_score"],
                    "status": "review_pending",
                }
            )

        # Save manifest to database
        with get_conn() as conn:
            save_manifest(conn, manifest)

        # Send review request email
        await self.resend.send_visual_review_request(
            to_email=owner_email,
            batch_id=batch_id,
            theme_slug=theme_slug,
            version=version,
            assets=manifest["assets"],
            total_cost=0.0,
        )

        logger.info(f"Sent review request for batch {batch_id}")

        return {
            "status": "review_pending",
            "batch_id": batch_id,
            "assets_count": len(manifest["assets"]),
            "assets": manifest["assets"],
        }
