"""
بنية الـ State لوكيل المنصة
المرجع: agents/platform/docs/spec.md § ٢٠
"""
from typing import TypedDict, Optional, List, Dict, Any
from enum import Enum


class PlatformStatus(Enum):
    IDLE                        = "idle"
    RUNNING                     = "running"
    WAITING_ASSETS              = "waiting_assets"
    WAITING_HUMAN_REVIEW        = "waiting_human_review"
    WAITING_ASSET_DECISION      = "waiting_asset_decision"
    RETRYING                    = "retrying"
    COMPLETED                   = "completed"
    FAILED                      = "failed"
    INCONSISTENT_EXTERNAL_STATE = "inconsistent_external_state"


class ReviewDecision(Enum):
    APPROVED_AS_IS       = "approved_as_is"
    APPROVED_WITH_EDITS  = "approved_with_edits"
    NEEDS_REVISION_MINOR = "needs_revision_minor"
    NEEDS_REVISION_MAJOR = "needs_revision_major"
    REJECTED             = "rejected"


class LaunchState(TypedDict):
    # هوية الحدث
    idempotency_key:    str
    event_type:         str
    theme_slug:         str
    version:            str
    approved_event_id:  str
    incoming_event:     Dict[str, Any]
    theme_contract:     Dict[str, Any]
    parsed:             Dict[str, Any]
    package_path:       str
    # الأصول
    collected_assets:       Dict[str, str]
    has_video:              bool
    asset_timeout_warning:  bool
    extension_used:         bool
    # Lemon Squeezy
    ls_product_id:        Optional[str]
    ls_variants:          List[Dict]
    vip_product_id:       Optional[str]
    # WordPress
    wp_post_id:           Optional[int]
    wp_post_url:          Optional[str]
    # محتوى الصفحة
    draft_page_content:   Optional[Dict]
    page_blocks:          Optional[str]
    # مراجعة بشرية
    revision_count:       int
    human_decision:       Optional[str]
    human_edits:          Optional[Dict]
    revision_notes:       Optional[str]
    # حالة
    status:               PlatformStatus
    error_code:           Optional[str]
    error:                Optional[str]
    logs:                 List[str]


class UpdateState(TypedDict):
    # هوية الحدث
    idempotency_key:    str
    event_type:         str
    event_id:           str
    theme_slug:         str
    new_version:        str
    previous_version:   Optional[str]
    # من Registry
    ls_product_id:          Optional[str]
    ls_single_variant:      Optional[str]
    ls_unlimited_variant:   Optional[str]
    wp_post_id:             Optional[int]
    wp_post_url:            Optional[str]
    # التحديث
    package_path:           str
    changelog:              Dict[str, Any]
    # إشعارات
    eligible_buyers:        List[Dict]
    notification_results:   Optional[Dict]
    # حالة
    status:                 PlatformStatus
    error_code:             Optional[str]
    error:                  Optional[str]
    logs:                   List[str]
