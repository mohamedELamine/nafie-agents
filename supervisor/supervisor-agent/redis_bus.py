"""Compatibility shim for legacy flat imports."""

from services.redis_bus import RedisBus, redis_bus

__all__ = ["RedisBus", "redis_bus"]
