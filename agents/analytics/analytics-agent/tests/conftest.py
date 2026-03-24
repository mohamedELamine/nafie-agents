"""
Shared fixtures for analytics-agent tests.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock

# Make the analytics-agent package importable
_AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT_DIR  = os.path.abspath(os.path.join(_AGENT_DIR, "..", "..", ".."))
sys.path.insert(0, _AGENT_DIR)
sys.path.insert(0, _ROOT_DIR)  # يجعل `core.contracts` قابلاً للاستيراد


# ─── DB connection mock ──────────────────────────────────────────────────────

@pytest.fixture
def mock_conn():
    """A mock psycopg2 connection with cursor support."""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor
    return conn


@pytest.fixture
def mock_get_conn(mock_conn):
    """Patches get_conn context manager to yield mock_conn."""
    from contextlib import contextmanager

    @contextmanager
    def _fake_get_conn():
        yield mock_conn

    return _fake_get_conn


# ─── Redis mock ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_redis_client():
    client = MagicMock()
    client.get.return_value = None          # signal not seen recently
    client.set.return_value = True
    client.publish.return_value = 1
    return client


@pytest.fixture
def mock_redis_bus(mock_redis_client):
    bus = MagicMock()
    bus.client = mock_redis_client
    bus.publish.return_value = True
    return bus


# ─── Common event fixtures ───────────────────────────────────────────────────

@pytest.fixture
def new_sale_event():
    return {
        "event_id": "evt_sale_001",
        "event_type": "NEW_SALE",
        "source": "lemon_squeezy",
        "occurred_at": "2025-06-15T14:30:00",
        "data": {
            "theme_slug": "fashion-store-20260310",
            "amount_usd": 39.0,
            "license_tier": "pro",
            "channel": "facebook",
        },
    }


@pytest.fixture
def support_ticket_event():
    return {
        "event_id": "evt_support_001",
        "event_type": "SUPPORT_TICKET_OPENED",
        "source": "support_agent",
        "occurred_at": "2025-06-15T10:00:00",
        "data": {
            "theme_slug": "fashion-store-20260310",
            "ticket_id": "ticket_001",
            "platform": "helpscout",
        },
    }
