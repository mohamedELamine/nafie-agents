"""
ContentState — بنية الـ State الموحدة لوكيل المحتوى
المرجع: spec.md § ٢٥
"""
from __future__ import annotations

from typing import List, Optional, TypedDict

from models import (
    ContentPiece,
    ContentPlan,
    ContentRequest,
    ContentTemplate,
    ContextBundle,
    FactSheet,
)


class ContentState(TypedDict, total=False):
    # ── الطلب والتخطيط ──────────────────────────────────
    idempotency_key:   str
    request:           ContentRequest
    content_plan:      Optional[ContentPlan]

    # ── السياق والحقائق ──────────────────────────────────
    context_bundle:    Optional[ContextBundle]
    fact_sheet:        Optional[FactSheet]
    selected_template: Optional[ContentTemplate]
    evidence_verified: bool

    # ── المخرجات ─────────────────────────────────────────
    content_piece:     Optional[ContentPiece]   # الرئيسي / للتحقق
    content_pieces:    List[ContentPiece]       # كل المتغيرات

    # ── حالة التحقق والمراجعة ────────────────────────────
    regeneration_count:    int
    validation_failed:     bool
    awaiting_human_review: bool
    retry_count:           int

    # ── حالة التسليم والتتبع ─────────────────────────────
    dispatch_status: Optional[str]
    status:          str
    error_code:      Optional[str]
    error_detail:    Optional[str]
    logs:            List[str]


def make_initial_state(request: ContentRequest) -> ContentState:
    """يبني الـ state الابتدائي من ContentRequest."""
    from models import build_content_idempotency_key
    return ContentState(
        idempotency_key       = build_content_idempotency_key(request),
        request               = request,
        content_plan          = None,
        context_bundle        = None,
        fact_sheet            = None,
        selected_template     = None,
        evidence_verified     = False,
        content_piece         = None,
        content_pieces        = [],
        regeneration_count    = 0,
        validation_failed     = False,
        awaiting_human_review = False,
        dispatch_status       = None,
        retry_count           = 0,
        status                = "started",
        error_code            = None,
        error_detail          = None,
        logs                  = [],
    )
