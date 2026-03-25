from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch


def _clone_state(state, **updates):
    data = state.model_dump() if hasattr(state, "model_dump") else state.dict()
    data.update(updates)
    return state.__class__(**data)


def test_node_extracts_best_time_and_best_channel_from_signal(
    marketing_env: SimpleNamespace,
    mock_redis_bus,
    sample_campaign_state,
) -> None:
    module = marketing_env.load_module(
        "marketing_agent.nodes.analytics_consumer",
        marketing_env.models.__file__.replace("models.py", "nodes/analytics_consumer.py"),
    )
    expected_time = datetime(2026, 1, 11, 9, 30, tzinfo=timezone.utc)
    mock_redis_bus.read_group.return_value = [
        {
            "__message_id": "1-0",
            "signal_type": "best_time",
            "data": {"best_time": expected_time.isoformat()},
        },
        {
            "__message_id": "2-0",
            "signal_type": "best_channel",
            "data": {"best_channel": "facebook_page"},
        },
    ]

    def _best_time_side_effect(state, best_time):
        return _clone_state(state, best_post_time=best_time)

    def _channel_side_effect(state, channels):
        assert state.best_post_time == expected_time
        return _clone_state(state, selected_channels=list(state.selected_channels) + channels)

    with patch.object(
        module,
        "update_state_with_best_post_time",
        side_effect=_best_time_side_effect,
    ) as mock_best_time, patch.object(
        module,
        "update_state_with_selected_channels",
        side_effect=_channel_side_effect,
    ) as mock_channels:
        result = module.make_analytics_consumer_node(mock_redis_bus)(sample_campaign_state)

    assert [signal["signal_type"] for signal in result["applied_signals"]] == [
        "best_time",
        "best_channel",
    ]
    assert mock_best_time.call_args.args[1] == expected_time
    assert mock_channels.call_args.args[1] == ["facebook_page"]
    assert mock_redis_bus.ack.call_count == 2


def test_node_ignores_unknown_signal_type_without_exception(
    marketing_env: SimpleNamespace,
    mock_redis_bus,
    sample_campaign_state,
) -> None:
    module = marketing_env.load_module(
        "marketing_agent.nodes.analytics_consumer",
        marketing_env.models.__file__.replace("models.py", "nodes/analytics_consumer.py"),
    )
    mock_redis_bus.read_group.return_value = [
        {"__message_id": "3-0", "signal_type": "unknown_signal", "data": {"value": 1}}
    ]

    with patch.object(module, "update_state_with_best_post_time") as mock_best_time, patch.object(
        module, "update_state_with_selected_channels"
    ) as mock_channels:
        result = module.make_analytics_consumer_node(mock_redis_bus)(sample_campaign_state)

    assert result["applied_signals"] == []
    mock_best_time.assert_not_called()
    mock_channels.assert_not_called()
    mock_redis_bus.ack.assert_called_once_with("analytics:signals", "3-0")


def test_node_updates_state_with_correct_values(
    marketing_env: SimpleNamespace,
    mock_redis_bus,
    sample_campaign_state,
) -> None:
    module = marketing_env.load_module(
        "marketing_agent.nodes.analytics_consumer",
        marketing_env.models.__file__.replace("models.py", "nodes/analytics_consumer.py"),
    )
    expected_time = datetime(2026, 1, 12, 14, 0, tzinfo=timezone.utc)
    applied_states = []
    mock_redis_bus.read_group.return_value = [
        {
            "__message_id": "4-0",
            "signal_type": "best_time",
            "data": {"best_time": expected_time.isoformat()},
        },
        {
            "__message_id": "5-0",
            "signal_type": "best_channel",
            "data": {"best_channel": ["instagram", "tiktok"]},
        },
    ]

    def _best_time_side_effect(state, best_time):
        updated = _clone_state(state, best_post_time=best_time)
        applied_states.append(updated)
        return updated

    def _channel_side_effect(state, channels):
        updated = _clone_state(state, selected_channels=channels)
        applied_states.append(updated)
        return updated

    with patch.object(
        module,
        "update_state_with_best_post_time",
        side_effect=_best_time_side_effect,
    ), patch.object(
        module,
        "update_state_with_selected_channels",
        side_effect=_channel_side_effect,
    ):
        module.make_analytics_consumer_node(mock_redis_bus)(sample_campaign_state)

    assert applied_states[0].best_post_time == expected_time
    assert applied_states[1].selected_channels == ["instagram", "tiktok"]
