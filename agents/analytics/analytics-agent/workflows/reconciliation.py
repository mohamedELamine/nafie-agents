from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..db import event_store
from ..db import metric_store
from ..db import signal_store
from ..logging_config import get_logger
from ..models import AttributionConfidence

logger = get_logger("workflows.reconciliation")


def reconcile_sales_data() -> None:
    """Reconcile sales data between Lemon Squeezy and Redis events."""
    try:
        logger.info("Starting sales data reconciliation...")

        # Get orders from Lemon Squeezy for the last 7 days
        ls_orders = __import__("services.lemon_squeezy_client").get_orders(
            api_key=__import__("os").getenv("LS_API_KEY", ""),
            since=datetime.utcnow() - timedelta(days=7),
        )

        # Get existing sale events from Redis
        redis_sales = event_store.get_events(
            event_type="NEW_SALE",
            since=datetime.utcnow() - timedelta(days=7),
            limit=1000,
        )

        # Create a set of Redis sale IDs
        redis_sale_ids = {
            e["raw_data"].get("sale_id")
            for e in redis_sales
            if e.get("raw_data", {}).get("sale_id")
        }

        # Count LS orders
        ls_orders_count = len(ls_orders)
        ls_sale_ids = {order.get("id") for order in ls_orders if order.get("id")}

        # Find discrepancies
        missing_in_redis = ls_sale_ids - redis_sale_ids
        extra_in_redis = redis_sale_ids - ls_sale_ids

        # Log discrepancies
        if missing_in_redis:
            logger.warning(
                f"Missing in Redis ({len(missing_in_redis)} orders): {list(missing_in_redis)[:5]}"
            )

        if extra_in_redis:
            logger.warning(
                f"Extra in Redis ({len(extra_in_redis)} orders): {list(extra_in_redis)[:5]}"
            )

        # Backfill missing sales
        backfill_count = 0
        for order_id in missing_in_redis:
            try:
                # Get order details
                order = __import__("services.lemon_squeezy_client").get_order(
                    api_key=__import__("os").getenv("LS_API_KEY", ""),
                    order_id=order_id,
                )

                if order:
                    sale_data = order.get("attributes", {})

                    # Backfill sale
                    event_store.backfill_sale(
                        conn=__import__("psycopg2").connect(
                            "postgresql://analytics:password@localhost:5432/analytics_db"
                        ),
                        sale_id=order_id,
                        sale_date=datetime.fromisoformat(
                            sale_data.get("occurred_at", datetime.utcnow().isoformat())
                        ),
                        theme_slug=sale_data.get("first_order_item", {})
                        .get("product", {})
                        .get("slug", "unknown"),
                        amount_usd=float(
                            sale_data.get("attributes", {}).get("price", 0)
                        ),
                        license_tier=sale_data.get("attributes", {})
                        .get("checkout_data", {})
                        .get("meta", {})
                        .get("customData", {})
                        .get("license_tier", "free"),
                    )
                    backfill_count += 1
                    logger.info(f"Backfilled sale: {order_id}")

            except Exception as e:
                logger.error(f"Error backfilling order {order_id}: {e}")

        if backfill_count > 0:
            logger.info(f"Backfilled {backfill_count} missing sales")

        # Check for RECONCILIATION_MISMATCH signal
        missing_threshold = 5
        extra_threshold = 5

        if (
            len(missing_in_redis) > missing_threshold
            or len(extra_in_redis) > extra_threshold
        ):
            logger.error(
                f"RECONCILIATION_MISMATCH: missing={len(missing_in_redis)}, extra={len(extra_in_redis)}"
            )

            # Emit critical signal
            from ..workflows.signal_generator import emit_immediate_signal
            from ..models import SignalType

            emit_immediate_signal(
                signal_type=SignalType.RECONCILIATION_MISMATCH,
                theme_slug="all",
                data={
                    "missing_in_redis": len(missing_in_redis),
                    "extra_in_redis": len(extra_in_redis),
                    "threshold": missing_threshold,
                },
            )

        logger.info("Completed sales data reconciliation")

    except Exception as e:
        logger.error(f"Error in reconcile_sales_data: {e}")
