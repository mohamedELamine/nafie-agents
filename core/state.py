"""
core/state.py
=============
BusinessState — الحالة المشتركة لكل المنظومة.
كل وكيل يقرأ منها ويكتب فيها عبر Redis.
"""

from typing import TypedDict, Optional, List, Dict, Any, Literal
from enum import Enum


# ══════════════════════════════════════════════════════
# التعدادات الأساسية
# ══════════════════════════════════════════════════════

class AgentName(str, Enum):
    SUPERVISOR       = "supervisor"
    BUILDER          = "builder"
    PLATFORM         = "platform"
    SUPPORT          = "support"
    CONTENT          = "content"
    MARKETING        = "marketing"
    ANALYTICS        = "analytics"
    VISUAL_PRODUCTION = "visual_production"


class EventType(str, Enum):
    # أحداث البناء
    THEME_BUILD_REQUESTED  = "theme.build.requested"
    THEME_BUILD_COMPLETED  = "theme.build.completed"
    THEME_BUILD_FAILED     = "theme.build.failed"

    # أحداث المنصة
    THEME_PUBLISH_REQUESTED = "platform.publish.requested"
    THEME_PUBLISHED         = "platform.published"
    PRODUCT_UPDATED         = "platform.product.updated"

    # أحداث الدعم
    TICKET_CREATED         = "support.ticket.created"
    TICKET_RESOLVED        = "support.ticket.resolved"
    TICKET_ESCALATED       = "support.ticket.escalated"

    # أحداث المحتوى
    CONTENT_REQUESTED      = "content.requested"
    CONTENT_READY          = "content.ready"

    # أحداث التسويق
    CAMPAIGN_TRIGGERED     = "marketing.campaign.triggered"
    CAMPAIGN_SENT          = "marketing.campaign.sent"

    # أحداث التحليل
    REPORT_REQUESTED       = "analytics.report.requested"
    REPORT_READY           = "analytics.report.ready"
    ANOMALY_DETECTED       = "analytics.anomaly.detected"

    # أحداث الإنتاج البصري
    VISUAL_REQUESTED       = "visual.requested"
    VISUAL_READY           = "visual.ready"

    # أحداث المشرف
    SUPERVISOR_ALERT       = "supervisor.alert"
    SUPERVISOR_DECISION    = "supervisor.decision"


class TaskStatus(str, Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"
    FAILED     = "failed"
    PAUSED     = "paused"


# ══════════════════════════════════════════════════════
# حدث المنظومة
# ══════════════════════════════════════════════════════

class BusinessEvent(TypedDict):
    event_id:    str               # UUID فريد
    event_type:  EventType
    source:      AgentName         # من أطلق الحدث
    target:      Optional[AgentName]  # None = broadcast
    payload:     Dict[str, Any]
    timestamp:   str               # ISO 8601
    trace_id:    str               # للربط بـ LangSmith
    priority:    int               # 1=عاجل · 5=عادي


# ══════════════════════════════════════════════════════
# معلومات القالب (مشتركة بين الوكلاء)
# ══════════════════════════════════════════════════════

class ThemeInfo(TypedDict):
    theme_slug:     str
    theme_name_ar:  str
    theme_name_en:  str
    domain:         str
    cluster:        str
    version:        str
    woo_enabled:    bool
    cod_enabled:    bool
    build_date:     str
    zip_path:       Optional[str]
    product_id:     Optional[int]   # WooCommerce product ID بعد النشر
    price:          Optional[float]
    status:         Literal["building", "ready", "published", "archived"]


# ══════════════════════════════════════════════════════
# حالة الأعمال المشتركة
# ══════════════════════════════════════════════════════

class BusinessState(TypedDict):
    # ── هوية الجلسة ──────────────────────────────────
    session_id:      str
    run_id:          str
    trace_id:        str
    initiated_by:    AgentName
    created_at:      str

    # ── معلومات القالب الحالي ────────────────────────
    current_theme:   Optional[ThemeInfo]

    # ── قائمة انتظار المهام ──────────────────────────
    task_queue:      List[Dict[str, Any]]
    active_tasks:    Dict[str, TaskStatus]   # task_id → status

    # ── حافلة الأحداث (مؤقتة في الجلسة) ─────────────
    pending_events:  List[BusinessEvent]
    processed_events: List[str]              # event_ids

    # ── حالة كل وكيل ─────────────────────────────────
    agent_status:    Dict[AgentName, TaskStatus]
    agent_last_seen: Dict[AgentName, str]    # ISO timestamps

    # ── المتغيرات المشتركة بين الوكلاء ───────────────
    shared_context:  Dict[str, Any]          # بيانات حرة

    # ── قرارات المشرف ────────────────────────────────
    supervisor_decisions: List[Dict[str, Any]]
    escalations:          List[Dict[str, Any]]

    # ── الأخطاء والتنبيهات ───────────────────────────
    errors:          List[Dict[str, Any]]
    warnings:        List[Dict[str, Any]]

    # ── المراقبة ─────────────────────────────────────
    langsmith_run_id: Optional[str]
    metrics:          Dict[str, Any]
