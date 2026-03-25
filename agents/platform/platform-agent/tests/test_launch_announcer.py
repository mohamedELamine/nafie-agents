from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from state import PlatformStatus


def test_launch_announcer_sends_resend_notification(
    platform_env: SimpleNamespace,
    sample_product_event,
) -> None:
    module = platform_env.load_module(
        "platform_launch_announcer_under_test",
        platform_env.agent_dir / "nodes" / "launch" / "launch_announcer.py",
    )
    registry = SimpleNamespace(db=MagicMock())
    redis_bus = MagicMock()
    redis_bus.build_event.side_effect = lambda **kwargs: kwargs
    resend = MagicMock()

    result = module.make_launch_announcer_node(registry, redis_bus, resend)(
        sample_product_event
    )

    assert result["status"].value == PlatformStatus.COMPLETED.value
    resend.send_launch_confirmation.assert_called_once()


def test_launch_announcer_uses_timezone_aware_launched_at(
    platform_env: SimpleNamespace,
    sample_product_event,
) -> None:
    module = platform_env.load_module(
        "platform_launch_announcer_under_test_tz",
        platform_env.agent_dir / "nodes" / "launch" / "launch_announcer.py",
    )
    registry = SimpleNamespace(db=MagicMock())
    redis_bus = MagicMock()
    redis_bus.build_event.side_effect = lambda **kwargs: kwargs
    resend = MagicMock()

    module.make_launch_announcer_node(registry, redis_bus, resend)(sample_product_event)

    launched_at = redis_bus.build_event.call_args.kwargs["data"]["launched_at"]
    assert datetime.fromisoformat(launched_at).tzinfo == timezone.utc
