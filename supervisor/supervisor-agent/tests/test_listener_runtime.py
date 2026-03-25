import asyncio
import importlib.util
import pathlib
import sys
import types
from unittest.mock import AsyncMock, MagicMock


SUPERVISOR_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _module(name: str, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_system_listener_applies_enum_health_status():
    class AgentHealthStatus(str):
        DEGRADED = "degraded"

        def __new__(cls, value):
            if value != "degraded":
                raise ValueError(value)
            return str.__new__(cls, value)

    redis_bus = MagicMock()
    redis_bus.ensure_consumer_group = AsyncMock()
    redis_bus.read_group = AsyncMock(return_value=None)
    redis_bus.ack = AsyncMock()

    health_monitor = MagicMock()
    health_monitor._check_agent_health = AsyncMock(return_value=types.SimpleNamespace(status=None))
    health_monitor.apply_degraded_mode = MagicMock()
    health_monitor.process_heartbeat = AsyncMock()

    orchestrator = MagicMock()
    orchestrator.on_step_completed = AsyncMock()
    conflict_resolver = MagicMock()

    _module("models", AgentHealthStatus=AgentHealthStatus)
    _module("redis_bus", redis_bus=redis_bus)
    workflows_pkg = _module("workflows")
    health_module = _module("workflows.health_monitor", health_monitor=health_monitor)
    orchestrator_module = _module("workflows.orchestrator", orchestrator=orchestrator)
    conflict_module = _module("workflows.conflict_resolver", conflict_resolver=conflict_resolver)
    workflows_pkg.health_monitor = health_module
    workflows_pkg.orchestrator = orchestrator_module
    workflows_pkg.conflict_resolver = conflict_module

    module = _load_module(
        "system_listener_under_test",
        SUPERVISOR_ROOT / "listeners" / "system_listener.py",
    )

    listener = module.SystemListener()
    asyncio.run(
        listener._handle_agent_status({"agent_name": "platform", "status": "degraded"})
    )

    health_monitor._check_agent_health.assert_awaited_once_with("platform")
    health_monitor.apply_degraded_mode.assert_called_once()
    args = health_monitor.apply_degraded_mode.call_args.args
    assert args[0] == "platform"
    assert args[1] == "degraded"


def test_command_listener_uses_injected_resend_client():
    resend_client = MagicMock()
    resend_client.send_critical_system_alert = AsyncMock()

    _module("redis_bus", redis_bus=MagicMock())
    _module("agent_registry", AGENT_REGISTRY={})
    workflows_pkg = _module("workflows")
    orchestrator_module = _module("workflows.orchestrator", orchestrator=MagicMock())
    workflows_pkg.orchestrator = orchestrator_module

    module = _load_module(
        "command_listener_under_test",
        SUPERVISOR_ROOT / "listeners" / "command_listener.py",
    )

    listener = module.CommandListener(resend_client=resend_client)
    asyncio.run(
        listener._handle_critical_alert(
            {"alert_type": "SYSTEM_ALERT", "details": {"severity": "high"}}
        )
    )

    resend_client.send_critical_system_alert.assert_awaited_once_with(
        alert_type="SYSTEM_ALERT",
        details={"severity": "high"},
    )
