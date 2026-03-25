"""
Node: HUMAN_REVIEW_GATE — T049
نقطة تعليق بشرية. يُرسل صفحة المنتج لصاحب المشروع وينتظر قراره.
MAX_REVISION_CYCLES = 3 (من .env)
المرجع: spec.md § ١٤ | tasks/phase3 § T049
"""
from __future__ import annotations
import logging
import os
from db.idempotency import mark_completed, mark_started
from db.registry import ProductRegistry
from services.resend_client import ResendClient
from services.redis_bus import RedisBus
from state import LaunchState, PlatformStatus, ReviewDecision

logger = logging.getLogger("platform_agent.nodes.launch.human_review_gate")
NODE_NAME = "HUMAN_REVIEW_GATE"
MAX_REVISION_CYCLES = int(os.getenv("MAX_REVISION_CYCLES", "3"))

def make_human_review_gate_node(
    registry: ProductRegistry,
    resend: ResendClient,
    redis_bus: RedisBus,
):
    def human_review_gate_node(state: LaunchState) -> dict:
        ikey = state["idempotency_key"]
        human_decision = state.get("human_decision")

        # إن لم يكن هناك قرار بعد → أرسل طلب المراجعة وعلّق
        if not human_decision:
            mark_started(registry.db, ikey, NODE_NAME)
            _send_review_request(resend, redis_bus, state)
            result = {
                **state,
                "status": PlatformStatus.WAITING_HUMAN_REVIEW,
                "logs": state.get("logs",[]) + ["HUMAN_REVIEW_GATE: WAITING — review request sent"],
            }
            return result

        # قرار موجود → معالجته
        revision_count = state.get("revision_count", 0)
        decision = human_decision

        if decision in (ReviewDecision.APPROVED_AS_IS.value, ReviewDecision.APPROVED_WITH_EDITS.value):
            result = {
                **state,
                "status": PlatformStatus.RUNNING,
                "logs": state.get("logs",[]) + [f"HUMAN_REVIEW_GATE: APPROVED ({decision})"],
            }
            mark_completed(registry.db, ikey, NODE_NAME, result)
            logger.info("HUMAN_REVIEW_GATE | APPROVED | theme=%s", state["theme_slug"])
            return result

        if decision in (ReviewDecision.NEEDS_REVISION_MINOR.value, ReviewDecision.NEEDS_REVISION_MAJOR.value):
            if revision_count >= MAX_REVISION_CYCLES - 1:
                # وصلنا الحد الأقصى → LAUNCH_HOLD
                result = {
                    **state,
                    "status": PlatformStatus.FAILED,
                    "error_code": "PLT_501",
                    "error": f"تجاوزنا {MAX_REVISION_CYCLES} دورات مراجعة — LAUNCH_HOLD",
                    "logs": state.get("logs",[]) + ["HUMAN_REVIEW_GATE: MAX_REVISIONS reached → LAUNCH_HOLD"],
                }
                mark_completed(registry.db, ikey, NODE_NAME, result)
                return result
            # دورة جديدة
            result = {
                **state,
                "revision_count": revision_count + 1,
                "revision_notes": state.get("human_edits", {}).get("notes", ""),
                "human_decision": None,  # reset للدورة التالية
                "status": PlatformStatus.RUNNING,
                "logs": state.get("logs",[]) + [f"HUMAN_REVIEW_GATE: revision #{revision_count+1}"],
            }
            logger.info("HUMAN_REVIEW_GATE | REVISION #%s | theme=%s", revision_count+1, state["theme_slug"])
            return result

        if decision == ReviewDecision.REJECTED.value:
            result = {
                **state,
                "status": PlatformStatus.FAILED,
                "error_code": "PLT_501",
                "error": "رفض صاحب المشروع الإطلاق — LAUNCH_CANCEL",
                "logs": state.get("logs",[]) + ["HUMAN_REVIEW_GATE: REJECTED"],
            }
            mark_completed(registry.db, ikey, NODE_NAME, result)
            logger.info("HUMAN_REVIEW_GATE | REJECTED | theme=%s", state["theme_slug"])
            return result

        # قرار غير معروف
        return {**state, "status": PlatformStatus.WAITING_HUMAN_REVIEW}

    return human_review_gate_node


def route_after_review(state: LaunchState) -> str:
    """LangGraph conditional edge — يُحدد الـ node التالي بعد HUMAN_REVIEW_GATE."""
    status = state.get("status")
    decision = state.get("human_decision")
    revision_count = state.get("revision_count", 0)

    if status == PlatformStatus.WAITING_HUMAN_REVIEW:
        return "END"
    if status == PlatformStatus.FAILED:
        return "END"
    if decision in (ReviewDecision.NEEDS_REVISION_MINOR.value, ReviewDecision.NEEDS_REVISION_MAJOR.value):
        return "page_writer"  # إعادة توليد الصفحة
    return "saga_publisher"   # موافق → نشر


def _send_review_request(resend: ResendClient, redis_bus: RedisBus, state: LaunchState) -> None:
    """يُرسل طلب المراجعة لصاحب المشروع عبر البريد الإلكتروني."""
    parsed = state.get("parsed", {})
    theme_name_ar = parsed.get("theme_name_ar", state["theme_slug"])
    ikey = state["idempotency_key"]
    owner_email = os.getenv("OWNER_EMAIL", "")

    review_url = f"{os.getenv('STORE_URL','')}/platform/review/{ikey}"

    try:
        resend._send(
            to=owner_email,
            subject=f"🔍 مراجعة مطلوبة — قالب {theme_name_ar}",
            html=(
                f"<div dir='rtl'>"
                f"<h2>طلب مراجعة صفحة المنتج</h2>"
                f"<p>يرجى مراجعة صفحة المنتج للقالب <strong>{theme_name_ar}</strong> واتخاذ قرار.</p>"
                f"<p><a href='{review_url}' style='background:#1a73e8;color:#fff;padding:10px 24px;"
                f"border-radius:6px;text-decoration:none;'>فتح صفحة المراجعة</a></p>"
                f"<p style='color:#999;font-size:12px;'>مفتاح الـ Workflow: {ikey}</p>"
                f"</div>"
            ),
        )
        # حفظ checkpoint في Redis
        redis_bus._redis.setex(
            f"workflow:{ikey}:checkpoint",
            172800,  # 48 ساعة TTL
            NODE_NAME,
        )
    except Exception as exc:
        logger.error("HUMAN_REVIEW_GATE | send_review_request failed | %s", exc)
