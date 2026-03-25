import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch


AGENT_DIR = Path(__file__).resolve().parents[1]


def _load_listener_module():
    saved = {
        name: sys.modules.get(name)
        for name in ("agent", "services", "services.redis_bus", "content_listener_under_test")
    }

    agent_module = types.ModuleType("agent")
    agent_module.run_content_pipeline = MagicMock()
    sys.modules["agent"] = agent_module

    services_pkg = types.ModuleType("services")
    services_pkg.__path__ = [str(AGENT_DIR / "services")]
    redis_bus_module = types.ModuleType("services.redis_bus")
    redis_bus_module.RedisBus = object
    services_pkg.redis_bus = redis_bus_module
    sys.modules["services"] = services_pkg
    sys.modules["services.redis_bus"] = redis_bus_module

    try:
        spec = importlib.util.spec_from_file_location(
            "content_listener_under_test",
            AGENT_DIR / "listeners" / "content_listener.py",
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["content_listener_under_test"] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module, agent_module.run_content_pipeline, saved
    except Exception:
        for name, original in saved.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
        raise


def _restore_modules(saved) -> None:
    for name, original in saved.items():
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original


def test_listener_routes_content_request_event_to_pipeline() -> None:
    content_listener, mock_run, saved = _load_listener_module()
    listener = content_listener.ContentListener(redis_bus=MagicMock())
    event = {
        "event_type": content_listener.EVENT_CONTENT_REQUEST,
        "source": "marketing_agent",
        "correlation_id": "corr_123",
        "data": {
            "content_type": "marketing_copy",
            "theme_slug": "theme-one",
            "context": {"theme_slug": "theme-one"},
            "output_mode": "variants",
            "variant_count": 2,
        },
    }

    try:
        listener._dispatch(event)
    finally:
        _restore_modules(saved)

    request = mock_run.call_args.args[0]
    assert request.content_type.value == "marketing_copy"
    assert request.theme_slug == "theme-one"
    assert request.created_at.tzinfo is not None


def test_listener_skips_unknown_event_without_exception() -> None:
    content_listener, mock_run, saved = _load_listener_module()
    listener = content_listener.ContentListener(redis_bus=MagicMock())

    try:
        listener._dispatch({"event_type": "UNKNOWN_EVENT", "data": {}})
    finally:
        _restore_modules(saved)

    mock_run.assert_not_called()


def test_listener_start_uses_init_pool_and_consumer_groups() -> None:
    content_listener, _, saved = _load_listener_module()
    redis_bus = MagicMock()
    listener = content_listener.ContentListener(redis_bus=redis_bus)

    try:
        with patch.object(content_listener, "init_pool") as mock_init_pool, patch.object(
            listener, "_listen_loop"
        ) as mock_loop:
            listener.start()
    finally:
        _restore_modules(saved)

    mock_init_pool.assert_called_once_with()
    redis_bus.ensure_consumer_group.assert_any_call(
        content_listener.STREAM_PRODUCT_EVENTS,
        content_listener.CONSUMER_GROUP,
    )
    redis_bus.ensure_consumer_group.assert_any_call(
        content_listener.STREAM_CONTENT_EVENTS,
        content_listener.CONSUMER_GROUP,
    )
    mock_loop.assert_called_once_with()
