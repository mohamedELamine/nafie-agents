import os
import httpx
import logging
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("visual_production.flux_client")


class FluxClient:
    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.base_url = "https://api.flux.ai/v1"
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def generate(
        self, prompt: str, negative_prompt: str, width: int = 1920, height: int = 1080
    ) -> bytes:
        """Generate image using Flux API"""
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "output_format": "webp",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/generate", headers=headers, json=payload
                )
                response.raise_for_status()

                image_bytes = response.content
                logger.info(f"Flux generated image: {len(image_bytes)} bytes")

                return image_bytes

        except httpx.TimeoutException:
            logger.error("Flux API timeout")
            raise
        except Exception as e:
            logger.error(f"Flux API error: {e}")
            raise

    async def estimate_cost(self, asset_count: int) -> float:
        """Estimate cost for generating specified number of assets"""
        # Flux pricing: $0.02 per image generation
        cost_per_image = 0.02
        return round(asset_count * cost_per_image, 2)

    async def generate_with_retry(
        self,
        prompt: str,
        negative_prompt: str,
        width: int = 1920,
        height: int = 1080,
        max_retries: int = 3,
    ) -> bytes:
        """Generate image with retry on timeout"""
        for attempt in range(max_retries):
            try:
                return await self.generate(prompt, negative_prompt, width, height)
            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"Flux timeout, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Flux API failed after {max_retries} retries")
                    raise
        raise Exception("Flux generation failed after max retries")

    async def generate_with_dimensions(
        self,
        prompt: str,
        dimensions: Tuple[int, int],
        negative_prompt: str = "no text, no watermarks, no logos, no people",
    ) -> bytes:
        """Generate image with specified dimensions"""
        width, height = dimensions
        return await self.generate(prompt, negative_prompt, width, height)
