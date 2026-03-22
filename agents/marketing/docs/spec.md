# وكيل التسويق — وكيل النشر وإدارة الحملات
## وثيقة المواصفات الشاملة v2 — Marketing Agent

> هذه النسخة تجمع v1 + تصحيحات ChatGPT المعتمدة + التصحيحات المعمارية الإضافية.
> تُعدّ المرجع التنفيذي الوحيد المعتمد لوكيل التسويق.

---

## فهرس المحتويات

1. نظرة عامة ومبادئ جوهرية
2. موقع الوكيل في المنظومة الكاملة
3. تصنيف القنوات — Channel Taxonomy
4. CHANNEL_REQUIREMENTS — متطلبات كل قناة (كاملة)
5. USER_LOCKED_DECISIONS — القرارات المحجوزة
6. الكيانات الجوهرية — Domain Model
7. READINESS_AGGREGATOR — بوابة جاهزية الحملة
8. Marketing Calendar — طبقة التنسيق الزمني
9. معمارية الوكيل — ثلاثة Workflows
10. Workflow الأول — Campaign Launcher
11. Workflow الثاني — Scheduler & Publisher
12. Workflow الثالث — Analytics Consumer
13. ASSET_COLLECTOR — جمع الأصول مع Snapshot
14. CHANNEL_ROUTER — توجيه المحتوى
15. PLATFORM_PUBLISHER — النشر على المنصات
16. REJECTION_HANDLER — معالجة الرفض الكامل
17. AUTO_APPLICABLE_SIGNALS — سياسة الإشارات التلقائية
18. القنوات المدفوعة — Proposal-Only Policy
19. Website Placements — مواصفات الموقع
20. Idempotency Strategy
21. Event Contract Schemas
22. أمان وحدود الصلاحية
23. Error Codes Catalog
24. بنية الـ State
25. البيئة المحلية ومتغيرات البيئة
26. دستور الوكيل
27. قائمة التحقق النهائية

---

## ١. نظرة عامة ومبادئ جوهرية

### الهدف

بناء وكيل تسويق يتولى نشر المحتوى على القنوات المناسبة في التوقيت الأمثل، وإدارة الحملات التسويقية المتكاملة، وجدولة المنشورات بمحتوى مُجمَّد مضمون السلامة، واستهلاك تقارير وكيل التحليل لتحسين القرارات المستقبلية — كل ذلك ضمن صلاحيات محددة بدقة وقنوات مُعرَّفة بالكامل لا تفاوض فيها.

### المحاور الأربعة

```
١. النشر العضوي      → نشر على AUTONOMOUS_CHANNELS في التوقيت الصحيح
٢. إدارة الحملات     → تنسيق النص + الصورة + القناة + التوقيت
٣. التنسيق الزمني    → جدولة مبنية على بيانات، مع frequency caps وblackout dates
٤. استهلاك التحليل  → يقرأ إشارات وكيل التحليل ويُعدّل قراراته بسياسة محددة
   (لا ينتج تحليلاً — ذلك شأن وكيل التحليل)
```

### المبادئ غير القابلة للتفاوض

- **كل قناة مُعرَّفة في CHANNEL_REQUIREMENTS** — أي قناة غير مُعرَّفة تُوقف التنفيذ
- **USER_LOCKED_DECISIONS لا تُمسّ** — ستة قرارات محجوزة لصاحب المشروع
- **القنوات المدفوعة proposal-only في v1** — إعداد وانتظار لا تنفيذ
- **ScheduledPost نسخة مجمّدة** — لا يتغير المحتوى بعد الجدولة
- **fallback حتمي لا عشوائي** — select_best_variant() يختار default_variant
- **Analytics signals مقيّدة بسياسة** — لا تطبيق تلقائي لكل إشارة
- **رفض المنصة لا يُكتم** — كل رفض يُوثَّق ويُبلَّغ فوراً
- **الفشل الصامت ممنوع** — كل خطأ له كود محدد

---

## ٢. موقع الوكيل في المنظومة الكاملة

```
وكيل المحتوى
    │ CONTENT_READY (EMAIL_LAUNCH, MARKETING_COPY, SOCIAL_CAPTION)
    ▼
وكيل التسويق ◄── وكيل الإنتاج البصري (THEME_ASSETS_READY)
    │             وكيل التحليل (ANALYTICS_REPORT)
    │
    ├── ينشر على: Facebook / Instagram / TikTok / WhatsApp
    ├── يُحدّث: بانرات وإشعارات الموقع
    ├── يُعدّ: مقترحات Google Ads / Meta Ads (بدون تنفيذ)
    │
    │ حدث: CAMPAIGN_LAUNCHED
    │ حدث: POST_PUBLISHED
    └──► وكيل التحليل ← يُسجّل كل نشر لتتبع النتائج
```

### الوكيل مُستهلِك لا مُنتِج

- يأخذ المحتوى من وكيل المحتوى — لا ينتجه
- يستهلك إشارات وكيل التحليل — لا يُنتجها
- يُعدّ مقترحات الإعلانات المدفوعة — لا ينفّذها

---

## ٣. تصنيف القنوات — Channel Taxonomy

```python
class ChannelType(Enum):
    ORGANIC_CONTENT = "organic_content"
    PAID_ADS        = "paid_ads"
    NOTIFICATION    = "notification"
    WEBSITE         = "website"

class Channel(Enum):
    # قنوات المحتوى العضوي
    FACEBOOK    = "facebook"
    INSTAGRAM   = "instagram"
    TIKTOK      = "tiktok"

    # قنوات الإعلان المدفوع (proposal-only في v1)
    GOOGLE_ADS  = "google_ads"
    META_ADS    = "meta_ads"
    TIKTOK_ADS  = "tiktok_ads"

    # قنوات الإشعار
    EMAIL       = "email"
    WHATSAPP    = "whatsapp"

    # قنوات الموقع
    SITE_BANNER      = "site_banner"
    SITE_POPUP       = "site_popup"
    NOTIFICATION_BAR = "notification_bar"


CHANNEL_TAXONOMY = {
    ChannelType.ORGANIC_CONTENT: [
        Channel.FACEBOOK, Channel.INSTAGRAM, Channel.TIKTOK,
    ],
    ChannelType.PAID_ADS: [
        Channel.GOOGLE_ADS, Channel.META_ADS, Channel.TIKTOK_ADS,
    ],
    ChannelType.NOTIFICATION: [
        Channel.EMAIL, Channel.WHATSAPP,
    ],
    ChannelType.WEBSITE: [
        Channel.SITE_BANNER, Channel.SITE_POPUP, Channel.NOTIFICATION_BAR,
    ],
}

PAID_CHANNELS       = {Channel.GOOGLE_ADS, Channel.META_ADS, Channel.TIKTOK_ADS}
AUTONOMOUS_CHANNELS = {
    Channel.FACEBOOK, Channel.INSTAGRAM, Channel.TIKTOK,
    Channel.EMAIL, Channel.WHATSAPP,
    Channel.SITE_BANNER, Channel.SITE_POPUP, Channel.NOTIFICATION_BAR,
}

# قاعدة صارمة: كل قناة يجب أن تكون في CHANNEL_REQUIREMENTS
ALL_CHANNELS_MUST_HAVE_REQUIREMENTS = True
```

---

## ٤. CHANNEL_REQUIREMENTS — متطلبات كل قناة (كاملة)

```python
@dataclass
class ChannelRequirement:
    channel:           Channel
    channel_type:      ChannelType
    text_required:     bool
    image_required:    bool
    video_required:    bool
    image_preferred:   bool
    video_preferred:   bool
    wait_minutes:      int
    fallback_allowed:  bool
    max_text_chars:    Optional[int]
    content_types:     List[str]
    notes:             str = ""


CHANNEL_REQUIREMENTS: Dict[Channel, ChannelRequirement] = {

    Channel.FACEBOOK: ChannelRequirement(
        channel          = Channel.FACEBOOK,
        channel_type     = ChannelType.ORGANIC_CONTENT,
        text_required    = True,
        image_required   = False,
        video_required   = False,
        image_preferred  = True,
        video_preferred  = False,
        wait_minutes     = 30,
        fallback_allowed = True,
        max_text_chars   = 63206,
        content_types    = ["marketing_copy", "social_caption", "email_launch"],
        notes            = "ينشر بنص وحده بعد 30 دقيقة إن لم تأتِ الصورة",
    ),

    Channel.INSTAGRAM: ChannelRequirement(
        channel          = Channel.INSTAGRAM,
        channel_type     = ChannelType.ORGANIC_CONTENT,
        text_required    = True,
        image_required   = True,
        video_required   = False,
        image_preferred  = True,
        video_preferred  = False,
        wait_minutes     = 30,
        fallback_allowed = False,
        max_text_chars   = 2200,
        content_types    = ["social_caption", "marketing_copy"],
        notes            = "يتطلب Instagram Business Account. لا نشر بدون صورة.",
    ),

    Channel.TIKTOK: ChannelRequirement(
        channel          = Channel.TIKTOK,
        channel_type     = ChannelType.ORGANIC_CONTENT,
        text_required    = True,
        image_required   = False,
        video_required   = True,
        image_preferred  = False,
        video_preferred  = True,
        wait_minutes     = 60,
        fallback_allowed = False,
        max_text_chars   = 2200,
        content_types    = ["social_caption", "marketing_copy"],
        notes            = "يتطلب TikTok for Business. تحقق من API availability في المنطقة.",
    ),

    Channel.EMAIL: ChannelRequirement(
        channel          = Channel.EMAIL,
        channel_type     = ChannelType.NOTIFICATION,
        text_required    = True,
        image_required   = False,
        video_required   = False,
        image_preferred  = False,
        video_preferred  = False,
        wait_minutes     = 0,
        fallback_allowed = True,
        max_text_chars   = None,
        content_types    = ["email_launch", "email_campaign"],
    ),

    Channel.WHATSAPP: ChannelRequirement(
        channel          = Channel.WHATSAPP,
        channel_type     = ChannelType.NOTIFICATION,
        text_required    = True,
        image_required   = False,
        video_required   = False,
        image_preferred  = False,
        video_preferred  = False,
        wait_minutes     = 0,
        fallback_allowed = True,
        max_text_chars   = 4096,
        content_types    = ["marketing_copy", "social_caption"],
        notes            = "WhatsApp Business API — يتطلب opt-in من المستقبل",
    ),

    # ── قنوات الإعلان المدفوع (proposal-only) ─────────────

    Channel.GOOGLE_ADS: ChannelRequirement(
        channel          = Channel.GOOGLE_ADS,
        channel_type     = ChannelType.PAID_ADS,
        text_required    = True,
        image_required   = False,
        video_required   = False,
        image_preferred  = True,
        video_preferred  = False,
        wait_minutes     = 0,
        fallback_allowed = True,
        max_text_chars   = 300,
        content_types    = ["marketing_copy"],
        notes            = "proposal-only في v1 — لا تنفيذ بدون موافقة صاحب المشروع",
    ),

    Channel.META_ADS: ChannelRequirement(
        channel          = Channel.META_ADS,
        channel_type     = ChannelType.PAID_ADS,
        text_required    = True,
        image_required   = True,
        video_required   = False,
        image_preferred  = True,
        video_preferred  = False,
        wait_minutes     = 0,
        fallback_allowed = False,
        max_text_chars   = 125,
        content_types    = ["marketing_copy"],
        notes            = "proposal-only في v1 — يشمل Facebook Ads وInstagram Ads",
    ),

    Channel.TIKTOK_ADS: ChannelRequirement(
        channel          = Channel.TIKTOK_ADS,
        channel_type     = ChannelType.PAID_ADS,
        text_required    = True,
        image_required   = False,
        video_required   = True,
        image_preferred  = False,
        video_preferred  = True,
        wait_minutes     = 0,
        fallback_allowed = False,
        max_text_chars   = 100,
        content_types    = ["marketing_copy"],
        notes            = "proposal-only في v1 — مستقبلاً",
    ),

    # ── قنوات الموقع ──────────────────────────────────────

    Channel.SITE_BANNER: ChannelRequirement(
        channel          = Channel.SITE_BANNER,
        channel_type     = ChannelType.WEBSITE,
        text_required    = True,
        image_required   = True,
        video_required   = False,
        image_preferred  = True,
        video_preferred  = False,
        wait_minutes     = 30,
        fallback_allowed = False,
        max_text_chars   = 150,
        content_types    = ["marketing_copy"],
        notes            = "يحتاج WebsitePlacementSpec كاملاً",
    ),

    Channel.SITE_POPUP: ChannelRequirement(
        channel          = Channel.SITE_POPUP,
        channel_type     = ChannelType.WEBSITE,
        text_required    = True,
        image_required   = False,
        video_required   = False,
        image_preferred  = True,
        video_preferred  = False,
        wait_minutes     = 0,
        fallback_allowed = True,
        max_text_chars   = 200,
        content_types    = ["marketing_copy"],
        notes            = "يحتاج WebsitePlacementSpec كاملاً",
    ),

    Channel.NOTIFICATION_BAR: ChannelRequirement(
        channel          = Channel.NOTIFICATION_BAR,
        channel_type     = ChannelType.WEBSITE,
        text_required    = True,
        image_required   = False,
        video_required   = False,
        image_preferred  = False,
        video_preferred  = False,
        wait_minutes     = 0,
        fallback_allowed = True,
        max_text_chars   = 100,
        content_types    = ["marketing_copy"],
        notes            = "شريط الإشعار العلوي — نص قصير فقط",
    ),
}


def get_channel_requirements(channel: Channel) -> ChannelRequirement:
    """
    يجلب متطلبات القناة — يُوقف التنفيذ إن لم تكن مُعرَّفة.
    لا قناة غير مُعرَّفة تمر بصمت.
    """
    if channel not in CHANNEL_REQUIREMENTS:
        raise ConfigurationError(
            f"PLT_CHANNEL_NOT_CONFIGURED: متطلبات القناة غير مُعرَّفة: {channel.value}"
        )
    return CHANNEL_REQUIREMENTS[channel]
```

---

## ٥. USER_LOCKED_DECISIONS — القرارات المحجوزة

```python
USER_LOCKED_DECISIONS = {
    "budget_change": {
        "الوصف":    "أي تغيير في ميزانية الإعلانات المدفوعة",
        "السبب":    "إنفاق مالي حقيقي — لا أتوماتيكية في صرف المال",
        "الإجراء":  "إيقاف فوري + إشعار صاحب المشروع",
    },
    "new_campaign_type": {
        "الوصف":    "إطلاق نوع حملة لم يُطلق من قبل",
        "السبب":    "قرار استراتيجي يحتاج رؤية صاحب المشروع",
        "الإجراء":  "إعداد مقترح + انتظار موافقة صريحة",
    },
    "discount_change": {
        "الوصف":    "أي خصم أو تغيير في السعر",
        "السبب":    "قرار تجاري مباشر يؤثر على الإيرادات",
        "الإجراء":  "إيقاف فوري + إشعار صاحب المشروع",
    },
    "targeting_change": {
        "الوصف":    "تغيير الجمهور المستهدف أو البلدان في الإعلانات",
        "السبب":    "يؤثر على الإنفاق والنتائج",
        "الإجراء":  "إيقاف فوري + إشعار صاحب المشروع",
    },
    "crisis_response": {
        "الوصف":    "أي رد على هجوم أو أزمة سمعة",
        "السبب":    "قرار حساس يتطلب حكماً بشرياً",
        "الإجراء":  "إيقاف كل النشر + إشعار عاجل فوري",
    },
    "campaign_stop": {
        "الوصف":    "إيقاف حملة جارية",
        "السبب":    "قد يؤثر على حجوزات وتوقعات",
        "الإجراء":  "إيقاف + انتظار أمر صريح",
    },
}


def check_locked_decision(action: str) -> tuple[bool, str]:
    if action in USER_LOCKED_DECISIONS:
        return True, USER_LOCKED_DECISIONS[action]["الإجراء"]
    return False, ""
```

---

## ٦. الكيانات الجوهرية — Domain Model

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Union
from datetime import datetime
from enum import Enum


class CampaignType(Enum):
    PRODUCT_LAUNCH  = "product_launch"
    PRODUCT_UPDATE  = "product_update"
    SEASONAL        = "seasonal"
    PROMOTIONAL     = "promotional"
    AWARENESS       = "awareness"
    RETARGETING     = "retargeting"


class CampaignObjective(Enum):
    """هدف الحملة — يؤثر على التوقيت والقنوات والتحليل"""
    TRAFFIC          = "traffic"
    AWARENESS        = "awareness"
    CONVERSION       = "conversion"
    LAUNCH_VISIBILITY = "launch_visibility"
    LIST_GROWTH      = "list_growth"


class CampaignStatus(Enum):
    PLANNED    = "planned"
    ACTIVE     = "active"
    PAUSED     = "paused"
    COMPLETED  = "completed"
    CANCELLED  = "cancelled"


class PostStatus(Enum):
    SCHEDULED  = "scheduled"
    PUBLISHED  = "published"
    FAILED     = "failed"
    REJECTED   = "rejected"
    SKIPPED    = "skipped"


class AssetReadiness(Enum):
    READY       = "ready"
    WAITING     = "waiting"
    TIMEOUT     = "timeout"
    UNAVAILABLE = "unavailable"


class PaidApprovalStatus(Enum):
    NOT_REQUESTED = "not_requested"
    PENDING       = "pending"
    APPROVED      = "approved"
    REJECTED      = "rejected"
    EXPIRED       = "expired"


@dataclass
class Campaign:
    campaign_id:          str
    campaign_type:        CampaignType
    campaign_objective:   CampaignObjective
    theme_slug:           Optional[str]
    name:                 str
    channels:             List[Channel]
    content_ids:          List[str]
    asset_ids:            List[str]
    status:               CampaignStatus
    paid_approval_status: PaidApprovalStatus
    scheduled_at:         Optional[datetime]
    launched_at:          Optional[datetime]
    completed_at:         Optional[datetime]
    created_at:           datetime
    correlation_id:       str


@dataclass
class ContentSnapshot:
    """نسخة مجمّدة من المحتوى عند الجدولة — لا تتغير"""
    content_id:      str
    content_version: str
    content_body:    str
    content_type:    str
    variant_label:   Optional[str]
    snapshot_hash:   str       # md5(content_body + content_version)
    frozen_at:       datetime


@dataclass
class AssetSnapshot:
    """نسخة مجمّدة من الأصل عند الجدولة"""
    asset_id:      str
    asset_version: str
    asset_url:     str
    asset_type:    str          # "image" | "video"
    snapshot_hash: str
    frozen_at:     datetime


@dataclass
class ScheduledPost:
    post_id:              str
    campaign_id:          str
    channel:              Channel
    content_snapshot:     ContentSnapshot    # نسخة مجمّدة — لا تتغير
    asset_snapshot:       Optional[AssetSnapshot]
    scheduled_at:         datetime
    published_at:         Optional[datetime]
    platform_post_id:     Optional[str]
    status:               PostStatus
    retry_count:          int
    error_detail:         Optional[str]
    idempotency_key:      str


@dataclass
class WebsitePlacementSpec:
    """مواصفات خاصة لقنوات الموقع"""
    placement_type:  str             # "banner" | "popup" | "notification_bar"
    target_pages:    List[str]       # ["home", "themes", "all"]
    cta_url:         Optional[str]
    cta_text:        Optional[str]
    priority:        int             # 1 = أعلى
    dismissible:     bool
    start_at:        datetime
    end_at:          Optional[datetime]
    audience_scope:  str             # "all" | "new_visitors" | "returning"
    theme_slug:      Optional[str]


@dataclass
class AnalyticsSignal:
    signal_id:      str
    signal_type:    str
    channel:        Optional[Channel]
    theme_slug:     Optional[str]
    recommendation: str
    confidence:     float
    data:           Dict
    received_at:    datetime
    auto_applicable: bool    # مُحدَّد من AUTO_APPLICABLE_SIGNALS


@dataclass
class CampaignReadinessState:
    """حالة جاهزية الحملة من READINESS_AGGREGATOR"""
    product_live:      bool
    content_ready:     bool
    assets_ready:      bool
    assets_timeout:    bool
    min_bundle_met:    bool    # الحد الأدنى من المحتوى متوفر
    ready_to_launch:   bool
    waiting_for:       List[str]
```

---

## ٧. READINESS_AGGREGATOR — بوابة جاهزية الحملة

### المشكلة التي يحلها

```python
"""
Campaign Launcher يحتاج ثلاثة أحداث:
  NEW_PRODUCT_LIVE + CONTENT_READY + THEME_ASSETS_READY

هذه الأحداث قد تصل بترتيب مختلف أو بفاصل زمني.
بدون طبقة تجميع:
  - الحملة قد تُطلَق ناقصة
  - الحملة قد تُطلَق مرتين
  - الحملة قد تبقى معلقة بلا state واضح

READINESS_AGGREGATOR يحل هذا بقاعدة جاهزية واضحة.
"""

CAMPAIGN_READINESS_RULE = {
    "required": [
        "product_live",    # NEW_PRODUCT_LIVE وصل
        "content_ready",   # CONTENT_READY وصل (حزمة أدنى)
    ],
    "optional_with_timeout": {
        "assets_ready": 120,  # دقيقتان انتظار — ثم يُطلَق بما هو متاح
    },
    "min_content_bundle": {
        # الحد الأدنى للمحتوى قبل الإطلاق
        "required_any_of": ["marketing_copy", "social_caption"],
    },
}
```

### التنفيذ

```python
class ReadinessAggregator:
    """
    يتتبع وصول الأحداث لكل theme_slug.
    يُطلق الحملة فور اكتمال الشروط الإلزامية.
    """

    def on_event(self, event: dict) -> Optional[CampaignReadinessState]:
        event_type = event["event_type"]
        theme_slug = event["data"].get("theme_slug")

        if not theme_slug:
            return None

        state = self._get_or_create_state(theme_slug, event)

        if event_type == "NEW_PRODUCT_LIVE":
            state["product_live"]   = True
            state["product_data"]   = event["data"]

        elif event_type == "CONTENT_READY":
            content_type = event["data"].get("content_type")
            if content_type in ["marketing_copy", "social_caption", "email_launch"]:
                state["content_ready"] = True
                state["content_data"].append(event["data"])

        elif event_type == "THEME_ASSETS_READY":
            state["assets_ready"] = True
            state["assets_data"]  = event["data"]["assets"]

        self._save_state(theme_slug, state)
        return self._evaluate_readiness(theme_slug, state)


    def _evaluate_readiness(
        self,
        theme_slug: str,
        state:      dict,
    ) -> Optional[CampaignReadinessState]:

        product_live   = state.get("product_live", False)
        content_ready  = state.get("content_ready", False)
        assets_ready   = state.get("assets_ready", False)

        # فحص assets timeout
        assets_timeout = False
        if not assets_ready and state.get("product_live_at"):
            elapsed = (datetime.utcnow() - state["product_live_at"]).seconds / 60
            assets_timeout = elapsed >= CAMPAIGN_READINESS_RULE["optional_with_timeout"]["assets_ready"]

        # فحص الحد الأدنى من المحتوى
        content_types  = [c["content_type"] for c in state.get("content_data", [])]
        min_bundle_met = any(
            ct in content_types
            for ct in CAMPAIGN_READINESS_RULE["min_content_bundle"]["required_any_of"]
        )

        # هل يمكن الإطلاق؟
        ready_to_launch = (
            product_live and
            content_ready and
            min_bundle_met and
            (assets_ready or assets_timeout)
        )

        waiting_for = []
        if not product_live:    waiting_for.append("NEW_PRODUCT_LIVE")
        if not content_ready:   waiting_for.append("CONTENT_READY")
        if not assets_ready and not assets_timeout:
            waiting_for.append("THEME_ASSETS_READY (انتظار 2 دقيقة)")

        return CampaignReadinessState(
            product_live    = product_live,
            content_ready   = content_ready,
            assets_ready    = assets_ready,
            assets_timeout  = assets_timeout,
            min_bundle_met  = min_bundle_met,
            ready_to_launch = ready_to_launch,
            waiting_for     = waiting_for,
        )
```

---

## ٨. Marketing Calendar — طبقة التنسيق الزمني

```python
"""
Marketing Calendar ليس مجرد جدول — هو طبقة تنسيق زمني.
يُقرر: متى يُنشر، أي قناة أولاً، هل يتكرر، blackout dates، frequency caps.
"""

BLACKOUT_DATES: List[str] = [
    # أيام لا يُنشر فيها تسويق (تُحدَّث يدوياً)
    # صيغة: "MM-DD" للتكرار السنوي أو "YYYY-MM-DD" لمرة واحدة
]

FREQUENCY_CAPS = {
    Channel.FACEBOOK:   {"per_day": 2,  "per_week": 6},
    Channel.INSTAGRAM:  {"per_day": 2,  "per_week": 5},
    Channel.TIKTOK:     {"per_day": 1,  "per_week": 3},
    Channel.EMAIL:      {"per_day": 1,  "per_week": 2},
    Channel.WHATSAPP:   {"per_day": 1,  "per_week": 2},
    Channel.SITE_BANNER:{"per_day": 1,  "per_week": 7},
}

NO_OVERLAP_WINDOW_MINUTES = {
    Channel.FACEBOOK:  30,
    Channel.INSTAGRAM: 60,
    Channel.EMAIL:     120,
}


class MarketingCalendar:

    def schedule_campaign(
        self,
        campaign:     Campaign,
        content_data: List[dict],
        assets_data:  dict,
    ) -> List[ScheduledPost]:
        posts = []

        for channel in campaign.channels:
            if channel in PAID_CHANNELS:
                continue

            req = get_channel_requirements(channel)

            # فحص frequency cap
            if self._cap_exceeded(channel):
                continue

            # فحص blackout dates
            optimal_time = self.get_optimal_time(channel, campaign.theme_slug)
            if self._is_blackout(optimal_time):
                optimal_time = self._next_available_slot(channel, optimal_time)

            # اختيار المحتوى والأصل
            content = self._select_content(channel, content_data, req)
            if not content:
                continue

            asset = self._select_asset(channel, assets_data, req)

            # إنشاء Snapshots مجمّدة
            content_snapshot = self._freeze_content(content)
            asset_snapshot   = self._freeze_asset(asset) if asset else None

            post = ScheduledPost(
                post_id          = str(uuid.uuid4()),
                campaign_id      = campaign.campaign_id,
                channel          = channel,
                content_snapshot = content_snapshot,
                asset_snapshot   = asset_snapshot,
                scheduled_at     = optimal_time,
                published_at     = None,
                platform_post_id = None,
                status           = PostStatus.SCHEDULED,
                retry_count      = 0,
                error_detail     = None,
                idempotency_key  = build_post_idempotency_key(
                    campaign.campaign_id,
                    channel,
                    content_snapshot.content_id,
                    content_snapshot.variant_label or "default",
                    optimal_time,
                ),
            )
            posts.append(post)
            self._save_to_calendar(post)
            self._update_frequency_counter(channel)

        return posts


    def get_optimal_time(
        self,
        channel:    Channel,
        theme_slug: Optional[str],
    ) -> datetime:
        signal = analytics_signals.get_latest(
            signal_type = "best_time",
            channel     = channel,
            min_confidence = 0.85,
        )
        if signal:
            return parse_recommended_time(signal.recommendation)
        return self._default_time(channel)


    def _freeze_content(self, content: dict) -> ContentSnapshot:
        body = content.get("body", "")
        return ContentSnapshot(
            content_id      = content["content_id"],
            content_version = content.get("metadata", {}).get("template_id", "1.0"),
            content_body    = body,
            content_type    = content["content_type"],
            variant_label   = content.get("variant_label"),
            snapshot_hash   = hashlib.md5(body.encode()).hexdigest(),
            frozen_at       = datetime.utcnow(),
        )

    def _freeze_asset(self, asset: dict) -> AssetSnapshot:
        return AssetSnapshot(
            asset_id      = asset.get("asset_id", str(uuid.uuid4())),
            asset_version = asset.get("version", "1.0"),
            asset_url     = asset["url"],
            asset_type    = asset["type"],
            snapshot_hash = hashlib.md5(asset["url"].encode()).hexdigest(),
            frozen_at     = datetime.utcnow(),
        )

    def _cap_exceeded(self, channel: Channel) -> bool:
        caps    = FREQUENCY_CAPS.get(channel)
        if not caps:
            return False
        today   = db.count_posts_today(channel)
        weekly  = db.count_posts_this_week(channel)
        return today >= caps["per_day"] or weekly >= caps["per_week"]

    def _is_blackout(self, dt: datetime) -> bool:
        day_str  = dt.strftime("%m-%d")
        date_str = dt.strftime("%Y-%m-%d")
        return day_str in BLACKOUT_DATES or date_str in BLACKOUT_DATES


DEFAULT_POSTING_TIMES = {
    Channel.FACEBOOK:   "20:00",
    Channel.INSTAGRAM:  "19:00",
    Channel.TIKTOK:     "21:00",
    Channel.EMAIL:      "10:00",
    Channel.WHATSAPP:   "09:00",
    Channel.SITE_BANNER: "08:00",
}
```

---

## ٩. معمارية الوكيل — ثلاثة Workflows

```
Workflow 1: Campaign Launcher
  المُشغِّل: READINESS_AGGREGATOR → ready_to_launch = True
  الطبيعة:  خطي — يجمع الأصول ويُطلق الحملة

Workflow 2: Scheduler & Publisher
  المُشغِّل: cron كل 5 دقائق
  الطبيعة:  دائم — ينشر المجدوَل في وقته

Workflow 3: Analytics Consumer
  المُشغِّل: ANALYTICS_REPORT من وكيل التحليل
  الطبيعة:  خطي — يُحدّث قرارات التوقيت والقنوات بسياسة محددة
```

---

## ١٠. Workflow الأول — Campaign Launcher

### خريطة الـ Nodes

```
[READINESS_AGGREGATOR]  ← يستمع لـ NEW_PRODUCT_LIVE + CONTENT_READY + THEME_ASSETS_READY
      │
      ▼ (ready_to_launch = True)
[CAMPAIGN_ENTRY]
      │
      ▼
[IDEMPOTENCY_CHECK] ──► مكتمل → END
      │
      ▼
[LOCKED_DECISION_CHECK]──► محجوز → [OWNER_NOTIFICATION] → END
      │
      ▼
[ASSET_COLLECTOR]
      │
      ▼
[CHANNEL_ROUTER]        ← AUTONOMOUS_CHANNELS فقط
      │
      ▼
[CALENDAR_SCHEDULER]    ← يُجمّد المحتوى + يُحدد التوقيت الأمثل
      │
      ▼
[PAID_CHANNEL_GATE]     ← يُعدّ المقترح وينتظر — لا ينفذ
      │
      ▼
[CAMPAIGN_RECORDER]
      │
      ▼
[LAUNCH_ANNOUNCER]      ← CAMPAIGN_LAUNCHED على Redis
      │
      ▼
     END
```

---

## ١١. Workflow الثاني — Scheduler & Publisher

### خريطة الـ Nodes

```
[CRON_TRIGGER]          ← كل 5 دقائق
      │
      ▼
[DUE_POSTS_FETCHER]
      │
      ▼ (لكل منشور مستحق)
[IDEMPOTENCY_CHECK] ──► منشور مسبقاً → SKIP
      │
      ▼
[SNAPSHOT_INTEGRITY_CHECK] ← هل Snapshot لا تزال صالحة؟
      │
      ▼
[PLATFORM_PUBLISHER]
      │
      ├── نجح   → [POST_RECORDER] → [PUBLISH_ANNOUNCER]
      ├── رُفض  → [REJECTION_HANDLER]
      └── فشل   → [RETRY_SCHEDULER] (≤ 3 مرات)
```

### SNAPSHOT_INTEGRITY_CHECK

```python
def snapshot_integrity_check_node(state: MarketingState) -> MarketingState:
    """
    يتحقق أن المحتوى المجمّد لا يزال صالحاً قبل النشر.
    URL الصورة قد ينتهي — snapshot_hash يكتشف التغيير.
    """
    post = state["current_post"]

    # تحقق من Content Snapshot
    current_hash = hashlib.md5(
        post.content_snapshot.content_body.encode()
    ).hexdigest()

    if current_hash != post.content_snapshot.snapshot_hash:
        state["status"]     = "error"
        state["error_code"] = "MKT_SNAPSHOT_INTEGRITY_FAILED"
        return state

    # تحقق من Asset URL (إن وُجد)
    if post.asset_snapshot:
        if not is_url_accessible(post.asset_snapshot.asset_url):
            state["status"]     = "error"
            state["error_code"] = "MKT_ASSET_URL_EXPIRED"
            # محاولة تجديد الـ URL من visual_store
            fresh_url = visual_store.get_fresh_url(
                post.asset_snapshot.asset_id,
                post.asset_snapshot.asset_version,
            )
            if fresh_url:
                post.asset_snapshot.asset_url = fresh_url
                state["current_post"] = post
            else:
                return state

    return state
```

---

## ١٢. Workflow الثالث — Analytics Consumer

```python
"""
يستهلك إشارات وكيل التحليل بسياسة محددة لا يتجاوزها.
ليس كل إشارة تُطبَّق آلياً.
"""

def analytics_consumer_workflow(event: dict) -> None:
    report = event["data"]

    for signal_data in report.get("signals", []):
        signal_type = signal_data["type"]
        policy      = AUTO_APPLICABLE_SIGNALS.get(signal_type)

        if not policy:
            # إشارة غير معروفة → تُحفظ فقط
            analytics_signals.save(build_signal(signal_data, auto_applicable=False))
            continue

        auto_applicable = (
            policy["auto_apply"] is not False and
            signal_data["confidence"] >= policy["min_confidence"]
        )

        signal = build_signal(signal_data, auto_applicable=auto_applicable)
        analytics_signals.save(signal)

        if auto_applicable:
            apply_signal(signal, policy)


def apply_signal(signal: AnalyticsSignal, policy: dict) -> None:
    if policy["auto_apply"] == True:
        if signal.signal_type == "best_time":
            update_default_posting_time(signal.channel, signal.recommendation)

        elif signal.signal_type == "high_performance":
            upgrade_channel_priority(signal.channel)

    elif policy["auto_apply"] == "deprioritize_only":
        # فقط تخفيض الأولوية — لا إيقاف القناة
        downgrade_channel_priority(
            channel = signal.channel,
            reason  = signal.recommendation,
        )
```

---

## ١٣. ASSET_COLLECTOR — جمع الأصول مع Snapshot

```python
def asset_collector_node(state: MarketingState) -> MarketingState:
    theme_slug = state["theme_slug"]

    # النصوص من وكيل المحتوى
    texts = content_store.get_ready_content(
        theme_slug    = theme_slug,
        content_types = ["marketing_copy", "social_caption", "email_launch"],
    )

    # الأصول من وكيل الإنتاج البصري
    visuals = visual_store.get_assets(
        theme_slug  = theme_slug,
        asset_types = ["hero_image", "preview_images", "promo_video"],
    )

    state["available_texts"]   = texts
    state["available_visuals"] = visuals
    state["asset_readiness"]   = assess_readiness(texts, visuals)

    return state


def assess_readiness(
    texts:   list,
    visuals: dict,
) -> Dict[Channel, AssetReadiness]:
    readiness = {}

    for channel in AUTONOMOUS_CHANNELS:
        req = get_channel_requirements(channel)  # يُوقف إن غير مُعرَّف

        has_text  = bool(texts)
        has_image = bool(
            visuals.get("hero_image") or
            visuals.get("preview_images")
        )
        has_video = bool(visuals.get("promo_video"))

        if req.text_required and not has_text:
            readiness[channel] = AssetReadiness.UNAVAILABLE
        elif req.image_required and not has_image:
            readiness[channel] = AssetReadiness.WAITING
        elif req.video_required and not has_video:
            readiness[channel] = AssetReadiness.WAITING
        else:
            readiness[channel] = AssetReadiness.READY

    return readiness
```

---

## ١٤. CHANNEL_ROUTER — توجيه المحتوى

```python
def select_content_for_channel(
    channel:      Channel,
    content_data: List[dict],
    req:          ChannelRequirement,
) -> Optional[dict]:
    preferred_types = req.content_types

    for content_type in preferred_types:
        matching = [c for c in content_data if c["content_type"] == content_type]
        if not matching:
            continue

        # إن وُجدت متغيرات → اختر deterministically
        if len(matching) > 1:
            return select_best_variant_deterministic(matching, channel)

        return matching[0]

    return None


def select_best_variant_deterministic(
    variants: List[dict],
    channel:  Channel,
) -> dict:
    """
    يختار المتغير الأفضل بطريقة حتمية لا عشوائية.
    الترتيب: إشارة التحليل > default_variant > أعلى validation_score > الأول
    """
    # ١. إشارة التحليل بثقة عالية
    signal = analytics_signals.get_latest(
        signal_type    = "best_variant",
        channel        = channel,
        min_confidence = 0.75,
    )
    if signal:
        preferred_label = signal.data.get("label")
        for v in variants:
            if v.get("variant_label") == preferred_label:
                return v

    # ٢. المتغير المُعلَّم كـ default
    for v in variants:
        if v.get("variant_label") == "A" or v.get("is_default"):
            return v

    # ٣. أعلى validation_score
    return max(variants, key=lambda v: v.get("validation_score", 0))
```

---

## ١٥. PLATFORM_PUBLISHER — النشر على المنصات

```python
def platform_publisher_node(state: MarketingState) -> MarketingState:
    post    = state["current_post"]
    channel = post.channel
    snapshot = post.content_snapshot

    try:
        if channel == Channel.FACEBOOK:
            result = publish_to_facebook(post)
        elif channel == Channel.INSTAGRAM:
            result = publish_to_instagram(post)
        elif channel == Channel.TIKTOK:
            result = publish_to_tiktok(post)
        elif channel == Channel.EMAIL:
            result = send_email_campaign(post)
        elif channel == Channel.WHATSAPP:
            result = send_whatsapp_message(post)
        elif channel in (Channel.SITE_BANNER, Channel.SITE_POPUP, Channel.NOTIFICATION_BAR):
            result = update_website_placement(post)
        else:
            raise ConfigurationError(f"قناة غير مدعومة: {channel}")

        post.status           = PostStatus.PUBLISHED
        post.published_at     = datetime.utcnow()
        post.platform_post_id = result.get("post_id")

    except PlatformRejectionError as e:
        post.status       = PostStatus.REJECTED
        post.error_detail = str(e)
        state["rejection_error"]  = e
        state["route"]            = "handle_rejection"

    except Exception as e:
        post.status       = PostStatus.FAILED
        post.error_detail = str(e)
        post.retry_count += 1
        state["route"] = "retry" if post.retry_count < MAX_PUBLISH_RETRIES else "fail"

    state["current_post"] = post
    return state
```

---

## ١٦. REJECTION_HANDLER — معالجة الرفض الكامل

```python
@dataclass
class PlatformRejectionError(Exception):
    channel: Channel
    code:    Optional[str]
    message: str


REJECTION_POLICIES = {
    "policy_violation": {
        "retry":   False,
        "notify":  True,
        "action":  "review_content",
        "note":    "خرق سياسات المنصة — لا إعادة محاولة",
    },
    "rate_limit": {
        "retry":        True,
        "retry_after":  3600,
        "notify":       False,
        "note":         "حد المعدل — يُعاد بعد ساعة",
    },
    "media_error": {
        "retry":        True,
        "retry_after":  300,
        "notify":       True,
        "note":         "خطأ في الأصول — يُعاد بعد 5 دقائق",
    },
    "auth_error": {
        "retry":   False,
        "notify":  True,
        "action":  "refresh_token_or_reauth",
        "note":    "Token منتهي أو مُلغى — يحتاج إعادة مصادقة يدوية",
    },
    "unknown": {
        "retry":   False,
        "notify":  True,
        "note":    "خطأ غير معروف — إشعار فوري",
    },
}


def classify_rejection(error: PlatformRejectionError) -> str:
    code    = (error.code or "").lower()
    message = error.message.lower()

    auth_keywords   = ["token", "auth", "permission", "access", "expired",
                       "unauthorized", "forbidden"]
    policy_keywords = ["policy", "community standards", "مخالفة", "سياسة"]
    rate_keywords   = ["rate limit", "too many", "throttle", "429"]
    media_keywords  = ["media", "image", "video", "asset", "upload"]

    if any(kw in code or kw in message for kw in auth_keywords):
        return "auth_error"
    if any(kw in message for kw in policy_keywords):
        return "policy_violation"
    if any(kw in message for kw in rate_keywords):
        return "rate_limit"
    if any(kw in message for kw in media_keywords):
        return "media_error"
    return "unknown"


def rejection_handler_node(state: MarketingState) -> MarketingState:
    post   = state["current_post"]
    error  = state["rejection_error"]
    reason = classify_rejection(error)
    policy = REJECTION_POLICIES[reason]

    log_rejection({
        "post_id":   post.post_id,
        "channel":   post.channel.value,
        "reason":    reason,
        "code":      error.code,
        "message":   error.message,
        "timestamp": datetime.utcnow().isoformat(),
    })

    if policy["notify"]:
        notify_owner_of_rejection(post, reason, error.message, policy["note"])

    if reason == "auth_error":
        # يُحاول تجديد الـ Token تلقائياً أولاً
        refreshed = attempt_token_refresh(post.channel)
        if refreshed:
            post.status      = PostStatus.SCHEDULED
            post.retry_count += 1
            post.scheduled_at = datetime.utcnow() + timedelta(minutes=5)
        else:
            # فشل التجديد → حاجة لتدخل يدوي
            post.status = PostStatus.REJECTED
            notify_owner_for_manual_reauth(post.channel)

    elif policy["retry"]:
        post.status       = PostStatus.SCHEDULED
        post.retry_count += 1
        post.scheduled_at = datetime.utcnow() + timedelta(
            seconds = policy.get("retry_after", 300)
        )

    else:
        post.status = PostStatus.REJECTED

    state["current_post"] = post
    return state
```

---

## ١٧. AUTO_APPLICABLE_SIGNALS — سياسة الإشارات التلقائية

```python
"""
ليس كل إشارة تُطبَّق آلياً — لكل نوع سياسة.
الإشارات التي تمس USER_LOCKED_DECISIONS مُحجوبة دائماً.
"""

AUTO_APPLICABLE_SIGNALS = {
    "best_time": {
        "min_confidence": 0.85,
        "auto_apply":     True,
        "description":    "تحديث وقت النشر الافتراضي",
        "locked":         False,
    },
    "high_performance": {
        "min_confidence": 0.90,
        "auto_apply":     True,
        "description":    "رفع أولوية قناة ذات أداء جيد",
        "locked":         False,
    },
    "low_performance": {
        "min_confidence": 0.90,
        "auto_apply":     "deprioritize_only",   # تخفيض فقط — لا إيقاف
        "description":    "تخفيض أولوية قناة ذات أداء ضعيف",
        "locked":         False,
    },
    "best_variant": {
        "min_confidence": 0.75,
        "auto_apply":     True,
        "description":    "تفضيل متغير معين في قناة معينة",
        "locked":         False,
    },

    # إشارات محجوبة — لا تُطبَّق أبداً آلياً
    "channel_disable": {
        "min_confidence": 1.0,
        "auto_apply":     False,
        "description":    "إيقاف قناة — قرار بشري",
        "locked":         True,
    },
    "budget_shift": {
        "min_confidence": 1.0,
        "auto_apply":     False,
        "description":    "تغيير الميزانية — USER_LOCKED",
        "locked":         True,
    },
    "campaign_stop": {
        "min_confidence": 1.0,
        "auto_apply":     False,
        "description":    "إيقاف حملة — USER_LOCKED",
        "locked":         True,
    },
}


def process_signal(signal_data: dict) -> None:
    signal_type = signal_data["type"]
    policy      = AUTO_APPLICABLE_SIGNALS.get(signal_type)

    if not policy:
        analytics_signals.save(build_signal(signal_data, auto_applicable=False))
        return

    if policy["locked"]:
        # إشارة محجوبة → تُحفظ وتُبلَّغ لصاحب المشروع للاطلاع فقط
        analytics_signals.save(build_signal(signal_data, auto_applicable=False))
        notify_owner_of_locked_signal(signal_data, policy["description"])
        return

    auto_applicable = (
        policy["auto_apply"] is not False and
        signal_data.get("confidence", 0) >= policy["min_confidence"]
    )

    signal = build_signal(signal_data, auto_applicable=auto_applicable)
    analytics_signals.save(signal)

    if auto_applicable:
        apply_signal(signal, policy)
```

---

## ١٨. القنوات المدفوعة — Proposal-Only Policy

```python
"""
في v1، القنوات المدفوعة ليست publishing channels.
هي review-only proposal channels.

ما يفعله الوكيل:
  ١. يجمع المحتوى والأصول المناسبة
  ٢. يُعدّ مقترح الحملة الكامل
  ٣. يُرسل للمراجعة البشرية
  ٤. ينتظر الموافقة الصريحة
  ٥. لا يُنفّذ بأي حال

لماذا؟
Google Ads / Meta Ads عالم مستقل يتضمن:
  budgets / bidding strategies / targeting trees /
  approvals / creative variants / compliance / spend monitoring
هذا خارج نطاق v1 ويُفصل لاحقاً في Paid Acquisition Agent إن لزم.
"""


def paid_channel_gate_node(state: MarketingState) -> MarketingState:
    paid_requested = [
        ch for ch in state.get("requested_paid_channels", [])
        if ch in PAID_CHANNELS
    ]

    if not paid_requested:
        return state

    # إعداد المقترح فقط
    proposal = build_paid_campaign_proposal(
        channels   = paid_requested,
        content    = state["available_texts"],
        visuals    = state["available_visuals"],
        theme_slug = state["theme_slug"],
        objective  = state.get("campaign_objective"),
    )

    resend_client.emails.send({
        "from":    STORE_EMAIL_FROM,
        "to":      OWNER_EMAIL,
        "subject": f"مقترح حملة مدفوعة — {state['theme_slug']}",
        "html":    render_email_template("paid_campaign_proposal", {
            "theme_name": state["theme_name_ar"],
            "channels":   [ch.value for ch in paid_requested],
            "objective":  state.get("campaign_objective", {}).value if state.get("campaign_objective") else "غير محدد",
            "proposal":   proposal,
        }),
    })

    state["paid_approval_status"] = PaidApprovalStatus.PENDING
    state["paid_channels_pending"] = paid_requested

    return state
```

---

## ١٩. Website Placements — مواصفات الموقع

```python
def update_website_placement(post: ScheduledPost) -> dict:
    """
    قنوات الموقع تحتاج WebsitePlacementSpec كاملاً.
    تختلف عن social posts في: placement_id, start/end, audience scope.
    """
    spec = post.placement_spec   # يجب أن يكون موجوداً

    if not spec:
        raise ConfigurationError(
            f"WebsitePlacementSpec مطلوب لقناة الموقع: {post.channel.value}"
        )

    payload = {
        "placement_type":  spec.placement_type,
        "target_pages":    spec.target_pages,
        "content":         post.content_snapshot.content_body,
        "cta_url":         spec.cta_url,
        "cta_text":        spec.cta_text,
        "priority":        spec.priority,
        "dismissible":     spec.dismissible,
        "start_at":        spec.start_at.isoformat(),
        "end_at":          spec.end_at.isoformat() if spec.end_at else None,
        "audience_scope":  spec.audience_scope,
    }

    if post.asset_snapshot:
        payload["image_url"] = post.asset_snapshot.asset_url

    # استدعاء WordPress REST API لتحديث البانر
    response = wp_client.post(
        endpoint = "/wp-json/ar-themes/v1/placements",
        data     = payload,
    )

    return {"post_id": response.get("placement_id")}


def build_placement_spec_from_campaign(
    channel:    Channel,
    campaign:   Campaign,
    theme_slug: str,
) -> WebsitePlacementSpec:
    """يبني مواصفات الموقع من بيانات الحملة."""
    return WebsitePlacementSpec(
        placement_type = channel.value.replace("site_", ""),
        target_pages   = ["home", "themes"],
        cta_url        = f"{STORE_URL}/themes/{theme_slug}/",
        cta_text       = "اكتشف القالب",
        priority       = 1,
        dismissible    = True,
        start_at       = datetime.utcnow(),
        end_at         = datetime.utcnow() + timedelta(days=7),
        audience_scope = "all",
        theme_slug     = theme_slug,
    )
```

---

## ٢٠. Idempotency Strategy

```python
def build_post_idempotency_key(
    campaign_id:   str,
    channel:       Channel,
    content_id:    str,
    variant_label: str,
    scheduled_at:  datetime,
) -> str:
    """
    يشمل: campaign + channel + content + variant + scheduled_slot.
    يمنع نشر نفس المتغير مرتين في نفس الفترة الزمنية.
    """
    # تقريب الوقت إلى أقرب 30 دقيقة لتجميع الإعادات المشروعة
    slot = scheduled_at.replace(
        minute  = (scheduled_at.minute // 30) * 30,
        second  = 0,
        microsecond = 0,
    )
    slot_str = slot.strftime("%Y%m%d%H%M")

    return (
        f"post:{campaign_id}"
        f":{channel.value}"
        f":{content_id}"
        f":{variant_label}"
        f":{slot_str}"
    )


def check_post_idempotency(idempotency_key: str) -> bool:
    """يُرجع True إن كان المنشور نُشر مسبقاً."""
    return db.fetchone(
        "SELECT 1 FROM published_posts WHERE idempotency_key = %s",
        [idempotency_key]
    ) is not None
```

---

## ٢١. Event Contract Schemas

### CAMPAIGN_LAUNCHED (مُطلَق)

```json
{
  "event_id":      "uuid-v4",
  "event_type":    "CAMPAIGN_LAUNCHED",
  "event_version": "1.0",
  "source":        "marketing_agent",
  "occurred_at":   "ISO-datetime",
  "correlation_id": "launch:{theme_slug}:{version}",
  "data": {
    "campaign_id":       "camp-uuid",
    "campaign_type":     "product_launch",
    "campaign_objective": "launch_visibility",
    "theme_slug":        "restaurant_modern",
    "channels":          ["facebook", "instagram", "email"],
    "posts_scheduled":   4,
    "first_post_at":     "ISO-datetime"
  }
}
```

### POST_PUBLISHED (مُطلَق)

```json
{
  "event_id":      "uuid-v4",
  "event_type":    "POST_PUBLISHED",
  "event_version": "1.0",
  "source":        "marketing_agent",
  "occurred_at":   "ISO-datetime",
  "correlation_id": "launch:{theme_slug}:{version}",
  "data": {
    "post_id":            "post-uuid",
    "campaign_id":        "camp-uuid",
    "channel":            "facebook",
    "platform_post_id":   "123456789",
    "theme_slug":         "restaurant_modern",
    "content_type":       "marketing_copy",
    "content_snapshot_hash": "abc123",
    "campaign_objective": "launch_visibility"
  }
}
```

---

## ٢٢. أمان وحدود الصلاحية

```python
CAN_DO = [
    "جدولة ونشر على AUTONOMOUS_CHANNELS",
    "تجميد المحتوى والأصول عند الجدولة (Snapshot)",
    "اختيار التوقيت من Analytics Signals بسياسة محددة",
    "إعادة المحاولة عند الفشل المؤقت",
    "تجديد Tokens تلقائياً عند auth_error",
    "تحديث Website Placements",
    "إعداد مقترحات الحملات المدفوعة وانتظار الموافقة",
    "تطبيق frequency caps وblackout dates",
]

CANNOT_DO = [
    "النشر على PAID_CHANNELS بدون موافقة صريحة",
    "تغيير أسعار أو عروض (USER_LOCKED)",
    "تغيير جمهور الإعلانات (USER_LOCKED)",
    "الرد على أزمة سمعة (USER_LOCKED)",
    "إيقاف حملة جارية (USER_LOCKED)",
    "إنفاق أي مبلغ مالي",
    "تطبيق إشارة تحليل من النوع المحجوب",
    "تعديل المحتوى بعد الجدولة (Snapshot مجمّد)",
    "تجاوز USER_LOCKED_DECISIONS لأي سبب",
]

SECURITY_REQUIREMENTS = [
    "PAID_CHANNELS: proposal-only في v1 — لا API calls لتنفيذ إعلانات",
    "Facebook/Instagram Access Tokens في .env",
    "TikTok API credentials في .env",
    "Tokens تُجدَّد قبل انتهائها بـ 48 ساعة",
    "ALL_CHANNELS_MUST_HAVE_REQUIREMENTS: ConfigurationError إن تُكسر",
    "ScheduledPost.content_snapshot غير قابل للتعديل بعد الإنشاء",
    "رفض المنصة يُبلَّغ فوراً — لا يُكتم",
    "USER_LOCKED_DECISIONS: أي محاولة تتجاوزها تُوقف التنفيذ",
]
```

---

## ٢٣. Error Codes Catalog

```python
MARKETING_ERROR_CODES = {
    # التهيئة
    "MKT_CHANNEL_NOT_CONFIGURED":    "قناة غير مُعرَّفة في CHANNEL_REQUIREMENTS",

    # الجاهزية
    "MKT_READINESS_NOT_MET":         "شروط إطلاق الحملة غير مكتملة",
    "MKT_MIN_CONTENT_BUNDLE_MISSING": "الحد الأدنى من المحتوى غير متوفر",

    # الحملة
    "MKT_CAMPAIGN_DUPLICATE":        "الحملة مُنشأة مسبقاً",
    "MKT_LOCKED_DECISION_REQUIRED":  "قرار محجوز يحتاج موافقة صاحب المشروع",
    "MKT_NO_CONTENT_AVAILABLE":      "لا محتوى متاح من وكيل المحتوى",
    "MKT_NO_CHANNELS_SELECTED":      "لا قنوات مؤهلة للنشر",

    # الأصول
    "MKT_ASSET_TIMEOUT":             "انتهت مهلة انتظار الأصول",
    "MKT_REQUIRED_ASSET_MISSING":    "أصل إلزامي غائب",
    "MKT_SNAPSHOT_INTEGRITY_FAILED": "Content Snapshot تغيّر بعد الجدولة",
    "MKT_ASSET_URL_EXPIRED":         "رابط الأصل منتهي الصلاحية",

    # النشر
    "MKT_PLATFORM_REJECTION":        "رفضت المنصة النشر",
    "MKT_POLICY_VIOLATION":          "خرق سياسات المنصة",
    "MKT_RATE_LIMITED":              "تجاوز حد المنصة",
    "MKT_MEDIA_ERROR":               "خطأ في رفع الأصول للمنصة",
    "MKT_AUTH_ERROR":                "Token منتهي أو مُلغى",
    "MKT_MAX_RETRIES_REACHED":       "تجاوز حد إعادة المحاولة",

    # القنوات المدفوعة
    "MKT_PAID_AWAITING_APPROVAL":    "مقترح حملة مدفوعة يُنتظر موافقته",

    # التحليل
    "MKT_SIGNAL_LOCKED":             "إشارة تحليل محجوبة — تحتاج قرار بشري",

    # Website Placements
    "MKT_PLACEMENT_SPEC_MISSING":    "WebsitePlacementSpec مطلوب لقناة الموقع",
    "MKT_WP_PLACEMENT_FAILED":       "فشل تحديث placement على WordPress",
}
```

---

## ٢٤. بنية الـ State

```python
class MarketingState(TypedDict):
    # الهوية
    idempotency_key:      str
    campaign_id:          str
    campaign_type:        CampaignType
    campaign_objective:   CampaignObjective
    theme_slug:           Optional[str]
    theme_name_ar:        Optional[str]

    # الجاهزية
    readiness_state:      Optional[CampaignReadinessState]

    # الأصول
    available_texts:      List[dict]
    available_visuals:    Dict[str, str]
    asset_readiness:      Dict[str, str]

    # القنوات
    selected_channels:       List[Channel]
    skipped_channels:        List[Channel]
    waiting_channels:        Dict[str, int]
    requested_paid_channels: List[Channel]
    paid_channels_pending:   List[Channel]
    paid_approval_status:    PaidApprovalStatus

    # الجدولة
    scheduled_posts:      List[ScheduledPost]

    # النشر الحالي
    current_post:         Optional[ScheduledPost]
    rejection_error:      Optional[PlatformRejectionError]

    # الحالة
    route:      Optional[str]
    status:     str
    error_code: Optional[str]
    logs:       List[str]
```

---

## ٢٥. البيئة المحلية ومتغيرات البيئة

```env
# Facebook / Instagram
FB_PAGE_ID=...
FB_PAGE_ACCESS_TOKEN=...
IG_ACCOUNT_ID=...
IG_ACCESS_TOKEN=...

# TikTok
TIKTOK_CLIENT_KEY=...
TIKTOK_CLIENT_SECRET=...
TIKTOK_ACCESS_TOKEN=...

# WhatsApp Business
WA_PHONE_NUMBER_ID=...
WA_ACCESS_TOKEN=...

# Google Ads (proposal-only)
GOOGLE_ADS_CLIENT_ID=...
GOOGLE_ADS_DEVELOPER_TOKEN=...

# Meta Ads (proposal-only)
META_ADS_ACCOUNT_ID=...

# WordPress (لـ Website Placements)
WP_SITE_URL=https://ar-themes.com
WP_API_USER=marketing_agent
WP_API_PASSWORD=...

# Resend
RESEND_API_KEY=...
STORE_EMAIL_FROM=قوالب عربية <hello@ar-themes.com>
OWNER_EMAIL=owner@ar-themes.com

# Redis
REDIS_URL=redis://localhost:6379

# قاعدة البيانات
DATABASE_URL=postgresql://user:pass@localhost/marketing_db

# ضوابط التشغيل
MAX_PUBLISH_RETRIES=3
SCHEDULER_INTERVAL_MINUTES=5
READINESS_ASSETS_TIMEOUT_MINUTES=120
ANALYTICS_CONFIDENCE_THRESHOLD=0.85
TOKEN_RENEWAL_HOURS_BEFORE=48

LOG_LEVEL=INFO
```

---

## ٢٦. دستور الوكيل

```markdown
# دستور وكيل التسويق v2

## الهوية
أنا وكيل تسويق متخصص في نشر محتوى قوالب WordPress العربي
وإدارة حملاته على القنوات الرقمية بصلاحيات محددة لا أتجاوزها.

## القواعد المطلقة
١. USER_LOCKED_DECISIONS لا تُمسّ — ستة قرارات لصاحب المشروع وحده
٢. كل قناة مُعرَّفة في CHANNEL_REQUIREMENTS — ConfigurationError إن لم تكن
٣. القنوات المدفوعة proposal-only — إعداد وانتظار لا تنفيذ
٤. ScheduledPost نسخة مجمّدة — لا تتغير بعد الجدولة
٥. select_best_variant: حتمي لا عشوائي
٦. Analytics signals: كل إشارة لها سياسة — لا تطبيق أعمى
٧. رفض المنصة لا يُكتم — يُوثَّق ويُبلَّغ فوراً
٨. READINESS_AGGREGATOR يُطلق الحملة — لا مؤقتات عشوائية
٩. الوكيل ينشر — لا ينتج محتوىً
١٠. الوكيل يستهلك التحليل — لا ينتجه

## ما أُجيده
- تجميع أحداث الإطلاق وتقييم جاهزية الحملة
- تجميد المحتوى والأصول عند الجدولة (Snapshot)
- جدولة بالتوقيت الأمثل مع frequency caps وblackout dates
- معالجة رفض المنصات بسياسة شاملة تشمل auth_error
- تطبيق إشارات التحليل بحسب نوعها وثقتها
- إعداد مقترحات الحملات المدفوعة للمراجعة البشرية

## ما أتجنبه
- أي قرار من USER_LOCKED_DECISIONS
- تنفيذ إعلانات مدفوعة في v1
- النشر على قناة غير مُعرَّفة في CHANNEL_REQUIREMENTS
- fallback عشوائي في اختيار المتغيرات
- تطبيق إشارات محجوبة تلقائياً
- تعديل Snapshot بعد الجدولة
```

---

## ٢٧. قائمة التحقق النهائية

### Campaign Launcher Workflow

```
□ READINESS_AGGREGATOR: كل الأحداث المطلوبة وصلت أو انتهت مهلة الأصول
□ idempotency_key — لا حملة مكررة
□ USER_LOCKED_DECISIONS مفحوصة قبل أي تحرك
□ get_channel_requirements: ConfigurationError إن قناة غير مُعرَّفة
□ ASSET_COLLECTOR: نصوص + أصول من المصادر الصحيحة
□ CHANNEL_ROUTER: AUTONOMOUS_CHANNELS فقط
□ Instagram: صورة إلزامية — لا نشر بدونها
□ TikTok: فيديو إلزامي — لا نشر بدونه
□ Facebook: fallback بنص وحده بعد 30 دقيقة
□ CALENDAR_SCHEDULER: Content Snapshot + Asset Snapshot مجمّدان
□ Idempotency key: campaign + channel + content + variant + scheduled_slot
□ PAID_CHANNEL_GATE: مقترح فقط + إشعار + PaidApprovalStatus.PENDING
□ campaign_objective مُعرَّف
□ CAMPAIGN_LAUNCHED بالصيغة الموحدة
```

### Scheduler & Publisher Workflow

```
□ cron كل 5 دقائق
□ idempotency: post_id لا يُنشر مرتين
□ SNAPSHOT_INTEGRITY_CHECK: hash_match + URL accessible
□ get_channel_requirements: لا قناة بلا متطلبات
□ PLATFORM_PUBLISHER: API صحيح لكل قناة
□ Website Placements: WebsitePlacementSpec موجودة
□ رفض: classify_rejection (policy/rate/media/auth/unknown)
□ auth_error: محاولة تجديد تلقائية أولاً
□ policy_violation: لا إعادة + إشعار صاحب المشروع
□ POST_PUBLISHED لوكيل التحليل
```

### Analytics Consumer Workflow

```
□ ANALYTICS_REPORT مُستقبَل
□ كل إشارة مُقيَّمة ضد AUTO_APPLICABLE_SIGNALS
□ إشارات محجوبة: تُحفظ + تُبلَّغ — لا تُطبَّق
□ best_time ≥ 0.85: يُحدّث DEFAULT_POSTING_TIMES
□ high_performance ≥ 0.90: يرفع أولوية القناة
□ low_performance ≥ 0.90: يُخفّض فقط — لا يُوقف
□ channel_disable: لا تُطبَّق — USER_LOCKED
□ لا إنتاج تحليل — استهلاك فقط
```
