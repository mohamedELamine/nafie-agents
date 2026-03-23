"""
Attribution Model: last_touch_v1
Attribution في v1 = Marketing Influence Approximation — تقريب لا حقيقة.
الثقة مُعلَنة دائماً في كل سجل.
"""
import os
from datetime import datetime, timedelta
from typing import List, Optional

from ..db import event_store
from ..db import attribution_store
from ..db.connection import get_conn
from ..logging_config import get_logger
from ..metric_definitions import ATTRIBUTION_MODEL, ATTRIBUTION_WINDOW_DAYS
from ..models import AttributionChannel, AttributionConfidence, AttributionRecord

logger = get_logger("workflows.attribution")


def attribute_sale(
    sale_id:      str,
    sale_date:    datetime,     # من occurred_at — ليس received_at
    theme_slug:   str,
    amount_usd:   float,
    license_tier: str,
) -> Optional[AttributionRecord]:
    """
    يربط البيع بمصدره التقريبي (last_touch_v1).
    يُحسَّب من أحداث النشر في نافذة ATTRIBUTION_WINDOW_DAYS أيام.
    """
    try:
        window_days  = int(os.getenv("ATTRIBUTION_WINDOW_DAYS", ATTRIBUTION_WINDOW_DAYS))
        window_start = sale_date - timedelta(days=window_days)

        with get_conn() as conn:
            # أحداث النشر قبل البيع في النافذة الزمنية
            recent_posts = event_store.get_events(
                conn,
                event_type = "POST_PUBLISHED",
                theme_slug = theme_slug,
                since      = window_start,
                before     = sale_date,
            )
            recent_campaigns = event_store.get_events(
                conn,
                event_type = "CAMPAIGN_LAUNCHED",
                theme_slug = theme_slug,
                since      = window_start,
                before     = sale_date,
            )
            recent_emails = event_store.get_events(
                conn,
                event_type = "CONTENT_PRODUCED",
                theme_slug = theme_slug,
                since      = window_start,
                before     = sale_date,
            )

            # جمع القنوات المُلامَسة بالترتيب الزمني
            channels_touched: List[AttributionChannel] = []
            for post in sorted(recent_posts, key=lambda x: x["occurred_at"]):
                ch_str = post.get("raw_data", {}).get("channel", "unknown")
                try:
                    ch = AttributionChannel(ch_str.lower())
                except ValueError:
                    ch = AttributionChannel.UNKNOWN
                if ch not in channels_touched:
                    channels_touched.append(ch)

            if recent_campaigns:
                for camp in recent_campaigns:
                    ch_str = camp.get("raw_data", {}).get("channel", "unknown")
                    try:
                        ch = AttributionChannel(ch_str.lower())
                    except ValueError:
                        ch = AttributionChannel.UNKNOWN
                    if ch not in channels_touched:
                        channels_touched.append(ch)

            if recent_emails:
                if AttributionChannel.EMAIL not in channels_touched:
                    channels_touched.append(AttributionChannel.EMAIL)

            # تحديد آخر قناة (last touch)
            attributed_to = (
                channels_touched[-1] if channels_touched
                else AttributionChannel.DIRECT
            )

            # حساب الثقة
            time_since_last_post: Optional[float] = None
            if recent_posts:
                last_post_time     = max(p["occurred_at"] for p in recent_posts)
                time_since_last_post = (sale_date - last_post_time).total_seconds() / 3600

            if time_since_last_post is not None and time_since_last_post <= 24:
                confidence = AttributionConfidence.MEDIUM
            elif channels_touched:
                confidence = AttributionConfidence.LOW
            else:
                confidence = AttributionConfidence.LOW  # الأكثر شيوعاً في v1

            attribution_note = (
                f"استنتاج من {len(recent_posts)} منشور في نافذة {window_days} أيام. "
                f"ثقة: {confidence.value}. "
                "هذا تقريب لا Attribution دقيق."
            )

            record = AttributionRecord(
                sale_id                = sale_id,
                theme_slug             = theme_slug,
                amount_usd             = amount_usd,
                license_tier           = license_tier,
                channels_touched       = channels_touched,
                attributed_to          = attributed_to,
                attribution_model      = ATTRIBUTION_MODEL,
                attribution_confidence = confidence,
                attribution_note       = attribution_note,
                sale_date              = sale_date,
            )

            attribution_store.save_record(conn, record)
            logger.info(
                f"Attributed sale {sale_id} → {attributed_to.value} "
                f"[{confidence.value}]"
            )
            return record

    except Exception as e:
        logger.error(f"Error in attribute_sale for {sale_id}: {e}")
        return None
