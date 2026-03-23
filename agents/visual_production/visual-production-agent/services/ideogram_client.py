import os
import httpx
import logging
from typing import Optional, Tuple

logger = logging.getLogger("visual_production.ideogram_client")


class IdeogramClient:
    def __init__(self, api_key: str, timeout: int = 60):
        self.api_key = api_key
        self.base_url = "https://api.ideogram.ai/v1"
        self.timeout = timeout

    async def generate_with_text(
        self, prompt: str, arabic_text: str, dimensions: Tuple[int, int] = (1920, 1080)
    ) -> bytes:
        """Generate image with Arabic text using Ideogram"""
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        payload = {
            "image_size": f"{dimensions[0]}x{dimensions[1]}",
            "prompt": prompt,
            "text": arabic_text,
            "model": "Generative-2.0",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/generate", headers=headers, json=payload
                )
                response.raise_for_status()

                image_bytes = response.content
                logger.info(f"Ideogram generated image with text: {len(image_bytes)} bytes")

                return image_bytes

        except httpx.TimeoutException:
            logger.error("Ideogram API timeout")
            raise
        except Exception as e:
            logger.error(f"Ideogram API error: {e}")
            raise

    async def estimate_cost(self, asset_count: int) -> float:
        """Estimate cost for generating specified number of assets with text"""
        # Ideogram pricing: $0.03 per image with text
        cost_per_image = 0.03
        return round(asset_count * cost_per_image, 2)

    async def generate_with_dimensions(
        self, prompt: str, arabic_text: str, dimensions: Tuple[int, int]
    ) -> bytes:
        """Generate image with Arabic text at specified dimensions"""
        return await self.generate_with_text(prompt, arabic_text, dimensions)
