import logging
import os
from typing import Dict, Any

logger = logging.getLogger("visual_production.visual_listener")


class VisualListener:
    def __init__(self):
        pass

    async def on_theme_approved(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle THEME_APPROVED event"""
        theme_contract = event_data.get("theme_contract", {})
        theme_slug = theme_contract.get("slug", "unknown")
        version = theme_contract.get("version", "1.0")

        # Generate batch ID
        import uuid

        batch_id = f"{theme_slug}_{version}_{uuid.uuid4().hex[:8]}"

        logger.info(f"Received THEME_APPROVED for {theme_slug} v{version}")

        # Run visual pipeline
        from agent import visual_agent

        result = await visual_agent.run_visual_pipeline(
            theme_contract=theme_contract,
            batch_id=batch_id,
            version=version,
            owner_email=event_data.get("owner_email") or os.environ.get("VISUAL_OWNER_EMAIL", "admin@example.com"),
        )

        return result

    async def handle_event(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming events"""
        if event_type == "THEME_APPROVED":
            return await self.on_theme_approved(event_data)

        logger.warning(f"Unknown event type: {event_type}")
        return {"status": "ignored"}
