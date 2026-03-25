import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest


AGENT_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = AGENT_DIR.parents[2]

for path in (AGENT_DIR, ROOT_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


@pytest.fixture
def mock_claude_client() -> MagicMock:
    client = MagicMock()
    client.generate_content.return_value = []
    return client


@pytest.fixture
def sample_content_request():
    from models import ContentCategory, ContentRequest, ContentTrigger, ContentType

    return ContentRequest(
        request_id="req_123",
        trigger=ContentTrigger.EVENT,
        requester="event:NEW_PRODUCT_LIVE",
        content_type=ContentType.MARKETING_COPY,
        content_category=ContentCategory.COMMERCIAL,
        theme_slug="theme-one",
        theme_contract={"slug": "theme-one", "version": "1.0.0"},
        raw_context={"theme_slug": "theme-one"},
        target_agent="marketing_agent",
        correlation_id="corr_123",
        priority="normal",
        output_mode="variants",
        variant_count=2,
        evidence_contract=None,
        created_at=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_content_plan():
    from models import ContentCategory, ContentPlan, ContentType, ReviewPolicy

    return ContentPlan(
        request_id="req_123",
        content_type=ContentType.MARKETING_COPY,
        content_category=ContentCategory.COMMERCIAL,
        tone="confident",
        channel_style="social",
        structure=["hook", "value", "cta"],
        word_budget=120,
        key_messages=["RTL support", "WooCommerce ready"],
        context_bundle=None,
        fact_sheet=None,
        template_id=None,
        review_policy=ReviewPolicy.AUTO_IF_SCORE,
        output_mode="variants",
        variant_count=2,
    )


@pytest.fixture
def sample_fact_sheet():
    from models import FactSheet

    return FactSheet(
        verified_facts=["يدعم WooCommerce", "متوافق مع RTL"],
        allowed_inferences=["مناسب للمتاجر العربية"],
        forbidden_claims=["يزيد المبيعات 200%"],
        constitution_version="1.0",
        template_version="default",
    )
