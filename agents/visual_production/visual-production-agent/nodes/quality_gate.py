import logging
from typing import Dict, Any

logger = logging.getLogger("visual_production.quality_gate")


class QualityGateNode:
    def __init__(self, image_processor, max_size_kb: float = 2048.0):
        self.processor = image_processor
        self.max_size_kb = max_size_kb
        self.min_dimensions = (400, 300)  # Minimum acceptable dimensions

    def __call__(self, generated_assets: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Quality check: dimensions + size + quality score"""
        approved_assets = {}
        rejected_assets = []

        for asset_type, asset in generated_assets.items():
            image_bytes = asset.get("image_bytes", b"")

            # Check 1: Dimensions
            width, height = asset.get("dimensions", (0, 0))
            dimensions_ok = width >= self.min_dimensions[0] and height >= self.min_dimensions[1]

            # Check 2: Size
            size_kb = len(image_bytes) / 1024
            size_ok = size_kb <= self.max_size_kb

            # Check 3: Quality estimate
            quality_score = self.processor.estimate_quality(image_bytes)
            quality_ok = quality_score >= 0.5  # Minimum 0.5 quality

            # Determine result
            if dimensions_ok and size_ok and quality_ok:
                approved_assets[asset_type] = asset
                approved_assets[asset_type]["quality_score"] = quality_score
                approved_assets[asset_type]["size_kb"] = size_kb
                approved_assets[asset_type]["dimensions_ok"] = True
            else:
                rejected_assets.append({"asset_type": asset_type, "reasons": []})

                if not dimensions_ok:
                    rejected_assets[-1]["reasons"].append(f"Invalid dimensions: {width}x{height}")
                if not size_ok:
                    rejected_assets[-1]["reasons"].append(
                        f"Too large: {size_kb:.1f}KB (max {self.max_size_kb}KB)"
                    )
                if not quality_ok:
                    rejected_assets[-1]["reasons"].append(f"Low quality: {quality_score:.2f}")

        logger.info(
            f"Quality gate: {len(approved_assets)} approved, {len(rejected_assets)} rejected"
        )

        return {
            "approved": approved_assets,
            "rejected": rejected_assets,
            "approved_count": len(approved_assets),
            "rejected_count": len(rejected_assets),
        }


quality_gate_node = QualityGateNode(image_processor=None)
