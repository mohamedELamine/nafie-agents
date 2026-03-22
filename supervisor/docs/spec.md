# وكيل المشرف — نظام التنسيق والحوكمة
## وثيقة المواصفات الشاملة v2 — Supervisor Agent

> هذه النسخة تجمع v1 + التصحيحات المعمارية الكاملة.
> تُعدّ المرجع التنفيذي الوحيد المعتمد لوكيل المشرف.

---

## فهرس المحتويات

1. نظرة عامة ومبادئ جوهرية
2. موقع الوكيل في المنظومة الكاملة
3. Agent Registry — سجل الوكلاء الرسمي
4. REDIS_CHANNELS — قنوات الاتصال الرسمية
5. الأدوار الأربعة — مجالات المسؤولية
6. نموذج الصلاحيات — السلطة عبر الأحداث
7. الكيانات الجوهرية — Domain Model
8. Workflow State Machine — انتقالات الحالة
9. WorkflowStep Schema — تعريف الخطوات
10. Workflow Definitions — تعريفات العمليات
11. Event Envelope — بنية الأحداث الموسّعة
12. Policy Engine — إدارة السياسات
13. System Degradation Policy — سياسة التدهور
14. Workflow Orchestrator — تشغيل العمليات
15. Conflict Resolver — حل التعارضات
16. Health Monitor — مراقبة الصحة
17. Supervisor Audit Log — سجل التدقيق الشامل
18. Redis Failure Mode — فشل Redis
19. Self-healing Boundaries — حدود الإصلاح الذاتي
20. Override Authority — حدود التجاوز
21. USER_LOCKED_DECISIONS — حدود لا تُتجاوز
22. علاقة المشرف بصاحب المشروع
23. معمارية الوكيل — ثلاثة Workflows
24. SUPERVISOR_EVENTS — الأحداث الخاصة
25. Idempotency Strategy
26. Event Contract Schemas
27. Error Codes Catalog
28. بنية الـ State
29. البيئة المحلية ومتغيرات البيئة
30. دستور الوكيل
31. قائمة التحقق النهائية

---

## ١. نظرة عامة ومبادئ جوهرية

### الهدف

بناء وكيل مشرف يتولى تنسيق العمليات الكبيرة عبر المنظومة: تشغيل Workflows المركّبة بـ State Machine صريحة، حل التعارضات بقواعد محددة، مراقبة الصحة مع سياسة تدهور واضحة، وإدارة السياسات العليا — كل ذلك عبر Agent Registry رسمي وأحداث Redis حصراً مع سياسة فشل Redis محددة.

### المبادئ غير القابلة للتفاوض

- **ليس Single Point of Failure** — الوكلاء تعمل بدونه
- **Agent Registry مصدر الحقيقة** — لا معرفة hardcoded عن الوكلاء
- **State Machine صريحة** — لا انتقالات رمادية في Workflows
- **Degradation Policy كوداً** — سلوك التدهور محدد لا مخمَّن
- **السلطة عبر الأحداث فقط** — لا function calls مباشرة
- **Audit Log لكل إجراء** — لا حدث بلا أثر
- **Redis failure = graceful degradation** — لا صمت عند فشل البنية التحتية
- **Self-healing محدود** — يكتشف ويُبلّغ، لا يُصلح بمفرده إلا في حالات محددة
- **USER_LOCKED_DECISIONS محصّنة** — حتى في الطوارئ القصوى

---

## ٢. موقع الوكيل في المنظومة الكاملة

```
صاحب المشروع
    │ أوامر يدوية / موافقات
    ▼
وكيل المشرف ← طبقة التنسيق
    │
    ├── ينسّق ← وكيل البناء          (critical)
    ├── ينسّق ← وكيل الإنتاج البصري  (important)
    ├── ينسّق ← وكيل المنصة           (critical)
    ├── ينسّق ← وكيل الدعم             (semi-critical)
    ├── ينسّق ← وكيل المحتوى           (important)
    ├── ينسّق ← وكيل التسويق           (normal)
    ├── ينسّق ← وكيل التحليل           (optional)
    └── ينسّق ← وكيل الإنتاج السمعي البصري (important)

الوكلاء تعمل باستقلالية تامة في عملياتها اليومية.
المشرف يتدخل فقط في العمليات الكبيرة والتعارضات والصحة.
```

---

## ٣. Agent Registry — سجل الوكلاء الرسمي

```python
"""
مصدر الحقيقة الوحيد عن الوكلاء.
المشرف لا يعرف شيئاً عن وكيل لا يوجد في Registry.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional


class AgentCriticality(Enum):
    CRITICAL      = "critical"      # إيقافه يوقف الإطلاق
    SEMI_CRITICAL = "semi_critical" # إيقافه يُقيّد لكن لا يوقف
    IMPORTANT     = "important"     # إيقافه يُشغَّل degraded mode
    NORMAL        = "normal"        # إيقافه يُؤجّل وظيفة
    OPTIONAL      = "optional"      # إيقافه لا يؤثر على الإطلاق


@dataclass
class AgentRegistryEntry:
    agent_name:            str
    redis_channel:         str
    consumes_events:       List[str]
    emits_events:          List[str]
    supports_pause:        bool
    supports_resume:       bool
    heartbeat_required:    bool
    heartbeat_interval_sec: int
    criticality:           AgentCriticality
    owner_locked_domains:  List[str]
    degraded_fallback:     Optional[str]   # ماذا تفعل المنظومة إن تعطّل
    status:                str = "active"  # active | paused | disabled


AGENT_REGISTRY: dict[str, AgentRegistryEntry] = {

    "builder_agent": AgentRegistryEntry(
        agent_name             = "builder_agent",
        redis_channel          = "builder_events",
        consumes_events        = ["BUILD_REQUEST", "AGENT_PAUSE", "AGENT_RESUME"],
        emits_events           = ["THEME_BUILT", "THEME_APPROVED", "BUILD_FAILED"],
        supports_pause         = True,
        supports_resume        = True,
        heartbeat_required     = True,
        heartbeat_interval_sec = 60,
        criticality            = AgentCriticality.CRITICAL,
        owner_locked_domains   = [],
        degraded_fallback      = "block_all_launches",
    ),

    "visual_production_agent": AgentRegistryEntry(
        agent_name             = "visual_production_agent",
        redis_channel          = "visual_events",
        consumes_events        = ["THEME_APPROVED", "THEME_UPDATED",
                                   "AGENT_PAUSE", "AGENT_RESUME"],
        emits_events           = ["THEME_ASSETS_READY", "THEME_ASSETS_PARTIALLY_READY",
                                   "THEME_ASSETS_FAILED"],
        supports_pause         = True,
        supports_resume        = True,
        heartbeat_required     = True,
        heartbeat_interval_sec = 60,
        criticality            = AgentCriticality.IMPORTANT,
        owner_locked_domains   = [],
        degraded_fallback      = "launch_with_placeholder_assets",
    ),

    "platform_agent": AgentRegistryEntry(
        agent_name             = "platform_agent",
        redis_channel          = "platform_events",
        consumes_events        = ["THEME_ASSETS_READY", "CONTENT_READY",
                                   "AGENT_PAUSE", "AGENT_RESUME"],
        emits_events           = ["NEW_PRODUCT_LIVE", "THEME_UPDATED_LIVE",
                                   "LAUNCH_FAILED"],
        supports_pause         = True,
        supports_resume        = True,
        heartbeat_required     = True,
        heartbeat_interval_sec = 60,
        criticality            = AgentCriticality.CRITICAL,
        owner_locked_domains   = ["pricing", "product_deletion"],
        degraded_fallback      = "block_all_launches",
    ),

    "support_agent": AgentRegistryEntry(
        agent_name             = "support_agent",
        redis_channel          = "support_events",
        consumes_events        = ["NEW_PRODUCT_LIVE", "CONTENT_READY",
                                   "AGENT_PAUSE", "AGENT_RESUME"],
        emits_events           = ["KNOWLEDGE_BASE_UPDATED", "SUPPORT_TICKET_RESOLVED",
                                   "RECURRING_ISSUE_DETECTED"],
        supports_pause         = True,
        supports_resume        = True,
        heartbeat_required     = True,
        heartbeat_interval_sec = 120,
        criticality            = AgentCriticality.SEMI_CRITICAL,
        owner_locked_domains   = [],
        degraded_fallback      = "launch_allowed_kb_flagged_pending",
    ),

    "content_agent": AgentRegistryEntry(
        agent_name             = "content_agent",
        redis_channel          = "content_events",
        consumes_events        = ["NEW_PRODUCT_LIVE", "THEME_UPDATED_LIVE",
                                   "CONTENT_REQUEST", "AGENT_PAUSE", "AGENT_RESUME"],
        emits_events           = ["CONTENT_READY", "CONTENT_PRODUCED"],
        supports_pause         = True,
        supports_resume        = True,
        heartbeat_required     = True,
        heartbeat_interval_sec = 120,
        criticality            = AgentCriticality.IMPORTANT,
        owner_locked_domains   = [],
        degraded_fallback      = "use_default_content_template",
    ),

    "marketing_agent": AgentRegistryEntry(
        agent_name             = "marketing_agent",
        redis_channel          = "marketing_events",
        consumes_events        = ["NEW_PRODUCT_LIVE", "CONTENT_READY",
                                   "ANALYTICS_SIGNAL", "AGENT_PAUSE", "AGENT_RESUME"],
        emits_events           = ["CAMPAIGN_LAUNCHED", "POST_PUBLISHED"],
        supports_pause         = True,
        supports_resume        = True,
        heartbeat_required     = True,
        heartbeat_interval_sec = 120,
        criticality            = AgentCriticality.NORMAL,
        owner_locked_domains   = ["budget_change", "discount_change",
                                   "targeting_change", "crisis_response", "campaign_stop"],
        degraded_fallback      = "continue_without_marketing",
    ),

    "analytics_agent": AgentRegistryEntry(
        agent_name             = "analytics_agent",
        redis_channel          = "analytics_events",
        consumes_events        = ["NEW_SALE", "POST_PUBLISHED", "CONTENT_PRODUCED",
                                   "SUPPORT_TICKET_RESOLVED", "AGENT_PAUSE", "AGENT_RESUME"],
        emits_events           = ["ANALYTICS_SIGNAL", "WEEKLY_REPORT_READY"],
        supports_pause         = True,
        supports_resume        = True,
        heartbeat_required     = False,   # batch — لا heartbeat لحظي
        heartbeat_interval_sec = 300,
        criticality            = AgentCriticality.OPTIONAL,
        owner_locked_domains   = [],
        degraded_fallback      = "continue_without_optimization",
    ),

    "visual_audio_agent": AgentRegistryEntry(
        agent_name             = "visual_audio_agent",
        redis_channel          = "visual_audio_events",
        consumes_events        = ["THEME_APPROVED", "AGENT_PAUSE", "AGENT_RESUME"],
        emits_events           = ["THEME_ASSETS_READY"],
        supports_pause         = True,
        supports_resume        = True,
        heartbeat_required     = True,
        heartbeat_interval_sec = 60,
        criticality            = AgentCriticality.IMPORTANT,
        owner_locked_domains   = [],
        degraded_fallback      = "launch_with_placeholder_assets",
    ),
}


def get_agent(agent_name: str) -> AgentRegistryEntry:
    if agent_name not in AGENT_REGISTRY:
        raise ConfigurationError(
            f"SUP_AGENT_NOT_REGISTERED: {agent_name}"
        )
    return AGENT_REGISTRY[agent_name]


def get_agents_by_criticality(
    criticality: AgentCriticality,
) -> List[AgentRegistryEntry]:
    return [
        a for a in AGENT_REGISTRY.values()
        if a.criticality == criticality
    ]
```

---

## ٤. REDIS_CHANNELS — قنوات الاتصال الرسمية

```python
REDIS_CHANNELS = {
    "supervisor":   "supervisor_events",
    "builder":      "builder_events",
    "visual":       "visual_events",
    "platform":     "platform_events",
    "support":      "support_events",
    "content":      "content_events",
    "marketing":    "marketing_events",
    "analytics":    "analytics_events",
    "visual_audio": "visual_audio_events",
}

HEARTBEAT_CHANNEL = "heartbeat_events"
AUDIT_CHANNEL     = "audit_events"

def get_agent_channel(agent_name: str) -> str:
    entry = get_agent(agent_name)
    return entry.redis_channel
```

---

## ٥. الأدوار الأربعة — مجالات المسؤولية

```python
SUPERVISOR_ROLES = {
    "workflow_orchestrator": "تشغيل العمليات المركّبة بـ State Machine صريحة",
    "conflict_resolver":     "حل التعارضات بقواعد محددة — تصعيد الغامض",
    "health_monitor":        "مراقبة صحة كل وكيل مع سياسة تدهور",
    "policy_engine":         "إدارة الميزانية والسياسات العليا للمنظومة",
}
```

---

## ٦. نموذج الصلاحيات — السلطة عبر الأحداث

```python
SUPERVISOR_CAN_DO = [
    "WORKFLOW_START",
    "WORKFLOW_CANCEL",
    "AGENT_PAUSE",
    "AGENT_RESUME",
    "POLICY_UPDATE",
    "SYSTEM_ALERT",
    "SUPERVISOR_OVERRIDE",   # مُوثَّق دائماً
    "HEALTH_CHECK_REQUEST",
]

SUPERVISOR_CANNOT_DO = [
    "استدعاء functions الوكلاء مباشرةً",
    "تجاوز USER_LOCKED_DECISIONS",
    "تعديل قواعد البيانات مباشرةً",
    "إرسال بريد للعملاء بلا وكيل",
    "تغيير أسعار",
    "إلغاء معاملات مالية",
    "الموافقة على تصاميم بدلاً من صاحب المشروع",
]
```

---

## ٧. الكيانات الجوهرية — Domain Model

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class WorkflowType(Enum):
    THEME_LAUNCH      = "theme_launch"
    THEME_UPDATE      = "theme_update"
    SEASONAL_CAMPAIGN = "seasonal_campaign"
    SYSTEM_RECOVERY   = "system_recovery"
    BATCH_CONTENT     = "batch_content"


class WorkflowStatus(Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    WAITING    = "waiting"
    PAUSED     = "paused"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"


class ConflictType(Enum):
    SIGNAL_CONTRADICTION = "signal_contradiction"
    RESOURCE_CONTENTION  = "resource_contention"
    BUDGET_EXCEEDED      = "budget_exceeded"
    DEPENDENCY_FAILURE   = "dependency_failure"
    AGENT_TIMEOUT        = "agent_timeout"


class AgentHealthStatus(Enum):
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


class AuditCategory(Enum):
    WORKFLOW    = "workflow"
    CONFLICT    = "conflict"
    HEALTH      = "health"
    POLICY      = "policy"
    OVERRIDE    = "override"
    COMMAND     = "command"
    ESCALATION  = "escalation"


@dataclass
class WorkflowStep:
    """تعريف خطوة صارم — لا Dict فضفاضة"""
    step_number:      int
    name:             str
    agent:            str
    trigger_event:    str
    wait_for_event:   Optional[str]
    timeout_minutes:  Optional[int]
    parallel_group:   Optional[str]   # خطوات بنفس المجموعة تعمل معاً
    required:         bool
    condition_key:    Optional[str]   # شرط تشغيل اختياري
    on_timeout:       str             # "retry" | "fail" | "skip"
    on_failure:       str             # "retry" | "fail" | "skip" | "compensate"


@dataclass
class WorkflowInstance:
    instance_id:      str
    workflow_type:    WorkflowType
    business_key:     str            # مفتاح idempotency الأعمق
    theme_slug:       Optional[str]
    correlation_id:   str
    current_step:     int
    total_steps:      int
    status:           WorkflowStatus
    started_at:       datetime
    completed_at:     Optional[datetime]
    failed_step:      Optional[int]
    failure_reason:   Optional[str]
    retry_count:      int
    context:          Dict
    step_history:     List[Dict]     # سجل كل خطوة


@dataclass
class EventEnvelope:
    """بنية الأحداث الموسّعة للمشرف"""
    event_id:           str
    event_type:         str
    event_version:      str
    source:             str
    occurred_at:        datetime
    correlation_id:     str          # الرحلة الكبرى
    causation_id:       Optional[str]  # الحدث الذي سبّب هذا
    workflow_id:        Optional[str]
    step_id:            Optional[str]
    retry_attempt:      int
    data:               Dict


@dataclass
class ConflictRecord:
    conflict_id:       str
    conflict_type:     ConflictType
    agents_involved:   List[str]
    description:       str
    signals:           List[Dict]
    resolution:        Optional[str]
    resolution_detail: Optional[str]
    resolved_at:       Optional[datetime]
    escalated:         bool
    created_at:        datetime


@dataclass
class AgentHealthRecord:
    agent_name:      str
    status:          AgentHealthStatus
    last_heartbeat:  Optional[datetime]
    queue_depth:     int
    active_jobs:     int
    error_rate:      float
    version:         Optional[str]
    mode:            str   # "normal" | "degraded" | "paused"
    last_checked:    datetime
    issues:          List[str]


@dataclass
class PolicyRule:
    policy_id:   str
    rule_type:   str
    condition:   str
    action:      str
    value:       Any
    active:      bool
    created_at:  datetime
    expires_at:  Optional[datetime]


@dataclass
class SupervisorAuditLog:
    """سجل تدقيق شامل — كل إجراء مُسجَّل"""
    log_id:         str
    category:       AuditCategory
    action:         str
    target:         Optional[str]
    workflow_id:    Optional[str]
    correlation_id: Optional[str]
    details:        Dict[str, Any]
    outcome:        Optional[str]
    created_at:     datetime


@dataclass
class OverrideLog:
    override_id:          str
    supervisor_decision:  str
    overridden_agent:     str
    original_signal:      Dict
    override_reason:      str
    applied_at:           datetime
    outcome:              Optional[str]
```

---

## ٨. Workflow State Machine — انتقالات الحالة

```python
"""
جدول انتقالات صارم — لا انتقال خارج هذه القواعد.
"""

ALLOWED_WORKFLOW_TRANSITIONS = {
    WorkflowStatus.PENDING:   [WorkflowStatus.RUNNING,
                                WorkflowStatus.CANCELLED],
    WorkflowStatus.RUNNING:   [WorkflowStatus.WAITING,
                                WorkflowStatus.PAUSED,
                                WorkflowStatus.FAILED,
                                WorkflowStatus.COMPLETED,
                                WorkflowStatus.CANCELLED],
    WorkflowStatus.WAITING:   [WorkflowStatus.RUNNING,
                                WorkflowStatus.PAUSED,
                                WorkflowStatus.FAILED,
                                WorkflowStatus.CANCELLED],
    WorkflowStatus.PAUSED:    [WorkflowStatus.RUNNING,
                                WorkflowStatus.CANCELLED],
    WorkflowStatus.FAILED:    [],   # نهائي — retry = instance جديدة
    WorkflowStatus.COMPLETED: [],   # نهائي
    WorkflowStatus.CANCELLED: [],   # نهائي
}

TERMINAL_STATES = {
    WorkflowStatus.FAILED,
    WorkflowStatus.COMPLETED,
    WorkflowStatus.CANCELLED,
}


def transition_workflow(
    instance:   WorkflowInstance,
    new_status: WorkflowStatus,
    reason:     str = "",
) -> WorkflowInstance:
    allowed = ALLOWED_WORKFLOW_TRANSITIONS.get(instance.status, [])

    if new_status not in allowed:
        raise InvalidTransitionError(
            f"SUP_INVALID_TRANSITION: "
            f"{instance.status.value} → {new_status.value} "
            f"غير مسموح | instance: {instance.instance_id}"
        )

    instance.status = new_status

    if new_status in TERMINAL_STATES:
        instance.completed_at = datetime.utcnow()

    # تسجيل في Audit Log
    write_audit(SupervisorAuditLog(
        log_id         = str(uuid.uuid4()),
        category       = AuditCategory.WORKFLOW,
        action         = f"transition:{instance.status.value}→{new_status.value}",
        target         = instance.instance_id,
        workflow_id    = instance.instance_id,
        correlation_id = instance.correlation_id,
        details        = {"reason": reason, "step": instance.current_step},
        outcome        = None,
        created_at     = datetime.utcnow(),
    ))

    workflow_store.save(instance)
    return instance


"""
ملاحظة: FAILED نهائي.
Retry = إنشاء WorkflowInstance جديدة بنفس business_key.
لا "إعادة تشغيل" من نفس الـ instance.
"""
```

---

## ٩. WorkflowStep Schema — تعريف الخطوات

```python
"""
WorkflowStep dataclass صارم بدل Dict.
كل خطوة معرّفة بالكامل — لا غموض في on_timeout أو on_failure.
"""

STEP_ON_TIMEOUT = {
    "retry":      "أعد تشغيل الخطوة",
    "fail":       "فشّل الـ Workflow",
    "skip":       "تخطَّ للخطوة التالية (للخطوات الاختيارية)",
}

STEP_ON_FAILURE = {
    "retry":      "أعد المحاولة بحسب retry_policy",
    "fail":       "فشّل الـ Workflow",
    "skip":       "تخطَّ (للخطوات الاختيارية)",
    "compensate": "شغّل rollback_steps",
}
```

---

## ١٠. Workflow Definitions — تعريفات العمليات

```python
WORKFLOW_PRIORITY = {
    WorkflowType.SYSTEM_RECOVERY:   100,
    WorkflowType.THEME_LAUNCH:      90,
    WorkflowType.THEME_UPDATE:      80,
    WorkflowType.SEASONAL_CAMPAIGN: 60,
    WorkflowType.BATCH_CONTENT:     40,
}

WORKFLOW_DEFINITIONS = {

    WorkflowType.THEME_LAUNCH: {
        "timeout_minutes": 240,
        "retry_policy":    {"max_retries": 2, "backoff_minutes": 30},
        "compensation":    "notify_owner_of_partial_launch",
        "steps": [
            WorkflowStep(
                step_number    = 1,
                name           = "theme_approval",
                agent          = "builder_agent",
                trigger_event  = "THEME_APPROVED",
                wait_for_event = "THEME_APPROVED",
                timeout_minutes = None,   # يدوي — لا timeout
                parallel_group = None,
                required       = True,
                condition_key  = None,
                on_timeout     = "fail",
                on_failure     = "fail",
            ),
            WorkflowStep(
                step_number    = 2,
                name           = "visual_production",
                agent          = "visual_production_agent",
                trigger_event  = "THEME_APPROVED",
                wait_for_event = "THEME_ASSETS_READY",
                timeout_minutes = 120,
                parallel_group = None,
                required       = True,
                condition_key  = None,
                on_timeout     = "retry",
                on_failure     = "compensate",
            ),
            WorkflowStep(
                step_number    = 3,
                name           = "platform_launch",
                agent          = "platform_agent",
                trigger_event  = "THEME_ASSETS_READY",
                wait_for_event = "NEW_PRODUCT_LIVE",
                timeout_minutes = 60,
                parallel_group = None,
                required       = True,
                condition_key  = None,
                on_timeout     = "retry",
                on_failure     = "fail",
            ),
            WorkflowStep(
                step_number    = 4,
                name           = "support_kb",
                agent          = "support_agent",
                trigger_event  = "NEW_PRODUCT_LIVE",
                wait_for_event = "KNOWLEDGE_BASE_UPDATED",
                timeout_minutes = 30,
                parallel_group = "post_launch",   # يعمل مع step 5
                required       = False,
                condition_key  = None,
                on_timeout     = "skip",
                on_failure     = "skip",
            ),
            WorkflowStep(
                step_number    = 5,
                name           = "marketing_launch",
                agent          = "marketing_agent",
                trigger_event  = "NEW_PRODUCT_LIVE",
                wait_for_event = "CAMPAIGN_LAUNCHED",
                timeout_minutes = 30,
                parallel_group = "post_launch",
                required       = False,
                condition_key  = None,
                on_timeout     = "skip",
                on_failure     = "skip",
            ),
            WorkflowStep(
                step_number    = 6,
                name           = "analytics_register",
                agent          = "analytics_agent",
                trigger_event  = "NEW_PRODUCT_LIVE",
                wait_for_event = None,   # fire and forget
                timeout_minutes = None,
                parallel_group = "post_launch",
                required       = False,
                condition_key  = None,
                on_timeout     = "skip",
                on_failure     = "skip",
            ),
        ],
    },

    WorkflowType.THEME_UPDATE: {
        "timeout_minutes": 120,
        "retry_policy":    {"max_retries": 1, "backoff_minutes": 15},
        "compensation":    "notify_owner_of_update_failure",
        "steps": [
            WorkflowStep(
                step_number    = 1,
                name           = "theme_built",
                agent          = "builder_agent",
                trigger_event  = "THEME_UPDATED",
                wait_for_event = "THEME_UPDATED",
                timeout_minutes = None,
                parallel_group = None,
                required       = True,
                condition_key  = None,
                on_timeout     = "fail",
                on_failure     = "fail",
            ),
            WorkflowStep(
                step_number    = 2,
                name           = "partial_visual",
                agent          = "visual_production_agent",
                trigger_event  = "THEME_UPDATED",
                wait_for_event = "THEME_ASSETS_UPDATED",
                timeout_minutes = 60,
                parallel_group = None,
                required       = False,
                condition_key  = "requires_visual_update",
                on_timeout     = "skip",
                on_failure     = "skip",
            ),
            WorkflowStep(
                step_number    = 3,
                name           = "platform_update",
                agent          = "platform_agent",
                trigger_event  = "THEME_UPDATED",
                wait_for_event = "THEME_UPDATED_LIVE",
                timeout_minutes = 30,
                parallel_group = None,
                required       = True,
                condition_key  = None,
                on_timeout     = "retry",
                on_failure     = "fail",
            ),
        ],
    },
}


def build_workflow_business_key(
    workflow_type: WorkflowType,
    context:       dict,
) -> str:
    """مفتاح idempotency مخصص لكل نوع Workflow."""
    if workflow_type == WorkflowType.THEME_LAUNCH:
        return (
            f"theme_launch"
            f":{context['theme_slug']}"
            f":{context['theme_version']}"
        )
    elif workflow_type == WorkflowType.THEME_UPDATE:
        return (
            f"theme_update"
            f":{context['theme_slug']}"
            f":{context.get('target_version', 'latest')}"
        )
    elif workflow_type == WorkflowType.SEASONAL_CAMPAIGN:
        return f"seasonal_campaign:{context['campaign_id']}"
    elif workflow_type == WorkflowType.SYSTEM_RECOVERY:
        return f"system_recovery:{datetime.utcnow().strftime('%Y%m%d%H')}"
    else:
        return f"{workflow_type.value}:{uuid.uuid4()}"
```

---

## ١١. Event Envelope — بنية الأحداث الموسّعة

```python
"""
كل حدث صادر عن المشرف يحمل طبقات معرفة إضافية.
تُمكّن من تتبع: من بدأ ماذا؟ وما الذي سبّب ماذا؟
"""

def build_supervisor_event(
    event_type:    str,
    correlation_id: str,
    data:          dict,
    causation_id:  Optional[str] = None,
    workflow_id:   Optional[str] = None,
    step_id:       Optional[str] = None,
    retry_attempt: int = 0,
) -> dict:
    return {
        "event_id":       str(uuid.uuid4()),
        "event_type":     event_type,
        "event_version":  "1.0",
        "source":         "supervisor_agent",
        "occurred_at":    datetime.utcnow().isoformat() + "Z",
        "correlation_id": correlation_id,
        "causation_id":   causation_id,
        "workflow_id":    workflow_id,
        "step_id":        step_id,
        "retry_attempt":  retry_attempt,
        "data":           data,
    }
```

---

## ١٢. Policy Engine — إدارة السياسات

```python
DEFAULT_POLICIES = {

    "daily_visual_budget": PolicyRule(
        policy_id  = "pol_visual_budget",
        rule_type  = "budget",
        condition  = "daily_visual_cost > 20.0",
        action     = "pause_visual_production",
        value      = {"threshold_usd": 20.0},
        active     = True,
        created_at = datetime.utcnow(),
        expires_at = None,
    ),

    "daily_theme_limit": PolicyRule(
        policy_id  = "pol_theme_limit",
        rule_type  = "rate_limit",
        condition  = "themes_built_today >= 3",
        action     = "pause_builder",
        value      = {"limit": 3},
        active     = True,
        created_at = datetime.utcnow(),
        expires_at = None,
    ),

    "api_cost_critical": PolicyRule(
        policy_id  = "pol_api_critical",
        rule_type  = "budget",
        condition  = "total_api_cost_today > 50.0",
        action     = "alert_owner_pause_non_critical",
        value      = {"threshold_usd": 50.0},
        active     = True,
        created_at = datetime.utcnow(),
        expires_at = None,
    ),

    "quality_threshold": PolicyRule(
        policy_id  = "pol_quality",
        rule_type  = "threshold",
        condition  = "theme_score < 70",
        action     = "block_launch",
        value      = {"minimum_score": 70},
        active     = True,
        created_at = datetime.utcnow(),
        expires_at = None,
    ),
}
```

---

## ١٣. System Degradation Policy — سياسة التدهور

```python
"""
سلوك المنظومة عند تعطّل كل وكيل — محدد كوداً لا مخمَّن.
"""

DEGRADED_MODE_RULES = {

    "builder_agent": {
        "impact":   "critical",
        "action":   "block_all_new_launches",
        "message":  "لا إطلاق بدون وكيل البناء",
    },

    "visual_production_agent": {
        "impact":   "degraded",
        "action":   "launch_with_placeholder_assets",
        "message":  "إطلاق بأصول مؤقتة + إشعار صاحب المشروع",
        "fallback_assets": {
            "hero_image":  "/assets/placeholders/hero_default.webp",
            "thumbnail":   "/assets/placeholders/thumb_default.webp",
            "screenshot":  "/assets/placeholders/screenshot_default.png",
        },
    },

    "platform_agent": {
        "impact":   "critical",
        "action":   "block_all_launches",
        "message":  "لا إطلاق بدون وكيل المنصة",
    },

    "support_agent": {
        "impact":   "semi_critical",
        "action":   "launch_allowed_kb_pending",
        "message":  "الإطلاق مسموح، قاعدة المعرفة ستُبنى لاحقاً",
    },

    "content_agent": {
        "impact":   "degraded",
        "action":   "use_default_content_template",
        "message":  "نصوص افتراضية حتى يعود الوكيل",
        "default_template": "default_product_description",
    },

    "marketing_agent": {
        "impact":   "normal",
        "action":   "continue_without_marketing",
        "message":  "الإطلاق يكمل، التسويق يُؤجَّل",
    },

    "analytics_agent": {
        "impact":   "optional",
        "action":   "continue_without_optimization",
        "message":  "الإنتاج يستمر، التحليل يُعاد لاحقاً",
    },
}


def get_degraded_action(agent_name: str) -> dict:
    return DEGRADED_MODE_RULES.get(agent_name, {
        "impact":  "unknown",
        "action":  "alert_owner",
        "message": f"وكيل غير محدد السياسة: {agent_name}",
    })


SYSTEM_HEALTH_THRESHOLDS = {
    "critical_agents_down_for_critical_alert": 1,
    "non_critical_agents_down_for_degraded":   2,
}
```

---

## ١٤. Workflow Orchestrator — تشغيل العمليات

```python
class WorkflowOrchestrator:

    def start_workflow(
        self,
        workflow_type:  WorkflowType,
        trigger_event:  dict,
    ) -> WorkflowInstance:

        definition   = WORKFLOW_DEFINITIONS[workflow_type]
        context      = trigger_event["data"]
        business_key = build_workflow_business_key(workflow_type, context)

        # Idempotency check
        existing = workflow_store.get_by_business_key(business_key)
        if existing and existing.status not in TERMINAL_STATES:
            log.info(f"Workflow موجود مسبقاً: {business_key}")
            return existing

        instance = WorkflowInstance(
            instance_id    = str(uuid.uuid4()),
            workflow_type  = workflow_type,
            business_key   = business_key,
            theme_slug     = context.get("theme_slug"),
            correlation_id = trigger_event["correlation_id"],
            current_step   = 1,
            total_steps    = len(definition["steps"]),
            status         = WorkflowStatus.PENDING,
            started_at     = datetime.utcnow(),
            completed_at   = None,
            failed_step    = None,
            failure_reason = None,
            retry_count    = 0,
            context        = context,
            step_history   = [],
        )

        transition_workflow(instance, WorkflowStatus.RUNNING, "بدء التشغيل")
        write_audit(SupervisorAuditLog(
            log_id         = str(uuid.uuid4()),
            category       = AuditCategory.WORKFLOW,
            action         = "workflow_started",
            target         = instance.instance_id,
            workflow_id    = instance.instance_id,
            correlation_id = instance.correlation_id,
            details        = {"workflow_type": workflow_type.value, "business_key": business_key},
            outcome        = None,
            created_at     = datetime.utcnow(),
        ))

        self._execute_step(instance, definition["steps"][0])
        return instance


    def on_step_completed(
        self,
        instance_id:     str,
        completed_event: str,
        event_data:      dict,
        causation_id:    str,
    ) -> None:
        instance   = workflow_store.get(instance_id)
        definition = WORKFLOW_DEFINITIONS[instance.workflow_type]
        steps      = definition["steps"]

        current_step_def = steps[instance.current_step - 1]

        if current_step_def.wait_for_event != completed_event:
            return

        # تسجيل إتمام الخطوة
        instance.step_history.append({
            "step":       instance.current_step,
            "name":       current_step_def.name,
            "completed":  datetime.utcnow().isoformat(),
            "event":      completed_event,
        })

        # التحقق من انتهاء Workflow
        if instance.current_step >= instance.total_steps:
            transition_workflow(instance, WorkflowStatus.COMPLETED, "كل الخطوات اكتملت")
            self._emit_workflow_completed(instance)
            return

        # الخطوة التالية
        instance.current_step += 1
        next_step = steps[instance.current_step - 1]

        # فحص الشرط إن وُجد
        if next_step.condition_key:
            if not self._evaluate_condition(next_step.condition_key, instance.context):
                instance.current_step += 1
                if instance.current_step > instance.total_steps:
                    transition_workflow(instance, WorkflowStatus.COMPLETED, "اكتمل مع تخطي شرطي")
                    return
                next_step = steps[instance.current_step - 1]

        transition_workflow(instance, WorkflowStatus.RUNNING, f"خطوة {instance.current_step}")
        self._execute_step(instance, next_step)


    def handle_step_timeout(
        self,
        instance_id: str,
        step_num:    int,
    ) -> None:
        instance   = workflow_store.get(instance_id)
        definition = WORKFLOW_DEFINITIONS[instance.workflow_type]
        step_def   = definition["steps"][step_num - 1]
        retry      = definition["retry_policy"]

        write_audit(SupervisorAuditLog(
            log_id         = str(uuid.uuid4()),
            category       = AuditCategory.WORKFLOW,
            action         = f"step_timeout:step_{step_num}",
            target         = instance_id,
            workflow_id    = instance_id,
            correlation_id = instance.correlation_id,
            details        = {"step": step_num, "step_name": step_def.name},
            outcome        = None,
            created_at     = datetime.utcnow(),
        ))

        if step_def.on_timeout == "retry":
            if instance.retry_count < retry["max_retries"]:
                instance.retry_count += 1
                workflow_store.save(instance)
                schedule_retry(instance_id, after_minutes=retry["backoff_minutes"])
                return
            else:
                step_def = WorkflowStep(**{**vars(step_def), "on_timeout": "fail"})

        if step_def.on_timeout == "skip" and not step_def.required:
            instance.step_history.append({
                "step":   step_num,
                "status": "skipped_timeout",
            })
            instance.current_step += 1
            workflow_store.save(instance)
            return

        # fail
        transition_workflow(
            instance,
            WorkflowStatus.FAILED,
            f"timeout at step {step_num}",
        )
        instance.failed_step   = step_num
        instance.failure_reason = f"step timeout: {step_def.name}"
        workflow_store.save(instance)
        notify_owner_of_workflow_failure(instance)
```

---

## ١٥. Conflict Resolver — حل التعارضات

```python
CONFLICT_RESOLUTION_RULES = {
    "analytics_vs_marketing": {
        "rule":     "if analytics.confidence >= 0.85: follow_analytics",
        "fallback": "escalate_to_owner",
    },
    "platform_not_ready_vs_marketing": {
        "rule":     "pause_marketing_until_platform_ready",
        "fallback": "cancel_campaign",
    },
    "content_failed_vs_platform_waiting": {
        "rule":     "use_default_content_template",
        "fallback": "delay_15min_then_retry",
    },
    "budget_exceeded_vs_production_running": {
        "rule":     "pause_non_critical_immediately",
        "fallback": "pause_all_and_alert",
    },
}


class ConflictResolver:

    def resolve(self, conflict: ConflictRecord) -> None:
        rule_key = self._find_rule(conflict)

        write_audit(SupervisorAuditLog(
            log_id         = str(uuid.uuid4()),
            category       = AuditCategory.CONFLICT,
            action         = "conflict_detected",
            target         = str(conflict.agents_involved),
            correlation_id = None,
            details        = {"type": conflict.conflict_type.value,
                               "description": conflict.description},
            outcome        = None,
            created_at     = datetime.utcnow(),
        ))

        if rule_key:
            self._apply_rule(rule_key, conflict)
            write_audit(SupervisorAuditLog(
                log_id         = str(uuid.uuid4()),
                category       = AuditCategory.CONFLICT,
                action         = "conflict_resolved",
                target         = conflict.conflict_id,
                details        = {"rule": rule_key},
                outcome        = "applied_rule",
                created_at     = datetime.utcnow(),
            ))
        else:
            conflict.escalated = True
            conflict_store.save(conflict)
            notify_owner_of_conflict(conflict)
            write_audit(SupervisorAuditLog(
                log_id     = str(uuid.uuid4()),
                category   = AuditCategory.ESCALATION,
                action     = "conflict_escalated_to_owner",
                target     = conflict.conflict_id,
                details    = {"reason": "no matching rule"},
                outcome    = "escalated",
                created_at = datetime.utcnow(),
            ))
```

---

## ١٦. Health Monitor — مراقبة الصحة

```python
HEARTBEAT_CONTRACT = {
    "event_type":    "AGENT_HEARTBEAT",
    "interval_sec":  60,
    "required_fields": ["agent_status", "queue_depth", "active_jobs",
                         "version", "mode"],
    "schema": {
        "agent_status": str,     # "healthy" | "degraded" | "paused"
        "queue_depth":  int,
        "active_jobs":  int,
        "version":      str,     # "1.0.0"
        "mode":         str,     # "normal" | "degraded"
    },
}

HEALTH_THRESHOLDS = {
    "heartbeat_timeout_minutes": 5,
    "queue_depth_warning":       50,
    "queue_depth_critical":      200,
    "error_rate_warning":        0.05,
    "error_rate_critical":       0.20,
    "api_cost_warning_usd":      40,
    "api_cost_critical_usd":     50,
}


class HealthMonitor:

    def run_health_checks(self) -> List[AgentHealthRecord]:
        records = []

        for agent_name, entry in AGENT_REGISTRY.items():
            if not entry.heartbeat_required:
                continue

            record = self._check_agent(agent_name, entry)
            records.append(record)
            health_store.save(record)

            if record.status == AgentHealthStatus.UNHEALTHY:
                self._handle_unhealthy(agent_name, record, entry)
            elif record.status == AgentHealthStatus.DEGRADED:
                self._handle_degraded(agent_name, record)

        self._check_redis_queues()
        self._check_api_costs()
        return records


    def _handle_unhealthy(
        self,
        agent_name: str,
        record:     AgentHealthRecord,
        entry:      AgentRegistryEntry,
    ) -> None:
        write_audit(SupervisorAuditLog(
            log_id     = str(uuid.uuid4()),
            category   = AuditCategory.HEALTH,
            action     = "agent_unhealthy",
            target     = agent_name,
            details    = {"issues": record.issues, "criticality": entry.criticality.value},
            outcome    = None,
            created_at = datetime.utcnow(),
        ))

        # إجراء بحسب criticality
        if entry.criticality == AgentCriticality.CRITICAL:
            # إيقاف Workflows المعلّقة التي تنتظر هذا الوكيل
            self._block_dependent_workflows(agent_name)

        # تطبيق Degradation Policy
        degraded_action = get_degraded_action(agent_name)

        # إشعار صاحب المشروع دائماً عند CRITICAL
        if entry.criticality in (AgentCriticality.CRITICAL,
                                   AgentCriticality.SEMI_CRITICAL):
            notify_owner_agent_unhealthy(agent_name, record, degraded_action)

        # إطلاق SYSTEM_ALERT
        redis.publish(REDIS_CHANNELS["supervisor"], json.dumps(
            build_supervisor_event(
                event_type     = "SYSTEM_ALERT",
                correlation_id = f"health:{agent_name}",
                data           = {
                    "severity":       "critical",
                    "agent":          agent_name,
                    "criticality":    entry.criticality.value,
                    "issues":         record.issues,
                    "degraded_action": degraded_action["action"],
                },
            )
        ))
```

---

## ١٧. Supervisor Audit Log — سجل التدقيق الشامل

```python
"""
كل إجراء يُسجَّل — لا حدث بلا أثر.
"""

AUDIT_TRIGGERS = {
    "workflow_start":          AuditCategory.WORKFLOW,
    "workflow_step_transition": AuditCategory.WORKFLOW,
    "workflow_completed":       AuditCategory.WORKFLOW,
    "workflow_failed":          AuditCategory.WORKFLOW,
    "policy_applied":           AuditCategory.POLICY,
    "conflict_detected":        AuditCategory.CONFLICT,
    "conflict_resolved":        AuditCategory.CONFLICT,
    "conflict_escalated":       AuditCategory.ESCALATION,
    "manual_command_received":  AuditCategory.COMMAND,
    "agent_paused":             AuditCategory.HEALTH,
    "agent_resumed":            AuditCategory.HEALTH,
    "agent_unhealthy":          AuditCategory.HEALTH,
    "override_applied":         AuditCategory.OVERRIDE,
    "escalation_sent":          AuditCategory.ESCALATION,
}


def write_audit(log: SupervisorAuditLog) -> None:
    audit_store.save(log)
    # نشر على audit_events لأي مستهلك خارجي
    redis.publish(AUDIT_CHANNEL, json.dumps({
        "log_id":         log.log_id,
        "category":       log.category.value,
        "action":         log.action,
        "target":         log.target,
        "workflow_id":    log.workflow_id,
        "correlation_id": log.correlation_id,
        "created_at":     log.created_at.isoformat(),
    }))
```

---

## ١٨. Redis Failure Mode — فشل Redis

```python
"""
كل سلطة المشرف عبر Redis.
فشل Redis = failure mode مركزي يحتاج سياسة.
"""

REDIS_FAILURE_POLICY = {

    "detection": {
        "method":          "health check كل 30 ثانية",
        "timeout_seconds": 5,
    },

    "on_failure": {
        "workflow_orchestrator": "freeze — لا خطوات جديدة، لا إلغاء",
        "health_monitor":        "read_only_local_cache",
        "policy_engine":         "apply_last_known_policies_only",
        "manual_controller":     "reject_new_commands",
        "pending_events":        "buffer_locally_max_100",
    },

    "recovery": {
        "on_redis_reconnect": [
            "flush_local_buffer_to_redis",
            "re_evaluate_active_workflows",
            "resume_health_checks",
            "notify_owner_of_outage_and_recovery",
        ],
    },

    "owner_notification": {
        "on_outage_start":    "فوري — تنبيه حرج",
        "on_outage_duration": "كل 15 دقيقة",
        "on_recovery":        "فوري",
    },
}


class RedisHealthChecker:

    def check(self) -> bool:
        try:
            redis.ping()
            return True
        except:
            return False

    def handle_failure(self) -> None:
        notify_owner_redis_failure()
        supervisor_state["redis_available"] = False
        supervisor_state["mode"]            = "degraded"

        write_audit(SupervisorAuditLog(
            log_id     = str(uuid.uuid4()),
            category   = AuditCategory.HEALTH,
            action     = "redis_failure_detected",
            target     = "redis",
            details    = {"action": "entering_degraded_mode"},
            outcome    = None,
            created_at = datetime.utcnow(),
        ))

    def handle_recovery(self) -> None:
        supervisor_state["redis_available"] = True
        supervisor_state["mode"]            = "normal"
        self._flush_local_buffer()
        notify_owner_redis_recovered()
```

---

## ١٩. Self-healing Boundaries — حدود الإصلاح الذاتي

```python
"""
المشرف يكتشف ويُبلّغ.
الإصلاح الذاتي محدود بحالات آمنة فقط.
"""

SELF_HEALING_ALLOWED = {
    "retry_failed_workflow_step": {
        "condition": "step.on_timeout == 'retry' and retry_count < max_retries",
        "action":    "schedule_retry",
        "safe":      True,
    },
    "skip_optional_timed_out_step": {
        "condition": "not step.required and step.on_timeout == 'skip'",
        "action":    "advance_to_next_step",
        "safe":      True,
    },
    "apply_degradation_policy": {
        "condition": "agent_unhealthy and degraded_fallback defined",
        "action":    "apply_degraded_fallback",
        "safe":      True,
    },
    "pause_on_budget_exceeded": {
        "condition": "policy_violated and action == 'pause'",
        "action":    "emit_AGENT_PAUSE",
        "safe":      True,
    },
}

SELF_HEALING_FORBIDDEN = {
    "restart_agent_process":      "يحتاج تدخل infra",
    "repair_database_records":    "يحتاج تدخل بشري",
    "recreate_failed_content":    "يحتاج قرار بشري",
    "recover_from_financial_error": "يحتاج تدخل مالي بشري",
    "override_USER_LOCKED":        "محظور مطلقاً",
}
```

---

## ٢٠. Override Authority — حدود التجاوز

```python
OVERRIDEABLE = {
    "analytics_signal":        True,
    "content_agent_rejection": True,
    "visual_agent_timeout":    True,
    "marketing_schedule":      True,
}

NON_OVERRIDEABLE = [
    "budget_change", "discount_change", "targeting_change",
    "crisis_response", "campaign_stop", "product_deletion",
    "financial_transactions", "customer_data_access",
    "theme_approval", "visual_review", "product_page_review",
]


def log_override(
    conflict:  ConflictRecord,
    rule:      dict,
) -> None:
    override = OverrideLog(
        override_id         = str(uuid.uuid4()),
        supervisor_decision = rule.get("action", ""),
        overridden_agent    = ", ".join(conflict.agents_involved),
        original_signal     = {"signals": conflict.signals},
        override_reason     = str(rule),
        applied_at          = datetime.utcnow(),
        outcome             = None,
    )
    override_store.save(override)
    notify_owner_of_override(override)

    write_audit(SupervisorAuditLog(
        log_id     = str(uuid.uuid4()),
        category   = AuditCategory.OVERRIDE,
        action     = "override_applied",
        target     = str(conflict.agents_involved),
        details    = {"override_id": override.override_id, "rule": str(rule)},
        outcome    = None,
        created_at = datetime.utcnow(),
    ))
```

---

## ٢١. USER_LOCKED_DECISIONS — حدود لا تُتجاوز

```python
SUPERVISOR_LOCKED = [
    "budget_change", "discount_change", "targeting_change",
    "crisis_response", "campaign_stop",
    "product_deletion", "price_modification",
    "financial_refund", "customer_data_export",
    "security_policy_change", "theme_approval",
    "visual_review", "product_page_review",
]


def validate_supervisor_action(action: str) -> tuple[bool, str]:
    if action in SUPERVISOR_LOCKED:
        return False, f"SUP_LOCKED_DECISION: {action} محجوز لصاحب المشروع"
    return True, ""
```

---

## ٢٢. علاقة المشرف بصاحب المشروع

```python
OWNER_NOTIFICATION_TRIGGERS = {
    "workflow_failed":        "Workflow فشل بعد كل المحاولات",
    "agent_unhealthy":        "وكيل في حالة حرجة",
    "conflict_unresolvable":  "تعارض بلا قاعدة",
    "budget_critical":        "ميزانية تجاوزت الحد",
    "redis_failure":          "Redis متعطل",
    "override_applied":       "المشرف تجاوز قراراً (توثيق)",
    "manual_action_required": "إجراء يدوي ضروري",
}

MANUAL_TRIGGERS_FROM_OWNER = {
    "start_theme_launch":      "يبدأ Workflow إطلاق",
    "start_seasonal_campaign": "يبدأ حملة موسمية",
    "pause_all_marketing":     "يُجمّد التسويق",
    "resume_marketing":        "يستأنف التسويق",
    "override_conflict":       "يُقرر في تعارض مُصعَّد",
    "update_policy":           "يُعدّل سياسة",
    "emergency_stop":          "يوقف المنظومة",
}
```

---

## ٢٣. معمارية الوكيل — ثلاثة Workflows

```
Workflow 1: Orchestration Engine
  المُشغِّل: THEME_APPROVED / THEME_UPDATED / CAMPAIGN_START
  الطبيعة:  State Machine صارمة

Workflow 2: Health & Policy Daemon
  المُشغِّل: cron كل 60 ثانية
  الطبيعة:  daemon مستمر

Workflow 3: Manual Controller
  المُشغِّل: أوامر يدوية من صاحب المشروع
  الطبيعة:  استجابة فورية + Audit Log
```

---

## ٢٤. SUPERVISOR_EVENTS — الأحداث الخاصة

```python
SUPERVISOR_EMITS = {
    "WORKFLOW_START":       "بدء Workflow",
    "WORKFLOW_CANCEL":      "إلغاء Workflow",
    "WORKFLOW_COMPLETED":   "اكتمال Workflow",
    "WORKFLOW_FAILED":      "فشل Workflow",
    "AGENT_PAUSE":          "تجميد وكيل",
    "AGENT_RESUME":         "استئناف وكيل",
    "POLICY_UPDATE":        "تحديث سياسة",
    "SYSTEM_ALERT":         "تنبيه نظام",
    "SUPERVISOR_OVERRIDE":  "تجاوز موثَّق",
    "CONFLICT_DETECTED":    "تعارض مكتشف",
    "HEALTH_DEGRADED":      "وكيل متدهور",
}

SUPERVISOR_CONSUMES = {
    "THEME_APPROVED":       "يبدأ THEME_LAUNCH workflow",
    "THEME_UPDATED":        "يبدأ THEME_UPDATE workflow",
    "AGENT_HEARTBEAT":      "يُحدّث سجل الصحة",
    "WORKFLOW_STEP_DONE":   "يُكمّل خطوة",
    "NEW_PRODUCT_LIVE":     "يُشغّل الخطوات المتوازية",
}
```

---

## ٢٥. Idempotency Strategy

```python
"""
idempotency مبنية على business_key لا على معرّف عام.
"""
# راجع build_workflow_business_key في القسم ١٠
# FAILED نهائي — retry = instance جديدة بنفس business_key
```

---

## ٢٦. Event Contract Schemas

### WORKFLOW_START

```json
{
  "event_id":       "uuid-v4",
  "event_type":     "WORKFLOW_START",
  "event_version":  "1.0",
  "source":         "supervisor_agent",
  "occurred_at":    "ISO-datetime",
  "correlation_id": "launch:restaurant_modern:20250316-0001",
  "causation_id":   "event-uuid-of-THEME_APPROVED",
  "workflow_id":    "wf-uuid",
  "step_id":        null,
  "retry_attempt":  0,
  "data": {
    "workflow_type":   "theme_launch",
    "business_key":    "theme_launch:restaurant_modern:20250316-0001",
    "theme_slug":      "restaurant_modern",
    "total_steps":     6,
    "timeout_minutes": 240
  }
}
```

### SYSTEM_ALERT

```json
{
  "event_type":  "SYSTEM_ALERT",
  "source":      "supervisor_agent",
  "data": {
    "severity":        "critical",
    "agent":           "platform_agent",
    "criticality":     "critical",
    "issues":          ["لا heartbeat منذ 8 دقائق"],
    "degraded_action": "block_all_launches"
  }
}
```

### AGENT_HEARTBEAT (مُستقبَل)

```json
{
  "event_type":  "AGENT_HEARTBEAT",
  "source":      "marketing_agent",
  "occurred_at": "ISO-datetime",
  "data": {
    "agent_status": "healthy",
    "queue_depth":  12,
    "active_jobs":  2,
    "version":      "1.0.0",
    "mode":         "normal"
  }
}
```

---

## ٢٧. Error Codes Catalog

```python
SUPERVISOR_ERROR_CODES = {
    "SUP_AGENT_NOT_REGISTERED":   "وكيل غير موجود في Registry",
    "SUP_WORKFLOW_NOT_FOUND":     "نوع Workflow غير معرَّف",
    "SUP_WORKFLOW_DUPLICATE":     "Workflow نشط بنفس business_key",
    "SUP_INVALID_TRANSITION":     "انتقال حالة غير مسموح في State Machine",
    "SUP_WORKFLOW_TIMEOUT":       "Workflow تجاوز الحد الزمني",
    "SUP_WORKFLOW_FAILED":        "Workflow فشل بعد كل المحاولات",
    "SUP_STEP_TIMEOUT":           "خطوة تجاوزت مهلتها",
    "SUP_CONFLICT_UNRESOLVABLE":  "تعارض بلا قاعدة — مُصعَّد",
    "SUP_POLICY_VIOLATION":       "انتهاك سياسة",
    "SUP_LOCKED_DECISION":        "محاولة تجاوز قرار محجوز",
    "SUP_AGENT_UNHEALTHY":        "وكيل في حالة حرجة",
    "SUP_REDIS_FAILURE":          "Redis متعطل — degraded mode",
    "SUP_OVERRIDE_BLOCKED":       "تجاوز على قرار مقفول",
    "SUP_BUDGET_EXCEEDED":        "ميزانية تجاوزت الحد",
    "SUP_COMMAND_UNAUTHORIZED":   "أمر من مصدر غير موثوق",
    "SUP_SELF_HEALING_FORBIDDEN": "إصلاح ذاتي محظور لهذه الحالة",
}
```

---

## ٢٨. بنية الـ State

```python
class SupervisorState(TypedDict):
    active_workflows:    List[WorkflowInstance]
    completed_workflows: List[str]
    failed_workflows:    List[str]
    pending_conflicts:   List[ConflictRecord]
    agent_health:        Dict[str, AgentHealthRecord]
    last_health_check:   Optional[datetime]
    active_policies:     List[PolicyRule]
    policy_violations:   List[Dict]
    override_log:        List[OverrideLog]
    redis_available:     bool
    mode:                str   # "normal" | "degraded"
    system_status:       str   # "healthy" | "degraded" | "critical"
    status:              str
    error_code:          Optional[str]
    logs:                List[str]
```

---

## ٢٩. البيئة المحلية ومتغيرات البيئة

```env
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:pass@localhost/supervisor_db
RESEND_API_KEY=...
STORE_EMAIL_FROM=قوالب عربية <hello@ar-themes.com>
OWNER_EMAIL=owner@ar-themes.com

HEALTH_CHECK_INTERVAL_SECONDS=60
HEARTBEAT_TIMEOUT_MINUTES=5
QUEUE_DEPTH_WARNING=50
QUEUE_DEPTH_CRITICAL=200
ERROR_RATE_WARNING=0.05
ERROR_RATE_CRITICAL=0.20

DAILY_VISUAL_BUDGET_USD=20.0
DAILY_API_COST_CRITICAL_USD=50.0
DAILY_THEME_LIMIT=3
MIN_THEME_QUALITY_SCORE=70

THEME_LAUNCH_TIMEOUT_MINUTES=240
THEME_UPDATE_TIMEOUT_MINUTES=120

REDIS_CHECK_INTERVAL_SECONDS=30
REDIS_LOCAL_BUFFER_MAX=100

LOG_LEVEL=INFO
```

---

## ٣٠. دستور الوكيل

```markdown
# دستور وكيل المشرف v2

## الهوية
أنا طبقة التنسيق العليا — أرى المنظومة كاملة وأُنسّق الكبير.
Agent Registry مصدر معرفتي عن الوكلاء.
State Machine مرجعي في كل انتقال.
Audit Log أثري في كل إجراء.

## القواعد المطلقة
١. Agent Registry مصدر الحقيقة — لا hardcoded knowledge
٢. State Machine صارمة — لا انتقالات خارج الجدول
٣. Audit Log لكل إجراء — لا حدث بلا أثر
٤. Degradation Policy كوداً — لا تخمين عند التعطل
٥. السلطة عبر الأحداث فقط — لا function calls مباشرة
٦. USER_LOCKED_DECISIONS محصّنة — حتى في الطوارئ
٧. Redis failure = graceful degradation — لا صمت
٨. Self-healing في الحدود الآمنة فقط
٩. كل Override مُوثَّق + إشعار صاحب المشروع
١٠. لست Single Point of Failure — الوكلاء تعمل بدوني

## ما أُجيده
- Workflow بـ State Machine صريحة وخطوات صارمة
- حل التعارضات بقواعد وتصعيد الغامض
- Health Monitor مع Degradation Policy محددة
- Policy Engine للميزانية والسياسات
- Audit Log شامل لكل إجراء
- Graceful degradation عند فشل Redis
```

---

## ٣١. قائمة التحقق النهائية

### Orchestration Engine

```
□ THEME_APPROVED → يبدأ THEME_LAUNCH بعد business_key check
□ State Machine: كل انتقال عبر transition_workflow()
□ FAILED نهائي — retry = WorkflowInstance جديدة
□ WorkflowStep.on_timeout و on_failure مُطبَّقان دائماً
□ خطوات parallel_group تعمل معاً
□ شروط condition_key مُقيَّمة قبل تشغيل الخطوة
□ كل انتقال في Audit Log
□ WORKFLOW_COMPLETED / WORKFLOW_FAILED مُطلَقان
□ Workflow Priority عند التنافس: SYSTEM_RECOVERY أولاً
```

### Health & Policy Daemon

```
□ يعمل كل 60 ثانية
□ Agent Registry مصدر قائمة الوكلاء المراقَبة
□ Heartbeat contract: agent_status + queue_depth + active_jobs + version + mode
□ Degradation Policy مُطبَّقة عند unhealthy
□ CRITICAL agent unhealthy → block_dependent_workflows
□ SYSTEM_ALERT مُطلَق للحالات الحرجة
□ Redis health check كل 30 ثانية
□ Redis failure → local buffer + notify_owner
□ Policy Engine يُطبَّق في كل tick
□ كل إجراء في Audit Log
```

### Manual Controller

```
□ كل أمر يمر عبر validate_supervisor_action
□ USER_LOCKED_DECISIONS: رفض فوري
□ emergency_stop: كل الوكلاء + Audit Log + إشعار
□ update_policy: Audit Log + إشعار صاحب المشروع
□ override_conflict: Audit Log + OverrideLog + إشعار
```

### Agent Registry

```
□ كل وكيل جديد يُضاف للـ Registry قبل التشغيل
□ criticality محدد لكل وكيل
□ degraded_fallback محدد لكل وكيل
□ get_agent() يُوقف عند وكيل غير مسجَّل
```
