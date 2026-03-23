# Implementation Plan: supervisor-agent
**Branch**: `supervisor-agent-v1` | **Date**: 2026-03-22 | **Spec**: `supervisor/docs/spec.md`

---

## Summary

وكيل مشرف يتولى تنسيق العمليات الكبيرة (Workflows) بـ State Machine صريحة، حل التعارضات، مراقبة صحة الوكلاء مع سياسة تدهور محددة، وإدارة السياسات العليا (ميزانية + جودة) — كل ذلك عبر Agent Registry رسمي وأحداث Redis حصراً. **ليس Single Point of Failure.**

---

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: langgraph>=0.2.0, fastapi>=0.110.0, psycopg2-binary, redis[hiredis], resend, apscheduler
**Storage**: PostgreSQL (workflow_instances, supervisor_audit_log, conflict_records, policy_rules, agent_health, override_log)
**Testing**: pytest
**الاتصال**: Redis Pub/Sub + Streams حصراً — لا function calls مباشرة
**نمط المعالجة**: Event-driven (يستمع) + Scheduled checks (كل دقيقة للـ Health Monitor)

---

## Constitution Check

| المبدأ | الحالة |
|--------|--------|
| ليس Single Point of Failure | ✓ degraded_fallback لكل وكيل في AGENT_REGISTRY |
| Agent Registry مصدر الحقيقة | ✓ لا hardcoded knowledge عن الوكلاء |
| State Machine صريحة | ✓ ALLOWED_WORKFLOW_TRANSITIONS + TERMINAL_STATES |
| السلطة عبر الأحداث | ✓ لا function calls مباشرة، كل إجراء = حدث |
| Audit Log لكل إجراء | ✓ supervisor_audit_log في PostgreSQL |
| USER_LOCKED_DECISIONS محصّنة | ✓ ValidationError فوري عند أي محاولة |
| Redis failure = graceful | ✓ local log + Resend alert مباشرة |

---

## Project Structure

```
supervisor/supervisor-agent/
├── pyproject.toml
├── Dockerfile
├── .env.example
├── logging_config.py
├── models.py                   # WorkflowType/Status/Step, ConflictType, AgentHealth, Policy, AuditLog
├── state.py                    # SupervisorState TypedDict
├── agent_registry.py           # AGENT_REGISTRY + get_agent() + DEGRADED_MODE_RULES
├── workflow_definitions.py     # WORKFLOW_DEFINITIONS + WORKFLOW_PRIORITY + build_workflow_business_key()
├── policy_engine.py            # DEFAULT_POLICIES + evaluate_policies() + USER_LOCKED_DECISIONS
│
├── db/
│   ├── __init__.py
│   ├── workflow_store.py       # save, get, get_by_business_key, get_active_workflows, list_by_status
│   ├── audit_store.py          # write_audit — لا تحذف مطلقاً
│   ├── conflict_store.py       # save_conflict, get_open_conflicts, resolve_conflict
│   ├── health_store.py         # save_health_record, get_health, get_all_health
│   └── policy_store.py         # save_policy, get_active_policies, deactivate_policy
│
├── services/
│   ├── __init__.py
│   ├── redis_bus.py            # publish_supervisor_event, read_group, ack, build_supervisor_event()
│   └── resend_client.py        # send_owner_alert, send_critical_system_alert
│
├── workflows/
│   ├── __init__.py
│   ├── orchestrator.py         # WorkflowOrchestrator: start, on_step_completed, handle_timeout, cancel
│   ├── state_machine.py        # transition_workflow() + validate_transition() + ALLOWED_WORKFLOW_TRANSITIONS
│   ├── conflict_resolver.py    # ConflictResolver: detect_conflict, resolve_by_rules, escalate_ambiguous
│   ├── health_monitor.py       # HealthMonitor: check_all_agents, apply_degraded_mode, run_scheduled
│   └── policy_enforcer.py      # PolicyEnforcer: check_policies, enforce, apply_budget_action
│
├── listeners/
│   ├── __init__.py
│   ├── system_listener.py      # يستمع على supervisor_events + كل قنوات الوكلاء للـ heartbeat
│   └── command_listener.py     # يستمع على أوامر صاحب المشروع (WORKFLOW_START, AGENT_PAUSE, إلخ)
│
└── api/
    ├── __init__.py
    └── main.py                 # FastAPI: /health + /workflows + /agents/health + /audit + /policies
```

---

## Workflow Architecture (3 Workflows رئيسية)

```
Workflow 1: Workflow Orchestrator
  ← يُشغَّل بطلب من صاحب المشروع أو حدث محدد
  → State Machine: PENDING → RUNNING → WAITING → COMPLETED/FAILED
  → كل خطوة = حدث Redis → انتظار حدث الإتمام

Workflow 2: Conflict Resolver
  ← SIGNAL_CONTRADICTION, BUDGET_EXCEEDED, DEPENDENCY_FAILURE
  → قواعد محددة للحل + تصعيد الغامض لصاحب المشروع

Workflow 3: Health Monitor
  ← heartbeat_events كل دقيقة
  → AgentHealthStatus: HEALTHY / DEGRADED / UNHEALTHY / UNKNOWN
  → تطبيق DEGRADED_MODE_RULES عند التدهور
```

---

## Workflows المدعومة

```python
THEME_LAUNCH:      builder → visual → platform → [support || marketing || analytics] (متوازيان)
THEME_UPDATE:      builder → [visual?] → platform
SEASONAL_CAMPAIGN: marketing → [content || analytics] (متوازيان)
SYSTEM_RECOVERY:   health_check → apply_degraded → notify_owner
BATCH_CONTENT:     content → [support KB update]
```

---

## Error Codes

```python
SUP_001 = "AGENT_NOT_REGISTERED"
SUP_101 = "INVALID_WORKFLOW_TRANSITION"
SUP_102 = "WORKFLOW_ALREADY_TERMINAL"
SUP_103 = "WORKFLOW_BUSINESS_KEY_EXISTS"   # idempotency
SUP_201 = "CONFLICT_UNRESOLVABLE"          # تصعيد للمالك
SUP_301 = "USER_LOCKED_DECISION_ATTEMPTED" # حدث حرج فوري
SUP_401 = "HEARTBEAT_TIMEOUT"
SUP_402 = "AGENT_HEALTH_CRITICAL"
SUP_501 = "REDIS_FAILURE"                  # graceful degradation
SUP_601 = "POLICY_ENFORCEMENT_FAILED"
```

---

## Event Contracts

**Inbound**: `THEME_APPROVED`, `THEME_ASSETS_READY`, `NEW_PRODUCT_LIVE`, `KNOWLEDGE_BASE_UPDATED`, `CAMPAIGN_LAUNCHED`, `HEARTBEAT`, `ANALYTICS_SIGNAL`, `WORKFLOW_START` (owner), `AGENT_PAUSE` (owner), `AGENT_RESUME` (owner)

**Outbound**: `WORKFLOW_STARTED`, `WORKFLOW_COMPLETED`, `WORKFLOW_FAILED`, `AGENT_PAUSE`, `AGENT_RESUME`, `POLICY_UPDATE`, `SYSTEM_ALERT`, `SUPERVISOR_OVERRIDE`

---

## USER_LOCKED_DECISIONS (محصّنة دائماً)

```python
USER_LOCKED_DECISIONS = [
    "pricing",           # أسعار المنتجات
    "product_deletion",  # حذف منتج
    "targeting_change",  # تغيير استهداف إعلاني
    "crisis_response",   # رد على أزمة عامة
    "campaign_stop",     # إيقاف حملة
    "budget_change",     # تغيير ميزانية تسويقية
]
```
