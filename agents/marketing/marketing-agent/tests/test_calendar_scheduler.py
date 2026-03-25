from datetime import datetime, timedelta, timezone
from types import SimpleNamespace


def _clone_state(state, **updates):
    data = state.model_dump() if hasattr(state, "model_dump") else state.dict()
    data.update(updates)
    return state.__class__(**data)


def test_scheduled_time_equals_best_time_when_present(
    marketing_env: SimpleNamespace,
    mock_redis_bus,
    mock_get_conn,
    sample_campaign_state,
) -> None:
    module = marketing_env.load_module(
        "marketing_agent.nodes.calendar_scheduler",
        marketing_env.models.__file__.replace("models.py", "nodes/calendar_scheduler.py"),
    )
    module.get_conn = mock_get_conn
    module.marketing_calendar.schedule_post.reset_mock()

    result = module.make_calendar_scheduler_node(mock_redis_bus)(sample_campaign_state)

    assert result["success"] is True
    scheduled_post = module.marketing_calendar.schedule_post.call_args.args[1]
    assert scheduled_post["scheduled_time"] == sample_campaign_state.best_post_time


def test_scheduled_time_defaults_to_now_plus_one_hour_using_timezone_aware_now(
    marketing_env: SimpleNamespace,
    mock_redis_bus,
    mock_get_conn,
    sample_campaign_state,
) -> None:
    module = marketing_env.load_module(
        "marketing_agent.nodes.calendar_scheduler",
        marketing_env.models.__file__.replace("models.py", "nodes/calendar_scheduler.py"),
    )
    module.get_conn = mock_get_conn
    module.marketing_calendar.schedule_post.reset_mock()
    fixed_now = datetime(2026, 1, 10, 15, 0, tzinfo=timezone.utc)

    class FakeDateTime(datetime):
        called_with = None

        @classmethod
        def now(cls, tz=None):
            cls.called_with = tz
            return fixed_now

    state = _clone_state(sample_campaign_state, best_post_time=None)
    original_datetime = module.datetime
    module.datetime = FakeDateTime
    try:
        result = module.make_calendar_scheduler_node(mock_redis_bus)(state)
    finally:
        module.datetime = original_datetime

    assert result["success"] is True
    scheduled_post = module.marketing_calendar.schedule_post.call_args.args[1]
    assert scheduled_post["scheduled_time"] == fixed_now + timedelta(hours=1)
    assert FakeDateTime.called_with == timezone.utc
    assert scheduled_post["scheduled_time"].tzinfo == timezone.utc
