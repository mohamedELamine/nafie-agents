import logging
from typing import Dict, Any, List
from ..models import AssetType, PromptBundle

logger = logging.getLogger("visual_production.prompt_builder")


class PromptBuilderNode:
    def __init__(self):
        self.base_prompts = {
            AssetType.HERO_IMAGE: "High-quality hero image for {domain} theme. Show the main value proposition.",
            AssetType.PRODUCT_CARD: "Product card image showing {domain} features. Professional and clean.",
            AssetType.SCREENSHOT_HOME: "Homepage screenshot for {domain} theme, showing main sections.",
            AssetType.SCREENSHOT_INNER: "Inner page screenshot showing {domain} functionality.",
            AssetType.VIDEO_PREVIEW: "Video preview thumbnail for {domain} theme showcase.",
        }

    def __call__(
        self,
        domain: str,
        cluster: str,
        colors: List[str],
        features: List[str],
        asset_type: AssetType,
    ) -> Dict[str, Any]:
        """Build prompt with 5 layers: base + domain + cluster + style + negative"""
        base_prompt = self.base_prompts[asset_type]

        # Layer 1: Base + Domain
        prompt = base_prompt.format(domain=domain)

        # Layer 2: Cluster context
        if cluster:
            prompt += f" This is for a {cluster} website."

        # Layer 3: Style requirements
        prompt += " Modern, professional, and clean design."

        # Layer 4: Features
        if features:
            prompt += f" Showcase: {', '.join(features)}"

        # Layer 5: Negative prompt
        negative_prompt = (
            "no text, no watermarks, no logos, no people, "
            "no blurry images, no low quality, no shadows, no gradients"
        )

        # Add color preferences
        if colors:
            color_str = ", ".join(colors)
            prompt += f" Use these colors: {color_str}"

        logger.info(f"Built prompt for {asset_type}: {len(prompt)} chars")

        return {"prompt": prompt, "negative_prompt": negative_prompt}


prompt_builder_node = PromptBuilderNode()
