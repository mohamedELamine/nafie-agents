from __future__ import annotations

import asyncio
import importlib.util
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.integration

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


def test_workflow_start_command_reaches_supervisor_consumer(
    redis_bus, db_conn, monkeypatch
):
    with db_conn.cursor() as cursor:
        cursor.execute("SELECT 1")

    workflow_definitions = _load_module(
        "workflow_definitions",
        SUPERVISOR_ROOT / "workflow_definitions.py",
    )

    async def fake_start_workflow(workflow_type, trigger_event, context):
        await redis_bus.publish_supervisor_event(
            channel="supervisor_events",
            event_type="WORKFLOW_STARTED",
            data={
                "workflow_type": workflow_type.value,
                "theme_slug": context.get("theme_slug"),
            },
            workflow_id="wf_123",
        )
        return types.SimpleNamespace(instance_id="wf_123")

    fake_orchestrator = types.SimpleNamespace(start_workflow=fake_start_workflow)

    _module("redis_bus", redis_bus=redis_bus)
    _module("agent_registry", AGENT_REGISTRY={})
    _module("models", EventEnvelope=object)
    workflows_pkg = _module("workflows")
    workflows_pkg.orchestrator = _module(
        "workflows.orchestrator",
        orchestrator=fake_orchestrator,
    )

    command_listener = _load_module(
        "supervisor_command_listener_integration",
        SUPERVISOR_ROOT / "listeners" / "command_listener.py",
    )

    asyncio.run(
        redis_bus.publish_supervisor_event(
            channel="workflow_commands",
            event_type="WORKFLOW_START",
            data={
                "workflow_type": workflow_definitions.WorkflowType.THEME_LAUNCH.value,
                "context": {
                    "theme_slug": "theme-one",
                    "version": "1.0.0",
                    "correlation_id": "corr_123",
                },
            },
        )
    )

    listener = command_listener.CommandListener()
    asyncio.run(listener._consume_commands())

    published = redis_bus.read_supervisor_stream("supervisor_events")
    assert published
    assert published[-1]["event_type"] == "WORKFLOW_STARTED"
    assert published[-1]["data"]["theme_slug"] == "theme-one"
