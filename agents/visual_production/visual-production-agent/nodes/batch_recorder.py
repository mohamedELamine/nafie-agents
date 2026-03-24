import logging
from datetime import datetime, timezone
from typing import Any, Dict

from ..db import save_manifest, save_batch
from ..db.connection import get_conn

logger = logging.getLogger("visual_production.batch_recorder")


class BatchRecorderNode:
    def __init__(self):
        """No DB dependencies — uses get_conn() directly."""

    async def __call__(
        self,
        batch_id: str,
        theme_slug: str,
        version: str,
        total_cost: float,
        assets: list,
        status: str,
    ) -> Dict[str, Any]:
        """Save batch log + asset manifest via connection pool."""
        batch_log = {
            "batch_id": batch_id,
            "theme_slug": theme_slug,
            "started_at": datetime.now(timezone.utc),
            "budget_used": total_cost,
            "assets_count": len(assets),
            "status": status,
        }

        manifest = {
            "batch_id": batch_id,
            "theme_slug": theme_slug,
            "version": version,
            "assets": assets,
            "total_cost": total_cost,
            "status": status,
        }

        with get_conn() as conn:
            save_batch(conn, batch_log)
            save_manifest(conn, manifest)

        logger.info(f"Recorded batch {batch_id} with {len(assets)} assets")

        return {"batch_id": batch_id, "status": status, "assets_count": len(assets)}
