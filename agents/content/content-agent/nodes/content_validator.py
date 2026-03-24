"""
Node: CONTENT_VALIDATOR
ثلاث طبقات تحقق: بنيوية + لغوية + واقعية.
المرجع: spec.md § ١٤، Patch v2.1 § ١
"""
from __future__ import annotations
import logging
import os
import re
from typing import List, Tuple
from state import ContentState
from models import (
    BRAND_CONSTITUTION_FORBIDDEN_PATTERNS,
    ContentPiece, ContentPlan, ContentStatus, ContentType, FactSheet,
    calculate_english_ratio, count_words, detect_unverified_statistics,
    detect_tone_drift, validate_terminology,
)

logger = logging.getLogger("content_agent.nodes.content_validator")

MIN_VALIDATION_SCORE = float(os.getenv("MIN_VALIDATION_SCORE", "0.60"))

PRODUCT_PAGE_REQUIRED_KEYS = {"hero", "features", "pricing", "faq", "cta"}


def make_content_validator_node(claude_client):
    def content_validator_node(state: ContentState) -> dict:
        piece      = state.get("content_piece")
        plan       = state.get("content_plan")
        fact_sheet = state.get("fact_sheet")
        request    = state["request"]

        if not piece or not plan or not fact_sheet:
            return {
                "status":      "failed",
                "error_code":  "CON_GENERATION_FAILED",
                "error_detail": "piece أو plan أو fact_sheet غائب",
            }

        # ── طبقة ١: Structural ──
        s_score, s_issues = _validate_structural(piece, plan)

        # ── طبقة ٢: Language ──
        l_score, l_issues = _validate_language(piece, plan)

        # ── طبقة ٣: Factual ──
        category = request.content_category
        f_score, f_issues = _validate_factual(piece, fact_sheet, claude_client, category)

        final_score = (s_score * 0.25) + (l_score * 0.35) + (f_score * 0.40)

        piece.structural_score  = s_score
        piece.language_score    = l_score
        piece.factual_score     = f_score
        piece.validation_score  = final_score
        piece.validation_issues = s_issues + l_issues + f_issues

        if final_score < MIN_VALIDATION_SCORE:
            piece.status = ContentStatus.FAILED
            logger.warning(
                "content_validator.failed req=%s score=%.2f issues=%s",
                request.request_id, final_score, piece.validation_issues[:3],
            )
            return {
                "content_piece":    piece,
                "validation_failed": True,
                "status":           "validation_failed",
            }

        piece.status = ContentStatus.READY
        logger.info(
            "content_validator.passed req=%s score=%.2f",
            request.request_id, final_score,
        )
        return {
            "content_piece":    piece,
            "validation_failed": False,
            "status":           "validated",
        }

    return content_validator_node


def route_after_validation(state: ContentState) -> str:
    regen = state.get("regeneration_count", 0)
    if state.get("validation_failed"):
        if regen < 1:
            return "content_generator"   # إعادة توليد مرة واحدة
        return "content_error"           # CON_MAX_REGENERATION_REACHED
    return "review_gate"


# ── طبقة ١: Structural ────────────────────────────────────────────

def _validate_structural(piece: ContentPiece, plan: ContentPlan) -> Tuple[float, List[str]]:
    score  = 1.0
    issues = []

    word_count = count_words(str(piece.body))
    min_words  = plan.word_budget // 2

    if word_count < min_words:
        issues.append(f"CON_CONTENT_TOO_SHORT: {word_count} كلمة (الحد {min_words})")
        score -= 0.3

    if word_count > plan.word_budget * 1.5:
        issues.append(f"محتوى طويل جداً: {word_count} كلمة")
        score -= 0.1

    if piece.content_type == ContentType.PRODUCT_PAGE_FULL:
        valid, missing = _validate_product_page_schema(piece.body)
        if not valid:
            issues.append(f"CON_PRODUCT_PAGE_SCHEMA_INVALID: حقول غائبة: {missing}")
            score -= 0.5

    return max(score, 0.0), issues


def _validate_product_page_schema(body) -> Tuple[bool, List[str]]:
    if not isinstance(body, dict):
        return False, list(PRODUCT_PAGE_REQUIRED_KEYS)
    missing = [k for k in PRODUCT_PAGE_REQUIRED_KEYS if k not in body]
    return len(missing) == 0, missing


# ── طبقة ٢: Language ─────────────────────────────────────────────

def _validate_language(piece: ContentPiece, plan: ContentPlan) -> Tuple[float, List[str]]:
    score  = 1.0
    issues = []
    body   = str(piece.body)

    for pattern in BRAND_CONSTITUTION_FORBIDDEN_PATTERNS:
        if re.search(pattern, body, re.I | re.U):
            issues.append(f"CON_CONSTITUTION_VIOLATION: {pattern}")
            score -= 0.3

    english_ratio = calculate_english_ratio(body)
    if english_ratio > 0.15:
        issues.append(f"CON_EXCESSIVE_ENGLISH: {english_ratio:.0%}")
        score -= 0.1

    for term_issue in validate_terminology(body):
        issues.append(f"CON_TERMINOLOGY_DRIFT: {term_issue}")
        score -= 0.05

    for tone_issue in detect_tone_drift(body, plan.tone):
        issues.append(f"CON_TONE_DRIFT: {tone_issue}")
        score -= 0.1

    return max(score, 0.0), issues


# ── طبقة ٣: Factual ──────────────────────────────────────────────

def _validate_factual(
    piece:        ContentPiece,
    fact_sheet:   FactSheet,
    claude_client,
    category,
) -> Tuple[float, List[str]]:
    score  = 1.0
    issues = []
    body   = str(piece.body)

    unverified = detect_unverified_statistics(body)
    if unverified:
        issues.append(f"CON_UNVERIFIED_STATISTICS: {unverified}")
        score -= 0.3

    result = claude_client.factual_check_safe(body, fact_sheet, category)

    # إن كان الفشل يستوجب وقف العملية
    if "fallback" in result and result["fallback"] == "fail":
        issues.append("CON_FORBIDDEN_CLAIM: فشل التحقق الدلالي — فئة TRANSACTIONAL تتطلب الدقة")
        score -= 0.4
    elif result.get("violations"):
        for v in result["violations"]:
            issues.append(f"CON_FORBIDDEN_CLAIM: {v}")
            score -= 0.2

    for feature in _check_feature_claims(body, fact_sheet.verified_facts):
        issues.append(f"CON_UNVERIFIED_FEATURE: {feature}")
        score -= 0.15

    return max(score, 0.0), issues


def _check_feature_claims(body: str, verified_facts: List[str]) -> List[str]:
    """يكشف ميزات مذكورة غير موجودة في verified_facts."""
    violations = []
    feature_pattern = re.compile(r'(?:يدعم|يتضمن|يتيح|يوفر)\s+([\u0600-\u06FF\s]{5,30})', re.U)
    claims = feature_pattern.findall(body)
    for claim in claims:
        claim_clean = claim.strip()
        found = any(claim_clean in fact for fact in verified_facts)
        if not found and len(claim_clean) > 8:
            violations.append(claim_clean)
    return violations[:3]  # أقصى 3 للتقرير
