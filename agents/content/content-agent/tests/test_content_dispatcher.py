import importlib.util
import pathlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

AGENT_ROOT = pathlib.Path(__file__).resolve().parents[1]
PROJECT_ROOT = AGENT_ROOT.parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

sys.modules.setdefault("redis", MagicMock())

services_pkg = types.ModuleType("services")
services_pkg.__path__ = [str(AGENT_ROOT / "services")]
redis_bus_stub = types.ModuleType("services.redis_bus")
redis_bus_stub.STREAM_ANALYTICS_EVENTS = "analytics-events"
services_pkg.redis_bus = redis_bus_stub
sys.modules["services"] = services_pkg
sys.modules["services.redis_bus"] = redis_bus_stub


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

from core.contracts import EVENT_CONTENT_READY, STREAM_CONTENT_EVENTS

content_dispatcher = _load_module(
    "content_dispatcher_under_test",
    AGENT_ROOT / "nodes" / "content_dispatcher.py",
)
make_content_dispatcher_node = content_dispatcher.make_content_dispatcher_node


def test_content_dispatcher_publishes_content_ready_to_stream():
    redis_bus = MagicMock()
    redis_bus.build_event.side_effect = lambda **kwargs: kwargs

    piece = SimpleNamespace(
        content_id="content_1",
        content_type=SimpleNamespace(value="email_launch"),
        theme_slug="theme-one",
        title="Launch email",
        body="Body copy",
        metadata={"locale": "ar"},
        validation_score=0.91,
    )
    request = SimpleNamespace(
        request_id="req_1",
        correlation_id="corr_1",
        target_agent="marketing_agent",
    )

    result = make_content_dispatcher_node(redis_bus)(
        {
            "content_piece": piece,
            "content_pieces": [piece],
            "request": request,
        }
    )

    assert result["status"] == "dispatched"
    redis_bus.publish_stream.assert_any_call(
        STREAM_CONTENT_EVENTS,
        {
            "event_type": EVENT_CONTENT_READY,
            "data": {
                "content_id": "content_1",
                "content_type": "email_launch",
                "theme_slug": "theme-one",
                "title": "Launch email",
                "body": "Body copy",
                "variants": None,
                "metadata": {"locale": "ar"},
                "validation_score": 0.91,
                "request_id": "req_1",
                "target_agent": "marketing_agent",
            },
            "correlation_id": "corr_1",
        },
    )
