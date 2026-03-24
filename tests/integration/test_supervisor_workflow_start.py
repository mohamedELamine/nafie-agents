import asyncio
import importlib.util
import pathlib
import sys
import types
from unittest.mock import AsyncMock, MagicMock

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SUPERVISOR_ROOT = PROJECT_ROOT / "supervisor" / "supervisor-agent"


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


def test_workflow_start_command_reaches_orchestrator_with_real_enum():
    orchestrator = MagicMock()
    orchestrator.start_workflow = AsyncMock(return_value=types.SimpleNamespace(instance_id="wf_1"))

    _module("redis_bus", redis_bus=MagicMock())
    _module("agent_registry", AGENT_REGISTRY={})
    _module("models", EventEnvelope=object)
    workflows_pkg = _module("workflows")
    orchestrator_module = _module("workflows.orchestrator", orchestrator=orchestrator)
    workflows_pkg.orchestrator = orchestrator_module

    workflow_definitions = _load_module(
        "workflow_definitions",
        SUPERVISOR_ROOT / "workflow_definitions.py",
    )
    command_listener = _load_module(
        "supervisor_command_listener_integration",
        SUPERVISOR_ROOT / "listeners" / "command_listener.py",
    )

    listener = command_listener.CommandListener()
    payload = {
        "data": {
            "event_type": "WORKFLOW_START",
            "data": {
                "workflow_type": "theme_launch",
                "context": {
                    "theme_slug": "theme-one",
                    "version": "1.0.0",
                    "correlation_id": "corr_1",
                },
            },
        }
    }

    asyncio.run(listener._process_command(payload))

    orchestrator.start_workflow.assert_awaited_once_with(
        workflow_type=workflow_definitions.WorkflowType.THEME_LAUNCH,
        trigger_event=payload["data"]["data"],
        context={
            "theme_slug": "theme-one",
            "version": "1.0.0",
            "correlation_id": "corr_1",
        },
    )
