"""
Resend Client — إشعارات وكيل المحتوى
يُرسل إشعارات المراجعة البشرية وتأكيدات الإنتاج.
المرجع: spec.md § ١٥
"""
from __future__ import annotations

import logging
import os
from string import Template
from typing import Optional

import resend as resend_lib

logger = logging.getLogger("content_agent.services.resend_client")


class ContentResendClient:

    def __init__(
        self,
        api_key:    Optional[str] = None,
        from_email: Optional[str] = None,
        owner_email: Optional[str] = None,
    ):
        self._enabled       = bool(api_key or os.environ.get("RESEND_API_KEY"))
        resend_lib.api_key  = api_key or os.environ.get("RESEND_API_KEY", "")
        self._from          = from_email  or os.environ.get("STORE_EMAIL_FROM", "hello@ar-themes.com")
        self._owner         = owner_email or os.environ.get("OWNER_EMAIL", "owner@ar-themes.com")
        if not self._enabled:
            logger.warning("RESEND_API_KEY missing; content email notifications are disabled")

    def send_review_request(
        self,
        content_type:     str,
        theme_slug:       str,
        validation_score: float,
        body_preview:     str,
        review_key:       str,
        requester:        str,
    ) -> bool:
        """يُرسل إشعار المراجعة البشرية لصاحب المشروع."""
        subject = f"محتوى يستوجب مراجعتك — {content_type} — {theme_slug}"
        html    = _render_review_template({
            "content_type":     content_type,
            "theme_slug":       theme_slug,
            "validation_score": f"{validation_score:.0%}",
            "body_preview":     body_preview[:300],
            "review_key":       review_key,
            "requester":        requester,
        })
        return self._send(self._owner, subject, html)

    def send_content_ready_confirmation(
        self,
        content_type: str,
        theme_slug:   str,
        content_id:   str,
        target_agent: str,
    ) -> bool:
        """تأكيد إنتاج المحتوى وإرساله."""
        subject = f"محتوى جاهز — {content_type}"
        html    = f"""
        <div dir="rtl" style="font-family: Arial; padding: 20px;">
            <h2>محتوى جديد جاهز ✓</h2>
            <p>النوع: <strong>{content_type}</strong></p>
            <p>القالب: <strong>{theme_slug or 'عام'}</strong></p>
            <p>المعرّف: <code>{content_id}</code></p>
            <p>أُرسل إلى: <strong>{target_agent}</strong></p>
        </div>
        """
        return self._send(self._owner, subject, html)

    def _send(self, to: str, subject: str, html: str) -> bool:
        if not self._enabled:
            logger.info("resend.skipped to=%s subject=%s reason=disabled", to, subject)
            return True
        try:
            resend_lib.Emails.send({
                "from":    self._from,
                "to":      [to],
                "subject": subject,
                "html":    html,
            })
            logger.info("resend.sent to=%s subject=%s", to, subject)
            return True
        except Exception as exc:
            logger.error("resend.failed to=%s err=%s", to, exc)
            return False


def _render_review_template(ctx: dict) -> str:
    tmpl = Template("""
    <div dir="rtl" style="font-family: Arial; padding: 20px;">
        <h2>محتوى يستوجب مراجعتك</h2>
        <table style="border-collapse: collapse; width: 100%;">
            <tr><td><strong>النوع</strong></td><td>${content_type}</td></tr>
            <tr><td><strong>القالب</strong></td><td>${theme_slug}</td></tr>
            <tr><td><strong>درجة التحقق</strong></td><td>${validation_score}</td></tr>
            <tr><td><strong>طُلب من</strong></td><td>${requester}</td></tr>
        </table>
        <h3>معاينة المحتوى</h3>
        <blockquote style="background:#f5f5f5; padding:10px; border-right:4px solid #333;">
            ${body_preview}
        </blockquote>
        <p>مفتاح المراجعة: <code>${review_key}</code></p>
        <p>استخدم الـ API للموافقة أو الرفض:
            <br>POST /review/${review_key}
        </p>
    </div>
    """)
    return tmpl.safe_substitute(ctx)
