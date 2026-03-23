"""
Event Collector — طبقة ١
سريع جداً: تخزين + idempotency + attribution فوري عند NEW_SALE.
"""
import os
from datetime import datetime
from typing import Any, Dict

from ..db import event_store
from ..db.connection import get_conn
from ..logging_config import get_logger
from ..models import AnalyticsEvent
from .attribution import attribute_sale

logger = get_logger("workflows.event_collector")

# قنوات Redis المُستمَع عليها
INBOUND_STREAMS = [
    "product-events",
    "support-events",
    "marketing-events",
    "content-events",
    "builder-events",
]

CONSUMER_GROUP = "analytics-agent"
CONSUMER_NAME  = "event_collector"


def event_collector_node(event: Dict[str, Any]) -> None:
    """
    يُعالج حدثاً واحداً:
    1. يتحقق من التكرار (idempotency)
    2. يُخزّن في DB
    3. يُطلق attribution إن كان NEW_SALE
    """
    event_id = event.get("event_id")
    if not event_id:
        logger.warning("Received event without event_id — skipping")
        return

    with get_conn() as conn:
        # idempotency check
        if event_store.event_exists(conn, event_id):
            logger.debug(f"Duplicate event ignored: {event_id}")
            return

        # استخراج occurred_at (الوقت الحقيقي)
        occurred_at = event.get("occurred_at")
        if isinstance(occurred_at, str):
            try:
                occurred_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(
                    f"ANL_002: occurred_at مفقود أو خاطئ في {event_id} — "
                    "استخدام received_at كـ fallback للتخزين فقط"
                )
                occurred_at = datetime.utcnow()
        elif not isinstance(occurred_at, datetime):
            occurred_at = datetime.utcnow()

        received_at = datetime.utcnow()

        analytics_event = AnalyticsEvent(
            event_id     = event_id,
            event_type   = event.get("event_type", "UNKNOWN"),
            source_agent = event.get("source", event.get("source_agent", "unknown")),
            theme_slug   = event.get("data", {}).get("theme_slug") or event.get("theme_slug"),
            raw_data     = event.get("data", event.get("raw_data", {})),
            occurred_at  = occurred_at,
            received_at  = received_at,
        )

        event_store.save_event(conn, {
            "event_id":     analytics_event.event_id,
            "event_type":   analytics_event.event_type,
            "source_agent": analytics_event.source_agent,
            "theme_slug":   analytics_event.theme_slug,
            "raw_data":     analytics_event.raw_data,
            "occurred_at":  analytics_event.occurred_at,
            "received_at":  analytics_event.received_at,
            "processed":    False,
        })

        logger.debug(f"Stored event: {event_id} ({analytics_event.event_type})")

    # Attribution فوري عند NEW_SALE — بعد إغلاق الـ conn الأول
    if analytics_event.event_type == "NEW_SALE":
        _handle_new_sale(analytics_event)


def _handle_new_sale(event: AnalyticsEvent) -> None:
    """Attribution فوري لحدث بيع جديد."""
    raw = event.raw_data
    sale_id      = raw.get("order_id") or raw.get("sale_id")
    theme_slug   = event.theme_slug or raw.get("theme_slug", "unknown")
    amount_usd   = float(raw.get("amount_usd", 0))
    license_tier = raw.get("license_tier", "unknown")

    if not sale_id:
        logger.warning(f"NEW_SALE event {event.event_id} has no order_id — attribution skipped")
        return

    # attribute_sale يفتح connection خاصاً بها ويُغلقه
    attribute_sale(
        sale_id      = str(sale_id),
        sale_date    = event.occurred_at,   # occurred_at — ليس received_at
        theme_slug   = theme_slug,
        amount_usd   = amount_usd,
        license_tier = license_tier,
    )


def start_event_collector() -> None:
    """
    يبدأ الاستماع على كل Redis streams.
    يُشغَّل في thread منفصل من lifespan.
    """
    import time
    from ..services.redis_bus import get_redis_bus

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_bus = get_redis_bus(redis_url)

    # إنشاء consumer groups لكل stream
    for stream in INBOUND_STREAMS:
        redis_bus.ensure_consumer_group(stream, CONSUMER_GROUP)

    logger.info(f"Event collector started — listening on {len(INBOUND_STREAMS)} streams")

    while True:
        try:
            for stream in INBOUND_STREAMS:
                messages = redis_bus.read_group(
                    stream         = stream,
                    consumer_group = CONSUMER_GROUP,
                    consumer_name  = CONSUMER_NAME,
                    count          = 10,
                    block_ms       = 100,   # non-blocking per stream
                )
                for msg in messages:
                    message_id = msg.pop("__message_id", None)
                    try:
                        event_collector_node(msg)
                    except Exception as e:
                        logger.error(f"Error processing event from {stream}: {e}")
                    finally:
                        if message_id:
                            redis_bus.ack(stream, message_id)

        except KeyboardInterrupt:
            logger.info("Event collector stopped")
            break
        except Exception as e:
            logger.error(f"Event collector error: {e}")
            time.sleep(5)
