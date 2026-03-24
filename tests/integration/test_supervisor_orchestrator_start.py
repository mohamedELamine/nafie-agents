import asyncio
import importlib.util
import pathlib
import sys
import types
from unittest.mock import AsyncMock, MagicMock, call

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


def test_orchestrator_start_workflow_publishes_start_and_first_step():
    models = _load_module("models", SUPERVISOR_ROOT / "models.py")
    workflow_definitions = _load_module(
        "workflow_definitions",
        SUPERVISOR_ROOT / "workflow_definitions.py",
    )

    workflow_store = MagicMock()
    workflow_store.get_by_business_key.return_value = None
    workflow_store.save.side_effect = lambda instance: instance
    workflow_store.update_step = MagicMock()

    audit_store = MagicMock()
    conflict_store = MagicMock()
    health_store = MagicMock()
    policy_store = MagicMock()
    redis_bus = types.SimpleNamespace(publish_supervisor_event=AsyncMock())

    _module(
        "agent_registry",
        get_agent=lambda name: {"name": name},
        get_degraded_action=lambda name: None,
    )
    _module("db.workflow_store", workflow_store=workflow_store)
    _module("db.audit_store", audit_store=audit_store)
    _module("db.conflict_store", conflict_store=conflict_store)
    _module("db.health_store", health_store=health_store)
    _module("db.policy_store", policy_store=policy_store)
    _module("redis_bus", redis_bus=redis_bus)
    _module(
        "policy_engine",
        check_user_locked=lambda decision_domain: False,
        evaluate_policies=lambda context: [],
    )

    orchestrator_module = _load_module(
        "supervisor_orchestrator_integration",
        SUPERVISOR_ROOT / "workflows" / "orchestrator.py",
    )

    orchestrator = orchestrator_module.WorkflowOrchestrator(
        workflow_store=workflow_store,
        audit_store=audit_store,
        conflict_store=conflict_store,
        health_store=health_store,
        policy_store=policy_store,
        resend_client=MagicMock(),
    )

    instance = asyncio.run(
        orchestrator.start_workflow(
            workflow_type=workflow_definitions.WorkflowType.SEASONAL_CAMPAIGN,
            trigger_event={"event_type": "WORKFLOW_START"},
            context={"season": "ramadan", "year": 2026, "correlation_id": "corr_1"},
        )
    )

    assert instance.workflow_type == workflow_definitions.WorkflowType.SEASONAL_CAMPAIGN
    assert instance.business_key == "campaign_ramadan_2026"
    audit_store.write_audit.assert_called_once()
    workflow_store.update_step.assert_called_once()
    step_history_entry = workflow_store.update_step.call_args.args[1]
    assert step_history_entry.step_number == 1
    assert step_history_entry.agent_name == "marketing"
    assert step_history_entry.action == "create_campaign"
    assert redis_bus.publish_supervisor_event.await_args_list[0].kwargs["event_type"] == "WORKFLOW_STARTED"
    assert redis_bus.publish_supervisor_event.await_args_list[1].kwargs["channel"] == "agent:marketing:events"
    assert redis_bus.publish_supervisor_event.await_args_list[1].kwargs["event_type"] == "create_campaign_trigger"
