import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger("visual_production.storage_client")


class StorageClient:
    def __init__(self, storage_type: str = "local", storage_path: Optional[str] = None):
        self.storage_type = storage_type
        self.storage_path = storage_path or os.getenv("STORAGE_PATH", "/app/storage")
        os.makedirs(self.storage_path, exist_ok=True)

    async def save_asset(
        self, asset_bytes: bytes, asset_id: str, asset_type: str, dimensions: Tuple[int, int]
    ) -> str:
        """Save asset to storage and return URL"""
        try:
            # Create directory structure
            os.makedirs(os.path.join(self.storage_path, asset_type), exist_ok=True)

            # Generate filename
            filename = f"{asset_id}_{dimensions[0]}x{dimensions[1]}.webp"
            file_path = os.path.join(self.storage_path, asset_type, filename)

            # Save file
            with open(file_path, "wb") as f:
                f.write(asset_bytes)

            # Generate URL (for local storage)
            url = f"/assets/{asset_type}/{filename}"

            logger.info(f"Saved asset {asset_id}: {file_path}")

            return url

        except Exception as e:
            logger.error(f"Error saving asset: {e}")
            raise

    async def get_asset_url(self, asset_id: str, asset_type: str) -> Optional[str]:
        """Get asset URL by ID and type"""
        try:
            url = f"/assets/{asset_type}/{asset_id}.webp"
            return url

        except Exception as e:
            logger.error(f"Error getting asset URL: {e}")
            raise

    async def delete_asset(self, asset_id: str, asset_type: str) -> bool:
        """Delete asset from storage"""
        try:
            filename = f"{asset_id}.webp"
            file_path = os.path.join(self.storage_path, asset_type, filename)

            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted asset {asset_id}")
                return True
            else:
                logger.warning(f"Asset {asset_id} not found")
                return False

        except Exception as e:
            logger.error(f"Error deleting asset: {e}")
            raise

    async def get_asset_size(self, url: str) -> int:
        """Get asset size in bytes (for file storage)"""
        try:
            # For local storage, we need the actual file path
            if url.startswith("/assets/"):
                # Parse URL to get type and filename
                parts = url.split("/")
                asset_type = parts[2]
                filename = parts[3]

                file_path = os.path.join(self.storage_path, asset_type, filename)

                if os.path.exists(file_path):
                    return os.path.getsize(file_path)
                else:
                    return 0

            return 0

        except Exception as e:
            logger.error(f"Error getting asset size: {e}")
            return 0

    async def get_asset(self, asset_id: str, asset_type: str) -> Optional[bytes]:
        """Get asset from storage"""
        try:
            filename = f"{asset_id}.webp"
            file_path = os.path.join(self.storage_path, asset_type, filename)

            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    return f.read()

            logger.warning(f"Asset {asset_id} not found")
            return None

        except Exception as e:
            logger.error(f"Error getting asset: {e}")
            raise
