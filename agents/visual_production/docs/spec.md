# وكيل الإنتاج البصري — وكيل توليد الأصول المرئية
## وثيقة المواصفات الشاملة v2 — Visual Production Agent

> هذه النسخة تجمع v1 + تصحيحات ChatGPT المعتمدة + التصحيحات المعمارية الإضافية.
> تُعدّ المرجع التنفيذي الوحيد المعتمد لوكيل الإنتاج البصري.

---

## فهرس المحتويات

1. نظرة عامة ومبادئ جوهرية
2. موقع الوكيل في المنظومة الكاملة
3. Asset Set — مجموعة الأصول الكاملة
4. Input Contract — الحقول الإلزامية من THEME_CONTRACT
5. Prompt Builder — بناء الـ Prompts
6. Negative Prompts — العناصر المحظورة
7. أدوات الإنتاج — Tool Registry
8. Video Pipeline — مصدر الفيديو وبنيته
9. الكيانات الجوهرية — Domain Model
10. Cost Budget — الميزانية لكل قالب
11. معمارية الوكيل — Workflow
12. MULTI_GENERATOR — الإنتاج المتعدد
13. QUALITY_GATE — فحص الجودة الآلي
14. ASSET_SELECTOR — اختيار الأفضل
15. REVIEW_GATE — بوابة المراجعة البشرية
16. POST_PROCESSOR — المعالجة اللاحقة
17. ASSET_PUBLISHER — النشر والتخزين
18. BATCH_RECORDER — التسجيل الكامل
19. Retry Policy — سياسة إعادة المحاولة
20. Fallback Policy — التعامل مع فشل الأدوات
21. Asset Versioning — إصدارات الأصول
22. Asset Manifest — سجل الأصول النهائي
23. Partial Approval Policy — سياسة الاعتماد الجزئي
24. Retention Policy — دورة حياة الأصول
25. Idempotency Strategy
26. Event Contract Schemas
27. اتفاقية مسارات الملفات
28. أمان وخصوصية البيانات
29. Error Codes Catalog
30. بنية الـ State
31. البيئة المحلية ومتغيرات البيئة
32. دستور الوكيل
33. قائمة التحقق النهائية

---

## ١. نظرة عامة ومبادئ جوهرية

### الهدف

بناء وكيل إنتاج بصري يتولى — فور اعتماد القالب بشرياً — توليد مجموعة أصول مرئية كاملة من Prompts مبنية تلقائياً على THEME_CONTRACT، بأدوات متعددة تعمل بالتوازي، مع Negative Prompts إلزامية، وفحص جودة آلي قبل الاختيار، ومعالجة لاحقة للملفات، ومراجعة بشرية قبل الإطلاق.

### المبادئ غير القابلة للتفاوض

- **THEME_CONTRACT مصدر كل Prompt** — لا صورة بلا هوية من العقد
- **Negative Prompts إلزامية** — لا توليد بلا قائمة محظورات صريحة
- **QUALITY_GATE آلي قبل الاختيار** — لا اختيار من مرشحين لم يجتازوا الفحص
- **الفيديو: image-to-video في v1** — من hero_image المعتمد، صامت
- **Review Gate إلزامي** — لا أصل يخرج بدون موافقة صاحب المشروع
- **POST_PROCESSOR إلزامي** — WebP + ضغط + checksum قبل النشر
- **Retry قبل Fallback** — الخطأ المؤقت يُعاد، الدائم يُحوَّل للبديل
- **Asset Manifest محفوظ** — كل أصل مُنشور له سجل كامل

---

## ٢. موقع الوكيل في المنظومة الكاملة

```
وكيل البناء
    │ THEME_APPROVED
    ▼
وكيل الإنتاج البصري
    │
    │ VISUAL_REVIEW_REQUESTED → [مراجعة بشرية]
    │ THEME_ASSETS_READY
    ├──► وكيل المنصة   ← يُكمل Product Launch
    └──► وكيل التسويق ← يبني حملة الإطلاق
```

### مصدر الـ Screenshots

```python
"""
Screenshot الفعلي (1200x900):
  المصدر الأفضل: وكيل البناء يُنتجه من القالب المبني.
  v1 fallback: وكيل الإنتاج البصري يُولّده كـ mockup واقعي بـ Flux.

أصول التسويق: تُولَّد بالكامل من الأدوات البصرية.
"""
```

---

## ٣. Asset Set — مجموعة الأصول الكاملة

```python
ASSET_SET = {
    "required": {
        "screenshot":           {"dims": "1200x900",  "count": 1},
        "hero_image":           {"dims": "1600x900",  "count": 1},
        "preview_images":       {"dims": "1280x800",  "count": 3},
        "thumbnail":            {"dims": "600x450",   "count": 1},
        "og_image":             {"dims": "1200x630",  "count": 1},
        "demo_mockup":          {"dims": "1400x900",  "count": 2},  # desktop + mobile
        "social_cover":         {"dims": "1080x1080", "count": 1},
        "promo_video_vertical": {"dims": "1080x1920", "duration": 25},
    },
    "marketing": {
        "promo_video_horizontal": {"dims": "1920x1080", "duration": 45},
        "banner":                 {"dims": "1200x400",  "count": 1},
        "feature_graphics":       {"dims": "1200x675",  "count": 3},
        "rtl_preview":            {"dims": "1280x720",  "count": 1},
        "mobile_preview":         {"dims": "750x1334",  "count": 1},
    },
    "deferred": {
        "gif_preview":            "يُستخرج من الفيديو",
        "before_after":           "يحتاج تعريف القبل",
        "block_patterns_preview": "للـ WordPress.org مستقبلاً",
    },
}

REQUIRED_FOR_LAUNCH = list(ASSET_SET["required"].keys())
```

---

## ٤. Input Contract — الحقول الإلزامية من THEME_CONTRACT

```python
REQUIRED_CONTRACT_FIELDS = {
    "theme_slug":    {"default": None,  "fail_if_missing": True},
    "theme_name_ar": {"default": None,  "fail_if_missing": True},
    "domain":        {"default": "business_corporate", "fail_if_missing": False},
    "design_tokens": {"default": {"colors": {"primary": "#2D6A4F"}}, "fail_if_missing": False},
    "feature_list":  {"default": [], "fail_if_missing": False},
}

DOMAIN_DEFAULTS = {None: "business_corporate", "": "business_corporate"}

def parse_and_validate_contract(contract: dict) -> tuple[dict, List[str]]:
    issues   = []
    enriched = contract.copy()

    for field, spec in REQUIRED_CONTRACT_FIELDS.items():
        if not contract.get(field):
            if spec["fail_if_missing"]:
                raise ValueError(f"VIS_CONTRACT_MISSING_REQUIRED: {field}")
            enriched[field] = spec["default"]
            issues.append(f"حقل ناقص مع Default: {field}")

    # تطبيع domain
    domain = enriched.get("domain", "")
    if domain not in DOMAIN_STYLES:
        enriched["domain"] = DOMAIN_DEFAULTS.get(domain, "business_corporate")
        issues.append(f"domain غير معروف → business_corporate")

    return enriched, issues
```

---

## ٥. Prompt Builder — بناء الـ Prompts

```python
"""
كل Prompt = 5 طبقات مرتّبة.
"""

BASE_STYLE = """
clean professional UI design
modern Arabic RTL layout
high resolution product photography
no watermarks no human faces
realistic website mockup
professional studio lighting
"""

DOMAIN_STYLES = {
    "restaurant_cafe":   "warm inviting Arabic menu UI amber lighting elegant dining",
    "health_fitness":    "clean clinical blue white green Arabic medical interface",
    "business_corporate": "corporate minimal blue grey clean dashboard professional",
    "education_services": "bright engaging Arabic course content friendly professional",
    "ecommerce_retail":  "product-focused bright Arabic listings cart checkout dynamic",
}

ASSET_TYPE_RULES = {
    "screenshot":     "full homepage layout no browser chrome Arabic content",
    "hero_image":     "marketing hero laptop device mockup theme UI prominent",
    "demo_mockup":    "realistic device mockup laptop+smartphone theme visible clean",
    "social_cover":   "square 1:1 bold visual brand colors Arabic name if text",
    "preview_images": "specific feature close-up Arabic content clean crop",
    "feature_graphics": "single feature spotlight UI screenshot Arabic label",
    "rtl_preview":    "extreme RTL Arabic typography right-to-left reading",
    "mobile_preview": "smartphone portrait mobile-responsive Arabic UI",
    "banner":         "wide horizontal Arabic theme name brand colors minimal",
}

TOOL_RULES = {
    "flux_2_pro":   "photorealistic 8k product photography no artifacts",
    "ideogram_v3":  "Arabic text accurate typography brand colors",
    "kling_ai_2_1": "smooth 24fps UI animation professional transitions",
    "pika_labs":    "stylized social media motion engaging rhythm",
}

ARABIC_TEXT_POLICY = {
    "allowed_assets":   ["social_cover", "og_image", "banner", "feature_graphics"],
    "forbidden_assets": ["screenshot", "hero_image", "demo_mockup", "preview_images"],
    "text_source":      "theme_name_ar",   # المصدر الوحيد
    "ideogram_only":    True,
    "require_review":   True,
}

def build_prompt_spec(asset_type: str, tool: str, contract: dict) -> "PromptSpec":
    domain     = contract.get("domain", "business_corporate")
    colors     = contract.get("design_tokens", {}).get("colors", {})
    features   = contract.get("feature_list", [])[:5]
    primary    = colors.get("primary", "#2D6A4F")

    contract_layer = f"""
    primary color: {primary}
    domain: {domain}
    features: {', '.join(features)}
    Arabic RTL interface
    """

    prompt = "\n".join([
        BASE_STYLE,
        DOMAIN_STYLES.get(domain, DOMAIN_STYLES["business_corporate"]),
        contract_layer,
        ASSET_TYPE_RULES.get(asset_type, ""),
        TOOL_RULES.get(tool, ""),
    ]).strip()

    return PromptSpec(
        asset_type   = asset_type,
        tool         = tool,
        prompt       = prompt,
        negative     = build_negative_prompt(asset_type),
        dimensions   = ASSET_DIMENSIONS.get(asset_type, "1280x720"),
        duration_sec = ASSET_DURATIONS.get(asset_type),
        extra_params = {"seed": build_deterministic_seed(asset_type, contract)},
        prompt_hash  = hashlib.md5(prompt.encode()).hexdigest(),
    )

def build_deterministic_seed(asset_type: str, contract: dict) -> int:
    """نفس المدخلات → نفس الـ seed → استقرار النتائج."""
    key = f"{asset_type}:{contract.get('theme_slug', '')}:{contract.get('domain', '')}"
    return abs(hash(key)) % (2**32)
```

---

## ٦. Negative Prompts — العناصر المحظورة

```python
BASE_NEGATIVE_PROMPT = """
no watermarks no logos
no human faces no hands no fingers
no stock photo people
no blurry pixelated artifacts
no distorted text no lorem ipsum
no random latin gibberish
no non-Arabic UI in RTL sections
no competitor logos
no outdated browser designs
no cluttered layouts
no low contrast unreadable text
no NSFW content
"""

ASSET_TYPE_NEGATIVE = {
    "screenshot":          "no browser chrome no scroll indicators no partial elements",
    "hero_image":          "no multiple overlapping devices no unrealistic proportions",
    "social_cover":        "no more than 20% text no complex backgrounds",
    "promo_video_vertical": "no flash cuts no rapid flashes no audio implied",
}

def build_negative_prompt(asset_type: str) -> str:
    return f"{BASE_NEGATIVE_PROMPT}\n{ASSET_TYPE_NEGATIVE.get(asset_type, '')}".strip()
```

---

## ٧. أدوات الإنتاج — Tool Registry

```python
TOOL_REGISTRY = {
    "flux_2_pro": {
        "type": "image", "candidates": 3,
        "use_for": ["screenshot", "hero_image", "demo_mockup",
                    "preview_images", "feature_graphics", "rtl_preview", "mobile_preview"],
        "supports_negative": True,
    },
    "ideogram_v3": {
        "type": "image", "candidates": 2,
        "use_for": ["social_cover", "og_image", "thumbnail", "banner"],
        "supports_negative": False,
    },
    "kling_ai_2_1": {
        "type": "video", "mode": "image_to_video", "candidates": 1,
        "use_for": ["promo_video_vertical", "promo_video_horizontal"],
        "source_asset": "hero_image",
    },
    "pika_labs": {
        "type": "video", "mode": "image_to_video", "candidates": 1,
        "use_for": ["promo_video_vertical"],
        "source_asset": "hero_image",
    },
}

FALLBACK_CHAIN = {
    "flux_2_pro":   "ideogram_v3",
    "ideogram_v3":  "flux_2_pro",
    "kling_ai_2_1": "pika_labs",
    "pika_labs":    "kling_ai_2_1",
}

COST_PER_GENERATION = {
    "flux_2_pro":   0.055,
    "ideogram_v3":  0.08,
    "kling_ai_2_1": 0.35,
    "pika_labs":    0.25,
}
```

---

## ٨. Video Pipeline — مصدر الفيديو وبنيته

```python
"""
قرار معماري محسوم في v1: image-to-video لا text-to-video.

لماذا؟
  image-to-video: ينطلق من أصل معتمد → نتائج أكثر استقراراً.
  text-to-video:  أقل قابلية للتنبؤ + تكلفة أعلى.

سياسة الصوت:
  صامت افتراضياً — لا موسيقى، لا voice-over.
  نصوص عربية داخل الفيديو اختيارية.

ملاحظة توافق APIs:
  Kling AI 2.1: يدعم image-to-video مباشرة.
  Pika Labs: يدعم image-to-video بـ image2video endpoint.
  كلاهما يُستخدم بنفس المنطق لكن endpoints مختلفة.
"""

VIDEO_PIPELINE_V1 = {
    "mode":           "image_to_video",
    "source_asset":   "hero_image",
    "audio":          "none",
    "fps":            24,
    "storyboard": {
        "intro":      "fade in — hero image zoom out smooth",
        "middle":     "pan across UI elements Arabic RTL",
        "outro":      "zoom to brand color + optional theme name",
        "transitions": "smooth dissolve",
    },
}

def build_video_prompt(asset_type: str, contract: dict) -> str:
    domain  = contract.get("domain", "business_corporate")
    primary = contract.get("design_tokens", {}).get("colors", {}).get("primary", "#2D6A4F")

    return f"""
    Animate this Arabic WordPress theme UI smoothly.
    {DOMAIN_STYLES.get(domain, '')}
    Smooth 24fps transitions.
    Arabic RTL interface visible throughout.
    End on solid brand color {primary}.
    Professional product showcase. No audio. No watermarks. No faces.
    """.strip()
```

---

## ٩. الكيانات الجوهرية — Domain Model

```python
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AssetStatus(Enum):
    PENDING       = "pending"
    GENERATING    = "generating"
    QUALITY_CHECK = "quality_check"
    GENERATED     = "generated"
    SELECTED      = "selected"
    REVIEW_PENDING = "review_pending"
    APPROVED      = "approved"
    REJECTED      = "rejected"
    PROCESSING    = "processing"
    PUBLISHED     = "published"
    FAILED        = "failed"
    SKIPPED       = "skipped"


class ReviewDecision(Enum):
    APPROVED        = "approved"
    APPROVED_SUBSET = "approved_subset"
    REGENERATE      = "regenerate"
    REJECTED        = "rejected"


@dataclass
class QualityCheckResult:
    passed:             bool
    dimensions_correct: bool
    size_valid:         bool
    rejection_reasons:  List[str]


@dataclass
class PromptSpec:
    asset_type:   str
    tool:         str
    prompt:       str
    negative:     str
    dimensions:   str
    duration_sec: Optional[float]
    extra_params: Dict
    prompt_hash:  str


@dataclass
class AssetCandidate:
    candidate_id:    str
    asset_type:      str
    tool_used:       str
    file_path:       str
    file_size:       int
    dimensions:      Optional[str]
    duration_sec:    Optional[float]
    prompt_used:     str
    prompt_hash:     str
    negative_prompt: str
    generation_cost: float
    quality_check:   Optional[QualityCheckResult]
    generated_at:    datetime
    is_selected:     bool = False


@dataclass
class ProducedAsset:
    asset_id:            str
    theme_slug:          str
    asset_type:          str
    version:             str
    tool_used:           str
    source_candidate_id: str
    file_path:           str
    published_path:      str
    url:                 str
    dimensions:          Optional[str]
    duration_sec:        Optional[float]
    file_size_bytes:     int
    checksum:            str
    format:              str
    poster_path:         Optional[str]  # للفيديو
    status:              AssetStatus
    approved_at:         Optional[datetime]
    approved_by:         str
    approval_notes:      Optional[str]
    created_at:          datetime


@dataclass
class AssetManifest:
    manifest_id:      str
    theme_slug:       str
    version:          str
    batch_id:         str
    assets:           Dict[str, dict]
    total_cost:       float
    tools_used:       List[str]
    skipped_assets:   List[str]
    created_at:       datetime
    approved_at:      Optional[datetime]
    manifest_version: str = "1.0"
```

---

## ١٠. Cost Budget

```python
COST_BUDGET = {
    "required_only": 2.50,
    "full_v1":       5.00,
    "hard_limit":    8.00,
}

def check_budget_before_start(asset_types: List[str]) -> tuple[bool, float, str]:
    expected = sum(
        COST_PER_GENERATION[tool] * TOOL_REGISTRY[tool]["candidates"]
        for asset_type in asset_types
        for tool in get_tools_for_asset(asset_type)
    )
    if expected > COST_BUDGET["hard_limit"]:
        return False, expected, f"VIS_BUDGET_HARD_LIMIT: {expected:.2f}$"
    return True, expected, ""
```

---

## ١١. معمارية الوكيل — Workflow

```
[VISUAL_ENTRY]
      ▼
[IDEMPOTENCY_CHECK] ──► مكتمل → END
      ▼
[CONTRACT_PARSER]       ← تحقق + إثراء + Defaults
      ▼
[BUDGET_CALCULATOR]     ← فحص قبل البدء
      ▼
[PROMPT_BUILDER]        ← 5 طبقات + Negative + deterministic seed
      ▼
[MULTI_GENERATOR]       ← إنتاج متوازٍ
      ├── خطأ مؤقت → [RETRY_HANDLER]
      ├── outage   → [FALLBACK_HANDLER]
      ▼
[QUALITY_GATE]          ← فحص كل مرشح
      ▼
[ASSET_SELECTOR]        ← اختيار حتمي من الناجحين
      ▼
[REVIEW_GATE]           ← إشعار + انتظار
      ├── regenerate → [PROMPT_BUILDER] (≤3)
      ├── rejected   → [PRODUCTION_CANCEL]
      └── approved
              ▼
      [POST_PROCESSOR]   ← WebP + ضغط + checksum + poster frame
              ▼
      [ASSET_PUBLISHER]  ← حفظ + URL
              ▼
      [BATCH_RECORDER]   ← تسجيل كامل
              ▼
      [MANIFEST_BUILDER] ← manifest.json
              ▼
      [ASSETS_ANNOUNCER] ← THEME_ASSETS_READY
              ▼
             END
```

---

## ١٢. MULTI_GENERATOR — الإنتاج المتعدد

```python
import asyncio

async def multi_generator_node(state: dict) -> dict:
    tasks = [
        generate_with_retry(spec, state["theme_slug"])
        for spec in state["prompt_specs"]
    ]
    results    = await asyncio.gather(*tasks, return_exceptions=True)
    candidates = []
    total_cost = 0.0

    for spec, result in zip(state["prompt_specs"], results):
        if isinstance(result, Exception):
            fallback = await try_fallback(spec, state)
            if fallback:
                candidates.append(fallback)
                total_cost += fallback.generation_cost
            else:
                handle_asset_failure(spec.asset_type, spec.tool, str(result), state)
        else:
            candidates.append(result)
            total_cost += result.generation_cost

    state["candidates"]  = candidates
    state["total_cost"]  = total_cost
    return state
```

---

## ١٣. QUALITY_GATE — فحص الجودة الآلي

```python
def quality_gate_node(state: dict) -> dict:
    passed, failed = [], []

    for c in state["candidates"]:
        result = check_candidate_quality(c)
        c.quality_check = result
        (passed if result.passed else failed).append(c)

    # تحقق: هل لكل أصل إلزامي مرشح ناجح؟
    by_type = {}
    for c in passed:
        by_type.setdefault(c.asset_type, []).append(c)

    for asset_type in REQUIRED_FOR_LAUNCH:
        if asset_type not in by_type:
            policy = ASSET_FALLBACK_POLICY.get(asset_type, "skip_on_failure")
            if policy == "required_no_skip":
                state["status"]     = "failed"
                state["error_code"] = "VIS_REQUIRED_ASSET_NO_QUALITY_PASS"
                return state
            else:
                state.setdefault("skipped_assets", []).append(asset_type)

    state["candidates"] = passed
    return state


def check_candidate_quality(c: "AssetCandidate") -> QualityCheckResult:
    reasons = []

    # أبعاد
    expected = ASSET_DIMENSIONS.get(c.asset_type, "")
    dim_ok   = (c.dimensions == expected) if expected else True
    if not dim_ok:
        reasons.append(f"أبعاد خاطئة: {c.dimensions}")

    # حجم
    size_ok = c.file_size > 50_000
    if not size_ok:
        reasons.append(f"حجم صغير: {c.file_size} bytes")

    return QualityCheckResult(
        passed             = len(reasons) == 0,
        dimensions_correct = dim_ok,
        size_valid         = size_ok,
        rejection_reasons  = reasons,
    )
```

---

## ١٤. ASSET_SELECTOR — اختيار الأفضل

```python
def select_best_deterministic(
    asset_type: str,
    candidates: List["AssetCandidate"],
) -> "AssetCandidate":
    """
    الترتيب الحتمي:
    ١. قواعد صريحة بحسب نوع الأصل
    ٢. LLM تقييم
    ٣. Fallback: المرشح الأول
    """
    # أصول النص العربي → Ideogram
    if asset_type in ["social_cover", "og_image", "thumbnail", "banner"]:
        ideogram = [c for c in candidates if c.tool_used == "ideogram_v3"]
        if ideogram: return ideogram[0]

    # أصول الواقعية → Flux
    if asset_type in ["hero_image", "demo_mockup", "screenshot", "preview_images"]:
        flux = [c for c in candidates if c.tool_used == "flux_2_pro"]
        if flux: return flux[0]

    # LLM للباقي
    try:
        response = claude_client.messages.create(
            model      = "claude-sonnet-4-20250514",
            max_tokens = 5,
            system     = "اختر رقم المرشح الأفضل. أجب برقم فقط.",
            messages   = [{"role": "user", "content":
                f"نوع الأصل: {asset_type}\n" +
                "\n".join(f"{i+1}. {c.tool_used}" for i, c in enumerate(candidates))
            }],
        ).content[0].text.strip()
        idx = int(response) - 1
        return candidates[max(0, min(idx, len(candidates)-1))]
    except:
        return candidates[0]
```

---

## ١٥. REVIEW_GATE — بوابة المراجعة البشرية

```python
REVIEW_TIMEOUT_HOURS = 48
REVIEW_FINAL_TIMEOUT_HOURS = 72
MAX_REGENERATION_ATTEMPTS = 3

def review_gate_node(state: dict) -> dict:
    resend_client.emails.send({
        "from":    STORE_EMAIL_FROM,
        "to":      OWNER_EMAIL,
        "subject": f"أصول بصرية تنتظر مراجعتك — {state['theme_contract'].get('theme_name_ar', '')}",
        "html":    render_email_template("visual_review_request", {
            "theme_name":   state["theme_contract"].get("theme_name_ar", ""),
            "assets_count": len(state["selected_candidates"]),
            "total_cost":   f"{state['total_cost']:.2f}$",
            "skipped":      state.get("skipped_assets", []),
            "assets":       [{"type": a.asset_type, "tool": a.tool_used}
                             for a in state["selected_candidates"]],
            "approve_url":  build_approval_url(state["batch_id"]),
        }),
    })
    state["status"]         = "awaiting_review"
    state["review_sent_at"] = datetime.utcnow().isoformat()
    schedule_review_timeout(state["batch_id"], after_hours=REVIEW_TIMEOUT_HOURS)
    return state


def handle_final_timeout(batch_id: str) -> None:
    """بعد 72 ساعة → تجميد Batch + منع إصدار جديد."""
    batch = batch_store.get(batch_id)
    batch["status"] = "review_timeout"
    batch_store.save(batch_id, batch)
    notify_owner_of_freeze(batch_id)
```

---

## ١٦. POST_PROCESSOR — المعالجة اللاحقة

```python
def post_processor_node(state: dict) -> dict:
    processed = []
    for candidate in state["approved_candidates"]:
        if "video" in candidate.asset_type:
            result = process_video(candidate)
        else:
            result = process_image(candidate)
        processed.append(result)
    state["processed_assets"] = processed
    return state


def process_image(c: "AssetCandidate") -> dict:
    webp_path = convert_to_webp(c.file_path, quality=85)
    checksum  = compute_sha256(webp_path)
    if not verify_image_integrity(webp_path):
        raise ValueError(f"VIS_POST_PROCESS_FAILED: {c.asset_type}")
    return {"candidate_id": c.candidate_id, "asset_type": c.asset_type,
            "file_path": webp_path, "format": "webp", "checksum": checksum,
            "file_size": os.path.getsize(webp_path)}


def process_video(c: "AssetCandidate") -> dict:
    compressed  = compress_video(c.file_path, crf=23)
    poster      = extract_poster_frame(compressed, at_second=2)
    checksum    = compute_sha256(compressed)
    return {"candidate_id": c.candidate_id, "asset_type": c.asset_type,
            "file_path": compressed, "poster_path": poster,
            "format": "mp4", "checksum": checksum,
            "file_size": os.path.getsize(compressed)}
```

---

## ١٧. ASSET_PUBLISHER — النشر والتخزين

```python
def asset_publisher_node(state: dict) -> dict:
    published = []
    for asset_data in state["processed_assets"]:
        published_path = build_published_path(
            state["theme_slug"], state["theme_version"],
            asset_data["asset_type"], asset_data["format"],
        )
        shutil.copy2(asset_data["file_path"], published_path)

        # تحقق من سلامة النسخ
        if compute_sha256(published_path) != asset_data["checksum"]:
            raise ValueError(f"VIS_PUBLISH_INTEGRITY_FAILED: {asset_data['asset_type']}")

        produced = ProducedAsset(
            asset_id             = str(uuid.uuid4()),
            theme_slug           = state["theme_slug"],
            asset_type           = asset_data["asset_type"],
            version              = state["theme_version"],
            tool_used            = state["candidates_map"][asset_data["candidate_id"]].tool_used,
            source_candidate_id  = asset_data["candidate_id"],
            file_path            = asset_data["file_path"],
            published_path       = published_path,
            url                  = build_asset_url(published_path),
            dimensions           = ASSET_DIMENSIONS.get(asset_data["asset_type"]),
            duration_sec         = ASSET_DURATIONS.get(asset_data["asset_type"]),
            file_size_bytes      = asset_data["file_size"],
            checksum             = asset_data["checksum"],
            format               = asset_data["format"],
            poster_path          = asset_data.get("poster_path"),
            status               = AssetStatus.PUBLISHED,
            approved_at          = datetime.utcnow(),
            approved_by          = "owner",
            approval_notes       = state.get("approval_notes"),
            created_at           = datetime.utcnow(),
        )
        published.append(produced)

    state["produced_assets"] = published
    return state
```

---

## ١٨. BATCH_RECORDER — التسجيل الكامل

```python
def batch_recorder_node(state: dict) -> dict:
    batch_store.save(state["batch_id"], {
        "batch_id":               state["batch_id"],
        "theme_slug":             state["theme_slug"],
        "theme_version":          state["theme_version"],
        "prompt_builder_version": PROMPT_BUILDER_VERSION,
        "expected_cost":          state["expected_cost"],
        "actual_cost":            state["total_cost"],
        "cost_by_tool":           compute_cost_by_tool(state["candidates"]),
        "total_candidates":       len(state["candidates"]),
        "quality_passed":         sum(1 for c in state["candidates"] if c.quality_check and c.quality_check.passed),
        "skipped_assets":         state.get("skipped_assets", []),
        "selected_tools":         {c.asset_type: c.tool_used for c in state["selected_candidates"]},
        "review_decision":        state.get("review_decision"),
        "regeneration_attempts":  state.get("regeneration_count", 0),
        "published_count":        len(state.get("produced_assets", [])),
        "completed_at":           datetime.utcnow().isoformat(),
    })
    return state
```

---

## ١٩. Retry Policy — سياسة إعادة المحاولة

```python
RETRY_POLICY = {
    "transient_error":    {"max_retries": 3, "backoff": [5, 15, 30]},
    "rate_limit":         {"max_retries": 3, "backoff": [60, 120, 300]},
    "timeout":            {"max_retries": 2, "backoff": [30, 60]},
    "moderation_failure": {"max_retries": 1, "action": "modify_prompt"},
    "tool_outage":        {"max_retries": 0, "action": "fallback_immediately"},
}

async def generate_with_retry(spec: "PromptSpec", theme_slug: str) -> "AssetCandidate":
    for attempt in range(4):
        try:
            return await generate_asset(spec, theme_slug)
        except RateLimitError:
            wait = RETRY_POLICY["rate_limit"]["backoff"][min(attempt, 2)]
            await asyncio.sleep(wait)
        except TimeoutError:
            await asyncio.sleep(30)
        except ModerationError:
            spec = clean_prompt_for_moderation(spec)
            if attempt > 0: raise
        except ToolOutageError:
            raise
    raise RuntimeError(f"فشل بعد 3 محاولات: {spec.asset_type}")
```

---

## ٢٠. Fallback Policy

```python
ASSET_FALLBACK_POLICY = {
    "screenshot":              "required_no_skip",
    "hero_image":              "required_no_skip",
    "thumbnail":               "required_no_skip",
    "og_image":                "required_no_skip",
    "demo_mockup":             "required_no_skip",
    "social_cover":            "required_no_skip",
    "promo_video_vertical":    "required_no_skip",
    "preview_images":          "skip_on_failure",
    "promo_video_horizontal":  "skip_on_failure",
    "banner":                  "skip_on_failure",
    "feature_graphics":        "skip_on_failure",
    "rtl_preview":             "skip_on_failure",
    "mobile_preview":          "skip_on_failure",
}
```

---

## ٢١. Asset Versioning

```python
ASSETS_BY_CONTRACT_FIELD = {
    "design_tokens.colors": ["hero_image", "social_cover", "og_image",
                              "thumbnail", "banner", "feature_graphics"],
    "feature_list":         ["preview_images", "feature_graphics",
                              "demo_mockup", "promo_video_vertical"],
    "theme_name_ar":        ["social_cover", "og_image", "banner"],
    "domain":               "__all__",
}

def determine_assets_to_regenerate(old: dict, new: dict) -> List[str]:
    changed   = detect_contract_changes(old, new)
    to_regen  = set()
    for field in changed:
        affected = ASSETS_BY_CONTRACT_FIELD.get(field, [])
        if affected == "__all__":
            return REQUIRED_FOR_LAUNCH
        to_regen.update(affected)
    return list(to_regen)
```

---

## ٢٢. Asset Manifest

```python
def manifest_builder_node(state: dict) -> dict:
    manifest = AssetManifest(
        manifest_id   = str(uuid.uuid4()),
        theme_slug    = state["theme_slug"],
        version       = state["theme_version"],
        batch_id      = state["batch_id"],
        assets        = {
            a.asset_type: {
                "asset_id":      a.asset_id, "url": a.url,
                "tool_used":     a.tool_used, "checksum": a.checksum,
                "format":        a.format, "dimensions": a.dimensions,
                "prompt_hash":   state.get("prompt_hashes", {}).get(a.asset_type, ""),
                "approved_at":   a.approved_at.isoformat() if a.approved_at else None,
            }
            for a in state["produced_assets"]
        },
        total_cost    = state["total_cost"],
        tools_used    = list({a.tool_used for a in state["produced_assets"]}),
        skipped_assets = state.get("skipped_assets", []),
        created_at    = datetime.utcnow(),
        approved_at   = datetime.utcnow(),
    )
    path = build_manifest_path(state["theme_slug"], state["theme_version"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(manifest), f, ensure_ascii=False, indent=2, default=str)
    state["manifest"] = manifest
    return state
```

---

## ٢٣. Partial Approval Policy

```python
LAUNCH_REQUIREMENTS = {
    "product":   ["screenshot", "hero_image", "thumbnail", "og_image"],
    "marketing": ["social_cover", "promo_video_vertical"],
}

def evaluate_partial_approval(approved: List[str]) -> dict:
    can_product  = all(a in approved for a in LAUNCH_REQUIREMENTS["product"])
    can_marketing = all(a in approved for a in LAUNCH_REQUIREMENTS["marketing"])

    if can_product and can_marketing:
        events = ["THEME_ASSETS_READY"]
    elif can_product:
        events = ["THEME_ASSETS_PRODUCT_READY"]
    elif can_marketing:
        events = ["THEME_ASSETS_MARKETING_READY"]
    else:
        events = []

    return {"can_product": can_product, "can_marketing": can_marketing,
            "events_to_emit": events}
```

---

## ٢٤. Retention Policy

```python
RETENTION_POLICY = {
    "candidates_not_selected":          {"days": 7,    "after": "delete"},
    "candidates_selected_then_rejected": {"days": 30,   "after": "delete"},
    "approved_current":                  {"days": None, "after": "keep"},
    "approved_superseded":               {"days": 90,   "after": "archive"},
    "archived":                          {"days": 365,  "after": "delete"},
}
```

---

## ٢٥. Idempotency Strategy

```python
def build_visual_idempotency_key(theme_slug: str, version: str) -> str:
    return f"visual:{theme_slug}:{version}"
```

---

## ٢٦. Event Contract Schemas

### THEME_ASSETS_READY (مُطلَق)

```json
{
  "event_id": "uuid-v4", "event_type": "THEME_ASSETS_READY",
  "event_version": "1.0", "source": "visual_production_agent",
  "occurred_at": "ISO-datetime",
  "correlation_id": "visual:restaurant_modern:20250316-0001",
  "data": {
    "theme_slug": "restaurant_modern",
    "version":    "20250316-0001",
    "assets": {
      "screenshot":           "/assets/restaurant_modern/v1/screenshot/main.png",
      "hero_image":           "/assets/restaurant_modern/v1/hero/main.webp",
      "preview_images":       ["/assets/.../preview/01.webp"],
      "thumbnail":            "/assets/.../thumbnail/main.webp",
      "og_image":             "/assets/.../og/main.png",
      "demo_mockup":          ["/assets/.../mockup/desktop.webp"],
      "social_cover":         "/assets/.../social/main.png",
      "promo_video_vertical": "/assets/.../video/vertical.mp4"
    },
    "manifest_path": "/assets/restaurant_modern/v1/manifest.json",
    "total_cost":    3.85,
    "tools_used":    ["flux_2_pro", "ideogram_v3", "kling_ai_2_1"],
    "skipped_assets": []
  }
}
```

---

## ٢٧. اتفاقية مسارات الملفات

```
/assets/
  {theme_slug}/
    {version}/
      candidates/   ← 7 أيام
        {asset_type}/{candidate_id}.{ext}
      approved/     ← دائم (الإصدار الحالي)
        screenshot/main.png
        hero/main.webp
        preview/01.webp 02.webp 03.webp
        thumbnail/main.webp
        og/main.png
        mockup/desktop.webp mobile.webp
        social/main.png
        video/vertical.mp4 vertical_poster.webp
      archived/     ← 90 يوم
      manifest.json
```

```python
ASSET_SUBFOLDERS = {
    "screenshot": "screenshot", "hero_image": "hero",
    "preview_images": "preview", "thumbnail": "thumbnail",
    "og_image": "og", "demo_mockup": "mockup",
    "social_cover": "social", "banner": "banner",
    "promo_video_vertical": "video", "promo_video_horizontal": "video",
    "feature_graphics": "features", "rtl_preview": "rtl",
    "mobile_preview": "mobile",
}

def build_published_path(slug: str, version: str, asset_type: str, fmt: str) -> str:
    base     = os.environ["ASSETS_BASE_PATH"]
    subfolder = ASSET_SUBFOLDERS.get(asset_type, asset_type)
    return os.path.join(base, slug, version, "approved", subfolder, f"main.{fmt}")
```

---

## ٢٨. أمان وخصوصية البيانات

```python
VISUAL_SECURITY_REQUIREMENTS = [
    "API keys في .env — لا في الكود",
    "Negative Prompts: لا وجوه، لا watermarks، لا علامات منافسين",
    "ARABIC_TEXT_POLICY: النص من theme_name_ar فقط، Ideogram فقط",
    "Cost Budget يُفحص قبل كل توليد",
    "POST_PROCESSOR يُزيل metadata الحساسة",
    "Checksum بعد كل نسخ",
    "Candidates بعد 7 أيام → حذف",
    "لا بيانات عملاء في أي Prompt",
    "Review Gate إلزامي — لا أصل بدون موافقة",
]
```

---

## ٢٩. Error Codes Catalog

```python
VISUAL_ERROR_CODES = {
    "VIS_CONTRACT_MISSING_REQUIRED":       "حقل إلزامي غائب",
    "VIS_BUDGET_HARD_LIMIT":               "تجاوز الحد المطلق",
    "VIS_GENERATION_FAILED":               "فشل + Retry + Fallback",
    "VIS_REQUIRED_ASSET_FAILED":           "أصل إلزامي فشل — يوقف",
    "VIS_REQUIRED_ASSET_NO_QUALITY_PASS":  "لا مرشح ناجح لأصل إلزامي",
    "VIS_RATE_LIMIT":                      "تجاوز حد API",
    "VIS_MODERATION_FAILURE":              "Prompt مرفوض",
    "VIS_ASSET_SKIPPED":                   "أصل اختياري تخطّى",
    "VIS_QUALITY_FAILED":                  "مرشح لم يجتز الفحص",
    "VIS_REVIEW_TIMEOUT":                  "انتهت مهلة المراجعة",
    "VIS_MAX_REGENERATION":                "تجاوز حد إعادة الإنتاج",
    "VIS_POST_PROCESS_FAILED":             "فشل المعالجة اللاحقة",
    "VIS_PUBLISH_INTEGRITY_FAILED":        "checksum غير متطابق",
    "VIS_MANIFEST_BUILD_FAILED":           "فشل بناء Manifest",
    "VIS_ASSETS_READY_EMIT_FAILED":        "فشل إطلاق الحدث",
}
```

---

## ٣٠. بنية الـ State

```python
class VisualState(TypedDict):
    idempotency_key:       str
    batch_id:              str
    theme_slug:            str
    theme_version:         str
    theme_contract:        Dict
    asset_types:           List[str]
    expected_cost:         float
    prompt_specs:          List[PromptSpec]
    prompt_hashes:         Dict[str, str]
    candidates:            List[AssetCandidate]
    candidates_map:        Dict[str, AssetCandidate]
    total_cost:            float
    selected_candidates:   List[AssetCandidate]
    approved_candidates:   List[AssetCandidate]
    approved_asset_types:  Optional[List[str]]
    regeneration_count:    int
    regeneration_feedback: Optional[str]
    skipped_assets:        List[str]
    processed_assets:      List[dict]
    produced_assets:       List[ProducedAsset]
    manifest:              Optional[AssetManifest]
    review_sent_at:        Optional[str]
    review_decision:       Optional[str]
    approval_notes:        Optional[str]
    status:                str
    error_code:            Optional[str]
    logs:                  List[str]
```

---

## ٣١. البيئة المحلية ومتغيرات البيئة

```env
REPLICATE_API_TOKEN=...
IDEOGRAM_API_KEY=...
KLING_API_KEY=...
KLING_API_SECRET=...
PIKA_API_KEY=...

ASSETS_BASE_PATH=/var/assets
ASSETS_BASE_URL=https://ar-themes.com/assets

RESEND_API_KEY=...
STORE_EMAIL_FROM=قوالب عربية <hello@ar-themes.com>
OWNER_EMAIL=owner@ar-themes.com
REDIS_URL=redis://localhost:6379

COST_BUDGET_REQUIRED=2.50
COST_BUDGET_FULL=5.00
COST_BUDGET_HARD_LIMIT=8.00
MAX_REGENERATION_ATTEMPTS=3
REVIEW_TIMEOUT_HOURS=48
REVIEW_FINAL_TIMEOUT_HOURS=72

CANDIDATES_RETENTION_DAYS=7
REJECTED_RETENTION_DAYS=30
SUPERSEDED_RETENTION_DAYS=90

PROMPT_BUILDER_VERSION=1.0
VIDEO_MODE=image_to_video
VIDEO_AUDIO=none

LOG_LEVEL=INFO
```

---

## ٣٢. دستور الوكيل

```markdown
# دستور وكيل الإنتاج البصري v2

## الهوية
أنا مصنع الهوية البصرية — كل أصل يحمل روح القالب من عقده.

## القواعد المطلقة
١. THEME_CONTRACT مصدر كل Prompt — لا صورة من فراغ
٢. Negative Prompts إلزامية في كل توليد
٣. QUALITY_GATE يفحص كل مرشح قبل الاختيار
٤. الفيديو v1: image-to-video من hero_image — صامت
٥. Review Gate إلزامي — لا أصل بدون موافقة
٦. POST_PROCESSOR إلزامي — WebP + checksum
٧. Asset Manifest محفوظ لكل إصدار
٨. Retry قبل Fallback
٩. Hard Limit لا يُتجاوز
١٠. إعادة الإنتاج ≤ 3 مرات

## ما أُجيده
- Prompts 5 طبقات + Negative + deterministic seed
- إنتاج متوازٍ من 4 أدوات
- Retry ذكي + Fallback آمن
- Versioning ذكي: فقط المتأثر يُعاد

## ما أتجنبه
- التوليد بلا Negative Prompts
- إرسال أصول بلا مراجعة
- text-to-video في v1
- إعادة كل الأصول لكل تحديث
```

---

## ٣٣. قائمة التحقق النهائية

```
□ THEME_APPROVED مُستقبَل
□ idempotency_key — لا دفعة مكررة
□ CONTRACT_PARSER: حقول إلزامية موجودة أو Defaults مُطبَّقة
□ domain غير معروف → business_corporate
□ BUDGET_CALCULATOR: التكلفة < Hard Limit
□ PROMPT_BUILDER: 5 طبقات + Negative + deterministic seed
□ Arabic text: Ideogram فقط، theme_name_ar فقط، أصول مسموحة فقط
□ Video: image-to-video من hero_image، صامت، 24fps
□ MULTI_GENERATOR: توليد متوازٍ
□ خطأ مؤقت → RETRY بـ backoff
□ moderation → clean prompt + retry مرة واحدة
□ tool outage → FALLBACK فوراً
□ QUALITY_GATE: أبعاد + حجم لكل مرشح
□ مرشح راسب لا يصل لـ Review Gate
□ ASSET_SELECTOR: Ideogram لـ text, Flux للواقعية, LLM للباقي
□ REVIEW_GATE: إشعار مع روابط
□ Timeout 48h: تذكير
□ Timeout 72h: تجميد Batch
□ approved → POST_PROCESSOR: WebP + ضغط + checksum + poster
□ ASSET_PUBLISHER: نسخ + checksum check
□ BATCH_RECORDER: تكلفة + أدوات + قرار
□ MANIFEST_BUILDER: manifest.json
□ PARTIAL_APPROVAL: تحديد ما يُطلَق
□ THEME_ASSETS_READY بالصيغة الموحدة
□ Retention: candidates 7 أيام، rejected 30 يوماً
```
