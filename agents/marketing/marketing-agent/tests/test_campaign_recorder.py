from datetime import datetime, timezone
from types import SimpleNamespace

from core.contracts import EVENT_CAMPAIGN_LAUNCHED, EVENT_POST_PUBLISHED, STREAM_MARKETING_EVENTS


def test_campaign_recorder_records_each_post_id_via_get_conn(
    marketing_env: SimpleNamespace,
    mock_redis_bus,
    mock_get_conn,
    sample_campaign_state,
) -> None:
    module = marketing_env.load_module(
        "marketing_agent.nodes.campaign_recorder",
        marketing_env.models.__file__.replace("models.py", "nodes/campaign_recorder.py"),
    )
    module.get_conn = mock_get_conn
    module.marketing_calendar.get_scheduled_posts.return_value = [
        {
            "post_id": "post_1",
            "channel": "instagram",
            "format": "reel",
            "status": "published",
            "published_at": datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc),
            "scheduled_time": datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc),
        },
        {
            "post_id": "post_2",
            "channel": "facebook_page",
            "format": "feed_image",
            "status": "failed",
            "failure_reason": "rate_limited",
            "scheduled_time": datetime(2026, 1, 2, 13, 0, tzinfo=timezone.utc),
        },
        {
            "post_id": "post_3",
            "channel": "tiktok",
            "format": "story_video",
            "status": "scheduled",
            "scheduled_time": datetime(2026, 1, 2, 14, 0, tzinfo=timezone.utc),
        },
    ]

    result = module.make_campaign_recorder_node(mock_redis_bus)(sample_campaign_state)

    assert result["has_events"] is True
    assert mock_get_conn.calls == 1
    saved_post_ids = [
        call.args[1]["details"]["post_id"]
        for call in module.campaign_log.save_log.call_args_list
    ]
    assert saved_post_ids == ["post_1", "post_2", "post_3"]


def test_campaign_recorder_handles_published_failed_and_scheduled_posts_separately(
    marketing_env: SimpleNamespace,
    mock_redis_bus,
    mock_get_conn,
    sample_campaign_state,
) -> None:
    module = marketing_env.load_module(
        "marketing_agent.nodes.campaign_recorder",
        marketing_env.models.__file__.replace("models.py", "nodes/campaign_recorder.py"),
    )
    module.get_conn = mock_get_conn
    module.marketing_calendar.get_scheduled_posts.return_value = [
        {
            "post_id": "post_pub",
            "channel": "instagram",
            "format": "reel",
            "status": "published",
            "published_at": datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc),
            "scheduled_time": datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc),
        },
        {
            "post_id": "post_fail",
            "channel": "facebook_page",
            "format": "feed_image",
            "status": "failed",
            "failure_reason": "api_error",
            "scheduled_time": datetime(2026, 1, 2, 13, 0, tzinfo=timezone.utc),
        },
        {
            "post_id": "post_sched",
            "channel": "tiktok",
            "format": "story_video",
            "status": "scheduled",
            "scheduled_time": datetime(2026, 1, 2, 14, 0, tzinfo=timezone.utc),
        },
    ]

    result = module.make_campaign_recorder_node(mock_redis_bus)(sample_campaign_state)

    assert [event["event_type"] for event in result["events"]] == [
        "POST_PUBLISHED",
        "POST_FAILED",
        "POST_SCHEDULED",
    ]


def test_campaign_recorder_emits_stream_events_for_published_posts_only(
    marketing_env: SimpleNamespace,
    mock_redis_bus,
    mock_get_conn,
    sample_campaign_state,
) -> None:
    module = marketing_env.load_module(
        "marketing_agent.nodes.campaign_recorder",
        marketing_env.models.__file__.replace("models.py", "nodes/campaign_recorder.py"),
    )
    module.get_conn = mock_get_conn
    module.marketing_calendar.get_scheduled_posts.return_value = [
        {
            "post_id": "post_1",
            "channel": "instagram",
            "format": "reel",
            "status": "published",
            "published_at": datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc),
            "scheduled_time": datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc),
        },
        {
            "post_id": "post_2",
            "channel": "facebook_page",
            "format": "feed_image",
            "status": "failed",
            "failure_reason": "api_error",
            "scheduled_time": datetime(2026, 1, 2, 13, 0, tzinfo=timezone.utc),
        },
    ]

    module.make_campaign_recorder_node(mock_redis_bus)(sample_campaign_state)

    publish_calls = [call.args for call in mock_redis_bus.publish_stream.call_args_list]
    assert (
        STREAM_MARKETING_EVENTS,
        {
            "event_type": EVENT_POST_PUBLISHED,
            "campaign_id": "camp_123",
            "theme_slug": "theme-one",
            "data": {
                "post_id": "post_1",
                "channel": "instagram",
                "format": "reel",
                "published_at": "2026-01-02T12:00:00+00:00",
            },
        },
    ) in publish_calls
    assert (
        STREAM_MARKETING_EVENTS,
        {
            "event_type": EVENT_CAMPAIGN_LAUNCHED,
            "campaign_id": "camp_123",
            "theme_slug": "theme-one",
            "data": {"published_posts": 1},
        },
    ) in publish_calls
