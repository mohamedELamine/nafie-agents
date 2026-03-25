from datetime import datetime, timedelta, timezone
from types import SimpleNamespace


def _clone_state(state, **updates):
    data = state.model_dump() if hasattr(state, "model_dump") else state.dict()
    data.update(updates)
    return state.__class__(**data)


def test_node_returns_ready_when_content_and_assets_present(
    marketing_env: SimpleNamespace,
    sample_campaign_state,
) -> None:
    module = marketing_env.load_module(
        "marketing_agent.nodes.readiness_aggregator",
        marketing_env.models.__file__.replace("models.py", "nodes/readiness_aggregator.py"),
    )
    fixed_now = datetime(2026, 1, 10, 18, 0, tzinfo=timezone.utc)

    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    state = _clone_state(
        sample_campaign_state,
        product_launch_date=fixed_now - timedelta(hours=12),
    )
    original_datetime = module.datetime
    module.datetime = FakeDateTime
    try:
        result = module.make_readiness_aggregator_node(None)(state)
    finally:
        module.datetime = original_datetime

    assert result["readiness_status"] == "ready"
    assert result["has_content_ready"] is True
    assert result["has_assets_ready"] is True


def test_node_returns_not_ready_when_any_requirement_is_missing(
    marketing_env: SimpleNamespace,
    sample_campaign_state,
) -> None:
    module = marketing_env.load_module(
        "marketing_agent.nodes.readiness_aggregator",
        marketing_env.models.__file__.replace("models.py", "nodes/readiness_aggregator.py"),
    )
    fixed_now = datetime(2026, 1, 10, 18, 0, tzinfo=timezone.utc)

    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    state = _clone_state(
        sample_campaign_state,
        has_assets_ready=False,
        product_launch_date=fixed_now - timedelta(hours=12),
    )
    original_datetime = module.datetime
    module.datetime = FakeDateTime
    try:
        result = module.make_readiness_aggregator_node(None)(state)
    finally:
        module.datetime = original_datetime

    assert result["readiness_status"] == "partial"
    assert result["has_assets_ready"] is False


def test_node_calculates_time_since_launch_correctly(
    marketing_env: SimpleNamespace,
    sample_campaign_state,
) -> None:
    module = marketing_env.load_module(
        "marketing_agent.nodes.readiness_aggregator",
        marketing_env.models.__file__.replace("models.py", "nodes/readiness_aggregator.py"),
    )
    fixed_now = datetime(2026, 1, 11, 12, 0, tzinfo=timezone.utc)

    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    state = _clone_state(
        sample_campaign_state,
        product_launch_date=fixed_now - timedelta(hours=24),
    )
    original_datetime = module.datetime
    module.datetime = FakeDateTime
    try:
        result = module.make_readiness_aggregator_node(None)(state)
    finally:
        module.datetime = original_datetime

    assert result["time_since_launch"] == 24.0
