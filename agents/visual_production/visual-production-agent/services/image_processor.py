import logging
from io import BytesIO
from PIL import Image
from typing import Tuple, Optional

logger = logging.getLogger("visual_production.image_processor")


class ImageProcessor:
    def __init__(self, quality: int = 85):
        self.quality = quality

    async def to_webp(self, image_bytes: bytes, quality: Optional[int] = None) -> bytes:
        """Convert image to WebP format"""
        try:
            img = Image.open(BytesIO(image_bytes))
            img_bytes = BytesIO()

            # Convert to RGB if necessary
            if img.mode != "RGB":
                img = img.convert("RGB")

            img.save(img_bytes, format="WEBP", quality=quality or self.quality)

            webp_bytes = img_bytes.getvalue()
            logger.info(f"Converted to WebP: {len(image_bytes)} -> {len(webp_bytes)} bytes")

            return webp_bytes

        except Exception as e:
            logger.error(f"Error converting to WebP: {e}")
            raise

    async def validate_dimensions(
        self, image_bytes: bytes, expected_width: int, expected_height: int
    ) -> bool:
        """Validate image dimensions"""
        try:
            img = Image.open(BytesIO(image_bytes))
            actual_width, actual_height = img.size

            is_valid = actual_width == expected_width and actual_height == expected_height

            if not is_valid:
                logger.warning(
                    f"Dimension mismatch: expected {expected_width}x{expected_height}, "
                    f"got {actual_width}x{actual_height}"
                )

            return is_valid

        except Exception as e:
            logger.error(f"Error validating dimensions: {e}")
            return False

    async def resize(self, image_bytes: bytes, max_width: int) -> bytes:
        """Resize image to max width while maintaining aspect ratio"""
        try:
            img = Image.open(BytesIO(image_bytes))

            if img.mode != "RGB":
                img = img.convert("RGB")

            original_width, original_height = img.size

            if original_width <= max_width:
                logger.info(f"Image already within max width ({original_width}px < {max_width}px)")
                return image_bytes

            new_height = int(original_height * (max_width / original_width))
            resized = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            img_bytes = BytesIO()
            resized.save(img_bytes, format="WEBP", quality=self.quality)
            resized_bytes = img_bytes.getvalue()

            logger.info(
                f"Resized image: {original_width}x{original_height} -> {max_width}x{new_height}, "
                f"{len(image_bytes)} -> {len(resized_bytes)} bytes"
            )

            return resized_bytes

        except Exception as e:
            logger.error(f"Error resizing image: {e}")
            raise

    async def estimate_quality(self, image_bytes: bytes) -> float:
        """
        Estimate image quality (0-1) by analyzing artifacts and compression artifacts.
        This is a simple heuristic, not a comprehensive quality assessment.
        """
        try:
            img = Image.open(BytesIO(image_bytes))

            # Basic quality heuristic
            # - Larger file size relative to dimensions might indicate lower quality
            # - Check for visible artifacts

            width, height = img.size
            file_size_kb = len(image_bytes) / 1024

            # Normalize dimensions to 1920x1080 for comparison
            max_dimension = max(width, height)
            normalized_size = (1920 * 1080) / max_dimension
            quality = 1.0 - (file_size_kb / (normalized_size * 0.3))

            # Clamp quality between 0 and 1
            quality = max(0.0, min(1.0, quality))

            logger.info(f"Estimated quality: {quality:.2f}")

            return quality

        except Exception as e:
            logger.error(f"Error estimating quality: {e}")
            return 0.5  # Default to 0.5 if estimation fails
