"""
Immediate Evaluator — يعمل بجانب Event Collector.
يتحقق من نوافذ زمنية تحتاج تراكم بيانات.
يُشغَّل: على كل حدث (checks خفيفة) + كل 15 دقيقة (scheduled checks).
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from core.contracts import EVENT_ANALYTICS_SIGNAL, STREAM_ANALYTICS_SIGNALS
from ..db import event_store, signal_store
from ..db.connection import get_conn
from ..logging_config import get_logger
from ..metric_definitions import IMMEDIATE_THRESHOLDS, get_signal_target
from ..models import SignalPriority, SignalType

logger = get_logger("workflows.immediate_evaluator")


class ImmediateEvaluator:
    def evaluate(self, event: Dict[str, Any]) -> None:
        """Backward-compatible entry point used by the agent runtime."""
        self.on_new_event(event)

    def on_new_event(self, event: Dict[str, Any]) -> None:
        """
        يُشغَّل على كل حدث — checks خفيفة فقط (لا استعلامات ثقيلة).
        الفحوصات التي تحتاج نافذة زمنية → run_scheduled_checks().
        """
        try:
            event_type = event.get("event_type")
            theme_slug = event.get("theme_slug")

            # دعم عند تصعيد تذكرة — فحص surge فوري
            if event_type == "SUPPORT_TICKET_ESCALATED":
                self._check_support_surge(theme_slug)

            # مشكلة جودة متكررة — إشارة فورية لوكيل البناء
            if event_type == "RECURRING_ISSUE_DETECTED":
                raw = event.get("raw_data", {})
                _emit_signal(
                    signal_type  = SignalType.RECURRING_QUALITY_ISSUE,
                    theme_slug   = theme_slug,
                    data         = raw,
                    target_agent = get_signal_target("recurring_quality_issue"),
                    priority     = SignalPriority.IMMEDIATE,
                )

            # جدولة فحص بعد إطلاق منتج (no_sales check بعد 30 يوم)
            # يُعالَج في run_scheduled_checks عبر الـ DB

            # جدولة فحص حملة بلا منشور بعد 24 ساعة
            # يُعالَج في run_scheduled_checks

        except Exception as e:
            logger.error(f"Error in on_new_event: {e}")

    def run_scheduled_checks(self) -> None:
        """يُشغَّل كل 15 دقيقة — للفحوصات التي تحتاج نافذة زمنية."""
        logger.info("Running scheduled immediate evaluator checks")
        try:
            self._check_no_sales_products()
        except Exception as e:
            logger.error(f"_check_no_sales_products failed: {e}")

        try:
            self._check_sales_drop()
        except Exception as e:
            logger.error(f"_check_sales_drop failed: {e}")

        try:
            self._check_campaign_outputs()
        except Exception as e:
            logger.error(f"_check_campaign_outputs failed: {e}")

        logger.info("Completed scheduled immediate evaluator checks")

    # ── Checks ────────────────────────────────────────────────────────────────

    def _check_support_surge(self, theme_slug: Optional[str]) -> None:
        """
        فحص: >= 10 تذاكر مُصعَّدة في آخر 24 ساعة.
        المصدر: SUPPORT_TICKET_ESCALATED (لا RESOLVED).
        """
        threshold = IMMEDIATE_THRESHOLDS["support_surge"]["threshold"]  # 10
        since     = datetime.now(timezone.utc) - timedelta(hours=24)

        with get_conn() as conn:
            count = event_store.count_events(
                conn,
                event_type = "SUPPORT_TICKET_ESCALATED",
                theme_slug = theme_slug,
                since      = since,
            )

            if count >= threshold:
                if not signal_store.signal_sent_recently(
                    conn, "support_surge_alert", theme_slug, hours=24
                ):
                    _emit_signal(
                        signal_type  = SignalType.SUPPORT_SURGE_ALERT,
                        theme_slug   = theme_slug,
                        data         = {"ticket_count": count, "window_hours": 24},
                        target_agent = get_signal_target("support_surge_alert"),
                        priority     = SignalPriority.IMMEDIATE,
                        conn         = conn,
                    )

    def _check_no_sales_products(self) -> None:
        """
        فحص: قوالب لم تُباع منذ 30 يوماً.
        يعتمد على occurred_at للبيع — ليس received_at.
        """
        from ..services.product_registry import get_all_published_slugs, get_launch_date

        threshold_date = datetime.now(timezone.utc) - timedelta(
            days=IMMEDIATE_THRESHOLDS["no_sales_days"]["threshold"]
        )

        with get_conn() as conn:
            for theme_slug in get_all_published_slugs(conn):
                last_sale = event_store.get_last_event(
                    conn,
                    event_type = "NEW_SALE",
                    theme_slug = theme_slug,
                )

                launch_date    = get_launch_date(conn, theme_slug)
                reference_date = (
                    last_sale["occurred_at"] if last_sale else launch_date
                )

                if not reference_date:
                    continue

                if reference_date < threshold_date:
                    if not signal_store.signal_sent_recently(
                        conn, "no_output_alert", theme_slug, hours=24
                    ):
                        days_since = (datetime.now(timezone.utc) - reference_date).days
                        _emit_signal(
                            signal_type  = SignalType.NO_OUTPUT_ALERT,
                            theme_slug   = theme_slug,
                            data         = {"days_since_sale": days_since},
                            target_agent = get_signal_target("no_output_alert"),
                            priority     = SignalPriority.IMMEDIATE,
                            conn         = conn,
                        )

    def _check_sales_drop(self) -> None:
        """
        فحص: انخفاض > 50% مقارنة بالأسبوع الماضي.
        يعتمد على occurred_at.
        """
        now           = datetime.now(timezone.utc)
        this_week_start = now - timedelta(days=7)
        last_week_start = now - timedelta(days=14)

        with get_conn() as conn:
            this_week = event_store.count_events(
                conn,
                event_type = "NEW_SALE",
                since      = this_week_start,
            )
            last_week = event_store.count_events(
                conn,
                event_type = "NEW_SALE",
                since      = last_week_start,
                # before = this_week_start (not yet in count_events signature, use get_events)
            )
            # تصحيح: نحسب فترة الأسبوع الماضي فقط
            last_week_events = event_store.get_events(
                conn,
                event_type = "NEW_SALE",
                since      = last_week_start,
                before     = this_week_start,
            )
            last_week = len(last_week_events)

            if last_week > 0:
                drop_rate = (last_week - this_week) / last_week
                threshold = IMMEDIATE_THRESHOLDS["sales_drop_rate"]["threshold"]

                if drop_rate >= threshold:
                    if not signal_store.signal_sent_recently(
                        conn, "sales_drop_alert", None, hours=48
                    ):
                        _emit_signal(
                            signal_type  = SignalType.SALES_DROP_ALERT,
                            theme_slug   = None,
                            data         = {
                                "drop_rate":  round(drop_rate, 3),
                                "this_week":  this_week,
                                "last_week":  last_week,
                            },
                            target_agent = get_signal_target("sales_drop_alert"),
                            priority     = SignalPriority.IMMEDIATE,
                            conn         = conn,
                        )

    def _check_campaign_outputs(self) -> None:
        """
        فحص: حملات أُطلقت منذ > 24 ساعة بدون منشور.
        """
        threshold_hours = IMMEDIATE_THRESHOLDS["campaign_no_output_hours"]["threshold"]
        cutoff          = datetime.now(timezone.utc) - timedelta(hours=threshold_hours)

        with get_conn() as conn:
            launched = event_store.get_events(
                conn,
                event_type = "CAMPAIGN_LAUNCHED",
                before     = cutoff,
            )

            for campaign_event in launched:
                campaign_id = campaign_event.get("raw_data", {}).get("campaign_id")
                if not campaign_id:
                    continue

                posts = event_store.get_events(
                    conn,
                    event_type  = "POST_PUBLISHED",
                    since       = campaign_event["occurred_at"],
                    filter_data = {"campaign_id": campaign_id},
                )

                if len(posts) == 0:
                    if not signal_store.signal_sent_recently(
                        conn, "campaign_no_output", None, hours=24
                    ):
                        _emit_signal(
                            signal_type  = SignalType.CAMPAIGN_NO_OUTPUT,
                            theme_slug   = campaign_event.get("theme_slug"),
                            data         = {
                                "campaign_id":   campaign_id,
                                "hours_elapsed": threshold_hours,
                            },
                            target_agent = get_signal_target("campaign_no_output"),
                            priority     = SignalPriority.IMMEDIATE,
                            conn         = conn,
                        )


# ── Helper ────────────────────────────────────────────────────────────────────

def _emit_signal(
    signal_type:  SignalType,
    theme_slug:   Optional[str],
    data:         Dict[str, Any],
    target_agent: str,
    priority:     SignalPriority = SignalPriority.IMMEDIATE,
    conn          = None,
) -> None:
    """
    يُنشئ الإشارة، يُخزّنها، ويُرسلها على القناة الصحيحة.
    يقبل conn اختيارياً — يفتح واحداً جديداً إن لم يُعطَ.
    """
    from ..services.redis_bus import get_redis_bus

    signal_id = str(uuid.uuid4())
    now       = datetime.now(timezone.utc)

    signal_dict = {
        "signal_id":    signal_id,
        "signal_type":  signal_type.value,
        "priority":     priority.value,
        "target_agent": target_agent,
        "theme_slug":   theme_slug,
        "channel":      None,
        "recommendation": "",
        "confidence":   0.7,
        "supporting_pattern_id": None,
        "data":         data,
        "generated_at": now.isoformat(),
        "sent_at":      None,
    }

    def _save_and_publish(c):
        signal_store.save_signal(c, signal_dict)
        signal_store.mark_signal_sent(c, signal_id)

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        bus       = get_redis_bus(redis_url)
        bus.publish_stream(
            STREAM_ANALYTICS_SIGNALS,
            {
                "event_type": EVENT_ANALYTICS_SIGNAL,
                "source": "analytics_agent",
                **signal_dict,
            },
        )
        logger.info(f"Signal emitted: {signal_type.value} → {target_agent}")

    if conn is not None:
        _save_and_publish(conn)
    else:
        with get_conn() as c:
            _save_and_publish(c)
