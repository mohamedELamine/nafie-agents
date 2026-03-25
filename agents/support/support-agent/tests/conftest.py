"""
Shared fixtures for support-agent tests.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock

# Ensure the support-agent package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── Client mocks ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_helpscout_client():
    client = MagicMock()
    client.get_conversation.return_value = {
        "subject": "Problem with my license",
        "body": "I cannot activate my license key.",
    }
    client.add_note.return_value = True
    return client


@pytest.fixture
def mock_claude_client():
    client = MagicMock()
    client.classify_risk.return_value = ([], "low")
    return client


@pytest.fixture
def mock_qdrant_client():
    client = MagicMock()
    client.retrieve_knowledge.return_value = [
        {
            "answer": "Go to Settings → License and enter your key.",
            "score": 0.92,
            "source": "docs/license-activation.md",
        }
    ]
    return client


@pytest.fixture
def mock_resend_client():
    client = MagicMock()
    client.send.return_value = True
    return client


@pytest.fixture
def mock_redis_bus():
    bus = MagicMock()
    bus.publish.return_value = True
    return bus


# ─── Common state fixtures ───────────────────────────────────────────────────

@pytest.fixture
def base_ticket():
    return {
        "ticket_id": "ticket_001",
        "platform": "helpscout",
        "customer_email": "customer@example.com",
        "customer_name": "Ahmed Ali",
        "message": "I cannot activate my license key.",
        "subject": "License problem",
        "order_id": "ORD-123",
        "is_html": False,
    }


@pytest.fixture
def base_state(base_ticket):
    return {
        "ticket": base_ticket,
        "platform": "helpscout",
        "intent_classification": None,
        "risk_flags": [],
        "overall_risk_level": "low",
        "retrieval_results": [],
        "support_answer": None,
        "escalation_record": None,
        "success": True,
    }


@pytest.fixture
def state_with_intent(base_state):
    return {
        **base_state,
        "intent_classification": {
            "category": "technical",
            "intent_category": "technical",
            "confidence": 0.95,
        },
    }


@pytest.fixture
def state_with_answer(state_with_intent):
    return {
        **state_with_intent,
        "support_answer": {
            "answer_text": "Go to Settings → License and enter your key.",
            "confidence": 0.92,
            "sources": ["docs/license-activation.md"],
        },
    }
