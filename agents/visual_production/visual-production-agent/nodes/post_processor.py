import logging
from typing import Dict, Any

logger = logging.getLogger("visual_production.post_processor")


class PostProcessorNode:
    def __init__(self, image_processor):
        self.processor = image_processor

    def __call__(self, approved_assets: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Convert to WebP + resize + compress approved assets"""
        processed_assets = {}

        for asset_type, asset in approved_assets.items():
            image_bytes = asset.get("image_bytes", b"")
            dimensions = asset.get("dimensions", (1920, 1080))

            # Determine max width based on asset type
            if asset_type == AssetType.HERO_IMAGE:
                max_width = 1920
            elif asset_type == AssetType.PRODUCT_CARD:
                max_width = 800
            else:
                max_width = 1200

            # Convert to WebP
            webp_bytes = self.processor.to_webp(image_bytes, quality=85)

            # Resize if needed
            if dimensions[0] > max_width:
                webp_bytes = self.processor.resize(webp_bytes, max_width)

            # Estimate new size
            size_kb = len(webp_bytes) / 1024

            processed_assets[asset_type] = {
                "image_bytes": webp_bytes,
                "dimensions": dimensions,
                "size_kb": size_kb,
                "quality_score": self.processor.estimate_quality(webp_bytes),
            }

            logger.info(f"Processed {asset_type}: {size_kb:.1f}KB ({len(webp_bytes)} bytes)")

        return {
            "processed": processed_assets,
            "total_size_kb": sum(a["size_kb"] for a in processed_assets.values()),
        }


post_processor_node = PostProcessorNode(image_processor=None)
