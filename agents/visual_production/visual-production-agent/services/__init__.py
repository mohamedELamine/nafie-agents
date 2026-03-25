import os
from urllib.parse import urlparse

from .flux_client import FluxClient
from .ideogram_client import IdeogramClient
from .image_processor import ImageProcessor
from .redis_bus import RedisBus
from .resend_client import ResendClient
from .storage_client import StorageClient


def get_flux_client() -> FluxClient:
    return FluxClient(api_key=os.getenv("FLUX_API_KEY", ""))


def get_ideogram_client() -> IdeogramClient:
    return IdeogramClient(api_key=os.getenv("IDEOGRAM_API_KEY", ""))


def get_image_processor() -> ImageProcessor:
    return ImageProcessor()


def get_storage_client() -> StorageClient:
    return StorageClient(
        storage_type=os.getenv("STORAGE_TYPE", "local"),
        storage_path=os.getenv("STORAGE_PATH"),
    )


def get_redis_bus() -> RedisBus:
    parsed = urlparse(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    db = int((parsed.path or "/0").lstrip("/") or "0")
    return RedisBus(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        db=db,
    )


def get_resend_client() -> ResendClient:
    return ResendClient(api_key=os.getenv("RESEND_API_KEY", ""))


__all__ = [
    "FluxClient",
    "IdeogramClient",
    "ImageProcessor",
    "RedisBus",
    "ResendClient",
    "StorageClient",
    "get_flux_client",
    "get_ideogram_client",
    "get_image_processor",
    "get_storage_client",
    "get_redis_bus",
    "get_resend_client",
]
