"""Node: NOTIFICATION_SENDER — T061 | إرسال إيميلات التحديث مع idempotency"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started
from db.registry import ProductRegistry
from services.resend_client import ResendClient
from state import UpdateState

logger = logging.getLogger("platform_agent.nodes.update.notification_sender")
NODE_NAME = "NOTIFICATION_SENDER"

def make_notification_sender_node(registry: ProductRegistry, resend: ResendClient):
    def notification_sender_node(state: UpdateState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        eligible = state.get("eligible_buyers", [])
        theme_slug = state["theme_slug"]
        new_version = state["new_version"]
        changelog = state.get("changelog", {})

        # جلب theme_name_ar من record
        record = registry.get(theme_slug)
        theme_name_ar = record.get("theme_name_ar", theme_slug) if record else theme_slug

        sent = 0
        failed = 0
        for buyer in eligible:
            email = buyer.get("email", "")
            ok = resend.send_update_notification(
                to=email,
                theme_name_ar=theme_name_ar,
                theme_slug=theme_slug,
                new_version=new_version,
                changelog=changelog,
            )
            if ok:
                sent += 1
                _log_notification(registry.db, email, theme_slug, new_version)
            else:
                failed += 1

        total = len(eligible)
        error_code = None
        if sent == 0 and total > 0:
            error_code = "PLT_901"  # فشل كلي
        elif failed > 0:
            error_code = "PLT_902"  # فشل جزئي — يكمل

        result = {
            **state,
            "notification_results": {"sent": sent, "failed": failed, "total": total},
            "error_code": error_code,
            "logs": state.get("logs",[]) + [f"NOTIFICATION_SENDER: sent={sent} failed={failed}"],
        }
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("NOTIFICATION_SENDER | sent=%s failed=%s theme=%s v%s", sent, failed, theme_slug, new_version)
        return result
    return notification_sender_node

def _log_notification(db_conn, email: str, theme_slug: str, version: str) -> None:
    try:
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO notification_log (buyer_email, theme_slug, version) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                (email, theme_slug, version),
            )
        db_conn.commit()
    except Exception as exc:
        logger.warning("notification_log insert failed | %s", exc)
        db_conn.rollback()
