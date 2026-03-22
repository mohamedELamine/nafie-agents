"""
Background Tasks — T085
Timeout Watchdog: يفحص كل 5 دقائق workflows المعلّقة.
"""
from __future__ import annotations
import logging
import os
import threading
import time
from typing import Any
import psycopg2
from services.resend_client import ResendClient

logger = logging.getLogger("platform_agent.api.background")
CHECK_INTERVAL_SECONDS = 300  # 5 دقائق
ASSET_WARN_HOURS  = int(os.getenv("ASSET_INITIAL_WAIT_HOURS", "4"))
ASSET_CANCEL_HOURS = int(os.getenv("ASSET_INITIAL_WAIT_HOURS", "4")) + int(os.getenv("ASSET_EXTENSION_HOURS","4"))
REVIEW_TIMEOUT_HOURS = int(os.getenv("HUMAN_REVIEW_TIMEOUT_HOURS", "48"))


class TimeoutWatchdog:
    def __init__(self, db_conn, resend: ResendClient):
        self.db_conn = db_conn
        self.resend = resend
        self._stop = threading.Event()

    def start(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()
        return t

    def stop(self):
        self._stop.set()

    def _run(self):
        logger.info("TimeoutWatchdog started — interval=%ss", CHECK_INTERVAL_SECONDS)
        while not self._stop.is_set():
            try:
                self._check_asset_timeouts()
                self._check_review_timeouts()
            except Exception as exc:
                logger.error("TimeoutWatchdog | check failed | %s", exc)
            time.sleep(CHECK_INTERVAL_SECONDS)

    def _check_asset_timeouts(self):
        """يفحص workflows في WAITING_ASSETS."""
        with self.db_conn.cursor() as cur:
            # workflows منذ > ASSET_WARN_HOURS ولم يُشعَر بعد
            cur.execute("""
                SELECT idempotency_key, theme_slug, started_at
                FROM execution_log
                WHERE node_name = 'ASSET_WAITER'
                  AND status = 'started'
                  AND started_at < NOW() - INTERVAL '%s hours'
            """, (ASSET_WARN_HOURS,))
            rows = cur.fetchall()

        for ikey, theme_slug, started_at in rows:
            hours_waiting = (
                __import__("datetime").datetime.utcnow().replace(tzinfo=__import__("datetime").timezone.utc)
                - started_at.replace(tzinfo=__import__("datetime").timezone.utc)
            ).total_seconds() / 3600

            if hours_waiting > ASSET_CANCEL_HOURS:
                logger.warning("TimeoutWatchdog | AUTO_CANCEL | key=%s waited=%.1fh", ikey, hours_waiting)
                self._mark_cancelled(ikey)
            elif hours_waiting > ASSET_WARN_HOURS:
                logger.info("TimeoutWatchdog | ASSET_WARNING | key=%s waited=%.1fh", ikey, hours_waiting)
                owner = os.getenv("OWNER_EMAIL", "")
                if owner:
                    self.resend._send(
                        to=owner,
                        subject=f"⏳ انتظار Assets — قالب {theme_slug}",
                        html=f"<p>الـ workflow للقالب <strong>{theme_slug}</strong> ينتظر الأصول منذ {hours_waiting:.0f} ساعة. الرجاء اتخاذ قرار.</p>",
                    )

    def _check_review_timeouts(self):
        """يفحص reviews في WAITING_HUMAN_REVIEW منذ > 48 ساعة."""
        with self.db_conn.cursor() as cur:
            cur.execute("""
                SELECT idempotency_key
                FROM execution_log
                WHERE node_name = 'HUMAN_REVIEW_GATE'
                  AND status = 'started'
                  AND started_at < NOW() - INTERVAL '%s hours'
            """, (REVIEW_TIMEOUT_HOURS,))
            rows = cur.fetchall()

        for (ikey,) in rows:
            logger.warning("TimeoutWatchdog | REVIEW_TIMEOUT PLT_501 | key=%s", ikey)
            self._mark_cancelled(ikey)

    def _mark_cancelled(self, ikey: str):
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    UPDATE execution_log SET status='failed', error_code='PLT_501', completed_at=NOW()
                    WHERE idempotency_key=%s
                """, (ikey,))
            self.db_conn.commit()
        except Exception as exc:
            logger.error("TimeoutWatchdog | mark_cancelled failed | %s", exc)
            self.db_conn.rollback()
