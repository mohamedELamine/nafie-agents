import asyncio
import logging
from typing import Any, Dict, List

from ..models import AssetType, PromptBundle

logger = logging.getLogger("visual_production.multi_generator")


class MultiGeneratorNode:
    def __init__(self, flux_client, ideogram_client):
        self.flux = flux_client
        self.ideogram = ideogram_client

    async def __call__(
        self, prompt_bundles: Dict[str, PromptBundle]
    ) -> Dict[str, Dict[str, Any]]:
        """Generate assets in parallel using asyncio.gather"""
        asset_types: List[str] = []
        tasks = []

        for asset_type, bundle in prompt_bundles.items():
            if asset_type == AssetType.VIDEO_PREVIEW:
                logger.info("Skipping video preview generation (not implemented)")
                continue

            asset_types.append(asset_type)
            if bundle.generator == "ideogram":
                tasks.append(self._generate_with_ideogram(asset_type, bundle))
            else:
                tasks.append(self._generate_with_flux(asset_type, bundle))

        # gather returns results in the same order as tasks
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        generated_assets: Dict[str, Any] = {}
        failed_assets: Dict[str, str] = {}

        for asset_type, result in zip(asset_types, raw_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to generate {asset_type}: {result}")
                failed_assets[asset_type] = str(result)
            elif isinstance(result, dict):
                generated_assets[asset_type] = result

        total_generated = len(generated_assets)
        total_failed = len(failed_assets)

        logger.info(
            f"Generated {total_generated}/{len(tasks)} assets "
            f"({total_failed} failed)"
        )

        return {
            "generated": generated_assets,
            "failed": failed_assets,
            "total_generated": total_generated,
            "total_failed": total_failed,
        }

    async def _generate_with_flux(
        self, asset_type: str, bundle: PromptBundle
    ) -> Dict[str, Any]:
        """Generate using Flux API"""
        width, height = bundle.dimensions

        image_bytes = await self.flux.generate_with_retry(
            prompt=bundle.positive_prompt,
            negative_prompt=bundle.negative_prompt,
            width=width,
            height=height,
        )

        return {
            "asset_type": asset_type,
            "generator": "flux",
            "image_bytes": image_bytes,
            "dimensions": bundle.dimensions,
        }

    async def _generate_with_ideogram(
        self, asset_type: str, bundle: PromptBundle
    ) -> Dict[str, Any]:
        """Generate using Ideogram API with Arabic text"""
        image_bytes = await self.ideogram.generate_with_text(
            prompt=bundle.positive_prompt,
            arabic_text=bundle.positive_prompt[:50],
            dimensions=bundle.dimensions,
        )

        return {
            "asset_type": asset_type,
            "generator": "ideogram",
            "image_bytes": image_bytes,
            "dimensions": bundle.dimensions,
        }
