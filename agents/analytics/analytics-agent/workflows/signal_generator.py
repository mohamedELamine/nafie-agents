import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.contracts import EVENT_ANALYTICS_SIGNAL, STREAM_ANALYTICS_SIGNALS
from ..db import pattern_store
from ..db import signal_store
from ..db import report_store
from ..db.connection import get_conn
from ..logging_config import get_logger
from ..models import SignalType, SignalPriority, AttributionConfidence
from ..services.redis_bus import get_redis_bus
from ..services.resend_client import send_owner_critical_alert as _resend_alert

logger = get_logger("workflows.signal_generator")


def generate_signals_from_patterns(patterns: List[Any]) -> List[Any]:
    """Generate signals from detected patterns."""
    try:
        signals = []

        for pattern in patterns:
            if pattern.pattern_type == "SALES_DROP_7D":
                signal = create_signal(
                    signal_type=SignalType.SALES_DROP_ALERT,
                    priority=SignalPriority.IMMEDIATE,
                    target_agent="marketing_agent",
                    theme_slug="all",
                    confidence=0.9,
                    data={
                        "current_sales": pattern.supporting_metrics.get("current_sales", 0),
                        "previous_sales": pattern.supporting_metrics.get("previous_sales", 0),
                        "drop_percentage": pattern.supporting_metrics.get("drop_percentage", 0),
                        "period": "7 days",
                    },
                )
                signals.append(signal)

            elif pattern.pattern_type == "BEST_CHANNEL_30D":
                signal = create_signal(
                    signal_type=SignalType.BEST_CHANNEL,
                    priority=SignalPriority.WEEKLY,
                    target_agent="marketing_agent",
                    theme_slug="all",
                    confidence=0.6,
                    data={
                        "best_channel": pattern.supporting_metrics.get("best_channel"),
                        "sales_count": pattern.supporting_metrics.get("sales_count"),
                        "total_sales": pattern.supporting_metrics.get("total_sales"),
                    },
                )
                signals.append(signal)

        # Send signals to agents
        for signal in signals:
            send_to_target_agent(signal)

        logger.info(f"Generated {len(signals)} signals from patterns")
        return signals

    except Exception as e:
        logger.error(f"Error in generate_signals_from_patterns: {e}")
        return []


def emit_immediate_signal(
    signal_type: SignalType,
    theme_slug: str,
    data: Dict[str, Any],
    target_agent: str = "marketing_agent",
) -> None:
    """Emit an immediate signal for a specific situation."""
    try:
        signal = create_signal(
            signal_type=signal_type,
            priority=SignalPriority.IMMEDIATE,
            target_agent=target_agent,
            theme_slug=theme_slug,
            confidence=0.6,
            data=data,
        )

        send_to_target_agent(signal)

        logger.info(f"Emitted immediate signal: {signal_type.value}")

    except Exception as e:
        logger.error(f"Error emitting immediate signal: {e}")


def send_to_target_agent(signal: Any) -> None:
    """Send a signal to the target agent via Redis."""
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        redis_bus = get_redis_bus(redis_url=redis_url)
        signal_dict = {
            "signal_id": signal.signal_id,
            "signal_type": signal.signal_type.value,
            "priority": signal.priority.value,
            "target_agent": signal.target_agent,
            "theme_slug": signal.theme_slug,
            "data": signal.data,
            "generated_at": signal.generated_at.isoformat(),
        }

        with get_conn() as conn:
            if signal_store.signal_sent_recently(
                conn,
                signal.signal_type.value,
                signal.theme_slug,
            ):
                logger.debug(f"Signal already sent recently, skipping: {signal.signal_id}")
                return

            signal_store.save_signal(
                conn,
                {
                    **signal_dict,
                    "confidence": signal.confidence,
                    "channel": signal.channel,
                    "recommendation": signal.recommendation,
                    "supporting_pattern_id": signal.supporting_pattern_id,
                    "sent_at": None,
                },
            )
            signal_store.mark_signal_sent(conn, signal.signal_id)

        redis_bus.publish_stream(
            STREAM_ANALYTICS_SIGNALS,
            {
                "event_type": EVENT_ANALYTICS_SIGNAL,
                "source": "analytics_agent",
                **signal_dict,
            },
        )

        logger.debug(f"Sent signal to {signal.target_agent}: {signal.signal_id}")

    except Exception as e:
        logger.error(f"Error sending signal to target agent: {e}")


def send_owner_critical_alert_for_signal(
    signal_type: SignalType,
    data: Dict[str, Any],
) -> None:
    """Send critical alert to owner via Resend."""
    try:
        subject = f"CRITICAL: {signal_type.value}"
        body = f"""
        <h1>{signal_type.value}</h1>
        <p><strong>Confidence:</strong> HIGH</p>
        <p><strong>Theme:</strong> all</p>
        <h2>Details:</h2>
        <pre>{data}</pre>
        """

        success = _resend_alert(
            api_key=os.getenv("RESEND_API_KEY", ""),
            owner_email=os.getenv("OWNER_EMAIL", "owner@example.com"),
            subject=subject,
            body=body,
        )

        if success:
            logger.info(f"Sent owner critical alert for {signal_type.value}")
        else:
            logger.error(f"Failed to send owner critical alert for {signal_type.value}")

    except Exception as e:
        logger.error(f"Error sending owner critical alert: {e}")


def create_signal(
    signal_type: SignalType,
    priority: SignalPriority,
    target_agent: str,
    theme_slug: str,
    confidence: float,
    data: Dict[str, Any],
    channel: Optional[str] = None,
    recommendation: str = "",
    supporting_pattern_id: Optional[str] = None,
) -> Any:
    """Create a new analytics signal."""
    from ..models import AnalyticsSignal

    signal = AnalyticsSignal(
        signal_id=f"{signal_type.value}_{int(datetime.utcnow().timestamp())}",
        signal_type=signal_type,
        priority=priority,
        target_agent=target_agent,
        theme_slug=theme_slug,
        channel=channel,
        recommendation=recommendation,
        confidence=confidence,
        supporting_pattern_id=supporting_pattern_id,
        data=data,
        generated_at=datetime.utcnow(),
    )

    return signal
