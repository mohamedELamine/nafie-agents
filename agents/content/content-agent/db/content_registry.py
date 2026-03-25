"""
Content Registry — ذاكرة المحتوى
يمنع إعادة اختراع "لغة المنتج" في كل مرة.
المرجع: spec.md § ١٨
"""
from __future__ import annotations

import json
import re
from typing import Dict, Optional

import psycopg2.extras

from db.connection import get_conn
from logging_config import get_logger
from models import ContentPiece, ContentType

logger = get_logger("db.content_registry")


class ContentRegistryError(Exception):
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        super().__init__(message)


class ContentRegistry:
    """
    يُخزّن: الجمل الكنونية، الأوصاف المعتمدة، وصيغ الميزات.
    All DB access goes through get_conn() context manager (Law II).
    """

    # ── Canonical Phrases ─────────────────────────────────────────

    def get_phrases(self, theme_slug: str) -> Optional[Dict]:
        """جلب الجمل الكنونية لقالب محدد."""
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT canonical_phrases FROM content_registry WHERE theme_slug = %s",
                    [theme_slug],
                )
                row = cur.fetchone()
                if row and row["canonical_phrases"]:
                    phrases = row["canonical_phrases"]
                    return phrases if isinstance(phrases, dict) else json.loads(phrases)
                return None

    def update_phrases(
        self,
        theme_slug:   str,
        content_type: ContentType,
        piece:        ContentPiece,
        score:        float,
    ) -> None:
        """
        يُحدَّث بعد كل مخرج ناجح بدرجة ≥ 0.80.
        فقط المحتوى الجيد يدخل الـ Registry.
        Law III: ON CONFLICT DO NOTHING.
        """
        if score < 0.80:
            logger.debug(
                "content_registry.skip_update slug=%s score=%.2f",
                theme_slug, score,
            )
            return

        phrases = _extract_canonical_phrases(str(piece.body), content_type)

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO content_registry (theme_slug, content_type, canonical_phrases, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (theme_slug, content_type) DO NOTHING
                """, [
                    theme_slug,
                    content_type.value,
                    json.dumps(phrases, ensure_ascii=False),
                ])
            conn.commit()
        logger.info(
            "content_registry.updated slug=%s type=%s score=%.2f",
            theme_slug, content_type.value, score,
        )

    # ── Content Pieces ────────────────────────────────────────────

    def get_last_version(
        self,
        theme_slug:   str,
        content_type: ContentType,
    ) -> Optional[str]:
        """آخر إصدار منشور من محتوى نوع معين لقالب محدد."""
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT body FROM content_pieces
                    WHERE theme_slug = %s AND content_type = %s AND status = 'ready'
                    ORDER BY created_at DESC LIMIT 1
                """, [theme_slug, content_type.value])
                row = cur.fetchone()
                return row["body"] if row else None

    def save_content_piece(self, piece: ContentPiece) -> None:
        """يحفظ ContentPiece في قاعدة البيانات."""
        body = (
            json.dumps(piece.body, ensure_ascii=False)
            if isinstance(piece.body, dict)
            else piece.body
        )
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO content_pieces (
                        content_id, request_id, content_type, variant_label,
                        theme_slug, title, body, metadata, versioning,
                        structural_score, language_score, factual_score, validation_score,
                        validation_issues, status, target_agent, created_at
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    ON CONFLICT (content_id) DO NOTHING
                """, [
                    piece.content_id, piece.request_id, piece.content_type.value, piece.variant_label,
                    piece.theme_slug, piece.title, body,
                    json.dumps(piece.metadata,   ensure_ascii=False),
                    json.dumps(piece.versioning, ensure_ascii=False),
                    piece.structural_score, piece.language_score, piece.factual_score, piece.validation_score,
                    json.dumps(piece.validation_issues, ensure_ascii=False),
                    piece.status.value, piece.target_agent, piece.created_at,
                ])
            conn.commit()

    def get_content_piece(self, content_id: str) -> Optional[dict]:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM content_pieces WHERE content_id = %s",
                    [content_id],
                )
                row = cur.fetchone()
                return dict(row) if row else None

    # ── Human Review Queue ────────────────────────────────────────

    def queue_for_human_review(
        self,
        piece:        ContentPiece,
        review_key:   str,
        requester:    str,
        correlation_id: str,
    ) -> None:
        """يضع المحتوى في طابور المراجعة البشرية."""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO content_review_queue (
                        review_key, content_id, content_type, theme_slug,
                        body_preview, validation_score, requester, correlation_id,
                        created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (review_key) DO NOTHING
                """, [
                    review_key,
                    piece.content_id,
                    piece.content_type.value,
                    piece.theme_slug,
                    str(piece.body)[:500],
                    piece.validation_score,
                    requester,
                    correlation_id,
                ])
            conn.commit()

    def get_review_item(self, review_key: str) -> Optional[dict]:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM content_review_queue WHERE review_key = %s AND decision IS NULL",
                    [review_key],
                )
                row = cur.fetchone()
                return dict(row) if row else None

    def record_review_decision(
        self,
        review_key: str,
        decision:   str,
        notes:      Optional[str] = None,
    ) -> None:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE content_review_queue
                    SET decision = %s, notes = %s, decided_at = NOW()
                    WHERE review_key = %s
                """, [decision, notes, review_key])
            conn.commit()


# ── Private Helpers ────────────────────────────────────────────────

def _extract_canonical_phrases(
    body:         str,
    content_type: ContentType,
) -> Dict[str, str]:
    """
    يستخرج الجمل الكنونية من المحتوى الناجح.
    يُخزَّن للاستخدام المستقبلي في CONTEXT_ENRICHER.
    """
    phrases: Dict[str, str] = {}

    # استخراج السطر الأول كـ headline
    lines = [ln.strip() for ln in body.split("\n") if ln.strip()]
    if lines:
        phrases["headline"] = lines[0]

    # استخراج الجمل القصيرة (≤ 10 كلمات) كـ taglines
    taglines = []
    for line in lines[1:6]:
        if len(line.split()) <= 10 and len(line) > 10:
            taglines.append(line)
    if taglines:
        phrases["taglines"] = " | ".join(taglines[:3])

    # استخراج الميزات (سطور تبدأ بـ - أو •)
    features = []
    for line in lines:
        if re.match(r'^[-•✓]\s+', line):
            features.append(re.sub(r'^[-•✓]\s+', '', line))
    if features:
        phrases["features"] = " | ".join(features[:5])

    return phrases
