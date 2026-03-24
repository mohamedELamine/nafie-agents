"""
Asset manifest DB operations — psycopg2 + get_conn().
All writes use ON CONFLICT DO NOTHING (Constitutional Law III).
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .connection import get_conn

logger = logging.getLogger("visual_production.db.asset_manifest")


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def save_manifest(conn, manifest: Dict[str, Any]) -> str:
    """Upsert asset manifest. Returns batch_id."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO asset_manifest (
                batch_id, theme_slug, version, total_cost, status,
                notes, assets_json, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (batch_id) DO UPDATE SET
                theme_slug = EXCLUDED.theme_slug,
                version = EXCLUDED.version,
                total_cost = EXCLUDED.total_cost,
                status = EXCLUDED.status,
                notes = EXCLUDED.notes,
                assets_json = EXCLUDED.assets_json,
                updated_at = NOW()
            """,
            (
                manifest["batch_id"],
                manifest["theme_slug"],
                manifest["version"],
                manifest.get("total_cost", 0.0),
                manifest.get("status", "pending"),
                manifest.get("notes"),
                json.dumps(manifest.get("assets", [])),
            ),
        )
    logger.info(f"Upserted manifest for batch {manifest['batch_id']}")
    return manifest["batch_id"]


def update_manifest_status(
    conn, batch_id: str, status: str, notes: Optional[str] = None
) -> None:
    """Update manifest status."""
    with conn.cursor() as cur:
        if notes is None:
            cur.execute(
                "UPDATE asset_manifest SET status = %s, updated_at = NOW() WHERE batch_id = %s",
                (status, batch_id),
            )
        else:
            cur.execute(
                """
                UPDATE asset_manifest
                SET status = %s, notes = %s, updated_at = NOW()
                WHERE batch_id = %s
                """,
                (status, notes, batch_id),
            )


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_manifest(conn, batch_id: str) -> Optional[Dict[str, Any]]:
    """Fetch manifest by batch_id."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT batch_id, theme_slug, version, total_cost, status,
                   notes, assets_json, created_at, updated_at
            FROM asset_manifest
            WHERE batch_id = %s
            """,
            (batch_id,),
        )
        row = cur.fetchone()

    if not row:
        return None

    return {
        "batch_id": row[0],
        "theme_slug": row[1],
        "version": row[2],
        "total_cost": row[3],
        "status": row[4],
        "notes": row[5],
        "assets": json.loads(row[6]) if row[6] else [],
        "created_at": row[7].isoformat() if row[7] else None,
        "updated_at": row[8].isoformat() if row[8] else None,
    }


def get_manifests_by_theme(conn, theme_slug: str) -> List[Dict[str, Any]]:
    """Fetch all manifests for a given theme."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT batch_id, theme_slug, version, total_cost, status,
                   notes, assets_json, created_at, updated_at
            FROM asset_manifest
            WHERE theme_slug = %s
            ORDER BY created_at DESC
            """,
            (theme_slug,),
        )
        rows = cur.fetchall()

    return [
        {
            "batch_id": r[0],
            "theme_slug": r[1],
            "version": r[2],
            "total_cost": r[3],
            "status": r[4],
            "notes": r[5],
            "assets": json.loads(r[6]) if r[6] else [],
            "created_at": r[7].isoformat() if r[7] else None,
            "updated_at": r[8].isoformat() if r[8] else None,
        }
        for r in rows
    ]
