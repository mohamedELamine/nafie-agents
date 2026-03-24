import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
PLATFORM_ROOT = PROJECT_ROOT / "agents" / "platform" / "platform-agent"
CONTENT_ROOT = PROJECT_ROOT / "agents" / "content" / "content-agent"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _module(name: str, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def test_new_product_live_event_flows_from_platform_to_content_requests():
    _module(
        "db.idempotency",
        check_completed=lambda *args, **kwargs: False,
        mark_started=lambda *args, **kwargs: None,
        mark_completed=lambda *args, **kwargs: None,
    )
    _module("db.registry", ProductRegistry=object)
    _module("services.redis_bus", RedisBus=object)
    _module("services.resend_client", ResendClient=object)
    _module(
        "state",
        LaunchState=dict,
        PlatformStatus=types.SimpleNamespace(COMPLETED="completed"),
    )

    launch_announcer = _load_module(
        "platform_launch_announcer_integration",
        PLATFORM_ROOT / "nodes" / "launch" / "launch_announcer.py",
    )

    redis_bus = MagicMock()
    redis_bus.build_event.side_effect = lambda **kwargs: kwargs
    resend = MagicMock()
    registry = types.SimpleNamespace(db=object())

    state = {
        "idempotency_key": "launch:theme-one:1.0.0",
        "theme_slug": "theme-one",
        "version": "1.0.0",
        "approved_event_id": "evt_1",
        "wp_post_url": "https://example.com/theme-one",
        "ls_product_id": "prod_1",
        "theme_contract": {"slug": "theme-one", "palette": ["sand"]},
        "parsed": {"theme_name_ar": "قالب واحد"},
        "logs": [],
    }

    launch_announcer.make_launch_announcer_node(registry, redis_bus, resend)(state)
    published_event = redis_bus.publish_stream.call_args.args[1]

    run_calls = []
    _module("agent", run_content_pipeline=lambda request, **kwargs: run_calls.append(request))
    _module("services.redis_bus", RedisBus=object)

    sys.path.insert(0, str(CONTENT_ROOT))
    content_models = _load_module("models", CONTENT_ROOT / "models.py")
    content_listener = _load_module(
        "content_listener_platform_integration",
        CONTENT_ROOT / "listeners" / "content_listener.py",
    )

    class _ImmediateThread:
        def __init__(self, target, args=(), kwargs=None, daemon=None):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}

        def start(self):
            self.target(*self.args, **self.kwargs)

    content_listener.threading.Thread = _ImmediateThread

    listener = content_listener.ContentListener(redis_bus=MagicMock())
    listener._dispatch(published_event)

    assert len(run_calls) == 2
    produced_types = {request.content_type for request in run_calls}
    assert produced_types == {
        content_models.ContentType.EMAIL_LAUNCH,
        content_models.ContentType.MARKETING_COPY,
    }
    assert {request.theme_slug for request in run_calls} == {"theme-one"}
    assert {request.target_agent for request in run_calls} == {"marketing_agent"}
    assert {request.correlation_id for request in run_calls} == {"evt_1"}
