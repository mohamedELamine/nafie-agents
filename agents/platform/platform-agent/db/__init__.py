"""Platform DB surface for pooled connections and registry access."""

from .connection import get_conn
from .registry import ProductRegistry


def create_registry() -> ProductRegistry:
    """Build the shared ProductRegistry against the active DB pool."""
    return ProductRegistry(get_conn)


__all__ = ["ProductRegistry", "create_registry", "get_conn"]
