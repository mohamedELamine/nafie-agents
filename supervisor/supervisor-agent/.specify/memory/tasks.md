# Tasks: supervisor-agent
**Input**: `supervisor/docs/spec.md` + `plan.md` + `constitution.md`
**Implementation**: `/speckit.implement`

---

## Phase 1: Setup + Foundation

**Purpose**: بنية المشروع + Domain Model + Agent Registry + قاعدة البيانات

- [x] T001 إنشاء `pyproject.toml` (langgraph, fastapi, psycopg2-binary, redis[hiredis], resend, apscheduler)
- [x] T002 إنشاء `Dockerfile` (python:3.12-slim, non-root user, port 8000)
- [x] T003 إنشاء `.env.example` (DATABASE_URL, REDIS_URL, RESEND_API_KEY, OWNER_EMAIL, HEARTBEAT_TIMEOUT_SEC=120, HEALTH_CHECK_INTERVAL_SEC=60)
- [x] T004 إنشاء `logging_config.py` (configure_logging + get_logger بصيغة `agent=supervisor`)
- [x] T005 إنشاء `models.py`:
  - Enums: WorkflowType, WorkflowStatus, ConflictType, AgentHealthStatus, AuditCategory, AgentCriticality
  - Dataclasses: WorkflowStep, WorkflowInstance, EventEnvelope, ConflictRecord, AgentHealthRecord, PolicyRule, SupervisorAuditLog, OverrideLog
  - `ALLOWED_WORKFLOW_TRANSITIONS` dict + `TERMINAL_STATES` set
- [x] T006 إنشاء `agent_registry.py`:
  - `AgentRegistryEntry` dataclass
  - `AGENT_REGISTRY` dict (8 وكلاء: builder, visual_production, platform, support, content, marketing, analytics, visual_audio)
  - `get_agent(agent_name)`, `get_agents_by_criticality()`
  - `DEGRADED_MODE_RULES` dict + `get_degraded_action(agent_name)`
  - `REDIS_CHANNELS` dict + `get_agent_channel()`
- [x] T007 إنشاء `workflow_definitions.py`:
  - `WORKFLOW_DEFINITIONS` (THEME_LAUNCH, THEME_UPDATE, SEASONAL_CAMPAIGN, SYSTEM_RECOVERY, BATCH_CONTENT)
  - `WORKFLOW_PRIORITY` dict
  - `build_workflow_business_key(workflow_type, context) → str`
- [x] T008 إنشاء `policy_engine.py`:
  - `DEFAULT_POLICIES` dict (daily_visual_budget, daily_theme_limit, api_cost_critical, quality_threshold)
  - `USER_LOCKED_DECISIONS` list
  - `check_user_locked(domain)` — يرفع SUP_301 فوراً
  - `evaluate_policies(context) → List[PolicyRule]` — يُطبَّق على كل workflow
- [x] T009 إنشاء `state.py` (SupervisorState TypedDict + make_initial_state())
- [x] T010 [P] إنشاء `db/workflow_store.py` (save, get, get_by_business_key, get_active_workflows, list_by_status, update_step)
- [x] T011 [P] إنشاء `db/audit_store.py` (write_audit — لا تحذف مطلقاً، append-only)
- [x] T012 [P] إنشاء `db/conflict_store.py` (save_conflict, get_open_conflicts, resolve_conflict, get_conflict_history)
- [x] T013 [P] إنشاء `db/health_store.py` (save_health_record, get_health, get_all_health, get_unhealthy_agents)
- [x] T014 [P] إنشاء `db/policy_store.py` (save_policy, get_active_policies, deactivate_policy, get_policy_history)
- [x] T015 إنشاء `db/migrations/001_supervisor_tables.sql`:
  - `workflow_instances` (instance_id, workflow_type, business_key, theme_slug, correlation_id, current_step, total_steps, status, started_at, completed_at, failed_step, failure_reason, retry_count, context, step_history)
  - `supervisor_audit_log` (log_id, category, action, target, workflow_id, correlation_id, details, outcome, created_at) — لا حذف
  - `conflict_records` (conflict_id, conflict_type, agents_involved, description, resolution, resolved_at, escalated, created_at)
  - `agent_health` (agent_name, status, last_heartbeat, queue_depth, active_jobs, error_rate, mode, last_checked, issues)
  - `policy_rules` (policy_id, rule_type, condition, action, value, active, created_at, expires_at)
  - `override_log` (override_id, supervisor_decision, overridden_agent, original_signal, override_reason, applied_at, outcome)

---

## Phase 2: Services + Core Workflows

**Purpose**: التكاملات + منطق الـ Workflows الثلاثة

- [x] T016 إنشاء `services/redis_bus.py`:
  - `publish_supervisor_event(channel, event_type, data, correlation_id, causation_id, workflow_id)` → يبني EventEnvelope كامل
  - `read_group(channel, group, consumer, count)`, `ack(channel, group, msg_id)`
  - `ensure_consumer_group(channel, group)`
  - `build_supervisor_event()` — EventEnvelope builder
- [x] T017 إنشاء `services/resend_client.py` (send_owner_alert, send_critical_system_alert با retry=3 + fallback logging)
- [x] T018 إنشاء `workflows/state_machine.py`:
  - `transition_workflow(instance, new_status, reason) → WorkflowInstance`
  - `validate_transition(current_status, new_status)` — يرفع SUP_101 عند الخطأ
  - Audit log تلقائي عند كل transition
- [x] T019 إنشاء `workflows/orchestrator.py`:
  - `WorkflowOrchestrator` class
  - `start_workflow(workflow_type, trigger_event) → WorkflowInstance` — مع idempotency check
  - `on_step_completed(instance_id, completed_event, event_data, causation_id)` — يُحرّك الـ Workflow
  - `handle_step_timeout(instance_id, step_number)` — retry/fail/skip بحسب WorkflowStep
  - `cancel_workflow(instance_id, reason)` — لأوامر صاحب المشروع
  - `_execute_step(instance, step)` — إرسال trigger_event بـ EventEnvelope
  - `_handle_parallel_group(instance, steps, group_name)` — خطوات متوازية
  - `_emit_workflow_completed(instance)` — `WORKFLOW_COMPLETED` + audit
- [x] T020 إنشاء `workflows/conflict_resolver.py`:
  - `ConflictResolver` class
  - `detect_conflict(event) → Optional[ConflictRecord]` — SIGNAL_CONTRADICTION, BUDGET_EXCEEDED, DEPENDENCY_FAILURE
  - `resolve_by_rules(conflict) → Optional[str]` — قواعد محددة: higher_priority_wins, latest_signal_wins
  - `escalate_ambiguous(conflict)` — SYSTEM_ALERT + Resend للمالك
  - `record_resolution(conflict_id, resolution, detail)` — audit log
- [x] T021 إنشاء `workflows/health_monitor.py`:
  - `HealthMonitor` class
  - `check_all_agents() → Dict[str, AgentHealthRecord]` — يُشغَّل كل دقيقة
  - `process_heartbeat(agent_name, heartbeat_data)` — تحديث health record
  - `apply_degraded_mode(agent_name, health_status)` — تطبيق DEGRADED_MODE_RULES
  - `_check_heartbeat_timeout(agent_name)` — SUP_401 إن HEARTBEAT_TIMEOUT_SEC تجاوز
  - `get_system_health_summary() → dict` — للـ Dashboard API
- [x] T022 إنشاء `workflows/policy_enforcer.py`:
  - `PolicyEnforcer` class
  - `check_and_enforce(context) → List[str]` — يُطبَّق على كل workflow start
  - `apply_budget_action(policy, current_cost)` — pause_visual_production / alert_owner_pause_non_critical
  - `block_launch_if_quality_fails(theme_score)` — block إن < 70
  - `log_policy_enforcement(policy_id, action, outcome)` — audit log

---

## Phase 3: Listeners + API

**Purpose**: واجهة الاستماع + FastAPI

- [x] T023 إنشاء `listeners/system_listener.py`:
  - يستمع على `supervisor_events` + `heartbeat_events`
  - يُمرّر الـ heartbeats لـ HealthMonitor
  - يُمرّر أحداث إتمام الخطوات لـ WorkflowOrchestrator
  - يُمرّر التعارضات لـ ConflictResolver
  - Redis failure: يُسجّل محلياً + يُرسل Resend alert مباشرة
- [x] T024 إنشاء `listeners/command_listener.py`:
  - يستمع على أوامر صاحب المشروع عبر `supervisor_commands` channel
  - `WORKFLOW_START` → orchestrator.start_workflow()
  - `AGENT_PAUSE` → تحقق USER_LOCKED_DECISIONS + publish AGENT_PAUSE
  - `AGENT_RESUME` → publish AGENT_RESUME
  - `POLICY_UPDATE` → policy_store.save_policy()
  - كل أمر يُسجَّل في audit_log
- [x] T025 إنشاء `api/main.py`:
  - FastAPI lifespan (init DB + services + start listeners + start health_monitor scheduler)
  - GET /health — صحة المشرف نفسه
  - GET /workflows — قائمة الـ workflows الفعّالة مع حالتها
  - GET /workflows/{instance_id} — تفاصيل workflow + step_history
  - POST /workflows — إنشاء workflow جديد (يتحقق من USER_LOCKED_DECISIONS)
  - DELETE /workflows/{instance_id} — إلغاء workflow (CANCEL)
  - GET /agents/health — صحة كل الوكلاء من health_store
  - GET /audit?category=&since= — سجل التدقيق مع فلترة
  - GET /policies — السياسات الفعّالة
  - PUT /policies/{policy_id} — تعديل سياسة (يُسجَّل في audit)
  - GET /conflicts — التعارضات المفتوحة

---

**الإجمالي**: 25 مهمة | **[P]**: يمكن تشغيلها بالتوازي
