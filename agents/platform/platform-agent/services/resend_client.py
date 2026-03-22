"""
Resend Email Client — T034–T035

يُرسل 3 أنواع من الإيميلات:
  1. update_notification   — إشعار المشترين بتحديث القالب
  2. launch_confirmation   — إشعار صاحب المشروع بإطلاق ناجح
  3. inconsistency_alert   — تنبيه عاجل عند INCONSISTENT_STATE

Templates: agents/platform/platform-agent/templates/*.html

المرجع: agents/platform/docs/spec.md § ١٦
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional

import resend

logger = logging.getLogger("platform_agent.services.resend_client")

# ─── مسار قوالب الإيميلات ─────────────────────────────────
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class ResendClient:
    """
    Wrapper على Resend API.

    يستخدم HTML templates ويدعم batch sending للإشعارات الجماعية.
    """

    def __init__(self) -> None:
        resend.api_key = os.environ["RESEND_API_KEY"]
        self.from_email = os.environ["STORE_EMAIL_FROM"]
        self.store_url = os.getenv("STORE_URL", "https://nafic.com")
        self.owner_email = os.environ["OWNER_EMAIL"]

    # ─────────────────────────────────────────────────────────
    # إشعار تحديث القالب — للمشترين
    # ─────────────────────────────────────────────────────────

    def send_update_notification(
        self,
        to: str,
        theme_name_ar: str,
        theme_slug: str,
        new_version: str,
        changelog: Dict[str, Any],
    ) -> bool:
        """
        إرسال إشعار تحديث قالب واحد للمشتري.

        Args:
            to: بريد المشتري.
            theme_name_ar: اسم القالب بالعربية.
            theme_slug: slug القالب.
            new_version: الإصدار الجديد.
            changelog: {"summary_ar": str, "items_ar": list, "is_security": bool}.

        Returns:
            True عند النجاح، False عند الفشل.
        """
        html = self._render_template(
            "update_notification.html",
            {
                "theme_name_ar": theme_name_ar,
                "theme_slug": theme_slug,
                "new_version": new_version,
                "summary_ar": changelog.get("summary_ar", ""),
                "is_security": "✅ تحديث أمني" if changelog.get("is_security") else "",
                "store_url": self.store_url,
                "download_url": f"{self.store_url}/my-orders",
            },
        )

        subject = f"تحديث جديد لقالب {theme_name_ar} — v{new_version}"
        if changelog.get("is_security"):
            subject = f"[تحديث أمني] {subject}"

        return self._send(to=to, subject=subject, html=html)

    # ─────────────────────────────────────────────────────────
    # إشعار الإطلاق — لصاحب المشروع
    # ─────────────────────────────────────────────────────────

    def send_launch_confirmation(
        self,
        theme_name_ar: str,
        theme_slug: str,
        wp_post_url: str,
        version: str,
    ) -> bool:
        """
        إشعار صاحب المشروع بأن القالب أُطلق بنجاح.

        Returns:
            True عند النجاح، False عند الفشل.
        """
        html = self._render_template(
            "launch_confirmation.html",
            {
                "theme_name_ar": theme_name_ar,
                "theme_slug": theme_slug,
                "wp_post_url": wp_post_url,
                "version": version,
                "store_url": self.store_url,
            },
        )
        return self._send(
            to=self.owner_email,
            subject=f"🚀 تم إطلاق قالب {theme_name_ar} بنجاح!",
            html=html,
        )

    # ─────────────────────────────────────────────────────────
    # تنبيه INCONSISTENT_STATE — عاجل
    # ─────────────────────────────────────────────────────────

    def send_inconsistency_alert(
        self,
        theme_slug: str,
        wp_state: Dict[str, Any],
        ls_state: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        تنبيه عاجل عند تسجيل INCONSISTENT_STATE.

        يُرسل إلى OWNER_EMAIL فوراً — يستوجب تدخلاً بشرياً.

        Returns:
            True عند النجاح، False عند الفشل.
        """
        html = self._render_template(
            "inconsistency_alert.html",
            {
                "theme_slug": theme_slug,
                "wp_state": str(wp_state),
                "ls_state": str(ls_state),
                "context": str(context or {}),
                "error_code": "PLT_303",
            },
        )
        return self._send(
            to=self.owner_email,
            subject=f"⚠️ INCONSISTENT_STATE — قالب {theme_slug} يحتاج تدخلاً عاجلاً",
            html=html,
        )

    # ─────────────────────────────────────────────────────────
    # Batch update notifications
    # ─────────────────────────────────────────────────────────

    def send_batch_update_notifications(
        self,
        recipients: List[Dict[str, Any]],
        theme_name_ar: str,
        theme_slug: str,
        new_version: str,
        changelog: Dict[str, Any],
    ) -> Dict[str, int]:
        """
        إرسال إشعارات تحديث جماعية.

        Args:
            recipients: list of {"email": str, "tier": str}.

        Returns:
            {"sent": int, "failed": int}
        """
        sent = 0
        failed = 0

        for recipient in recipients:
            email = recipient.get("email", "")
            if not email:
                continue
            success = self.send_update_notification(
                to=email,
                theme_name_ar=theme_name_ar,
                theme_slug=theme_slug,
                new_version=new_version,
                changelog=changelog,
            )
            if success:
                sent += 1
            else:
                failed += 1

        logger.info(
            "resend.batch | theme=%s v%s | sent=%s failed=%s",
            theme_slug,
            new_version,
            sent,
            failed,
        )
        return {"sent": sent, "failed": failed}

    # ─────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────

    def _render_template(self, filename: str, variables: Dict[str, str]) -> str:
        """يقرأ template ويستبدل المتغيرات."""
        template_path = _TEMPLATES_DIR / filename
        if not template_path.exists():
            logger.warning("resend | template not found: %s", filename)
            # fallback بسيط
            return "<br>".join(f"{k}: {v}" for k, v in variables.items())

        raw = template_path.read_text(encoding="utf-8")
        try:
            return Template(raw).safe_substitute(variables)
        except Exception as exc:
            logger.warning("resend | template render error %s | %s", filename, exc)
            return raw

    def _send(self, to: str, subject: str, html: str) -> bool:
        """إرسال إيميل واحد — يعيد True عند النجاح."""
        try:
            result = resend.Emails.send(
                {
                    "from": self.from_email,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                }
            )
            email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
            logger.info("resend.send | to=%s subject=%r id=%s", to, subject[:60], email_id)
            return True
        except Exception as exc:
            logger.error("resend.send failed | to=%s subject=%r | %s", to, subject[:60], exc)
            return False
