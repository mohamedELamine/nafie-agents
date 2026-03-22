# وكيل توليد قوالب WordPress العربية
## وثيقة المواصفات الشاملة — Cluster-Based Product-Ready Theme Factory

---

## فهرس المحتويات

1. نظرة عامة ومبادئ جوهرية
2. كيف يعمل spec-kit فعلياً
3. مدخلات واجهة المستخدم — UI Schema الكاملة
4. معمارية الوكيل — LangGraph + خريطة Nodes
5. تفصيل كل Node
6. Human-in-the-Loop — نظام التوقف الذكي
7. بنية الـ State الكاملة
8. مواصفات WordPress + WooCommerce + COD
9. مخرجات الوكيل — قالب جاهز للبيع
10. بوابات الجودة
11. الذاكرة والحالة
12. معالجة الأخطاء والفشل
13. البيئة المحلية
14. نظام الإصدارات
15. الذاكرة بين المشاريع
16. دستور الوكيل
17. قائمة التحقق النهائية
18. التشغيل والمراقبة — ops-checklist + LangSmith
19. وضع التحديث — Update Mode

---

## ١. نظرة عامة ومبادئ جوهرية

### الهدف

بناء وكيل ذكاء اصطناعي محلي يأخذ مدخلات المستخدم عبر واجهة رسومية وينتج قالب WordPress عربي احترافي Block Theme (FSE)، متعدد الأغراض، شامل WooCommerce، جاهزاً للنشر وللبيع كمنتج علامة تجارية، مع Demo Content واسع + Demo Images + Brand Assets + توثيق كامل + اختبارات آلية + مراقبة Observability.

### المنظومة الكاملة

```
واجهة المستخدم (FastAPI + HTML)
        ↓
LangGraph (المنسق الرئيسي)
        ↓
┌─────────────────────────────────────────────────────────────┐
│  spec-kit + Claude Code     ← التخطيط (Spec/Plan/Tasks)     │
│  THEME_CONTRACT_GEN         ← عقد مشترك بين النموذجين       │
│  Gemini (Frontend)          ← Templates/Parts/Patterns/CSS  │
│  GLM (Backend)              ← PHP + Woo/COD + Settings       │
│  Claude API                 ← مراجعة RTL/A11y/UX/Logic       │
│  CodeRabbit API             ← مراجعة معايير/WPCS              │
│  Image Model (Gemini)       ← توليد صور Demo                  │
│  TestSprite (MCP)           ← اختبار UI/RTL/Woo/COD           │
│  LangSmith                  ← Traces/Observability            │
└─────────────────────────────────────────────────────────────┘
        ↓
قالب جاهز للبيع (ZIP + Demos + Docs + Assets + Reports)
```

### لماذا نموذجان مختلفان؟

الفصل بين Gemini وGLM ليس تحكماً — هو يعكس طبيعة العمل الفعلية:

| البُعد | Gemini — Frontend | GLM — Backend |
|--------|-------------------|---------------|
| الملفات | HTML/Blocks/Patterns/CSS/JS | PHP/functions/inc/WooCommerce |
| المنطق | بنية بصرية + RTL + Block markup | server-side logic + قواعد بيانات |
| الخطر | تقطع Block markup / RTL خاطئ | SQL injection / Nonce مفقود |
| الأداء | بنية الـ DOM + حجم CSS | PHP execution + DB queries |

**الشرط الجوهري:** كلا النموذجين ملزمان بـ **THEME_CONTRACT** قبل البدء.

### المبادئ غير القابلة للتفاوض

- **RTL أولاً دائماً** — كل قرار تصميمي يُختبر في RTL أولاً
- **العقد يسبق الكود** — THEME_CONTRACT يُنشأ قبل أي توليد
- **الكود خادم للمواصفات** — لا تغيير بنيوي إلا عند فشل اختبار أو بوابة جودة
- **الفشل الصامت ممنوع** — أي خطأ يُوثَّق ويُبلَّغ
- **لا توليد من قوالب تجارية جاهزة** — Scaffold داخلي فقط
- **الأمان لا تفاوض فيه** — أي XSS/CSRF يوقف التنفيذ فوراً
- **لا هلوسة مقبولة** — FUNCTION_WHITELIST_GATE + RAG إلزاميان
- **جاهزية البيع** — brand_ready = Demo + Assets + Docs + TestSprite إلزامي
- **WooCommerce + COD** مدعومة بحماية Abuse/Spam إلزامية
- **المراقبة مستمرة** — LangSmith trace لكل Run بلا استثناء

---

## ٢. كيف يعمل spec-kit فعلياً

spec-kit ليس API يُستدعى، بل CLI Tool يُثبَّت مرة واحدة:

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
specify init <project-name> --ai claude
# أو بدون Git:
specify init <project-name> --ai claude --no-git
```

### Slash Commands يُنفّذها Claude Code

| الأمر | الوظيفة | المخرج |
|-------|----------|--------|
| `/speckit.constitution` | مبادئ المشروع | `.specify/memory/constitution.md` |
| `/speckit.specify` | تعريف ما نريد بناءه | `spec.md` |
| `/speckit.clarify` | توضيح المتطلبات | تحديث `spec.md` |
| `/speckit.plan` | الخطة التقنية | `plan.md` |
| `/speckit.analyze` | تحليل تناسق الـ artifacts | تقرير نقص |
| `/speckit.tasks` | تفكيك المهام | `tasks.md` |
| `/speckit.implement` | **لا نستخدمه** — التنفيذ عبر GLM/Gemini | — |

### كيف يدمج LangGraph مع spec-kit

```python
import subprocess
from pathlib import Path

def run_speckit_command(command: str, prompt: str, project_path: str) -> str:
    result = subprocess.run(
        ["claude", "--print", f"{command} {prompt}"],
        cwd=project_path, capture_output=True, text=True
    )
    return result.stdout

def detect_speckit_feature_path(project_path: str) -> str:
    root = Path(project_path)
    candidates = []
    for base in [
        root / ".specify" / "specs",
        root / "specs",
        root / ".specify" / "specifications"
    ]:
        if base.exists():
            for d in base.glob("*"):
                if d.is_dir() and (d / "spec.md").exists():
                    candidates.append(d)
    if not candidates:
        raise RuntimeError("speckit specs folder not found")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return str(candidates[0])

def read_speckit_output(project_path: str) -> dict:
    feature_path = detect_speckit_feature_path(project_path)
    return {
        "feature_path": feature_path,
        "spec":  read_file(f"{feature_path}/spec.md"),
        "plan":  read_file(f"{feature_path}/plan.md"),
        "tasks": read_file(f"{feature_path}/tasks.md"),
    }
```

**لماذا لا نستخدم `/speckit.implement`؟**
لأنه يتجاوز حلقة المراجعة الكاملة: `Gemini/GLM → SELF_CRITIQUE → PHPStan → FUNCTION_WHITELIST → Claude → CodeRabbit → TestSprite → OPS_GATES`. نستخدم spec-kit للتخطيط فقط.

---

## ٣. مدخلات واجهة المستخدم — UI Schema الكاملة

### ٣.١ هوية القالب

```json
{
  "theme_name_ar": "اسم القالب بالعربية",
  "theme_name_en": "Theme Name in English",
  "theme_slug":    "auto — kebab-case، max 30، unique",
  "text_domain":   "auto = theme_slug",
  "author_name":   "Theme Author",
  "author_uri":    "https://example.com",
  "theme_uri":     "https://example.com/theme",
  "version":       "1.0.0"
}
```

ملف يُنشأ تلقائياً: `/project-state/identity.json`

### ٣.٢ المجال التجاري — Domains + Clusters

**Cluster** = عائلة قوالب | **Domain** = قالب مستقل داخل Cluster

| # | Domain | Cluster | WooCommerce |
|---|--------|---------|-------------|
| 1 | Fashion Store | Commerce | ✅ إلزامي |
| 2 | Perfume & Luxury | Commerce | ✅ إلزامي |
| 3 | Electronics | Commerce | ✅ إلزامي |
| 4 | Furniture & Home | Commerce | ✅ إلزامي |
| 5 | Beauty & Cosmetics | Commerce | ✅ إلزامي |
| 6 | Restaurant | Food & Hospitality | اختياري |
| 7 | Cafe | Food & Hospitality | اختياري |
| 8 | Hotel / Resort | Food & Hospitality | ❌ |
| 9 | Clinic / Medical | Health & Fitness | ❌ |
| 10 | Dental | Health & Fitness | ❌ |
| 11 | Gym / Fitness | Health & Fitness | اختياري |
| 12 | Corporate / B2B | Business & Real Estate | ❌ |
| 13 | Real Estate | Business & Real Estate | ❌ |
| 14 | Education / Courses | Education & Services | اختياري |
| 15 | Digital Agency | Education & Services | ❌ |

```json
{ "cluster": "commerce", "domain": "perfume_luxury" }
```

**قاعدة ثابتة:** Commerce domains → WooCommerce إلزامي تلقائياً.

### ٣.٣ Multi-purpose + WooCommerce

```json
{
  "multipurpose_mode": true,
  "woocommerce": {
    "enabled": true, "catalog_pages": true, "checkout_rtl": true
  }
}
```

### ٣.٤ توجه التصميم

```json
{
  "design_direction": {
    "type": "select", "default": "modern",
    "options": [
      {"value": "luxury",    "label": "فاخر — أسود وذهبي، خطوط رفيعة"},
      {"value": "modern",    "label": "عصري — ألوان جريئة، فراغات واسعة"},
      {"value": "minimal",   "label": "بسيط — أبيض سائد، تايبوغرافي قوي"},
      {"value": "warm",      "label": "دافئ — ألوان ترابية، طابع ودي"},
      {"value": "corporate", "label": "مؤسسي — كحلي ورمادي، احترافية عالية"}
    ]
  }
}
```

| التوجه | Primary | Accent | Radius | Font Weight |
|--------|---------|--------|--------|-------------|
| luxury | #0A0A0A | #C9A84C | 0px | 300 |
| modern | #1A1A2E | #E94560 | 8px | 500 |
| minimal | #111111 | #2563EB | 4px | 400 |
| warm | #3D2B1F | #E07B39 | 12px | 400 |
| corporate | #0F1E3C | #3B82F6 | 6px | 500 |

### ٣.٥ الخطوط

```json
{
  "fonts": {
    "heading": {"options": ["Cairo","Tajawal","Almarai","Noto Kufi Arabic","IBM Plex Sans Arabic","Readex Pro"]},
    "body":    {"options": ["Cairo","Tajawal","Almarai","Noto Kufi Arabic","IBM Plex Sans Arabic","Readex Pro"]},
    "loading_policy": {"default": "swap", "options": ["preload","swap","optional"]},
    "max_weights": 3
  }
}
```

### ٣.٦ لوحة الألوان

```json
{
  "palette": {
    "colors": {
      "primary": "#1A1A2E", "primary_hover": "#2D2D4E",
      "accent": "#E94560",  "accent_hover": "#C73652",
      "background": "#FFFFFF", "background_alt": "#F8F9FA",
      "surface": "#F1F3F5",    "text_primary": "#1A1A1A",
      "text_secondary": "#6B7280", "border": "#E5E7EB",
      "success": "#10B981"
    },
    "validation": "WCAG AA — contrast ≥ 4.5 إلزامي على كل نص"
  }
}
```

### ٣.٧ اللغة والاتجاه

```json
{
  "language": {
    "default": "ar_only",
    "options": [
      {"value": "ar_only",   "label": "عربي فقط — dir=rtl كامل"},
      {"value": "bilingual", "label": "ثنائي اللغة",
       "plugin": {"options": ["Polylang","WPML","TranslatePress"]}}
    ]
  }
}
```

### ٣.٨ نوع الموقع

```json
{
  "site_type": {
    "default": "full_site",
    "options": [
      {"value": "landing",       "label": "Landing Page — صفحة واحدة"},
      {"value": "full_site",     "label": "موقع كامل — صفحات متعددة"},
      {"value": "full_with_woo", "label": "موقع كامل + متجر WooCommerce"},
      {"value": "woo_only",      "label": "متجر WooCommerce فقط"}
    ]
  }
}
```

### ٣.٩ أقسام الصفحة الرئيسية

```json
{
  "home_sections": {
    "type": "multi_select_ordered", "required": ["hero"], "max": 10,
    "options": [
      {"value": "hero",            "label": "Hero — قسم الترحيب الرئيسي (إلزامي)"},
      {"value": "features",        "label": "المميزات / الخدمات"},
      {"value": "about_preview",   "label": "نبذة عن الشركة"},
      {"value": "products_grid",   "label": "شبكة المنتجات (Woo)"},
      {"value": "categories_grid", "label": "شبكة الفئات"},
      {"value": "testimonials",    "label": "آراء العملاء"},
      {"value": "stats_bar",       "label": "شريط الأرقام والإحصاءات"},
      {"value": "portfolio",       "label": "معرض الأعمال"},
      {"value": "team",            "label": "فريق العمل"},
      {"value": "pricing",         "label": "جدول الأسعار"},
      {"value": "blog_preview",    "label": "آخر المقالات"},
      {"value": "faq",             "label": "الأسئلة الشائعة"},
      {"value": "cta_banner",      "label": "بانر دعوة للتصرف"},
      {"value": "partners",        "label": "شركاء / عملاء"},
      {"value": "newsletter",      "label": "الاشتراك في النشرة البريدية"}
    ]
  }
}
```

### ٣.١٠ الهدف التجاري و CTA

```json
{
  "primary_cta": {
    "default": "purchase",
    "options": [
      {"value": "purchase",  "label": "شراء — يوجه لصفحة المتجر"},
      {"value": "booking",   "label": "حجز — نموذج حجز أو موعد"},
      {"value": "quote",     "label": "عرض سعر — نموذج طلب"},
      {"value": "whatsapp",  "label": "واتساب — فتح محادثة مباشرة"},
      {"value": "subscribe", "label": "اشتراك — قائمة بريدية"},
      {"value": "download",  "label": "تحميل — ملف أو تطبيق"}
    ]
  },
  "whatsapp_float": {
    "enabled": true,
    "number":  "+966XXXXXXXXX",
    "message": "مرحباً، أريد الاستفسار عن..."
  }
}
```

### ٣.١١ بوابات الدفع

```json
{
  "payment_gateways": {
    "type": "multi_select",
    "options": [
      {"value": "mada"},  {"value": "apple_pay"}, {"value": "google_pay"},
      {"value": "tabby"}, {"value": "tamara"},    {"value": "paytabs"},
      {"value": "hyperpay"}, {"value": "stripe"}, {"value": "paypal"},
      {"value": "cod", "label": "الدفع عند الاستلام (COD)"}
    ]
  }
}
```

### ٣.١٢ الهوية البصرية

```json
{
  "brand": {
    "logo":    {"format": "SVG مُفضَّل / PNG شفاف", "fallback": "placeholder بالـ theme_name_ar"},
    "favicon": {"format": "ICO / PNG 32×32",         "fallback": "يُولَّد من الحرف الأول للاسم"},
    "brand_colors_source": {"options": ["from_palette","from_logo"]}
  }
}
```

### ٣.١٣ الأداء والتوافق

```json
{
  "performance": {
    "target_lcp_ms": 2500, "target_cls": 0.1,
    "lazy_load_images": true, "webp_conversion": true,
    "browsers": {"chrome": "آخر إصداران", "safari": "آخر إصداران", "firefox": "آخر إصداران", "edge": "آخر إصداران"},
    "mobile_breakpoints": {"sm": "375px", "md": "768px", "lg": "1024px", "xl": "1280px"}
  }
}
```

### ٣.١٤ مستوى التخصيص

```json
{
  "customization_level": {
    "default": "standard",
    "options": [
      {"value": "minimal",  "label": "أساسي — ألوان وخطوط فقط"},
      {"value": "standard", "label": "قياسي — ألوان + خطوط + تخطيطات"},
      {"value": "full",     "label": "كامل — Site Editor + Custom Patterns + Settings API"}
    ]
  }
}
```

### ٣.١٥ سياسة JavaScript + حقل حر

```json
{
  "js_policy": {
    "no_jquery": true, "vanilla_only": true,
    "defer_all": true, "no_render_blocking": true
  },
  "custom_instructions": {
    "type": "textarea", "max_chars": 1000,
    "placeholder": "أي تعليمات خاصة أو متطلبات غير مُغطاة أعلاه..."
  }
}
```

### ٣.١٦ Experience Mode

```json
{
  "experience_mode": {
    "default": "feature_rich",
    "options": [
      {"value": "minimal",      "label": "A) Minimal — أداء عالي جداً (JS ≤ 10KB)"},
      {"value": "feature_rich", "label": "B) Feature-rich — تأثير بصري قوي (JS ≤ 35KB)"}
    ]
  }
}
```

| البُعد | Minimal | Feature-rich |
|--------|---------|--------------|
| JS budget | ≤ 10KB | ≤ 35KB |
| Animations | none | tasteful, performance-safe |
| Intersection Observer | ❌ | ✅ |
| Parallax | ❌ | ✅ محدود (max 1 element) |
| prefers-reduced-motion | ✅ دائماً | ✅ دائماً |
| css_transition_max | — | 400ms |

### ٣.١٧ COD Quick Order

```json
{
  "cod": {
    "enabled": true,
    "quick_order_form": {
      "enabled": true, "placement": "product_page",
      "style": "auto_by_experience_mode",
      "fields": ["name","phone","city","address","quantity","notes"],
      "customizable": true
    },
    "abuse_protection": {
      "rate_limit": "max 3 requests / IP / 10 minutes",
      "honeypot": true, "nonce": true
    }
  }
}
```

### ٣.١٨ وضع السوق

```json
{
  "market_mode": {
    "default": "brand_ready",
    "options": [
      {"value": "brand_ready", "label": "جاهز للبيع — Demo + Assets + Docs + TestSprite"},
      {"value": "dev_only",    "label": "للتطوير فقط — بدون Demo/Assets"}
    ]
  }
}
```

### ٣.١٩ Style Variations + Demo Content + Demo Images + Brand Assets

```json
{
  "style_variations": {"enabled": true, "variations": ["light","dark","seasonal"]},
  "demo_content": {"enabled": true, "content_level": "full"},
  "demo_images": {"enabled": true, "source": "mixed", "max_kb": 200},
  "brand_assets": {"enabled": true, "generate_mockup": true, "social_preview": true}
}
```

### ٣.٢٠ TestSprite

```json
{
  "testsprite": {
    "enabled": true, "mode": "smart",
    "test_scope": ["ui_interactions","rtl_behavior","woocommerce_flow","forms","cod_flow","print"],
    "auto_fix": true, "max_fix_cycles": 2
  }
}
```

### ٣.٢١ LangSmith Observability

```json
{
  "langsmith": {
    "enabled": true,
    "project_name": "arabic-theme-factory",
    "trace_level": "full",
    "capture_artifacts": ["prompts","tool_calls","metrics","gate_results"]
  }
}
```


---

## ٤. معمارية الوكيل — LangGraph + خريطة Nodes

```
INPUT (واجهة المستخدم)
        ↓
 1. NORMALIZER
        ↓
 2. ENV_CHECK
        ↓
 3. LANGSMITH_TRACE_INIT
        ↓
 4. MEMORY_LOAD
        ↓
 5. CLUSTER_DOMAIN_SELECTOR
        ↓
 5.1 THEME_CONTRACT_GEN          ← ينشئ العقد المشترك بين Gemini وGLM
     [CRITIC_AGENT ← هل العقد يُغطي كل نقاط التلاقي؟]
        ↓
 6. SEO_SCAFFOLD                 ← هيكل Arabic SEO
        ↓
 7. WP_SCAFFOLD
        ↓
 8. THEME_PLAN (spec-kit via Claude Code)
        ↓
 8.1 SPECKIT_PATH_DETECTOR
        ↓
 8.5 RISK_ASSESSOR
        ↓ [risk ≥ 0.35]
 8.6 HUMAN_CHECKPOINT_1
     [CRITIC_AGENT ← هل الخطة تقف على افتراضات خاطئة؟]
        ↓
 9. TOKEN_GEN
        ↓
 9.1 STYLE_VARIATION_ENGINE
        ↓
 9.2 EXPERIENCE_MODE_DECIDER
     [ASSUMPTION_CHECKER + DECISION_LOG]
        ↓
10. FILE_LIST (per Domain)
        ↓
[العينة التمثيلية: theme.json + header/footer + home + product template]
        ↓
11a-c. CODE_GEN_SAMPLE
        ↓
11d. HUMAN_CHECKPOINT_2
        ↓
11e. APPLY_HUMAN_FEEDBACK
        ↓
[حلقة باقي الملفات]
        ↓
12. ROUTE_FILE               ← يوجّه كل ملف لـ Gemini أو GLM أو كليهما
     [ASSUMPTION_CHECKER قبل كل Node رئيسية]
        ↓
13. GEMINI_CODEGEN           ← Frontend: HTML/Blocks/CSS/JS
    أو
    GLM_CODEGEN              ← Backend: PHP/functions/inc/WooCommerce
    [UNCERTAINTY_TRACKER ← النموذج يُعلن ثقته + ما يجهله]
        ↓
13.5 OUTPUT_PARSER          ← ✦ يُنظّف خرج النموذج — قبل أي Gate
        ↓
14. SELF_CRITIQUE            ← النموذج يراجع نفسه أولاً
        ↓
15. FUNCTION_WHITELIST_GATE  ← يمنع الهلوسة في WordPress/Woo API
        ↓
16. WP_COMPLIANCE_SCAN
        ↓
17. PHPSTAN_SCAN             ← أخطاء PHP الصامتة
        ↓
18. SECURITY_SCAN
        ↓
19. CLAUDE_REVIEW            ← RTL/A11y/UX/Logic
        ↓
20. CODERABBIT_REVIEW        ← WPCS/Standards
        ↓
    يحتاج fix? نعم → 21. FIX (patch-based)
                         ↓
                    22. SEMANTIC_DIFF  ← يمنع regression
                         ↓ [إن نجح]
                    → [13.5→14→15→16→17→18→19→20]
    لا → ملف تالٍ؟ نعم → 12
                    لا  ↓
23. COD_MODULE_BUILDER
        ↓
23.1 COD_SECURITY_GATE
        ↓
24. WOO_EMAIL_RTL            ← إيميلات WooCommerce بالعربية
        ↓
25. ARABIC_NUMERICS_GATE     ← التحقق من الأرقام والأسعار
        ↓
26. DEMO_CONTENT_GENERATOR
        ↓
27. VISUAL_PROFILE_SELECTOR
        ↓
28. DEMO_IMAGE_ENGINE
        ↓
29. BRAND_ASSET_GENERATOR
        ↓
30. BUILD_VALIDATE
        ↓
30.1 CHILD_THEME_GATE        ← جاهزية التوريث
        ↓
30.2 HUMAN_CHECKPOINT_3
        ↓
31. WP_INSTALL_SMOKE_TEST
        ↓
32. TESTSPRITE_SCAN
        ↓
    مشاكل؟ نعم → 32.1 TESTSPRITE_FIX → 12 → ... → TESTSPRITE_SCAN
    لا ↓
33. OPS_GATES
        ↓
33.5 DELIVERY_POLICY        ← ✦ يحسم: نُسلّم أم نوقف؟
        ↓
34. PACKAGE
        ↓
34.1 QUALITY_BADGE_GEN      ← ✦ شهادة الجودة المرئية
        ↓
35. MEMORY_SAVE
        ↓
36. LANGSMITH_TRACE_CLOSE
        ↓
OUTPUT ✓
```


---

## ٥. تفصيل كل Node

### Node 1: NORMALIZER

```python
"""
المدخل:  user_input (خام من الواجهة)
المخرج:  normalized_input + identity.json + theme_constitution.md

١. تحقق من الحقول الإلزامية (theme_name_ar, cluster, domain)
٢. توليد theme_slug: kebab-case max 30 + ensure_unique()
٣. إنشاء identity.json في /project-state/
٤. توليد build_version = f"{date}-{sequence}"
٥. قراءة: cluster/domain + experience_mode + cod + market_mode + langsmith
٦. إنشاء theme_constitution.md (دستور + تعليمات خاصة)
٧. استنتاج woocommerce_enabled تلقائياً إن كان domain في Commerce Cluster
"""
```

### Node 2: ENV_CHECK

```python
"""
□ Python 3.11+ / uv / specify-cli / Claude Code CLI
□ PHP 8.1+ / PHPStan / WordPress محلي / WooCommerce (إلزامي لـ Commerce domains)
□ صلاحيات كتابة OUTPUT_PATH
□ APIs: Claude + GLM + Gemini (Frontend) + CodeRabbit
□ RAG index: موجود ومحدَّث (wordpress_functions + woo_hooks + block_api)
□ Gemini Image API   (إن demo_images.enabled)
□ TestSprite API key (إن testsprite.enabled)
□ LangSmith API key  (إن langsmith.enabled)
Git: اختياري — specify init --no-git أولاً
"""
```

### Node 3: LANGSMITH_TRACE_INIT

```python
"""
- فتح Trace جديد في LangSmith:
  run_id, project_name, theme_slug, cluster, domain, experience_mode
- كل Node يفتح span داخل الـ Trace:
  span_name = node_name
  inputs    = state snapshot
  outputs   = node result + metrics
"""
```

### Node 4: MEMORY_LOAD

```python
"""
- تحميل الدروس المستفادة من المشاريع السابقة
- تصفيتها حسب: cluster + domain + experience_mode
- حقنها في State.lessons_learned
- تحميل similar_projects للمقارنة
- تحميل Golden Snapshots للـ domain إن وُجدت
"""
```

### Node 5: CLUSTER_DOMAIN_SELECTOR

```python
"""
يحمّل:
  /profiles/clusters/{cluster}.json   → ألوان + خطوط + توجه تصميم افتراضي
  /profiles/domains/{domain}.json     → templates + patterns + demo profile

يُثبّت في State:
  templates_required / patterns_required / demo_content_profile
  visual_profile_key / woocommerce_required / experience_mode_override
"""
```

#### هيكل Cluster Profiles — 5 ملفات

```json
// /profiles/clusters/commerce.json
{
  "cluster": "commerce", "woocommerce_required": true,
  "default_experience_mode": "feature_rich",
  "default_palette": {"primary":"#1A1A2E","accent":"#E94560","background":"#FFFFFF","text":"#1A1A1A"},
  "default_fonts": {"heading":"Almarai","body":"Cairo"},
  "shared_templates": ["index","archive","search","404","page","single"],
  "shared_patterns":  ["header-cta","footer-links","newsletter-signup"]
}
```

```json
// /profiles/clusters/food_hospitality.json
{
  "cluster": "food_hospitality", "woocommerce_required": false,
  "default_experience_mode": "feature_rich",
  "default_palette": {"primary":"#2D3A1E","accent":"#8B7355","background":"#FFFDF7","text":"#1C1C1C"},
  "default_fonts": {"heading":"Tajawal","body":"Cairo"},
  "shared_templates": ["index","page","404"],
  "shared_patterns": ["footer-simple","contact-map"]
}
```

```json
// /profiles/clusters/health_fitness.json
{
  "cluster": "health_fitness", "woocommerce_required": false,
  "default_experience_mode": "minimal",
  "default_palette": {"primary":"#1D4ED8","accent":"#06B6D4","background":"#F8FAFC","text":"#0F172A"},
  "default_fonts": {"heading":"IBM Plex Sans Arabic","body":"Cairo"},
  "shared_templates": ["index","page","404"],
  "shared_patterns": ["trust-badges","team-grid","appointment-cta"]
}
```

```json
// /profiles/clusters/business_real_estate.json
{
  "cluster": "business_real_estate", "woocommerce_required": false,
  "default_experience_mode": "minimal",
  "default_palette": {"primary":"#0F1E3C","accent":"#3B82F6","background":"#FFFFFF","text":"#1A1A1A"},
  "default_fonts": {"heading":"Readex Pro","body":"Cairo"},
  "shared_templates": ["index","page","404"],
  "shared_patterns": ["stats-bar","client-logos","footer-corporate"]
}
```

```json
// /profiles/clusters/education_services.json
{
  "cluster": "education_services", "woocommerce_required": false,
  "default_experience_mode": "feature_rich",
  "default_palette": {"primary":"#7C3AED","accent":"#F59E0B","background":"#FAF5FF","text":"#1A1A1A"},
  "default_fonts": {"heading":"Almarai","body":"Tajawal"},
  "shared_templates": ["index","page","404"],
  "shared_patterns": ["faq-accordion","instructor-card","cta-enroll"]
}
```

#### Domain Profiles — 15 ملف

```json
// commerce domains
{"domain":"fashion_store","cluster":"commerce","visual_profile_key":"fashion",
 "templates_required":["home","shop","single-product","cart","checkout","my-account","archive","search","404"],
 "patterns_required":["hero-fashion","lookbook-grid","featured-collection","product-card","products-grid","size-guide-cta","testimonials","instagram-feed-placeholder","newsletter-signup"],
 "woo_product_types":["simple","variable"],"woo_features":["product-gallery","variation-swatches","wishlist-cta"],
 "experience_mode_override":null,"cod_relevant":true,"seasonal_theme":"black_gold"}

{"domain":"perfume_luxury","cluster":"commerce","visual_profile_key":"luxury_store",
 "templates_required":["home","shop","single-product","cart","checkout","my-account","archive","search","404"],
 "patterns_required":["hero-luxury","fragrance-story","ingredient-spotlight","product-card","products-grid","gift-wrapping-cta","testimonials","loyalty-banner","newsletter-signup"],
 "woo_product_types":["simple","grouped"],"woo_features":["product-gallery","upsells","gift-note"],
 "experience_mode_override":"feature_rich","cod_relevant":true,"seasonal_theme":"black_gold"}

{"domain":"electronics","cluster":"commerce","visual_profile_key":"tech_store",
 "templates_required":["home","shop","single-product","cart","checkout","my-account","archive","search","404","compare"],
 "patterns_required":["hero-tech","spec-table","brand-logos","product-card","products-grid","compare-cta","warranty-badge","installment-banner","newsletter-signup"],
 "woo_product_types":["simple","variable","external"],"woo_features":["product-gallery","compare","stock-badge","installment-tabby"],
 "experience_mode_override":null,"cod_relevant":true,"seasonal_theme":"navy_pro"}

{"domain":"furniture_home","cluster":"commerce","visual_profile_key":"home_decor",
 "templates_required":["home","shop","single-product","cart","checkout","my-account","archive","search","404"],
 "patterns_required":["hero-room-scene","room-category-grid","material-details","product-card","products-grid","delivery-promise","testimonials","ar-view-cta","newsletter-signup"],
 "woo_product_types":["simple","variable"],"woo_features":["product-gallery","dimensions-tab","room-visualizer-placeholder"],
 "experience_mode_override":null,"cod_relevant":true,"seasonal_theme":"olive_warm"}

{"domain":"beauty_cosmetics","cluster":"commerce","visual_profile_key":"beauty",
 "templates_required":["home","shop","single-product","cart","checkout","my-account","archive","search","404"],
 "patterns_required":["hero-beauty","skin-type-quiz-cta","before-after-grid","product-card","products-grid","ingredient-highlight","testimonials","routine-builder-cta","newsletter-signup"],
 "woo_product_types":["simple","variable","bundle"],"woo_features":["product-gallery","shade-swatches","sample-add"],
 "experience_mode_override":null,"cod_relevant":true,"seasonal_theme":"black_gold"}

// food & hospitality
{"domain":"restaurant","cluster":"food_hospitality","visual_profile_key":"restaurant",
 "templates_required":["home","menu","single","about","contact","404"],
 "patterns_required":["hero-food","menu-section","daily-specials","chef-story","gallery-food","reservation-form","testimonials","location-map","opening-hours"],
 "woo_product_types":[],"woo_features":[],"experience_mode_override":"feature_rich","cod_relevant":false,"seasonal_theme":"olive_warm"}

{"domain":"cafe","cluster":"food_hospitality","visual_profile_key":"cafe",
 "templates_required":["home","menu","about","contact","404"],
 "patterns_required":["hero-cafe","drinks-grid","signature-item","ambience-gallery","loyalty-app-cta","testimonials","location-map","opening-hours"],
 "woo_product_types":[],"woo_features":[],"experience_mode_override":"feature_rich","cod_relevant":false,"seasonal_theme":"olive_warm"}

{"domain":"hotel_resort","cluster":"food_hospitality","visual_profile_key":"hospitality",
 "templates_required":["home","rooms","single-room","about","amenities","contact","404"],
 "patterns_required":["hero-hotel","room-card","amenities-grid","booking-cta","gallery-masonry","testimonials","location-map","awards-strip"],
 "woo_product_types":[],"woo_features":[],"experience_mode_override":"feature_rich","cod_relevant":false,"seasonal_theme":"desert_gold"}

// health & fitness
{"domain":"clinic_medical","cluster":"health_fitness","visual_profile_key":"clinic",
 "templates_required":["home","services","single-service","about","team","contact","404"],
 "patterns_required":["hero-clinic","services-grid","doctor-card","appointment-form","trust-badges","insurance-logos","testimonials","location-map"],
 "woo_product_types":[],"woo_features":[],"experience_mode_override":"minimal","cod_relevant":false,"seasonal_theme":"medical_blue"}

{"domain":"dental","cluster":"health_fitness","visual_profile_key":"clinic",
 "templates_required":["home","services","single-service","about","team","contact","404"],
 "patterns_required":["hero-dental","services-grid","before-after-smile","doctor-card","appointment-form","trust-badges","testimonials","location-map"],
 "woo_product_types":[],"woo_features":[],"experience_mode_override":"minimal","cod_relevant":false,"seasonal_theme":"medical_blue"}

{"domain":"gym_fitness","cluster":"health_fitness","visual_profile_key":"fitness",
 "templates_required":["home","classes","single-class","trainers","pricing","contact","404"],
 "patterns_required":["hero-gym","class-schedule","trainer-card","pricing-table","transformation-gallery","membership-cta","testimonials","location-map"],
 "woo_product_types":["simple"],"woo_features":["product-gallery","subscription-placeholder"],
 "experience_mode_override":"feature_rich","cod_relevant":false,"seasonal_theme":"dark_energy"}

// business & real estate
{"domain":"corporate_b2b","cluster":"business_real_estate","visual_profile_key":"corporate",
 "templates_required":["home","about","services","single-service","team","case-studies","single-case-study","contact","404"],
 "patterns_required":["hero-corporate","services-grid","stats-bar","case-study-card","client-logos","team-grid","cta-contact","testimonials","footer-corporate"],
 "woo_product_types":[],"woo_features":[],"experience_mode_override":"minimal","cod_relevant":false,"seasonal_theme":"navy_pro"}

{"domain":"real_estate","cluster":"business_real_estate","visual_profile_key":"real_estate",
 "templates_required":["home","listings","single-listing","about","agents","contact","404"],
 "patterns_required":["hero-real-estate","search-filter-bar","property-card","property-features","agent-card","map-embed","testimonials","cta-evaluate","footer-corporate"],
 "woo_product_types":[],"woo_features":[],"experience_mode_override":null,"cod_relevant":false,"seasonal_theme":"navy_pro"}

// education & services
{"domain":"education_courses","cluster":"education_services","visual_profile_key":"education",
 "templates_required":["home","courses","single-course","about","instructors","contact","404"],
 "patterns_required":["hero-education","course-card","curriculum-accordion","instructor-card","pricing-table","certificate-strip","testimonials","faq-accordion","cta-enroll"],
 "woo_product_types":["simple","external"],"woo_features":["product-gallery","course-preview-tab"],
 "experience_mode_override":null,"cod_relevant":false,"seasonal_theme":"modern_purple"}

{"domain":"digital_agency","cluster":"education_services","visual_profile_key":"agency",
 "templates_required":["home","services","single-service","portfolio","single-project","about","contact","404"],
 "patterns_required":["hero-agency","services-grid","portfolio-grid","process-steps","tech-stack-logos","team-grid","pricing-table","testimonials","cta-contact"],
 "woo_product_types":[],"woo_features":[],"experience_mode_override":"feature_rich","cod_relevant":false,"seasonal_theme":"modern_purple"}
```


---

### Node 5.1: THEME_CONTRACT_GEN

هذه أهم Node في المنظومة كلها. تُنشأ **قبل** أي توليد، وكلا النموذجين ملزمان بها.

```python
"""
المشكلة التي تحلها:
  Gemini يُولّد HTML مع class="cod-form-submit"
  GLM يتوقع id="cod_submit_btn"
  النتيجة: JavaScript لا يجد العنصر، النموذج لا يُرسَل بصمت.

الحل: عقد مشترك يُعرِّف كل نقاط التلاقي بين الطرفين
"""

def generate_theme_contract(state: ThemeState) -> dict:
    contract = {
        "version":    "1.0",
        "theme_slug": state["theme_slug"],
        "generated":  datetime.utcnow().isoformat(),

        # ── نقاط التلاقي: PHP ↔ HTML ─────────────────────────
        "ajax_endpoints": {
            "cod_submit":       f"{state['theme_slug']}_cod_submit",
            "newsletter_sub":   f"{state['theme_slug']}_newsletter",
            "appointment_book": f"{state['theme_slug']}_appointment",
        },
        "nonce_keys": {
            "cod":         f"{state['theme_slug']}_cod_nonce",
            "contact":     f"{state['theme_slug']}_contact_nonce",
        },
        "honeypot_field": f"{state['theme_slug']}_hp",

        # ── CSS Classes مُتفَّق عليها ─────────────────────────
        "css_classes": {
            "cod_form":       f"{state['theme_slug']}-cod-form",
            "cod_submit":     f"{state['theme_slug']}-cod-submit",
            "mini_cart":      f"{state['theme_slug']}-mini-cart",
            "whatsapp_float": f"{state['theme_slug']}-whatsapp",
        },

        # ── WordPress Hooks ───────────────────────────────────
        "hooks": {
            "after_single_product": "woocommerce_after_single_product_summary",
            "cart_totals":          "woocommerce_cart_totals",
            "checkout_before":      "woocommerce_before_checkout_form",
            "body_classes":         "body_class",
        },

        # ── theme.json Slots ──────────────────────────────────
        "theme_json_slugs": {
            "primary_color":   "primary",
            "accent_color":    "accent",
            "heading_font":    "heading",
            "body_font":       "body",
            "container_width": "content-size",
            "wide_width":      "wide-size",
        },

        # ── PHP Functions Namespace ───────────────────────────
        "php_namespace":  state["theme_slug"].replace("-","_"),
        "option_prefix":  f"{state['theme_slug'].replace('-','_')}_",

        # ── WooCommerce Template Slugs ────────────────────────
        "woo_templates": {
            "shop":           "woocommerce/shop.html",
            "single_product": "woocommerce/single-product.html",
            "cart":           "woocommerce/cart.html",
            "checkout":       "woocommerce/checkout.html",
        },
    }

    # يُكتب في /project-state/theme_contract.json
    write_json("/project-state/theme_contract.json", contract)
    state["theme_contract"] = contract
    return state
```

**الالتزام بالعقد:** كل prompt لـ Gemini وكل prompt لـ GLM يُحقن فيه:
```
=== THEME CONTRACT (ملزم) ===
{json.dumps(state["theme_contract"], ensure_ascii=False, indent=2)}
لا تستخدم أسماء غير هذه المُعرَّفة في العقد.
```

---

### Node 6: SEO_SCAFFOLD

```python
"""
يُنشئ هيكل Arabic SEO قبل أي توليد:

ينشئ inc/seo.php يشمل:
  □ hreflang: <link rel="alternate" hreflang="ar" href="...">
  □ og:locale = ar_SA
  □ Schema.org بالعربية (LocalBusiness/Product/Organization حسب Domain)
  □ Arabic-aware title format: "عنوان الصفحة | اسم الموقع"
  □ Description truncation يحترم الكلمات العربية (لا يقطع كلمة)

Schema.org حسب Domain:
  commerce/*     → Product + Organization
  restaurant     → Restaurant + Menu
  clinic_medical → MedicalClinic + Physician
  dental         → Dentist
  hotel_resort   → Hotel + LodgingBusiness
  real_estate    → RealEstateAgent + Place
  education/*    → EducationalOrganization + Course
  corporate_b2b  → Organization + Service
  gym_fitness    → SportsActivityLocation
  digital_agency → ProfessionalService
"""
```

---

### Node 7: WP_SCAFFOLD

```python
"""
ينشئ شجرة مجلدات القالب الكاملة مع placeholders:

{theme_slug}/
├── style.css          ← Theme Header كاملاً
├── functions.php      ← skeleton + namespace
├── theme.json         ← skeleton v3
├── /templates/        ← per domain_profile.templates_required
│   └── /woocommerce/  ← Commerce domains فقط
├── /parts/
├── /patterns/
├── /styles/           ← light.json + dark.json + seasonal.json
├── /inc/
│   ├── seo.php        ← من SEO_SCAFFOLD
│   └── cod-quick-order.php ← إن COD
├── /emails/           ← إن Woo (WOO_EMAIL_RTL)
├── /assets/
│   ├── /css/
│   │   └── print.css  ← Print Styles
│   └── /js/
└── /docs/             ← README + licenses + test-results placeholders
"""
```

---

### Node 8: THEME_PLAN (spec-kit via Claude Code)

```python
"""
١. specify init . --ai claude --no-git
٢. /speckit.constitution ← يُغذَّى بـ theme_constitution.md
٣. /speckit.specify      ← يُغذَّى بـ normalized_input + domain profile + theme_contract
٤. /speckit.clarify      ← تلقائي حتى لا يوجد غموض
٥. /speckit.plan         ← WordPress Block Theme + WooCommerce stack
٦. /speckit.tasks        ← تفكيك مهام كل ملف مع تحديد: Gemini أو GLM
"""
```

### Node 8.1: SPECKIT_PATH_DETECTOR

```python
"""
يكتشف المسار الحقيقي لـ spec.md/plan.md/tasks.md
ويدعم اختلافات المسارات بين إصدارات spec-kit:
  .specify/specs/{feature}/
  specs/{feature}/
  .specify/specifications/{feature}/
"""
```

### Node 8.5: RISK_ASSESSOR

```python
def calculate_risk(state: ThemeState) -> float:
    score = 0.0
    if state["speckit_clarify_count"] > 2:            score += 0.30
    if state["architectural_alternatives"] > 1:        score += 0.25
    if abs(actual - planned) / planned > 0.20:         score += 0.20
    if state["spec_plan_conflicts"]:                   score += 0.40
    if not state["similar_projects"]:                  score += 0.15
    if len(state.get("custom_instructions","")) > 500: score += 0.10
    if state["cod_enabled"] and not state["woocommerce_enabled"]: score += 0.30
    return min(score, 1.0)

CHECKPOINT_THRESHOLD = 0.35
```

### Node 9: TOKEN_GEN

```python
"""
يُولّد design_tokens.json من:
  - cluster_profile.default_palette (قابل للتجاوز)
  - design_direction tokens
  - خطوط المستخدم + أوزانها

المخرج: design_tokens.json في /project-state/
"""
```

### Node 9.1: STYLE_VARIATION_ENGINE

```python
"""
يولّد /styles/light.json + dark.json + seasonal.json

Seasonal بحسب Domain:
┌──────────────────────┬──────────────────┬────────────────────────┐
│ Domain               │ Seasonal Theme   │ الألوان                │
├──────────────────────┼──────────────────┼────────────────────────┤
│ Perfume / Fashion    │ Black Gold       │ #0A0A0A + #C9A84C      │
│ Beauty / Cosmetics   │ Black Gold       │ #0A0A0A + #C9A84C      │
│ Restaurant / Cafe    │ Olive Warm       │ #2D3A1E + #8B7355      │
│ Furniture / Home     │ Olive Warm       │ #2D3A1E + #8B7355      │
│ Clinic / Dental      │ Medical Blue     │ #EFF6FF + #1D4ED8      │
│ Education / Courses  │ Modern Purple    │ #FAF5FF + #7C3AED      │
│ Digital Agency       │ Modern Purple    │ #FAF5FF + #7C3AED      │
│ Corporate / B2B      │ Navy Pro         │ #0F1E3C + #3B82F6      │
│ Real Estate          │ Navy Pro         │ #0F1E3C + #3B82F6      │
│ Electronics          │ Navy Pro         │ #0F1E3C + #3B82F6      │
│ Hotel / Resort       │ Desert Gold      │ #FEF3C7 + #B45309      │
│ Gym / Fitness        │ Dark Energy      │ #111827 + #10B981      │
└──────────────────────┴──────────────────┴────────────────────────┘

Gate: contrast ≥ 4.5 لكل variation + seasonal مناسب للـ domain
"""
```

### Node 9.2: EXPERIENCE_MODE_DECIDER

```python
"""
يُطبّق منطق التحكيم قبل أي توليد.
Domain يتغلب على اختيار المستخدم في حالات محددة مع توثيق السبب.
"""

DOMAIN_MODE_RULES = {
    "fashion_store":    {"override": None,           "reason": None},
    "perfume_luxury":   {"override": "feature_rich", "reason": "الرفاهية تتطلب تأثيرات بصرية"},
    "electronics":      {"override": None,           "reason": None},
    "furniture_home":   {"override": None,           "reason": None},
    "beauty_cosmetics": {"override": None,           "reason": None},
    "restaurant":       {"override": "feature_rich", "reason": "صور الطعام تحتاج تأثيرات"},
    "cafe":             {"override": "feature_rich", "reason": "أجواء المكان تحتاج تأثيرات"},
    "hotel_resort":     {"override": "feature_rich", "reason": "الضيافة الفاخرة تستوجب feature_rich"},
    "clinic_medical":   {"override": "minimal",      "reason": "البيئة الطبية: لا animations"},
    "dental":           {"override": "minimal",      "reason": "البيئة الطبية: لا animations"},
    "gym_fitness":      {"override": "feature_rich", "reason": "الطاقة العالية تتطلب تأثيرات"},
    "corporate_b2b":    {"override": "minimal",      "reason": "B2B يعطي الأولوية للسرعة"},
    "real_estate":      {"override": None,           "reason": None},
    "education_courses":{"override": None,           "reason": None},
    "digital_agency":   {"override": "feature_rich", "reason": "الوكالة تعرض إبداعها بالتأثيرات"},
}

def decide_experience_mode(state: ThemeState) -> ThemeState:
    user_mode = state["experience_mode"]
    rule = DOMAIN_MODE_RULES.get(state["domain"], {"override": None, "reason": None})

    if rule["override"] and rule["override"] != user_mode:
        log_decision(state, {
            "decision": "experience_mode_override",
            "user_requested": user_mode,
            "resolved": rule["override"],
            "reason": rule["reason"]
        })
        state["warnings"].append(
            f"تم تغيير Experience Mode من '{user_mode}' إلى '{rule['override']}': {rule['reason']}"
        )
        state["experience_mode"] = rule["override"]

    resolved = state["experience_mode"]
    if resolved == "minimal":
        state["js_budget_kb"] = 10
        state["animation_policy"] = "none"
        state["intersection_observer_allowed"] = False
        state["parallax_allowed"] = False
    else:
        state["js_budget_kb"] = 35
        state["animation_policy"] = "tasteful_performance_safe"
        state["intersection_observer_allowed"] = True
        state["parallax_allowed"] = True

    state["prefers_reduced_motion_enforced"] = True
    state["css_transition_max_ms"] = 400
    return state
```


### Node 10: FILE_LIST

```python
"""
يبني قائمة الملفات الكاملة بناءً على:
  - domain_profile.templates_required
  - domain_profile.patterns_required
  - woocommerce_enabled → يضيف /templates/woocommerce/ + mini-cart
  - cod_enabled → يضيف /inc/cod-quick-order.php + /patterns/cod-form.php
  - experience_mode → يضيف JS files بحسب الميزانية

يُصنّف كل ملف:
  generator: "gemini" | "glm" | "both"
  type:      "critical" | "standard"
"""

# توزيع الملفات بين النموذجين
FILE_ROUTING = {
    # Gemini — Frontend
    "gemini": [
        "templates/**/*.html",
        "parts/*.html",
        "patterns/*.php",        # الجزء البصري فقط
        "styles/*.json",
        "assets/css/*.css",
        "assets/js/animations.js",
        "assets/js/menu.js",
    ],
    # GLM — Backend
    "glm": [
        "functions.php",
        "inc/*.php",
        "theme.json",            # tokens + settings API
        "assets/js/cod-form.js",
        "assets/js/woo-*.js",
        "emails/*.php",
    ],
    # كلاهما بالتسلسل: Gemini أولاً ثم GLM يُكمل
    "both": [
        "patterns/cod-form.php",         # HTML من Gemini + PHP logic من GLM
        "patterns/appointment-form.php", # HTML من Gemini + PHP logic من GLM
    ]
}
```

### Node 12: ROUTE_FILE

```python
"""
يُحدد لكل ملف في file_manifest:
  - النموذج المسؤول (gemini / glm / both)
  - الحالة: critical أو standard
  - يُحقن theme_contract في كل prompt
"""

def route_file(file_path: str, state: ThemeState) -> str:
    for pattern in FILE_ROUTING["gemini"]:
        if fnmatch(file_path, pattern): return "gemini"
    for pattern in FILE_ROUTING["glm"]:
        if fnmatch(file_path, pattern): return "glm"
    for pattern in FILE_ROUTING["both"]:
        if fnmatch(file_path, pattern): return "both"
    return "glm"  # افتراضي
```

### Node 13: GEMINI_CODEGEN / GLM_CODEGEN

كلا النموذجين يتلقيان prompt يشمل:

```python
def build_frontend_prompt(state, current_file):
    lessons = filter_lessons(state["lessons_learned"], current_file, state["domain"], state["experience_mode"])
    return f"""
{state['constitution_content']}

=== THEME CONTRACT (ملزم — لا تغيير) ===
{json.dumps(state['theme_contract'], ensure_ascii=False, indent=2)}

=== Cluster / Domain ===
Cluster: {state['cluster']} | Domain: {state['domain']}
Experience Mode: {state['experience_mode']} | JS Budget: {state['js_budget_kb']}KB

=== Design Tokens ===
{json.dumps(state['design_tokens'], ensure_ascii=False)}

=== المهمة ===
{get_task_for_file(state['speckit_tasks'], current_file)}

=== RAG Context — WordPress/Block API ===
{state['rag_context_for_file']}

=== دروس مستفادة ({len(lessons)}/8) ===
{chr(10).join(f'- {l}' for l in lessons) if lessons else 'لا دروس — مشروع جديد.'}

الآن ولّد: {current_file}
    """
```

#### Memory Injection — سقف صارم

```python
MEMORY_MAX_LESSONS       = int(os.getenv("MEMORY_MAX_LESSONS", 8))
MEMORY_MAX_LESSON_CHARS  = int(os.getenv("MEMORY_MAX_LESSON_CHARS", 120))
MEMORY_MAX_INJECT_TOKENS = int(os.getenv("MEMORY_MAX_INJECT_TOKENS", 400))

def filter_lessons(all_lessons, file, domain, experience_mode) -> list[str]:
    def score(lesson):
        s = 0
        if file.split("/")[-1].replace(".php","").replace(".html","") in lesson.lower(): s += 4
        if domain.replace("_"," ") in lesson.lower(): s += 3
        if experience_mode in lesson.lower(): s += 2
        if any(k in lesson.lower() for k in ["rtl","woocommerce","cod","security","nonce"]): s += 1
        return s
    ranked  = sorted(all_lessons, key=score, reverse=True)[:MEMORY_MAX_LESSONS]
    trimmed = [l[:MEMORY_MAX_LESSON_CHARS]+"…" if len(l)>MEMORY_MAX_LESSON_CHARS else l for l in ranked]
    result, tokens = [], 0
    for l in trimmed:
        t = len(l) // 4
        if tokens + t > MEMORY_MAX_INJECT_TOKENS: break
        result.append(l); tokens += t
    return result
```

### Node 13.5: OUTPUT_PARSER

يُشغَّل فوراً بعد كل GEMINI_CODEGEN / GLM_CODEGEN، قبل أي Gate. يضمن أن المدخل لكل Gate كود نظيف لا نثر ولا markdown.

```python
def output_parser(raw_output: str, expected_type: str, file: str) -> dict:
    """
    المشكلة التي يحلها:
      - Gemini يُغلّف الكود بـ markdown داخل markdown أحياناً
      - GLM يُضيف شرحاً نثرياً وسط الـ PHP
      - SELF_CRITIQUE والـ Gates تفترض كوداً نظيفاً دائماً — وهذا لن يحدث
    """

    # ١. تجريد markdown
    code = raw_output.strip()
    # إزالة ```php / ```html / ```json / ``` أياً كانت
    code = re.sub(r'^```[\w]*\n?', '', code, flags=re.MULTILINE)
    code = re.sub(r'\n?```$', '', code, flags=re.MULTILINE)
    # إزالة أي نثر قبل الكود (سطور تبدأ بـ "هذا الكود..." / "بالتأكيد..." / "إليك...")
    lines = code.split("\n")
    first_code_line = next(
        (i for i, l in enumerate(lines) if l.strip().startswith(("<?php","<!--","{",'<','@'))),
        0
    )
    code = "\n".join(lines[first_code_line:]).strip()

    # ٢. تحقق حسب نوع الملف
    if expected_type == "php":
        if not code.startswith("<?php"):
            code = "<?php\n" + code.lstrip("<?php").strip()
        opens  = code.count("{")
        closes = code.count("}")
        if opens != closes:
            return {
                "valid": False, "reason": "unbalanced_braces",
                "opens": opens, "closes": closes, "raw": code
            }

    elif expected_type == "html":
        opens  = len(re.findall(r'<!-- wp:', code))
        closes = len(re.findall(r'<!-- /wp:', code))
        if opens != closes:
            return {
                "valid": False, "reason": "unbalanced_blocks",
                "opens": opens, "closes": closes, "raw": code
            }

    elif expected_type == "json":
        try:
            json.loads(code)
        except json.JSONDecodeError:
            # محاولة إصلاح تلقائي: إضافة قوس مفقود
            fixed = attempt_json_fix(code)
            if fixed:
                return {"valid": True, "content": fixed, "auto_fixed": True}
            return {"valid": False, "reason": "invalid_json", "raw": code}

    # ٣. كشف النثر المتنكر ككود
    code_density = len(re.findall(r'[{};()<>/@]', code)) / max(len(code), 1)
    if code_density < 0.02 and expected_type in ["php", "html"]:
        return {"valid": False, "reason": "prose_not_code", "raw": code}

    return {"valid": True, "content": code}


def handle_parser_failure(failure: dict, file: str, attempt: int, state: ThemeState) -> ThemeState:
    if attempt < 2:
        # إعادة الطلب مع تعليمات صريحة
        state["retry_prompt_suffix"] = (
            "\n\nمهم جداً: أرجع الكود فقط، بدون أي شرح أو markdown أو نص قبله أو بعده."
        )
        state["retry_file"] = file
    else:
        # النموذج لا ينتج كوداً نظيفاً — HUMAN_CHECKPOINT إلزامي
        state["checkpoint_stage"]  = "output_parser_failure"
        state["checkpoint_reason"] = f"النموذج لا يُنتج كوداً نظيفاً للملف {file}: {failure['reason']}"
        state["status"] = "checkpoint_required"
    return state
```

### Node 14: SELF_CRITIQUE

```python
"""
النموذج يراجع كوده قبل إرساله للمراجعات الخارجية.
يكشف ~40% من المشاكل مبكراً ويُقلل review_rounds بشكل ملحوظ.
"""

def self_critique(code: str, file: str, generator: str, state: ThemeState) -> dict:
    critique_prompt = f"""
أنت مراجع كود WordPress عربي متخصص.
راجع هذا الكود وأجب بدقة على النقاط التالية:

الكود:
{code}

الملف: {file}
Domain: {state['domain']}

الأسئلة:
١. هل كل WordPress/WooCommerce function مستخدمة موجودة فعلاً؟ اذكر أي function مشكوك فيها.
٢. هل RTL صحيح في كل عنصر؟ ابحث عن LTR-only properties خاطئة.
٣. هل Block markup متوازن تماماً (لكل wp: يوجد /wp:)؟
٤. ما الذي قد يكسر في بيئة الإنتاج؟
٥. هل يلتزم الكود بـ THEME_CONTRACT؟

أجب بـ JSON:
{{"issues": [...], "suggestions": [...], "approved": bool}}
    """
    result = call_api(generator, critique_prompt)
    critique = parse_json(result)

    if not critique["approved"] or len(critique["issues"]) > 0:
        state["self_critique_issues"][file] = critique["issues"]
        # يُمرَّر للـ FIX مباشرة قبل الوصول للمراجعات الخارجية
        return {"needs_fix": True, "issues": critique["issues"]}
    return {"needs_fix": False}
```

### Node 15: FUNCTION_WHITELIST_GATE

```python
"""
يمنع الهلوسة في WordPress/WooCommerce API.
الأكثر فاعلية من أي مراجعة بشرية لهذا النوع من الأخطاء.
"""

# قواعد بيانات مفهرسة مسبقاً
RAG_SOURCES = {
    "wordpress_functions":   "wp_6.5_functions.json",    # كل functions.php الرسمية
    "woocommerce_hooks":     "wc_8x_hooks_filters.json", # كل hooks + filters
    "block_editor_api":      "gutenberg_blocks_api.json",# Block markup الصحيح
    "theme_json_schema":     "theme_json_v3_schema.json",# Schema رسمي
}

def function_whitelist_gate(code: str, file: str) -> dict:
    # استخراج كل function calls من الكود
    php_functions = extract_php_functions(code)     # regex على ()
    wp_hooks      = extract_wp_hooks(code)           # add_action/add_filter
    block_types   = extract_block_names(code)        # <!-- wp:xxx -->

    issues = []

    for fn in php_functions:
        if fn.startswith("wc_") or fn.startswith("wp_") or fn.startswith("get_"):
            if not rag_lookup(fn, "wordpress_functions") and not rag_lookup(fn, "woocommerce_hooks"):
                issues.append({
                    "type":     "hallucinated_function",
                    "function": fn,
                    "line":     find_line(code, fn),
                    "fix":      rag_suggest_alternative(fn)
                })

    for hook in wp_hooks:
        if not rag_lookup(hook, "woocommerce_hooks"):
            issues.append({
                "type": "invalid_hook",
                "hook": hook,
                "fix":  rag_suggest_alternative(hook)
            })

    for block in block_types:
        if not rag_lookup(block, "block_editor_api"):
            issues.append({
                "type":  "invalid_block_type",
                "block": block,
                "fix":   rag_suggest_alternative(block)
            })

    if issues:
        return {"passed": False, "issues": issues}
    return {"passed": True}
```

### Node 16: WP_COMPLIANCE_SCAN

```python
"""
□ theme.json صالح JSON + schema v3
□ style.css يحتوي Theme Header كاملاً (Theme Name, Text Domain, Version...)
□ Text Domain = theme_slug في كل دالة i18n
□ Block markup متوازن (<!-- wp:... --> / <!-- /wp:... -->)
□ Woo templates بالأسماء الصحيحة المُعرَّفة في theme_contract
□ لا PHP syntax errors (php -l)
"""
```

### Node 17: PHPSTAN_SCAN

```python
"""
أخطاء PHP الصامتة التي لا تُكشف بالعين.

يُشغّل: phpstan analyse --level=5 --no-progress {file}

يكشف:
□ استدعاء methods على null (الأخطر في WooCommerce)
  مثال: $order->get_id() قد يُعيد int|false — خطأ لو افترض النموذج int دائماً
□ return types خاطئة
□ Variables غير مُعرَّفة
□ Dead code
□ Type mismatches في WC_Order / WC_Product methods

FAIL → مُمرَّر لـ SELF_CRITIQUE + FIX مع تقرير PHPStan كاملاً
"""
```

### Node 18: SECURITY_SCAN

```python
"""
□ esc_html / esc_attr / esc_url / esc_textarea على كل output
□ wp_nonce_field + check_admin_referer / check_ajax_referer على كل form
□ sanitize_text_field / absint / wp_kses_post على كل input
□ current_user_can حيث يلزم
□ ممنوع: eval() / base64_decode() / exec() / shell_exec() / system()
□ لا SQL raw queries بدون $wpdb->prepare()
□ COD (إن enabled): nonce + rate_limit + honeypot جميعها موجودة
□ PHP namespace صحيح: كل الدوال تبدأ بـ {theme_slug}_

FAIL أمني → يُوقف الملف فوراً + أولوية قصوى في FIX
"""
```

### Node 19: CLAUDE_REVIEW

```python
"""
مراجعة منطقية عميقة تركّز على:
  - RTL: logical properties + is-directional + LTR islands الصحيحة
  - Accessibility: contrast + focus + aria + heading order
  - Block Structure: صحة الـ Blocks + الـ InnerBlocks
  - WooCommerce: صحة template hooks مع theme_contract
  - COD Form: صحة AJAX handler + أمان كامل
  - UX: تدفق المستخدم + وضوح CTA

المخرج: قائمة مُصنَّفة (critical / warning / info)
critical → يُحفَّز FIX فوراً
"""
```

### Node 20: CODERABBIT_REVIEW

```python
"""
معايير الكود:
  - WordPress Coding Standards (WPCS)
  - PHP 8.1 best practices
  - تسمية الدوال والمتغيرات (namespace صحيح)
  - لا كود مكرر
  - hooks بالأسماء المُعرَّفة في theme_contract
"""
```

### Node 21: FIX (patch-based)

```python
"""
يستقبل تقارير: SELF_CRITIQUE + FUNCTION_WHITELIST + PHPSTAN + SECURITY + COMPLIANCE + CLAUDE + CODERABBIT

المنطق:
  ١. تصنيف المشاكل حسب الأولوية (security > hallucination > rtl > compliance > style)
  ２. تطبيق الإصلاحات على الأسطر المتأثرة فقط (لا إعادة بناء كاملة)
  ٣. إعادة المراجعات للتحقق

الحدود:
  MAX_FIX_ATTEMPTS = 3 لكل ملف عادي
  إن تجاوز + ملف critical → HUMAN_CHECKPOINT
  إن تجاوز + ملف standard → تحذير + تسجيل + متابعة
"""
```

### Node 22: SEMANTIC_DIFF

```python
"""
يمنع regression بعد كل FIX.
المشكلة: FIX يُصلح مشكلة ويُدخل regression بصمت.
"""

def semantic_diff(before: str, after: str, file_type: str) -> dict:
    issues = []

    if file_type == "php":
        # يتحقق أن نفس الـ hooks لا تزال مُسجَّلة
        before_hooks = extract_wp_hooks(before)
        after_hooks  = extract_wp_hooks(after)
        removed = set(before_hooks) - set(after_hooks)
        if removed:
            issues.append({"type": "removed_hooks", "hooks": list(removed)})

        # يتحقق أن namespace لم يتغير
        before_ns = extract_namespace(before)
        after_ns  = extract_namespace(after)
        if before_ns != after_ns:
            issues.append({"type": "namespace_changed"})

    elif file_type == "html":
        # يتحقق أن Block structure لم تتغير بنيوياً
        before_blocks = count_block_types(before)
        after_blocks  = count_block_types(after)
        missing = {k: v for k, v in before_blocks.items() if k not in after_blocks}
        if missing:
            issues.append({"type": "missing_blocks", "blocks": missing})

        # يتحقق أن RTL properties لم تُحذف
        before_rtl = extract_rtl_properties(before)
        after_rtl  = extract_rtl_properties(after)
        if len(after_rtl) < len(before_rtl) * 0.8:
            issues.append({"type": "rtl_regression", "before": len(before_rtl), "after": len(after_rtl)})

    # التحقق الأشمل: الـ diff لا يحذف أكثر مما يُضيف بنسبة > 30%
    removed_lines = count_removed_lines(before, after)
    added_lines   = count_added_lines(before, after)
    if removed_lines > 0 and removed_lines > added_lines * 1.3:
        issues.append({"type": "excessive_deletion",
                       "removed": removed_lines, "added": added_lines})

    if issues:
        return {"passed": False, "issues": issues, "action": "revert_to_before_fix"}
    return {"passed": True}
```


### Node 23: COD_MODULE_BUILDER

```python
"""
الملفات المُنشأة (GLM):
  inc/cod-quick-order.php     ← المنطق الخلفي
  assets/js/cod-form.js       ← إرسال AJAX (≤ 8KB، vanilla JS)
  patterns/cod-form.php       ← HTML (Gemini) + PHP init (GLM)

آلية العمل عند إرسال النموذج:
  ١. check_ajax_referer(theme_contract.nonce_keys.cod)
  ٢. rate limit: transient بـ IP + timestamp — max 3/10min
     transient_key = 'cod_rate_' . md5($_SERVER['REMOTE_ADDR'])
  ٣. honeypot: إن امتلأ حقل theme_contract.honeypot_field → reject صامت
  ٤. sanitize_text_field على كل حقل نصي
  ٥. absint على الكمية و product_id
  ٦. wc_create_order(['customer_id' => 0])
  ٧. $order->add_product(wc_get_product($product_id), $qty)
  ٨. $order->set_address($shipping_data, 'shipping')
  ٩. $order->set_payment_method('cod')
  ١٠. $order->calculate_totals()
  ١١. $order->update_status('pending', 'COD Quick Order')
  ١٢. wp_send_json_success(['message' => 'تم استلام طلبك! سنتواصل معك قريباً.'])

print.css يشمل:
  @media print {
    .site-header, .site-footer, .cod-form, .wc-block-cart { display: none; }
    .woocommerce-order { direction: rtl; font-family: Cairo, sans-serif; }
    .order-total { font-size: 18pt; font-weight: bold; }
    .order-number::before { content: 'رقم الطلب: '; }
  }
"""
```

### Node 23.1: COD_SECURITY_GATE

```python
"""
PASS إذا تحققت جميع الشروط:
□ Nonce: wp_nonce_field(theme_contract.nonce_keys.cod)
□ check_ajax_referer موجود وصحيح في معالج AJAX
□ Rate limit: transient_key = 'cod_rate_' . md5($ip) / TTL = 600s
□ Honeypot: حقل مخفي (opacity:0 + position:absolute + tabindex:-1)
□ sanitize_text_field على كل input نصي
□ absint على الكمية
□ RTL: direction:rtl + text-align:right في النموذج كاملاً
□ لا PHP errors في Smoke Test
□ $order->get_id() > 0 بعد الإنشاء

FAIL → يُعيد لـ COD_MODULE_BUILDER بتقرير مفصَّل
max 2 محاولات → HUMAN_CHECKPOINT إلزامي
"""
```

### Node 24: WOO_EMAIL_RTL

```python
"""
إيميلات WooCommerce تخرج بـ LTR افتراضياً.
للمتاجر العربية هذا مشكلة تجارية فعلية.

يُنشئ: /emails/
  ├── customer-completed-order.php   ← تأكيد اكتمال الطلب
  ├── customer-new-order.php         ← إشعار طلب جديد
  ├── customer-invoice.php           ← فاتورة + توقيع عربي
  └── customer-processing-order.php ← تأكيد استلام الطلب

في functions.php:
  add_filter('woocommerce_email_styles', function($css) {
      return $css . '
          body { direction: rtl; font-family: Cairo, Tajawal, sans-serif; }
          .email-header { text-align: right; }
          .order-details td { text-align: right; }
          .order-total { font-weight: bold; }
      ';
  });

Gate: TESTSPRITE يختبر إرسال بريد اختباري + فحص direction
"""
```

### Node 25: ARABIC_NUMERICS_GATE

```python
"""
مشكلة صامتة شائعة:
  الأسعار والأرقام تخرج بـ Eastern Arabic numerals (٠١٢٣)
  أو تتقطع في RTL context

الفحوصات:
□ wc_price() يُخرج الأرقام بـ Western numerals داخل <bdi>
□ الأسعار: dir="ltr" داخل dir="rtl"
□ أرقام الهاتف: <span dir="ltr">+966XXXXXXXXX</span>
□ التواريخ: تُعرض بالتقويم الميلادي + اللغة العربية
□ ترقيم الصفحات: أرقام Western داخل pagination

الإصلاح التلقائي في functions.php:
  add_filter('formatted_woocommerce_price', function($price) {
      return '<bdi dir="ltr">' . $price . '</bdi>';
  });

  add_filter('woocommerce_price_format', function($format) {
      return '<bdi>%2$s</bdi>&nbsp;<span dir="rtl">%1$s</span>';
  });
"""
```

### Node 26: DEMO_CONTENT_GENERATOR

```python
"""
يولّد demo-content.xml + /project-state/demo_manifest.json
القاعدة: لا Lorem Ipsum — محتوى عربي حقيقي لكل Domain
"""

DEMO_CONTENT_MAP = {
    "fashion_store": {
        "woo": True,
        "products": [
            {"name":"فستان سهرة ملكي","price":"899","category":"فساتين"},
            {"name":"عباية بتطريز ذهبي","price":"699","category":"عبايات"},
            {"name":"بلوزة كاجوال أنيقة","price":"249","category":"تنسيقات يومية"},
            {"name":"تنورة ميدي كلاسيك","price":"349","category":"تنسيقات يومية"},
            {"name":"طقم عيد فاخر","price":"1299","category":"مجموعات"},
            {"name":"شال حرير ناعم","price":"199","category":"إكسسوارات"},
        ],
        "categories": ["فساتين","عبايات","تنسيقات يومية","مجموعات","إكسسوارات"],
        "posts": ["أبرز صيحات الموضة لهذا الموسم","كيف تبني خزانة ملابس كاملة بميزانية محدودة","دليل تنسيق العباية للمناسبات"],
        "pages": ["الرئيسية","المتجر","العروض","من نحن","تواصلي معنا"],
        "currency": "ر.س"
    },
    "perfume_luxury": {
        "woo": True,
        "products": [
            {"name":"عطر الياسمين الملكي","price":"599","category":"عطور نسائية"},
            {"name":"أو د بارفان الصحراء","price":"899","category":"عطور رجالية"},
            {"name":"مجموعة العود الفاخر","price":"1299","category":"هدايا"},
            {"name":"عطر النخيل الذهبي","price":"749","category":"عطور رجالية"},
            {"name":"بخور الأمير","price":"299","category":"بخور وعود"},
            {"name":"طقم هدية بريميوم","price":"1499","category":"هدايا"},
        ],
        "categories": ["عطور رجالية","عطور نسائية","هدايا","بخور وعود"],
        "posts": ["دليلك لاختيار عطر يدوم طويلاً","أشهر 5 عطور عربية في 2025","كيف تحفظ عطرك بشكل صحيح"],
        "pages": ["الرئيسية","المتجر","المجموعات","من نحن","تواصل معنا"],
        "currency": "ر.س"
    },
    "electronics": {
        "woo": True,
        "products": [
            {"name":"لابتوب فائق الأداء 15 بوصة","price":"3499","category":"لابتوبات"},
            {"name":"سماعة لاسلكية احترافية","price":"599","category":"صوتيات"},
            {"name":"شاشة 4K 27 بوصة","price":"1299","category":"شاشات"},
            {"name":"كيبورد ميكانيكي عربي","price":"349","category":"ملحقات"},
            {"name":"راوتر واي فاي 6","price":"449","category":"شبكات"},
            {"name":"كاميرا ويب 4K","price":"299","category":"كاميرات"},
        ],
        "categories": ["لابتوبات","صوتيات","شاشات","ملحقات","شبكات","كاميرات"],
        "posts": ["أفضل لابتوبات 2025 للعمل والدراسة","دليل شراء السماعة اللاسلكية","كيف تحمي بياناتك على الإنترنت"],
        "pages": ["الرئيسية","المتجر","العروض","الدعم الفني","تواصل معنا"],
        "currency": "ر.س"
    },
    "furniture_home": {
        "woo": True,
        "products": [
            {"name":"أريكة كلاسيكية 3 مقاعد","price":"3200","category":"غرفة المعيشة"},
            {"name":"طاولة طعام 6 أشخاص","price":"2800","category":"غرفة الطعام"},
            {"name":"سرير ملكي مع دولاب","price":"4500","category":"غرفة النوم"},
            {"name":"مكتب عمل خشب طبيعي","price":"1800","category":"المكتب"},
            {"name":"رف كتب جداري","price":"950","category":"المكتب"},
            {"name":"بساط فارسي كبير 3×4","price":"1200","category":"إكسسوارات"},
        ],
        "categories": ["غرفة المعيشة","غرفة الطعام","غرفة النوم","المكتب","إكسسوارات"],
        "posts": ["كيف تختار أريكة تدوم عشر سنوات","أفكار لتصميم غرفة معيشة عصرية","دليل الألوان لغرفة النوم المثالية"],
        "pages": ["الرئيسية","المتجر","العروض","من نحن","تواصل معنا"],
        "currency": "ر.س"
    },
    "beauty_cosmetics": {
        "woo": True,
        "products": [
            {"name":"كريم ترطيب يومي SPF50","price":"189","category":"عناية بالبشرة"},
            {"name":"سيروم الكولاجين الذهبي","price":"299","category":"عناية بالبشرة"},
            {"name":"أحمر شفاه ساتان 24 ساعة","price":"99","category":"مكياج"},
            {"name":"ماسكارا بانش","price":"129","category":"مكياج"},
            {"name":"عطر بودرة فاخر","price":"499","category":"عطور"},
            {"name":"طقم عناية كامل","price":"799","category":"مجموعات"},
        ],
        "categories": ["عناية بالبشرة","مكياج","عطور","مجموعات"],
        "posts": ["روتين العناية بالبشرة الصباحي","أفضل كريمات الحماية من الشمس لهذا الصيف","كيف تختارين المكياج المناسب لبشرتك"],
        "pages": ["الرئيسية","المتجر","العروض","من نحن","تواصلي"],
        "currency": "ر.س"
    },
    "restaurant": {
        "woo": False,
        "menu_sections": {
            "مقبلات":["حمص بالطحينة","متبل","سلطة فتوش","ورق عنب"],
            "أطباق رئيسية":["كباب مشوي","دجاج مشوي","سمك مقلي","مندي لحم"],
            "مشروبات":["عصير ليمون بالنعناع","تمر هندي","كركديه","شاهي"],
            "حلويات":["أم علي","كنافة","مهلبية","بقلاوة"]
        },
        "posts": ["قصتنا — رحلة من المطبخ إلى القلوب","مكوناتنا الطازجة مباشرة من المزرعة","احجز طاولتك لمناسبتك القادمة"],
        "pages": ["الرئيسية","قائمة الطعام","احجز طاولة","من نحن","تواصل معنا"],
        "currency": None
    },
    "cafe": {
        "woo": False,
        "menu_sections": {
            "مشروبات ساخنة":["قهوة إسبريسو","كابتشينو","لاتيه فانيلا","ماتشا لاتيه"],
            "مشروبات باردة":["فرابتشينو كراميل","موهيتو نعناع","عصير مانجو فريش"],
            "مأكولات":["كرواسان لوز","وافل بلجيكي","سلطة دجاج مشوي"]
        },
        "posts": ["لماذا قهوتنا مختلفة — سر الحبة الذهبية","مساحتنا المثالية للعمل والاجتماعات","برنامج الولاء — اشرب 9 واحصل على 1 مجاناً"],
        "pages": ["الرئيسية","قائمتنا","من نحن","تواصل معنا"],
        "currency": None
    },
    "hotel_resort": {
        "woo": False,
        "rooms": [
            {"name":"غرفة ديلوكس","price_night":"650","type":"standard"},
            {"name":"جناح بإطلالة بحرية","price_night":"1200","type":"suite"},
            {"name":"فيلا خاصة","price_night":"2500","type":"villa"},
        ],
        "amenities": ["مسبح لا نهائي","سبا ومركز صحي","مطعم 5 نجوم","مواصلات مجانية"],
        "posts": ["أفضل المواسم للزيارة وما يميزها","باقات العرسان — ليلة لا تُنسى","برنامج المغامرات والرياضات المائية"],
        "pages": ["الرئيسية","الغرف والأجنحة","المرافق","عروض","احجز الآن"],
        "currency": "ر.س"
    },
    "clinic_medical": {
        "woo": False,
        "services": [
            {"name":"الطب الباطني","desc":"فحص شامل ومتابعة الحالات المزمنة"},
            {"name":"طب الأطفال","desc":"رعاية صحية متخصصة من الولادة"},
            {"name":"الجراحة العامة","desc":"عمليات جراحية بأحدث التقنيات"},
        ],
        "team": ["د. أحمد الغامدي — باطنية","د. نورة العتيبي — أطفال"],
        "posts": ["نصائح للحفاظ على صحتك في الشتاء","متى يجب زيارة الطوارئ؟ دليل عملي","الفحوصات الدورية الضرورية لكل شخص"],
        "pages": ["الرئيسية","خدماتنا","فريق الأطباء","احجز موعداً","تواصل معنا"],
        "currency": None
    },
    "dental": {
        "woo": False,
        "services": [
            {"name":"تبييض الأسنان","desc":"نتائج فورية بتقنية ليزر"},
            {"name":"تركيبات وتيجان","desc":"ابتسامة مثالية تدوم طويلاً"},
            {"name":"زراعة الأسنان","desc":"حلول دائمة بأحدث الزرعات"},
        ],
        "team": ["د. خالد المنصور — جراحة فموية","د. سارة الحربي — تقويم"],
        "posts": ["5 نصائح للحفاظ على بياض أسنانك","زراعة الأسنان — الأسئلة الأكثر شيوعاً","متى تبدأ بتقويم أسنان طفلك؟"],
        "pages": ["الرئيسية","خدماتنا","فريقنا","ابتسامة هوليوود","احجز موعداً"],
        "currency": None
    },
    "gym_fitness": {
        "woo": False,
        "classes": [
            {"name":"يوغا الصباح","schedule":"6:00 - 7:00 ص","level":"مبتدئ"},
            {"name":"كروسفيت مكثف","schedule":"7:00 - 8:00 م","level":"متقدم"},
            {"name":"ملاكمة لياقة","schedule":"6:00 - 7:00 م","level":"متوسط"},
        ],
        "pricing": [{"plan":"شهري","price":"299"},{"plan":"ثلاثة أشهر","price":"799"},{"plan":"سنوي","price":"2499"}],
        "posts": ["5 تمارين لحرق الدهون بسرعة","التغذية السليمة قبل وبعد التمرين","كيف تبدأ رحلتك مع الكروسفيت"],
        "pages": ["الرئيسية","الكلاسات","المدربون","العضويات","تواصل معنا"],
        "currency": "ر.س"
    },
    "corporate_b2b": {
        "woo": False,
        "services": [
            {"name":"الاستشارات الإدارية","desc":"حلول استراتيجية لنمو مستدام"},
            {"name":"إدارة المشاريع","desc":"تنفيذ دقيق في الوقت والميزانية"},
            {"name":"التحول الرقمي","desc":"رقمنة العمليات وأتمتة الأعمال"},
        ],
        "stats": [{"value":"+150","label":"عميل"},{"value":"+10","label":"سنوات خبرة"},{"value":"98%","label":"نسبة رضا"}],
        "posts": ["كيف تختار شريك الاستشارات المناسب","التحول الرقمي في 2025 — فرص وتحديات","قصص نجاح عملائنا"],
        "pages": ["الرئيسية","خدماتنا","عن الشركة","أعمالنا","تواصل معنا"],
        "currency": None
    },
    "real_estate": {
        "woo": False,
        "listings": [
            {"name":"فيلا حديثة — حي النرجس","price":"3,200,000","type":"فيلا"},
            {"name":"شقة 4 غرف — الملقا","price":"950,000","type":"شقة"},
            {"name":"دوبلكس فاخر — العليا","price":"1,800,000","type":"دوبلكس"},
            {"name":"أرض سكنية — شمال الرياض","price":"1,100,000","type":"أرض"},
        ],
        "agents": ["م. فهد الحربي","أ. ريم القحطاني"],
        "posts": ["أفضل الأحياء للعائلات في الرياض 2025","كيف تشتري أول منزل لك — دليل خطوة بخطوة","الفرق بين دعم سكني وتمويل بنكي"],
        "pages": ["الرئيسية","العقارات","للبيع","للإيجار","تواصل معنا"],
        "currency": "ر.س"
    },
    "education_courses": {
        "woo": False,
        "courses": [
            {"name":"برمجة Python من الصفر","price":"399","level":"مبتدئ"},
            {"name":"تصميم الجرافيك — Figma","price":"499","level":"متوسط"},
            {"name":"تسويق رقمي متكامل","price":"599","level":"متوسط"},
            {"name":"ريادة الأعمال وبناء الستارت أب","price":"799","level":"متقدم"},
        ],
        "instructors": ["م. سلطان العمري","أ. منى الزهراني"],
        "posts": ["كيف تتعلم البرمجة في 3 أشهر","أهم مهارات سوق العمل في 2025","تجربة طالب — كيف غيّرت دورة واحدة مساري"],
        "pages": ["الرئيسية","الدورات","المدربون","شهاداتنا","تواصل معنا"],
        "currency": "ر.س"
    },
    "digital_agency": {
        "woo": False,
        "services": [
            {"name":"تصميم الهوية البصرية","desc":"شعار + دليل هوية متكامل"},
            {"name":"تطوير المواقع","desc":"مواقع سريعة وجذابة"},
            {"name":"إدارة السوشيال ميديا","desc":"محتوى يحوّل متابعين لعملاء"},
            {"name":"إعلانات Google و Meta","desc":"ROI مرتفع بميزانية مناسبة"},
        ],
        "portfolio": [{"name":"هوية شركة تقنية","type":"branding"},{"name":"متجر عطور إلكتروني","type":"web"}],
        "posts": ["لماذا هوية بصرية قوية تعني مبيعات أعلى","5 أخطاء شائعة في إدارة السوشيال ميديا","كيف قضينا 30 يوماً مع عميلنا وضاعفنا مبيعاته"],
        "pages": ["الرئيسية","خدماتنا","أعمالنا","من نحن","تواصل معنا"],
        "currency": None
    },
}
```


### Nodes 27-29: VISUAL_PROFILE_SELECTOR + DEMO_IMAGE_ENGINE + BRAND_ASSET_GENERATOR

```python
"""
Node 27: VISUAL_PROFILE_SELECTOR
  يختار Visual Profile من VISUAL_PROFILES dict:
  visual_profile_key → أسلوب توليد الصور + ألوان + نوع الصور (product/lifestyle/architectural)
  قواعد السلامة: لا وجوه واضحة / لا نصوص / لا علامات تجارية / لا علامات مائية

Node 28: DEMO_IMAGE_ENGINE
  يولّد صور الديمو بـ Gemini Image API
  لكل صورة: prompt من visual_profile + product_name + domain context
  → WebP → ضغط ≤ 200KB → /assets/images/demo/
  Fallback: مكتبة صور داخلية → placeholder محلي + تحذير في README

Node 29: BRAND_ASSET_GENERATOR
  screenshot.png (1200×900): لقطة الصفحة الرئيسية على متصفح وهمي
  social-preview.png (1200×630): اسم القالب + domain + لوحة الألوان
  mockup (اختياري): على laptop + mobile
"""
```

### Node 30: BUILD_VALIDATE

```python
"""
فحص شامل قبل الاختبار:

□ كل ملفات file_manifest موجودة
□ theme.json صالح + schema v3 + يلتزم بـ theme_contract
□ WooCommerce templates موجودة (إن Commerce domain)
□ COD form + COD_SECURITY_GATE passed (إن COD)
□ WooCommerce emails في /emails/ (إن Woo)
□ experience_mode محترم — JS budget لم يتجاوز
□ print.css موجود (إن COD / إن Woo)
□ inc/seo.php موجود + Schema.org صحيح للـ domain

ملفات حرجة (Checkpoint إلزامي عند فشلها):
  theme.json / style.css / functions.php
  parts/header.html / parts/footer.html / templates/home.html
  templates/woocommerce/shop.html + single-product.html (إن Woo)
  inc/cod-quick-order.php (إن COD)

Scoring Formula:
  RTL_SCORE           = 100 - (10×critical_rtl)   - (2×warning_rtl)
  ACCESSIBILITY_SCORE = 100 - (15×contrast_fail)  - (3×missing_aria)   - (2×heading_order)
  PERFORMANCE_SCORE   = 100 - (10×js_over_budget) - (1×css_over_50kb)  - (2×too_many_fonts)
  SECURITY_SCORE      = 100 - (30×xss)            - (10×missing_nonce) - (5×missing_escape) - (20×cod_gate_fail)
  WP_COMPLIANCE_SCORE = 100 - (20×block_markup_error) - (10×missing_textdomain)
  SEO_SCORE           = 100 - (20×missing_schema) - (10×missing_hreflang) - (5×missing_og)
  TESTSPRITE_SCORE    = 100 - (15×ui_fail) - (10×rtl_fail) - (5×woo_fail) - (5×cod_fail) - (3×a11y_fail)
  FINAL_SCORE = avg(RTL, ACCESSIBILITY, PERFORMANCE, SECURITY, WP_COMPLIANCE, SEO, TESTSPRITE)
"""
```

### Node 30.1: CHILD_THEME_GATE

```python
"""
يضمن أن القالب قابل للتوريث بدون كسر التحديثات.
القوالب التجارية تُباع للمطورين الذين يبنون child themes.

□ CSS في /styles/ لا يستخدم !important بشكل مفرط (max 5 استخدامات)
□ theme.json يُعرِّف settings بشكل صريح (لا يعتمد على defaults مخفية)
□ كل custom functions في namespace: {theme_slug}_
□ لا hardcoded paths — استخدم get_template_directory_uri() دائماً
□ wp_enqueue_scripts يستخدم get_template_directory_uri() + versioning
□ لا direct DB calls خارج $wpdb->prepare()
□ /patterns/ كلها مُسجَّلة عبر register_block_pattern() + قابلة للإلغاء

المخرج: /docs/child-theme-guide.md
  يشرح: ما يمكن override / ما يُعاد تعريفه / نقاط التوسعة المتاحة
"""
```

### Node 31: WP_INSTALL_SMOKE_TEST

```python
"""
□ تفعيل القالب بدون PHP errors
□ الصفحة الرئيسية تُحمَّل (HTTP 200)
□ WooCommerce يتفعَّل بدون تعارض (إن Woo)
□ demo-content.xml يُستورَد بنجاح
□ لا 404 في الأصول (CSS/JS/Images)
□ COD form يظهر في single-product (إن COD)
□ WooCommerce emails تُرسَل باتجاه RTL (إن Woo)
"""
```

### Node 32: TESTSPRITE_SCAN

```python
"""
سيناريوهات الاختبار الكاملة:

١. UI Interactions:
   □ كل أزرار CTA قابلة للنقر + تستجيب
   □ القائمة تعمل على الجوال (hamburger)
   □ النماذج تُرسَل بدون خطأ
   □ لا روابط 404
   □ الصور تُحمَّل بدون broken images

٢. RTL Behavior:
   □ direction=rtl واضح
   □ القائمة تبدأ من اليمين
   □ الأزرار والعناصر في الجهة الصحيحة
   □ الأيقونات الاتجاهية معكوسة صح
   □ أرقام الهاتف والأسعار: LTR داخل RTL
   □ النص العربي لا يتقطع

٣. WooCommerce Flow (إن Woo):
   □ صفحة المتجر تعرض المنتجات
   □ إضافة منتج للسلة تعمل
   □ Checkout fields بترتيب RTL صحيح
   □ بوابات الدفع الخليجية ظاهرة
   □ إيميل تأكيد الطلب يصل بـ RTL

٤. COD Flow (إن COD):
   □ النموذج يظهر في صفحة المنتج
   □ Honeypot مخفي + لا يقبل Tab
   □ إرسال ناجح → رسالة نجاح عربية
   □ Rate limit: الإرسال الرابع → رسالة خطأ
   □ Order يظهر في WooCommerce Admin
   □ print.css: Ctrl+P يُظهر فاتورة نظيفة

٥. Accessibility:
   □ التنقل بـ Tab بالترتيب الصحيح
   □ Focus states مرئية
   □ لا عناصر مخفية يقرأها Screen Reader

٦. Performance Smoke:
   □ الصفحة الرئيسية < 5 ثوانٍ (محلي)
   □ لا console errors في JavaScript
   □ لا JS يتجاوز الـ budget (10KB أو 35KB)

٧. SEO Smoke:
   □ Schema.org markup موجود
   □ hreflang موجود
   □ og:locale = ar_SA
"""
```

### Node 33: OPS_GATES

```python
OPS_DEFAULTS = {
    "MAX_TOOL_CALLS":          150,
    "MAX_REVIEW_ROUNDS":       5,
    "MAX_FIX_ATTEMPTS":        3,
    "MAX_COD_FIX_ATTEMPTS":    2,
    "MAX_TESTSPRITE_CYCLES":   2,
    "MAX_TOKENS_IN":           200_000,
    "MAX_TOKENS_OUT":          150_000,
    "COST_WARNING_USD":        5.00,
    "COST_HARD_LIMIT_USD":     15.00,
    "LATENCY_WARNING_MS":      60_000,
    "NODE_LATENCY_WARNING_MS": 15_000,
    "MIN_FINAL_SCORE":         85,
    "MIN_TESTSPRITE_SCORE":    85,
}

def load_ops_config() -> dict:
    config = dict(OPS_DEFAULTS)
    for key in OPS_DEFAULTS:
        val = os.getenv(key)
        if val is not None:
            config[key] = type(OPS_DEFAULTS[key])(val)
    return config

def run_ops_gates(state: ThemeState) -> ThemeState:
    cfg = load_ops_config()
    issues, warns = [], []

    # ١. Artifact Completeness
    missing = [f for f in state["file_manifest"] if state["generated_files"].get(f["path"]) is None]
    if missing: issues.append(f"ملفات ناقصة: {missing}")
    if not state.get("zip_path") or not Path(state["zip_path"]).exists():
        issues.append("ZIP غير موجود أو تالف")
    for doc in ["docs/demo-guide.md","docs/licenses.md","docs/test-results.md","docs/child-theme-guide.md","README.md"]:
        if doc not in state["generated_files"]: warns.append(f"ملف موثَّق ناقص: {doc}")

    # ٢. Cost Controls
    if state["tool_calls_count"] > cfg["MAX_TOOL_CALLS"]:
        warns.append(f"tool_calls={state['tool_calls_count']} تجاوز MAX={cfg['MAX_TOOL_CALLS']}")
    if state.get("cost_estimate") and state["cost_estimate"] > cfg["COST_HARD_LIMIT_USD"]:
        issues.append(f"التكلفة ${state['cost_estimate']:.2f} تجاوزت الحد الصارم")
    elif state.get("cost_estimate") and state["cost_estimate"] > cfg["COST_WARNING_USD"]:
        warns.append(f"التكلفة ${state['cost_estimate']:.2f} تجاوزت حد التحذير")

    # ٣. Performance Metrics
    if state["latency_total_ms"] > cfg["LATENCY_WARNING_MS"]:
        warns.append(f"latency={state['latency_total_ms']}ms تجاوز الحد")

    # ٤. Quality Gates
    if state["quality_scores"].get("final",0) < cfg["MIN_FINAL_SCORE"]:
        issues.append(f"FINAL_SCORE أقل من {cfg['MIN_FINAL_SCORE']}")
    if (state.get("testsprite_score") or 0) < cfg["MIN_TESTSPRITE_SCORE"]:
        issues.append(f"TESTSPRITE_SCORE أقل من {cfg['MIN_TESTSPRITE_SCORE']}")

    # ٥. Package Hash
    if state.get("zip_path") and Path(state["zip_path"]).exists():
        import hashlib
        state["package_hash"] = "sha256:" + hashlib.sha256(Path(state["zip_path"]).read_bytes()).hexdigest()

    # ٦. ops_report
    state["ops_report"] = {
        "run_id": state["run_id"], "build_version": state["build_version"],
        "thresholds_used": cfg, "issues": issues, "warnings": warns,
        "metrics": {
            "total_tokens_in": state["total_tokens_in"], "total_tokens_out": state["total_tokens_out"],
            "tool_calls_count": state["tool_calls_count"], "latency_total_ms": state["latency_total_ms"],
            "cost_estimate": state.get("cost_estimate"),
        },
        "scores": state["quality_scores"],
        "package_hash": state.get("package_hash"),
        "passed": len(issues) == 0,
    }

    state["status"] = "ops_checkpoint_required" if issues else "ops_passed"
    if issues: state["errors"].extend(issues)
    else: state["warnings"].extend(warns)
    return state
```

### Node 33.5: DELIVERY_POLICY

يُشغَّل بعد OPS_GATES مباشرة. يحسم سؤالاً واحداً بشكل لا لبس فيه:
**"نُسلّم أم نوقف؟"** — لا يترك القرار للوكيل ولا للصدفة.

```python
DELIVERY_POLICY = {

    # ── أولوية المراجعات عند التعارض ─────────────────────────────
    # Gate أعلى في القائمة تحسم دائماً على ما تحتها
    "review_priority": [
        "SECURITY",           # XSS / CSRF / SQL injection
        "FUNCTION_WHITELIST", # دوال مخترعة
        "PHPSTAN",            # أخطاء PHP صامتة
        "COD_SECURITY",       # nonce + rate-limit + honeypot
        "RTL",                # انكسار اتجاه واضح
        "ACCESSIBILITY",      # contrast + aria
        "WP_COMPLIANCE",      # block markup + text domain
        "SEO",                # schema + hreflang
        "WPCS",               # معايير تنسيق الكود
        "STYLE",              # اقتراحات بصرية
    ],

    # ── Hard Blocks: تمنع التسليم مطلقاً ─────────────────────────
    "hard_blocks": [
        {
            "id":        "security_fail",
            "condition": lambda s: s["quality_scores"].get("security", 0) < 100,
            "message":   "فشل أمني — XSS أو CSRF أو SQL غير محمي",
        },
        {
            "id":        "cod_security_fail",
            "condition": lambda s: s["cod_enabled"] and not s["cod_security_gate_passed"],
            "message":   "COD Security Gate فشل — nonce أو rate-limit أو honeypot مفقود",
        },
        {
            "id":        "rtl_critical",
            "condition": lambda s: s["quality_scores"].get("rtl", 0) < 85,
            "message":   "RTL منكسر في عناصر حرجة",
        },
        {
            "id":        "score_too_low",
            "condition": lambda s: s["quality_scores"].get("final", 0) < 85,
            "message":   "FINAL_SCORE أقل من 85",
        },
        {
            "id":        "testsprite_fail",
            "condition": lambda s: (s.get("testsprite_score") or 0) < 85,
            "message":   "TestSprite أقل من 85",
        },
        {
            "id":        "hallucinated_functions",
            "condition": lambda s: s.get("hallucinated_functions_count", 0) > 0,
            "message":   "دوال WordPress/WooCommerce مخترعة لم تُصلَح",
        },
        {
            "id":        "parser_failures",
            "condition": lambda s: s.get("parser_failure_unresolved", False),
            "message":   "OUTPUT_PARSER فشل ولم يُحَل — كود غير نظيف",
        },
    ],

    # ── Soft Warnings: تُسلَّم مع تحذير في الشهادة ──────────────
    "soft_warnings": [
        {
            "id":        "score_below_90",
            "condition": lambda s: 85 <= s["quality_scores"].get("final", 0) < 90,
            "message":   "FINAL_SCORE بين 85-90 — يُنصح بمراجعة بشرية",
        },
        {
            "id":        "performance_low",
            "condition": lambda s: s["quality_scores"].get("performance", 0) < 85,
            "message":   "أداء أقل من المستهدف — JS أو CSS قد يحتاج تحسين",
        },
        {
            "id":        "seo_incomplete",
            "condition": lambda s: s["quality_scores"].get("seo", 0) < 85,
            "message":   "SEO غير مكتمل — Schema.org أو hreflang يحتاج مراجعة",
        },
        {
            "id":        "high_cost",
            "condition": lambda s: (s.get("cost_estimate") or 0) > 10,
            "message":   "تكلفة Run مرتفعة — راجع fix_cycles وعدد الملفات",
        },
    ],
}

def can_deliver(state: ThemeState) -> dict:
    # تحقق من الـ Hard Blocks
    for block in DELIVERY_POLICY["hard_blocks"]:
        if block["condition"](state):
            return {
                "deliver": False,
                "block_id": block["id"],
                "message":  block["message"],
            }

    # تجميع الـ Soft Warnings
    active_warnings = [
        w for w in DELIVERY_POLICY["soft_warnings"]
        if w["condition"](state)
    ]

    return {
        "deliver":  True,
        "clean":    len(active_warnings) == 0,
        "warnings": [w["message"] for w in active_warnings],
        "label":    "✦ جاهز للبيع" if not active_warnings else "✦ جاهز مع تحفظات",
    }
```

### Node 34: PACKAGE

يستدعي `can_deliver()` أولاً — إن فشل يُوقف PACKAGE ويُفعّل HUMAN_CHECKPOINT.
إن نجح يُشغّل `QUALITY_BADGE_GEN` ثم يبني الحزمة.

#### Node 34.1: QUALITY_BADGE_GEN

```python
def generate_quality_badge(state: ThemeState) -> dict:
    """
    يحوّل نتائج Gates إلى شهادة جودة مرئية داخل المنتج.
    الهدف: جعل الاستثمار في الجودة مرئياً للمشتري — لا مجرد تقارير داخلية.
    """
    scores  = state["quality_scores"]
    delivery= can_deliver(state)

    badge = {
        "theme":    state["theme_name_ar"],
        "version":  state["build_version"],
        "date":     datetime.utcnow().strftime("%Y-%m-%d"),
        "label":    delivery["label"],
        "criteria": {
            "RTL والعربية":    {"score": scores.get("rtl",0),
                                "status": "✓" if scores.get("rtl",0) >= 95 else "~"},
            "الأمان":           {"score": scores.get("security",0),
                                "status": "✓" if scores.get("security",0) == 100 else "✗"},
            "WooCommerce":      {"score": state.get("testsprite_score",0),
                                "status": "✓" if (state.get("testsprite_score",0) >= 85) else "~"},
            "COD":              {"score": None,
                                "status": "✓" if state.get("cod_security_gate_passed") else ("—" if not state["cod_enabled"] else "✗")},
            "الأداء":           {"score": scores.get("performance",0),
                                "status": "✓" if scores.get("performance",0) >= 85 else "~"},
            "SEO العربي":       {"score": scores.get("seo",0),
                                "status": "✓" if scores.get("seo",0) >= 85 else "~"},
            "إمكانية الوصول":   {"score": scores.get("accessibility",0),
                                "status": "✓" if scores.get("accessibility",0) >= 85 else "~"},
        },
        "warnings": delivery.get("warnings", []),
        "testsprite_date": state.get("testsprite_results", {}).get("date"),
    }

    # ثلاثة ملفات مُولَّدة:
    write_svg_badge(badge)     # → /docs/quality-badge.svg
    write_json_report(badge)   # → /docs/quality-report.json
    inject_readme_section(badge, state["output_path"])  # → يُدمج في README.md

    return badge


# شكل القسم المُضاف لـ README.md تلقائياً:
README_BADGE_TEMPLATE = """
## ✦ شهادة جودة القالب

| المعيار | الحالة | الدرجة |
|---------|--------|--------|
| RTL والعربية | {rtl_status} مُتحقَّق | {rtl_score}/100 |
| الأمان | {sec_status} خالٍ من XSS/CSRF | {sec_score}/100 |
| WooCommerce | {woo_status} تدفق كامل | {woo_score}/100 |
| COD | {cod_status} محمي (nonce + rate-limit + honeypot) | — |
| الأداء | {perf_status} JS ≤ {js_kb}KB | {perf_score}/100 |
| SEO العربي | {seo_status} Schema.org + hreflang | {seo_score}/100 |
| إمكانية الوصول | {a11y_status} WCAG AA | {a11y_score}/100 |

> اختُبر بـ TestSprite — {test_date} | بُني بـ {build_version}
{warnings_section}
"""
```

#### بنية حزمة التسليم الكاملة

```
/output/{theme_slug}-v{version}/
├── {theme_slug}.zip
├── README.md              ← يشمل قسم "شهادة الجودة" مُولَّد تلقائياً
├── CHANGELOG.md
├── design-tokens.json
├── build_info.json        ← hash + ops metrics + scores + delivery_status
├── demo-content.xml
├── /styles/               ← light.json + dark.json + seasonal.json
├── /docs/
│   ├── quality-badge.svg  ← ✦ جديد — شهادة الجودة المرئية
│   ├── quality-report.json← ✦ جديد — تقرير تفصيلي لكل Gate
│   ├── demo-guide.md
│   ├── licenses.md
│   ├── test-results.md
│   ├── ops-report.json
│   ├── child-theme-guide.md
│   └── cod-setup.md
└── /assets/images/demo/
```

### Nodes 35-36: MEMORY_SAVE + LANGSMITH_TRACE_CLOSE

```python
"""
Node 35: MEMORY_SAVE
  يحفظ الدروس: fix cycles / RTL patterns / COD issues / TestSprite patterns
  يُحدث: projects table في SQLite
  يُحدث: Golden Snapshots للـ domain إن كانت النتائج ≥ 95

Node 36: LANGSMITH_TRACE_CLOSE
  يُغلق الـ Trace بجميع النتائج:
  final_score + readiness_level + zip_path + package_hash + ops_report + end_time
"""
```


---

## ٦. Human-in-the-Loop — نظام التوقف الذكي

### المبدأ

الوكيل يُقدِّر المخاطرة ويتوقف عند الحاجة فقط. التوقف يُحسب بـ `risk_score` لا بقاعدة ثابتة.

### نقاط التوقف الثلاث

| النقطة | المكان | شرط التفعيل |
|--------|--------|-------------|
| Checkpoint 1 | بعد THEME_PLAN | `risk_score ≥ 0.35` |
| Checkpoint 2 | بعد العينة التمثيلية | `risk ≥ 0.35` أو `rtl_issues > 0` أو `design_score < 80` |
| Checkpoint 3 | بعد BUILD_VALIDATE | `score < 85` أو `failed_files > 0` |

### Checkpoints إلزامية بغض النظر عن الـ risk

```python
must_checkpoint = (
    cod_security_gate_failed_after_max_attempts
    or ops_gates_cost_exceeded_hard_limit
    or critical_file_failed_after_max_fix_attempts
    or phpstan_critical_issues_unresolved
    or function_whitelist_gate_failed_repeatedly
    or semantic_diff_detected_regression
)
```

### خيارات رد المستخدم

| الخيار | الإجراء |
|--------|---------|
| ✅ وافق | `resume_node = next_node` |
| ✏️ عدّل + ملاحظات | `APPLY_HUMAN_FEEDBACK` |
| 🔁 أعد توليد [ملف] | `files_to_regenerate = [file]` |
| 🧩 اختر [بديل] | `selected_alternative = X` |
| ⛔ أوقف | `status = "cancelled"` |

---

## ٧. بنية الـ State الكاملة

```python
from typing import TypedDict, List, Optional, Dict, Any

class ThemeState(TypedDict):
    # المدخلات
    user_input:         Dict[str, Any]
    normalized_input:   Dict[str, Any]

    # الهوية
    theme_slug:         str
    theme_name_ar:      str
    theme_name_en:      str
    text_domain:        str
    build_version:      str
    market_mode:        str

    # Cluster / Domain
    cluster:            str
    domain:             str
    domain_profile:     Dict[str, Any]
    cluster_profile:    Dict[str, Any]
    multipurpose_mode:  bool
    woocommerce_enabled: bool

    # Theme Contract
    theme_contract:     Dict[str, Any]

    # Experience Mode
    experience_mode:               str
    js_budget_kb:                  int
    animation_policy:              str
    intersection_observer_allowed: bool
    parallax_allowed:              bool
    prefers_reduced_motion_enforced: bool
    css_transition_max_ms:         int

    # COD
    cod_enabled:              bool
    cod_quick_order_enabled:  bool
    cod_form_config:          Dict[str, Any]
    cod_security_gate_passed: bool
    cod_results:              Optional[Dict]

    # spec-kit
    speckit_spec:          Optional[str]
    speckit_plan:          Optional[str]
    speckit_tasks:         Optional[str]
    speckit_project_path:  Optional[str]
    speckit_feature_path:  Optional[str]
    speckit_clarify_count: int

    # خطة القالب
    theme_spec:             Dict[str, Any]
    design_tokens:          Dict[str, Any]
    file_manifest:          List[Dict]
    file_count_estimate:    int
    critical_files:         List[str]
    architectural_alternatives: int
    spec_plan_conflicts:    List[str]

    # RAG
    rag_context_for_file:   Optional[str]

    # Style Variations
    style_variations_enabled: bool
    style_variations_list:    List[str]
    style_variations_files:   List[str]

    # Demo
    demo_content_enabled:  bool
    demo_content_level:    str
    demo_manifest:         Optional[Dict]
    demo_images_enabled:   bool
    visual_profile:        Optional[Dict]
    demo_images_map:       Optional[Dict]

    # Brand Assets
    brand_assets_enabled:  bool
    brand_assets_map:      Optional[Dict[str, str]]

    # TestSprite
    testsprite_enabled:        bool
    testsprite_mode:           str
    testsprite_test_scope:     List[str]
    testsprite_auto_fix:       bool
    testsprite_max_fix_cycles: int
    testsprite_results:        Optional[Dict]
    testsprite_fix_count:      int
    testsprite_score:          Optional[int]

    # LangSmith
    langsmith_enabled:      bool
    langsmith_project_name: str
    langsmith_trace_id:     Optional[str]
    langsmith_spans:        List[Dict]

    # التنفيذ
    generated_files:        Dict[str, str]
    current_file:           Optional[str]
    file_owner:             Dict[str, str]     # file_path → gemini/glm/both
    sample_files_done:      bool
    files_to_regenerate:    List[str]

    # Self-Critique
    self_critique_issues:   Dict[str, List]   # file_path → issues

    # نتائج الفحص
    wp_compliance_result:  Optional[Dict]
    phpstan_result:        Optional[Dict]
    security_result:       Optional[Dict]
    claude_review:         Optional[str]
    coderabbit_review:     Optional[str]
    review_log:            List[Dict]

    # التصحيح
    fix_instructions:      Optional[str]
    fix_count:             int
    semantic_diff_results: Dict[str, Dict]    # file_path → diff result

    # Human-in-the-Loop
    checkpoint_preference: str
    checkpoint_stage:      Optional[str]
    checkpoint_id:         Optional[str]
    resume_node:           Optional[str]
    human_feedback:        Optional[str]
    feedback_targets:      List[str]
    risk_score:            float

    # Ops
    run_id:                str
    total_tokens_in:       int
    total_tokens_out:      int
    tool_calls_count:      int
    latency_total_ms:      int
    latency_per_node_ms:   Dict[str, int]
    gate_failures_count:   int
    review_rounds:         int
    cost_estimate:         Optional[float]
    ops_report:            Optional[Dict]
    package_hash:          Optional[str]
    injected_lessons_count: int

    # البيئة
    environment_valid:     bool
    environment_issues:    List[str]

    # التسليم
    output_path:           Optional[str]
    zip_path:              Optional[str]

    # الجودة
    quality_scores:        Dict[str, int]
    readiness_level:       str              # green | yellow | red

    # الحالة
    status:                str
    errors:                List[str]
    warnings:              List[str]

    # الذاكرة
    similar_projects:      List[Dict]
    lessons_learned:       List[str]
    golden_snapshots:      Dict[str, str]  # domain → snapshot path
```

---

## ٨. مواصفات WordPress + WooCommerce + COD

### نوع القالب: Block Theme (FSE) — إلزامي

WordPress 6.5+ / PHP 8.1+ / theme.json v3 / WooCommerce 8.x+ (إن Woo)

### بنية الملفات الكاملة

```
{theme_slug}/
├── style.css
├── functions.php
├── theme.json
├── /templates/
│   ├── index.html / home.html / front-page.html
│   ├── single.html / archive.html / page.html
│   ├── search.html / 404.html
│   └── /woocommerce/           ← Commerce domains فقط
│       ├── shop.html / single-product.html
│       ├── cart.html / checkout.html / my-account.html
├── /parts/
│   ├── header.html / footer.html
│   └── mini-cart.html          ← Woo
├── /patterns/
│   ├── hero-*.php              ← حسب Domain
│   ├── products-grid.php / product-card.php ← Woo
│   └── cod-form.php            ← COD
├── /inc/
│   ├── seo.php                 ← Arabic SEO + Schema.org
│   └── cod-quick-order.php     ← COD Logic
├── /emails/                    ← Woo RTL emails
│   ├── customer-completed-order.php
│   ├── customer-new-order.php
│   └── customer-invoice.php
├── /styles/
│   ├── light.json / dark.json / seasonal.json
├── /assets/
│   ├── /css/
│   │   └── print.css           ← للفواتير
│   └── /js/
│       ├── cod-form.js         ← COD AJAX
│       └── menu.js / animations.js
└── /docs/
    ├── README.md / CHANGELOG.md
    ├── demo-guide.md / licenses.md
    ├── test-results.md / ops-report.json
    └── child-theme-guide.md
```


---

## ٩. مخرجات الوكيل — قالب جاهز للبيع

```
/output/{theme_slug}-v{version}/
├── {theme_slug}.zip
├── README.md
│   ├── وصف القالب + Domain + Cluster
│   ├── شرح 3 style variations مع صور
│   ├── Experience Mode المُستخدَم + السبب
│   ├── دليل إعداد COD Quick Order (إن COD)
│   ├── جدول نتائج TestSprite
│   ├── ملخص ops metrics (درجات + latency)
│   ├── متطلبات التثبيت
│   └── ملاحظات Arabic SEO
├── CHANGELOG.md
├── design-tokens.json
├── build_info.json          ← hash + ops metrics + scores
├── demo-content.xml
├── /styles/
├── /docs/
└── /assets/images/demo/
```

---

## ١٠. بوابات الجودة

| Gate | المسؤول | شرط PASS |
|------|---------|----------|
| SELF_CRITIQUE | Gemini/GLM | لا issues حرجة |
| FUNCTION_WHITELIST | RAG DB | صفر functions مخترعة |
| WP_COMPLIANCE | Scan | لا block errors + theme header كامل |
| PHPSTAN | PHPStan level 5 | لا critical type errors |
| SECURITY | Scan | صفر XSS + Nonce موجود |
| CLAUDE_REVIEW | Claude API | لا critical RTL/A11y |
| CODERABBIT_REVIEW | CodeRabbit | لا WPCS violations حرجة |
| SEMANTIC_DIFF | Diff engine | لا regression بعد FIX |
| COD_SECURITY | Security check | nonce + rate_limit + honeypot |
| ARABIC_NUMERICS | Scan | أسعار في <bdi> + dir=ltr |
| STYLE_VARIATIONS | Contrast check | contrast ≥ 4.5 لكل variation |
| CHILD_THEME | Scan | namespace صحيح + لا hardcoded paths |
| BUILD_VALIDATE | Composite | FINAL_SCORE ≥ 85 |
| TESTSPRITE | TestSprite MCP | TESTSPRITE_SCORE ≥ 85 |
| OPS_GATES | ops_report | لا issues حرجة |

---

## ١١. الذاكرة والحالة

### قاعدة البيانات المحلية (SQLite)

```sql
-- المشاريع السابقة
CREATE TABLE projects (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       TEXT UNIQUE,
    theme_slug   TEXT,
    cluster      TEXT,
    domain       TEXT,
    experience_mode TEXT,
    final_score  INTEGER,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- الدروس المستفادة
CREATE TABLE lessons (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   INTEGER REFERENCES projects(id),
    domain       TEXT,
    cluster      TEXT,
    experience_mode TEXT,
    lesson_text  TEXT,
    relevance_tags TEXT,    -- JSON array
    fix_cycles   INTEGER DEFAULT 0,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Golden Snapshots لكل Domain
CREATE TABLE snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    domain       TEXT UNIQUE,
    file_path    TEXT,       -- /project-state/snapshots/{domain}/
    final_score  INTEGER,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Golden Snapshot System

```python
"""
بعد أول Run ناجح بدرجة ≥ 95 لكل Domain:
  يُحفظ Golden Snapshot لـ:
  - theme.json
  - parts/header.html
  - parts/footer.html

في كل Run لاحق لنفس الـ Domain:
  يُقارن SEMANTIC_DIFF الناتج الجديد بالـ Snapshot
  ويكشف لو النموذج نسي شيئاً كان موجوداً
"""
```

### سياسة تنظيف الذاكرة — prune_lessons()

**المشكلة:** بعد 50+ مشروع تتراكم دروس متضاربة. درس صحيح في `perfume_luxury` قد يُلوّث `clinic_medical`. الأخطر: هلوسة مُعززة بالذاكرة أشد خطراً من الهلوسة العادية — لأن النموذج يُطبّقها بثقة.

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class Lesson:
    id:          int
    text:        str
    domain:      str
    cluster:     str
    experience_mode: str
    created_at:  datetime
    usage_count: int   = 0
    helped:      int   = 0   # كم مرة أدى لـ fix أقل
    hurt:        int   = 0   # كم مرة سبق مشكلة بعده
    scope:       str   = "domain_specific"
    # "domain_specific" | "cluster_wide" | "universal"

    @property
    def confidence(self) -> float:
        total = self.helped + self.hurt
        return self.helped / total if total > 0 else 0.5  # neutral لو جديد


def prune_lessons(db) -> dict:
    """
    تُشغَّل تلقائياً كل أسبوع أو بعد كل 20 مشروع.
    """
    lessons  = db.get_all_lessons()
    deleted  = []
    promoted = []

    for lesson in lessons:
        age_days = (datetime.utcnow() - lesson.created_at).days

        # ١. احذف الدروس المتضاربة مع نفسها
        if lesson.confidence < 0.4 and lesson.usage_count >= 3:
            db.delete_lesson(lesson.id)
            deleted.append({"id": lesson.id, "reason": "low_confidence",
                            "text": lesson.text[:60]})
            continue

        # ٢. احذف الدروس القديمة غير المستخدمة
        if age_days > 90 and lesson.usage_count < 3:
            db.delete_lesson(lesson.id)
            deleted.append({"id": lesson.id, "reason": "stale_unused",
                            "text": lesson.text[:60]})
            continue

        # ٣. رفّع scope الدروس المثبَّتة عبر domains متعددة
        if lesson.usage_count > 15 and lesson.confidence > 0.8:
            if lesson.scope == "domain_specific":
                # تحقق: هل استُخدمت في أكثر من domain؟
                domains_used = db.get_lesson_domains(lesson.id)
                if len(domains_used) >= 3:
                    db.update_scope(lesson.id, "cluster_wide")
                    promoted.append({"id": lesson.id, "new_scope": "cluster_wide"})
            elif lesson.scope == "cluster_wide":
                clusters_used = db.get_lesson_clusters(lesson.id)
                if len(clusters_used) >= 3:
                    db.update_scope(lesson.id, "universal")
                    promoted.append({"id": lesson.id, "new_scope": "universal"})

    return {
        "deleted_count":  len(deleted),
        "promoted_count": len(promoted),
        "deleted":        deleted,
        "promoted":       promoted,
    }


def filter_lessons(all_lessons, file, domain, cluster, experience_mode) -> list[str]:
    """
    فلترة ذكية تحترم الـ scope وتمنع التلوث بين الـ domains.
    استبدال للنسخة السابقة.
    """
    universal       = [l for l in all_lessons if l.scope == "universal"
                       and l.confidence >= 0.6]
    cluster_wide    = [l for l in all_lessons if l.scope == "cluster_wide"
                       and l.cluster == cluster and l.confidence >= 0.65]
    domain_specific = [l for l in all_lessons if l.scope == "domain_specific"
                       and l.domain == domain and l.confidence >= 0.5]

    # الأولوية: domain_specific > cluster_wide > universal
    # الحد الأقصى 8 دروس بمجموع 400 token
    pools = [domain_specific, cluster_wide, universal]
    result, tokens = [], 0

    for pool in pools:
        ranked = sorted(pool, key=lambda l: l.confidence * l.usage_count, reverse=True)
        for lesson in ranked:
            text = lesson.text[:120] + "…" if len(lesson.text) > 120 else lesson.text
            t    = len(text) // 4
            if tokens + t > 400: break
            if len(result) >= 8:  break
            result.append(text)
            tokens += t

    return result
```

**تسجيل نتيجة الدرس بعد كل FIX:**

```python
def record_lesson_outcome(lesson_id: int, fix_avoided: bool, db) -> None:
    """
    يُشغَّل بعد كل دورة FIX لتحديث helped/hurt.
    fix_avoided=True  → الدرس ساعد في تجنب مشكلة
    fix_avoided=False → الـ fix حدث رغم الدرس
    """
    if fix_avoided:
        db.increment_helped(lesson_id)
    else:
        db.increment_hurt(lesson_id)
```

---

## ١٢. معالجة الأخطاء والفشل

```python
"""
تصنيف الأخطاء:

🔴 CRITICAL — يُوقف التنفيذ فوراً:
  - أخطاء أمنية (XSS/CSRF/SQL injection)
  - Function مخترعة في ملف حرجة
  - PHPStan: null pointer في WC_Order
  - package_hash مفقود

🟠 HIGH — يُفعّل Checkpoint:
  - FINAL_SCORE < 85
  - COD Security Gate يفشل بعد 2 محاولة
  - Semantic Diff يكتشف regression
  - تكلفة تتجاوز COST_HARD_LIMIT_USD

🟡 MEDIUM — يُضاف للـ warnings + يُستمر:
  - fix_count > MAX بملف non-critical
  - tool_calls يتجاوز MAX_TOOL_CALLS
  - latency يتجاوز الحد

🟢 LOW — يُسجَّل في review_log فقط:
  - WPCS style issues
  - اقتراحات CodeRabbit
  - دروس مستفادة جديدة
"""
```

---

## ١٣. البيئة المحلية

### متطلبات النظام

```bash
# Python
python 3.11+
uv (package manager)
specify-cli (spec-kit)
claude (Claude Code CLI)

# PHP
php 8.1+
phpstan (level 5+)
composer

# WordPress
WordPress 6.5+ محلي (Local WP / XAMPP / Docker)
WooCommerce 8.x+ (للـ Commerce domains)

# Node
node 18+
npm / yarn
```

### متغيرات البيئة

```env
# AI APIs
CLAUDE_API_KEY=sk-ant-...
GLM_API_KEY=...
GEMINI_FRONTEND_API_KEY=...
GEMINI_IMAGE_API_KEY=...
CODERABBIT_API_KEY=...

# RAG
RAG_INDEX_PATH=/path/to/rag/index/
RAG_WP_FUNCTIONS_JSON=/path/to/wp_6.5_functions.json
RAG_WC_HOOKS_JSON=/path/to/wc_8x_hooks.json
RAG_BLOCK_API_JSON=/path/to/gutenberg_blocks_api.json

# Testing & Observability
TESTSPRITE_API_KEY=...
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=arabic-theme-factory
LANGSMITH_TRACING=true

# WordPress Local
WP_LOCAL_PATH=/path/to/wordpress/
WP_LOCAL_URL=http://localhost
WP_TEST_USER=admin
WP_TEST_PASS=...

# Output
OUTPUT_PATH=/path/to/output/

# OPS Controls (كلها اختيارية — القيم الافتراضية في OPS_DEFAULTS)
MAX_FIX_ATTEMPTS=3
MAX_COD_FIX_ATTEMPTS=2
MAX_REVIEW_ROUNDS=5
MAX_TOOL_CALLS=150
MAX_TESTSPRITE_CYCLES=2
MAX_TOKENS_IN=200000
MAX_TOKENS_OUT=150000
COST_HARD_LIMIT_USD=15.00
COST_WARNING_USD=5.00
MIN_FINAL_SCORE=85
MIN_TESTSPRITE_SCORE=85

# Memory Controls
MEMORY_MAX_LESSONS=8
MEMORY_MAX_LESSON_CHARS=120
MEMORY_MAX_INJECT_TOKENS=400

# Demo & Market
DEMO_IMAGE_MAX_KB=200
MARKET_MODE=brand_ready

LOG_LEVEL=INFO
```

---

## ١٤. نظام الإصدارات

```python
"""
build_version = f"{date:%Y%m%d}-{sequence:04d}"
مثال: 20250315-0001

يُخزَّن في:
  /project-state/build_info.json
  build_info.json في حزمة التسليم

التغيير في theme.json يُحدَّث version تلقائياً:
  patch: إصلاح bug
  minor: إضافة feature
  major: تغيير بنيوي
"""
```

---

## ١٥. الذاكرة بين المشاريع

```python
"""
ما يُحفظ بعد كل مشروع ناجح:

١. الدروس المستفادة (lessons):
   - ملفات احتاجت أكثر fix cycles
   - أنماط نجحت في RTL
   - أخطاء COD الشائعة وحلولها
   - TestSprite issues المتكررة
   - performance wins

٢. domain_stats:
   - متوسط fix_cycles لكل domain
   - أكثر الملفات مشكلة لكل domain
   - أفضل design tokens أدت لـ score عالية

٣. Golden Snapshots:
   - theme.json / header.html / footer.html
   - تُحدَّث فقط إن كانت النتائج ≥ 95
"""
```

---

## ١٦. دستور الوكيل

```markdown
# دستور وكيل توليد قوالب WordPress العربية

## الهوية
أنا وكيل متخصص في توليد قوالب WordPress عربية احترافية.
أهدف دائماً لـ: RTL صحيح + أمان كامل + أداء ممتاز + جاهزية بيع فعلية.

## القواعد المطلقة
١. لا أُولّد كوداً يُكذّب عليه المستخدم (لا هلوسة في API names)
٢. لا أتجاوز THEME_CONTRACT بأي سبب
٣. لا أُولّد PHP بدون namespace صحيح
٤. أي مشكلة أمنية → أوقف الملف فوراً
٥. RTL أولاً في كل قرار تصميمي
٦. لا أعيد توليد ملف كامل إن كانت المشكلة في سطور محددة

## ما أُجيده
- Block Theme (FSE) structure كاملة
- WooCommerce integration صحيحة
- RTL logical properties والـ LTR islands الضرورية
- COD forms مع حماية كاملة
- Arabic SEO + Schema.org
- Print styles للفواتير

## ما أتجنبه
- استخدام functions غير موجودة في WordPress/WooCommerce
- hardcoded paths أو colors
- jQuery أو scripts تحجب الـ render
- !important بشكل مفرط
- Lorem Ipsum في demo content
```

---

## ١٧. قائمة التحقق النهائية

### قبل بدء البناء

```
□ theme_slug صالح وفريد
□ cluster + domain محددان بوضوح
□ experience_mode محدد (default: feature_rich)
□ البيئة سليمة: Python + uv + specify-cli + Claude Code + PHP + PHPStan + WP
□ RAG index محدَّث: WP functions + WC hooks + Block API
□ WooCommerce مُفعَّل (إن Commerce domain)
□ APIs تعمل: Claude + GLM + Gemini + CodeRabbit + TestSprite + LangSmith
□ دروس المشاريع السابقة محملة
□ market_mode محدد (default: brand_ready)
□ cod.enabled محدد + abuse_protection config صحيح
```

### أثناء البناء

```
□ LANGSMITH_TRACE_INIT نجح + trace_id في State
□ THEME_CONTRACT_GEN أنشأ theme_contract.json
□ CLUSTER_DOMAIN_SELECTOR حمّل profiles كاملة
□ SEO_SCAFFOLD أنشأ inc/seo.php + Schema صحيح
□ WP_SCAFFOLD أنشأ شجرة المجلدات كاملة
□ SPECKIT_PATH_DETECTOR حدد المسار الصحيح
□ EXPERIENCE_MODE_DECIDER ثبّت js_budget_kb
□ STYLE_VARIATION_ENGINE أنشأ /styles/*.json
□ كل ملف: SELF_CRITIQUE → FUNCTION_WHITELIST → PHPSTAN → SECURITY → CLAUDE → CODERABBIT
□ SEMANTIC_DIFF يُشغَّل بعد كل FIX
□ COD_MODULE_BUILDER + COD_SECURITY_GATE PASS (إن COD)
□ WOO_EMAIL_RTL أنشأ /emails/ (إن Woo)
□ ARABIC_NUMERICS_GATE PASS
□ fix_count ≤ 3 لكل ملف
```

### بعد اكتمال البناء

```
□ /styles/ variations صالحة + contrast ≥ 4.5
□ demo-content.xml صالح + لا Lorem Ipsum
□ صور demo WebP ≤ 200KB
□ screenshot.png 1200×900 / social-preview.png 1200×630
□ docs/ مكتملة (7 ملفات)
□ FINAL_SCORE ≥ 85 (شامل SEO_SCORE)
□ ZIP يُنصَّب بلا PHP errors
□ package_hash محسوب
□ CHILD_THEME_GATE PASS
```

### اختبار TestSprite

```
□ UI Interactions: صفر broken
□ RTL Behavior: صفر أخطاء حرجة
□ WooCommerce Flow: checkout يعمل + emails RTL صح
□ COD Flow: إرسال + rate-limit + RTL صحيح
□ Print: Ctrl+P يُظهر فاتورة نظيفة (إن COD/Woo)
□ SEO: Schema.org + hreflang موجودان
□ TESTSPRITE_SCORE ≥ 85
```

### Ops & LangSmith

```
□ OPS_GATES PASS
□ ops-report.json موجود في /docs/
□ LangSmith Trace مُغلق
□ build_info.json يشمل: ops metrics + package_hash + scores
□ MEMORY_SAVE اكتمل: lessons + domain_stats + snapshots
```

---

## ١٨. التشغيل والمراقبة

### هيكل ops-checklist.md

```markdown
# ops-checklist — {theme_slug} — {build_id}

## ١. Artifact Integrity
- [ ] كل ملفات file_manifest موجودة
- [ ] ZIP سليم (فك الضغط بلا أخطاء)
- [ ] package_hash: sha256:{hash}
- [ ] README.md يشمل كل أقسامه

## ٢. Anti-Hallucination Gates
- [ ] FUNCTION_WHITELIST_GATE: صفر functions مخترعة
- [ ] PHPSTAN level 5: صفر critical errors
- [ ] SELF_CRITIQUE: لا issues حرجة في أي ملف

## ٣. Quality Gates Summary
| Gate               | Status    | Score | Notes |
|--------------------|-----------|-------|-------|
| WP Compliance      | ✅ PASS   | —     | —     |
| Security           | ✅ PASS   | —     | —     |
| RTL                | ✅ PASS   | 98    | —     |
| Accessibility      | ✅ PASS   | 92    | —     |
| Performance        | ✅ PASS   | 88    | JS: 28KB |
| SEO                | ✅ PASS   | 90    | Schema.org |
| Style Variations   | ✅ PASS   | —     | —     |
| Arabic Numerics    | ✅ PASS   | —     | —     |
| Child Theme        | ✅ PASS   | —     | —     |
| TestSprite         | ✅ PASS   | 94    | 2 warnings |
| COD Security       | ✅ PASS   | —     | —     |
| OPS                | ✅ PASS   | —     | —     |

## ٤. Cost Controls
- [ ] tool_calls_count: {value} / 150
- [ ] review_rounds: {value} / 5
- [ ] cost_estimate: ${value}

## ٥. Human Approvals
- [ ] Checkpoint 1 (Plan): ✅ / ⏭️ skipped
- [ ] Checkpoint 2 (Sample): ✅ / ⏭️ skipped
- [ ] Checkpoint 3 (Final): ✅ Approved

## ٦. LangSmith
- [ ] Trace ID: {trace_id}
- [ ] Trace URL: https://smith.langchain.com/...
- [ ] Status: Closed ✅
```

### LangSmith — التكامل التقني

```python
from langsmith import Client
import os

ls_client = Client(api_key=os.environ["LANGSMITH_API_KEY"])

def init_trace(state: ThemeState) -> ThemeState:
    run = ls_client.create_run(
        name=f"theme-build-{state['theme_slug']}",
        project_name=state["langsmith_project_name"],
        inputs={
            "cluster": state["cluster"], "domain": state["domain"],
            "experience_mode": state["experience_mode"],
            "market_mode": state["market_mode"],
        }
    )
    state["langsmith_trace_id"] = run.id
    return state

def log_node_span(state, node_name, inputs, outputs, metrics):
    if not state["langsmith_enabled"]: return
    ls_client.create_run(
        name=node_name,
        project_name=state["langsmith_project_name"],
        parent_run_id=state["langsmith_trace_id"],
        inputs=inputs, outputs=outputs, extra={"metrics": metrics}
    )
```

### ما يُرصد في LangSmith

| البيانات | الوصف |
|----------|-------|
| Prompts | كل prompt أُرسل لـ Gemini / GLM / Claude |
| THEME_CONTRACT | نسخة العقد المُستخدَمة |
| SELF_CRITIQUE | نتائج كل مراجعة ذاتية |
| FUNCTION_WHITELIST | functions مكتشفة + مخترعة |
| PHPSTAN | تقارير الأخطاء الصامتة |
| Gate Results | PASS/FAIL + السبب لكل Gate |
| SEMANTIC_DIFF | اكتشافات regression |
| Fix Cycles | عدد دورات التصحيح لكل ملف |
| Token Usage | in/out لكل Node |
| Latency | وقت كل Node بالمللي ثانية |
| Final Score | الدرجة النهائية + readiness_level |


---

## ١٩. وضع التحديث — Update Mode

### لماذا التحديث يختلف جذرياً عن البناء من الصفر

البناء من الصفر = صفحة بيضاء. التحديث = نظام حي فيه بيانات حقيقية وعملاء فعليون وكود بشري قد يكون مخفياً. الخطأ هنا لا يُمسح بـ Ctrl+Z.

| البُعد | البناء من الصفر | التحديث |
|--------|----------------|---------|
| نقطة البداية | صفحة بيضاء | نظام حي بداخله قرارات بشرية |
| الفشل | إعادة المحاولة | موقع مكسور + عملاء غاضبون |
| HUMAN_CHECKPOINT | اختياري (risk-based) | إلزامي دائماً |
| file_owner | GLM أو Gemini | قد يكون "المطور القديم" |
| Regression | لا يوجد | Regression Suite إلزامي |
| SACRED_CODE | لا يوجد | كود بشري يجب الحفاظ عليه |
| Staging | اختياري | إلزامي قبل production |

### الأسئلة الجوهرية قبل أي تحديث

```
١. ما مصدر القالب الحالي؟
   □ قالب ولّده هذا الوكيل سابقاً      ← لدينا State + Memory كاملة
   □ قالب WordPress تجاري خارجي        ← نبدأ من صفر في الفهم
   □ قالب مخصص يدوي                   ← الأخطر

٢. ما طبيعة التحديث؟
   □ تحديث بصري (ألوان/خطوط/spacing)
   □ إضافة feature جديدة (COD لقالب ليس فيه)
   □ ترقية Domain (من generic → perfume_luxury)
   □ ترقية WordPress/WooCommerce نفسه
   □ إصلاح bug محدد

٣. هل الموقع حي (production)؟
   □ نعم → Staging بيئة إلزامية أولاً
   □ لا  → أقل خطورة لكن Staging ما زالت مُفضَّلة
```

### معمارية وضع التحديث

```
INPUT: رابط القالب الحالي / ملف ZIP
        ↓
 A. THEME_ANALYZER       ← يفهم القالب الحالي كاملاً
        ↓
 B. SACRED_CODE_EXTRACTOR ← يحمي الكود البشري
        ↓
 C. DIFF_PLANNER         ← يحدد ماذا يتغير وماذا يبقى
        ↓
 D. RISK_ASSESSOR_UPDATE ← أخطر من البناء الجديد
        ↓
 E. HUMAN_CHECKPOINT     ← إلزامي دائماً
        ↓
 F. STAGING_DEPLOY       ← لا تلمس production أبداً
        ↓
 G. SELECTIVE_UPDATE     ← يُعدّل الملفات المتأثرة فقط
          ↓
     [نفس حلقة: SELF_CRITIQUE → FUNCTION_WHITELIST → PHPSTAN → SECURITY → CLAUDE → CODERABBIT → FIX → SEMANTIC_DIFF]
        ↓
 H. REGRESSION_SUITE     ← ما كان يعمل لا يزال يعمل
        ↓
 I. HUMAN_FINAL_APPROVAL ← إلزامي قبل production
        ↓
OUTPUT: patch + migration guide + rollback instructions
```

### Node A: THEME_ANALYZER

```python
"""
يقرأ القالب الحالي ويبني خريطة المعرفة الكاملة.
"""

def analyze_theme(theme_path: str, state: UpdateState) -> dict:

    if state["source_theme_origin"] == "agent":
        # لدينا State كاملة — نحمّلها مباشرة
        previous_state = load_project_state(state["source_theme_slug"])
        return {
            "known_contract":      previous_state["theme_contract"],
            "known_domain":        previous_state["domain"],
            "known_experience":    previous_state["experience_mode"],
            "overridden_templates": [],
            "custom_code_blocks":   [],
        }

    # قالب خارجي أو مخصص — تحليل شامل
    structure_map = {
        "custom_hooks":     extract_custom_hooks(theme_path),
        "child_theme":      has_child_theme(theme_path),
        "customizer_data":  extract_customizer_options(theme_path),
        "active_plugins":   get_dependent_plugins(theme_path),
        "db_meta":          detect_theme_metas(theme_path),
        "overridden_woo_templates": find_overridden_woo_templates(theme_path),
        "hardcoded_values": detect_hardcoded_paths_colors(theme_path),
    }

    # أخطر ما يمكن اكتشافه
    if structure_map["overridden_woo_templates"]:
        state["warnings"].append(
            f"⚠️ WooCommerce templates معدَّلة يدوياً: {structure_map['overridden_woo_templates']}\n"
            "ستُفقد عند التحديث إن لم تُعالَج. HUMAN_CHECKPOINT إلزامي."
        )

    return structure_map
```

### Node B: SACRED_CODE_EXTRACTOR

```python
"""
المشكلة الأخطر في التحديث:
  functions.php قد يحتوي كوداً إضافياً يدوياً:
  مثلاً: حقل 'رقم الهوية' إلزامي في Checkout
  إن أعاد النموذج توليد functions.php من الصفر → هذا الكود يختفي
  → كل طلبات الشراء تكسر (حقل مطلوب اختفى)
  → بيانات عملاء مفقودة
"""

SACRED_CODE_MARKERS = [
    "// custom",
    "// DO NOT REMOVE",
    "// IMPORTANT",
    "// يدوي",
    "// مخصص",
    "// Client custom",
]

def extract_sacred_code(file_content: str, file_path: str) -> list[dict]:
    sacred_blocks = []
    lines = file_content.split("\n")

    for i, line in enumerate(lines):
        if any(marker in line for marker in SACRED_CODE_MARKERS):
            # استخراج الـ block كاملاً (من الـ comment حتى نهاية الـ function)
            block_start = i
            block_end   = find_block_end(lines, i)
            block_code  = "\n".join(lines[block_start:block_end])

            sacred_blocks.append({
                "file":    file_path,
                "start":   block_start,
                "code":    block_code,
                "marker":  line.strip(),
                "inject":  "end_of_file",  # أين يُحقن في الكود الجديد
            })

    return sacred_blocks
```

### Node C: DIFF_PLANNER

```python
"""
يبني جدول التغييرات لكل ملف في القالب:
"""

UPDATE_ACTIONS = {
    "SKIP":        "لا تغيير مطلوب",
    "PATCH":       "تعديل أسطر محددة",
    "REGENERATE":  "إعادة توليد كاملة",
    "MERGE":       "دمج القديم مع الجديد",
    "HUMAN_REVIEW":"لا يُمسّ بدون موافقة",
}

def plan_diff(update_type: str, domain_change: bool, sacred_files: list) -> list[dict]:
    plan = []

    for file in theme_manifest:
        action = "SKIP"
        risk   = "low"

        if update_type == "visual_only":
            if file.endswith(".json") or file.endswith(".css"):
                action = "PATCH"
            # كل PHP → SKIP

        elif update_type == "add_cod":
            if file == "inc/cod-quick-order.php": action = "CREATE"
            if file == "patterns/cod-form.php":   action = "CREATE"
            if file == "functions.php":            action = "MERGE"; risk = "high"
            if file == "templates/woocommerce/single-product.html": action = "PATCH"

        elif update_type == "domain_upgrade":
            if file in ["templates/","patterns/"]: action = "REGENERATE"
            if file == "functions.php":
                action = "MERGE"; risk = "high"
            if file == "theme.json":               action = "PATCH"

        # الكود المقدس → إلزامي HUMAN_REVIEW
        if file in sacred_files:
            action = "HUMAN_REVIEW"; risk = "critical"

        plan.append({
            "file": file, "action": action, "risk": risk,
            "notes": generate_notes(file, action, update_type)
        })

    return plan
```

### Node H: REGRESSION_SUITE

```python
"""
يبني BEFORE_SNAPSHOT قبل أي تغيير ثم يُقارن بعده.

BEFORE_SNAPSHOT يشمل:
  - لقطات شاشة للصفحات الرئيسية (screenshot_pages)
  - قائمة الـ routes التي تُعيد 200
  - نتائج TestSprite الحالية
  - JS console errors قبل التحديث

REGRESSION_CHECK بعد التحديث:
  □ كل صفحة كانت 200 لا تزال 200
  □ لا صور مكسورة جديدة
  □ WooCommerce checkout لا يزال يعمل
  □ COD form (إن كان موجوداً) لا يزال يعمل
  □ لا JS console errors جديدة
  □ Sacred code لا يزال موجوداً وفعّالاً

Visual Diff:
  لكل صفحة كانت في BEFORE_SNAPSHOT:
    diff_score = visual_compare(before_screenshot, after_screenshot)
    إن diff_score > VISUAL_DIFF_THRESHOLD:
      → يُبلَّغ بالفرق + سببه
      → HUMAN_APPROVAL إن كان في صفحة حرجة (home/shop/checkout)
"""
```

### سيناريوهات التحديث العملية

**السيناريو ١ — إضافة COD لقالب موجود**

```
THEME_ANALYZER → يتحقق: هل WooCommerce موجود؟
DIFF_PLANNER   → CREATE: inc/cod-quick-order.php
               → CREATE: patterns/cod-form.php
               → MERGE: functions.php (يُضاف AJAX handler + نضمن sacred code)
               → PATCH: single-product.html (يُضاف Pattern)
               → SKIP: كل الملفات الأخرى
SELECTIVE_UPDATE → ينفّذ فقط الملفات المُحددة
```

**السيناريو ٢ — تحديث بصري فقط**

```
DIFF_PLANNER   → PATCH: style.css + theme.json (tokens فقط)
               → REGENERATE: /styles/light.json + dark.json + seasonal.json
               → SKIP: كل PHP
REGRESSION_SUITE → يتحقق أن التخطيط لم يتأثر
```

**السيناريو ٣ — ترقية Domain**

```
THEME_ANALYZER → خريطة كاملة للـ templates والـ patterns
SACRED_CODE_EXTRACTOR → يحفظ أي كود مخصص في functions.php
DIFF_PLANNER   → REGENERATE: templates + patterns (domain profile جديد)
               → MERGE: functions.php (sacred code يُحقن في النهاية)
               → PATCH: theme.json (tokens جديدة)
               → PATCH: /styles/ (seasonal جديد)
REGRESSION_SUITE → يقارن كل الصفحات + يتحقق من sacred code
```

**السيناريو ٤ — ترقية WordPress/WooCommerce**

```
THEME_ANALYZER → يفحص deprecation warnings في PHP logs
FUNCTION_WHITELIST_GATE → يُشغَّل على كل الملفات بالـ whitelist الجديدة
PHPSTAN → يُشغَّل بالـ PHP version الجديدة
DIFF_PLANNER → PATCH: الملفات التي تستخدم deprecated functions فقط
```


---

## ٢٠. طبقة التفكير والنقد والشفافية

هذه الطبقة لا تُنتج كوداً — تضمن أن كل قرار مدروس، كل افتراض مُختبَر، وكل مخرج قابل للمراجعة.

---

### ٢٠.١ AssumptionChecker — التقييم الذاتي قبل القرار لا بعده

المشكلة الجوهرية: الوكيل الذي لا يعرف ما يفترضه لا يعرف متى يخطئ. كل Node تقف على افتراضات ضمنية لا تقولها — هذا المكوّن يجعلها صريحة ويتحقق منها قبل التنفيذ.

```python
class AssumptionChecker:

    ASSUMPTIONS = {
        "THEME_CONTRACT_GEN": [
            ("domain_profile محمَّل وصالح",
             lambda s: s.get("domain_profile") is not None),
            ("cluster_profile متوافق مع domain_profile",
             lambda s: s["domain_profile"].get("cluster") == s["cluster"]),
        ],
        "GEMINI_CODEGEN": [
            ("theme_contract لم يتغير منذ آخر استخدام",
             lambda s: s["theme_contract"].get("version") == s.get("last_contract_version")),
            ("RAG index يغطي WordPress version المُستهدَف",
             lambda s: rag_version_compatible(s.get("wp_version","6.5"))),
            ("الملف السابق في نفس الـ Domain لم يكسر الـ contract",
             lambda s: len(s.get("contract_violations",[])) == 0),
        ],
        "GLM_CODEGEN": [
            ("PHP version تدعم الـ types المُستخدَمة",
             lambda s: php_version_ok(s.get("php_version","8.1"))),
            ("theme_slug لا يحتوي أحرفاً تكسر transient key",
             lambda s: re.match(r'^[a-z0-9\-]+$', s["theme_slug"]) is not None),
        ],
        "COD_MODULE_BUILDER": [
            ("WooCommerce مُثبَّت فعلاً وليس مجرد موجود في file_manifest",
             lambda s: s.get("woocommerce_verified_installed", False)),
            ("theme_slug لا يتجاوز 30 حرفاً — لأن transient key له حد",
             lambda s: len(s["theme_slug"]) <= 30),
        ],
        "MEMORY_LOAD": [
            ("الدروس المحفوظة من نفس WordPress version الحالية",
             lambda s: lessons_version_compatible(s)),
            ("domain profile لم يتغير منذ حُفظت الدروس",
             lambda s: domain_profile_unchanged(s)),
        ],
        "EXPERIENCE_MODE_DECIDER": [
            ("js_budget_kb محدَّد في State",
             lambda s: s.get("js_budget_kb") is not None),
            ("prefers_reduced_motion policy موجودة في theme_constitution",
             lambda s: "prefers-reduced-motion" in s.get("constitution_content","")),
        ],
        "PACKAGE": [
            ("كل ملفات file_manifest موجودة فعلاً على القرص",
             lambda s: all_files_exist(s["file_manifest"], s["output_path"])),
            ("DELIVERY_POLICY أُشغِّل وأعاد deliver=True",
             lambda s: s.get("delivery_decision",{}).get("deliver") is True),
        ],
    }

    def check_before(self, node_name: str, state: ThemeState) -> dict:
        assumptions = self.ASSUMPTIONS.get(node_name, [])
        failures    = []

        for description, validator in assumptions:
            try:
                if not validator(state):
                    failures.append({
                        "assumption": description,
                        "impact":     "هذه الخطوة قد تُنتج نتيجة خاطئة بثقة كاملة",
                        "action":     "توقف وتحقق أولاً",
                    })
            except Exception as e:
                failures.append({
                    "assumption": description,
                    "impact":     f"تعذّر التحقق: {e}",
                    "action":     "افترض الفشل — توقف",
                })

        if failures:
            state["assumption_failures"][node_name] = failures
            # إن كان الفشل في node حرجة → HUMAN_CHECKPOINT
            if node_name in ["COD_MODULE_BUILDER","PACKAGE","THEME_CONTRACT_GEN"]:
                state["status"] = "checkpoint_required"
                state["checkpoint_reason"] = f"افتراضات {node_name} غير مُتحقَّق منها"

        return {
            "safe_to_proceed": len(failures) == 0,
            "failures":        failures,
        }
```

---

### ٢٠.٢ نظام الذاكرة الحيّة — ثلاثة مستويات لا نوع واحد

التمييز الجوهري: **المبادئ الثابتة ليست ذاكرة — هي جزء من دستور الوكيل** وتُحقن في system prompt مباشرة لا في حقل الدروس.

```python
from enum import Enum

class LessonType(Enum):
    EPHEMERAL  = "مؤقت"    # مرتبط بـ run بعينه — يُحذف تلقائياً بعده
    CONTEXTUAL = "سياقي"   # صحيح لهذا domain/cluster — يبقى ما بقي صالحاً
    PRINCIPLE  = "مبدأ"    # صالح لكل الحالات — يُرقَّى لدستور الوكيل

# أمثلة توضح الفرق:
LESSON_EXAMPLES = [
    {
        "text":    "في هذا الـ Run: Gemini أضاف <!-- wp:group --> زائداً في footer",
        "type":    LessonType.EPHEMERAL,
        "expires": "end_of_run",
        "note":    "لا قيمة له في run آخر — يُحذف تلقائياً",
    },
    {
        "text":    "perfume_luxury: hero section يحتاج min-height:100svh لا 100vh",
        "type":    LessonType.CONTEXTUAL,
        "domain":  "perfume_luxury",
        "note":    "صحيح لهذا domain — قد لا يصح لـ clinic_medical",
    },
    {
        "text":    "أي form فيه direction:rtl يحتاج text-align:right صريحاً — لا يُورَّث",
        "type":    LessonType.PRINCIPLE,
        "domain":  None,
        "note":    "اكتُشف في 12 domain — يُرقَّى لدستور الوكيل مباشرة",
    },
]


def classify_lesson(lesson_text: str, usage_history: list) -> LessonType:
    """
    يُصنَّف الدرس تلقائياً بناءً على سلوكه عبر الزمن.
    """
    domains_appeared_in = {h["domain"] for h in usage_history if h["lesson"] == lesson_text}
    times_used          = len(usage_history)
    confidence          = sum(1 for h in usage_history if h["helped"]) / max(times_used, 1)

    if times_used < 2:
        return LessonType.EPHEMERAL

    if len(domains_appeared_in) >= 5 and confidence >= 0.85:
        return LessonType.PRINCIPLE   # → يُرقَّى لدستور الوكيل

    if len(domains_appeared_in) >= 2:
        return LessonType.CONTEXTUAL

    return LessonType.EPHEMERAL


def promote_to_constitution(principle: str, state: ThemeState) -> None:
    """
    المبدأ الثابت لا يُحقن في حقل الدروس — يُضاف لـ theme_constitution.md مباشرة.
    يُشغَّل تلقائياً حين يُصنَّف درس كـ PRINCIPLE.
    """
    constitution_path = f"{state['speckit_project_path']}/.specify/memory/constitution.md"
    current = read_file(constitution_path)

    if principle not in current:
        new_section = f"\n## مبدأ مُستخلَص من التجربة\n- {principle}\n"
        append_to_file(constitution_path, new_section)
        state["constitution_content"] += new_section
        log(f"مبدأ جديد أُضيف للدستور: {principle[:60]}")
```

**سياسة حقن الذاكرة المُحدَّثة:**

```python
def inject_memory(state: ThemeState, node: str) -> str:
    """
    EPHEMERAL:  يُحقن فقط في نفس الـ Run
    CONTEXTUAL: يُحقن حين domain أو cluster يتطابق
    PRINCIPLE:  لا يُحقن هنا — موجود في system_prompt دائماً
    """
    run_id = state["run_id"]

    ephemeral  = [l for l in state["lessons"] if l.type == LessonType.EPHEMERAL
                  and l.run_id == run_id]
    contextual = [l for l in state["lessons"] if l.type == LessonType.CONTEXTUAL
                  and (l.domain == state["domain"] or l.cluster == state["cluster"])]

    # المبادئ موجودة في theme_constitution.md — لا تُعاد حقنها
    return format_for_prompt(ephemeral + contextual, max_tokens=400)
```

---

### ٢٠.٣ CriticAgent — محامي الشيطان

لا يبني شيئاً. يُستدعى في **ثلاث لحظات استراتيجية فقط** لا أكثر — وإلا تحوّل لعقبة.

```python
class CriticAgent:

    # يُستدعى فقط هنا — لا مكان آخر
    INVOCATION_POINTS = {
        "after_THEME_CONTRACT_GEN": "هل العقد يُغطي كل نقاط التلاقي بين Gemini وGLM؟",
        "after_THEME_PLAN":         "هل الخطة تقف على افتراضات خاطئة أو متعارضة؟",
        "before_PACKAGE":           "هل هناك سيناريوهات لم تُختبَر؟",
    }

    def critique(self, artifact: str, invocation_point: str,
                 state: ThemeState) -> dict:
        question = self.INVOCATION_POINTS[invocation_point]

        prompt = f"""
أنت وكيل نقد متخصص. مهمتك الوحيدة: إيجاد ما قد يفشل.
لا تقيّم الجودة. لا تقترح تحسينات. لا تُثني. فقط اكتشف الثغرات.

السؤال المحدد: {question}
Domain: {state['domain']} | Experience: {state['experience_mode']}
المادة:
{artifact[:3000]}

أجب على هذه الأسئلة الأربعة فقط:
١. ما الافتراض الأكثر خطورة هنا؟
٢. ما السيناريو الذي سيكسر هذا في الإنتاج؟
٣. ما الذي لم يُختبَر ويجب أن يُختبَر؟
٤. هل هناك تعارض بين هذا القرار وقرار سابق في State؟

أجب بـ JSON فقط — لا شرح إضافي:
{{"assumption": "...", "breaking_scenario": "...", "untested": "...", "conflict": "..." | null}}
        """

        result  = call_claude(prompt, temperature=0)
        flags   = parse_json(result)

        # يُضيف لـ State — لا يُوقف التنفيذ
        state["critic_flags"].append({
            "point":   invocation_point,
            "flags":   flags,
            "domain":  state["domain"],
            "run_id":  state["run_id"],
        })

        # يُعرض في HUMAN_CHECKPOINT القادم فقط
        return flags


    def format_for_checkpoint(self, state: ThemeState) -> str:
        """يُنسَّق عرض مُوجز للمستخدم في الـ Checkpoint."""
        if not state["critic_flags"]:
            return ""

        lines = ["⚠️ وكيل الناقد أثار التساؤلات التالية:"]
        for i, flag in enumerate(state["critic_flags"], 1):
            lines.append(f"\n{i}. [{flag['point']}]")
            if flag["flags"].get("breaking_scenario"):
                lines.append(f"   ◆ سيناريو الكسر: {flag['flags']['breaking_scenario']}")
            if flag["flags"].get("untested"):
                lines.append(f"   ◆ غير مُختبَر: {flag['flags']['untested']}")
            if flag["flags"].get("conflict"):
                lines.append(f"   ◆ تعارض محتمل: {flag['flags']['conflict']}")

        lines.append("\nهذه تساؤلات — القرار للمستخدم.")
        return "\n".join(lines)
```

**القيد الجوهري:** الناقد يُضيف `critic_flags` للـ State فقط. لا يُوقف. لا يُعيد. القرار دائماً للإنسان في HUMAN_CHECKPOINT القادم.

---

### ٢٠.٤ DecisionLog — كل قرار قابل للمراجعة

```python
class DecisionLog:
    """
    يُرفق مع كل مخرج سجلاً يشرح لماذا هذا المسار دون سواه.
    المخرج النهائي: /docs/decision-log.json — مرئي للمطور الذي يشتري القالب.
    """

    def record(self,
               node:         str,
               decision:     str,
               alternatives: list[str],
               reason:       str,
               assumptions:  list[str],
               risks:        list[str],
               state:        ThemeState,
               reversible:   bool = True) -> dict:

        entry = {
            "node":         node,
            "timestamp":    datetime.utcnow().isoformat(),
            "decision":     decision,
            "alternatives": alternatives,
            "reason":       reason,
            "assumptions":  assumptions,
            "risks":        risks,
            "reversible":   reversible,
            "domain":       state["domain"],
            "run_id":       state["run_id"],
        }

        state["decision_log"].append(entry)
        return entry


# أمثلة على القرارات المُسجَّلة تلقائياً:

DECISION_EXAMPLES = [
    {
        "node":       "EXPERIENCE_MODE_DECIDER",
        "decision":   "تغيير experience_mode من minimal إلى feature_rich",
        "alternatives": [
            "الإبقاء على minimal كما طلب المستخدم",
            "وضع hybrid: minimal لـ PHP، feature_rich لـ CSS فقط",
        ],
        "reason":     "domain=perfume_luxury يتطلب تأثيرات بصرية وفق DOMAIN_MODE_RULES",
        "assumptions": [
            "المستخدم يريد قالباً متوافقاً مع Domain profile لا تفضيله الشخصي فقط",
            "الأجهزة المستهدفة تدعم CSS animations بكفاءة",
        ],
        "risks": [
            "إن كان المستخدم يستهدف أجهزة قديمة — القرار خاطئ",
            "إن كان prefers-reduced-motion شائعاً في جمهوره — القرار مضر",
        ],
        "reversible": True,
    },
    {
        "node":       "CLUSTER_DOMAIN_SELECTOR",
        "decision":   "تفعيل WooCommerce تلقائياً",
        "alternatives": ["ترك القرار للمستخدم"],
        "reason":     "domain=fashion_store ينتمي لـ Commerce cluster — WooCommerce إلزامي",
        "assumptions": ["المستخدم يريد متجراً وليس موقعاً تعريفياً فقط"],
        "risks":      ["إن كان المستخدم يريد catalog بدون checkout — القرار زائد"],
        "reversible": True,
    },
    {
        "node":       "COD_SECURITY_GATE",
        "decision":   "رفض الملف وإعادته للتصحيح",
        "alternatives": ["قبول الملف مع تحذير"],
        "reason":     "Nonce مفقود — ثغرة CSRF حرجة لا تُقبَل بأي مستوى",
        "assumptions": [],
        "risks":      [],
        "reversible": False,
    },
]


def write_decision_log(state: ThemeState) -> None:
    """يُكتب في /docs/decision-log.json ضمن حزمة التسليم."""
    log_path = f"{state['output_path']}/{state['theme_slug']}/docs/decision-log.json"
    write_json(log_path, {
        "theme_slug":    state["theme_slug"],
        "build_version": state["build_version"],
        "domain":        state["domain"],
        "total_decisions": len(state["decision_log"]),
        "decisions":     state["decision_log"],
    })
```

---

### ٢٠.٥ UncertaintyTracker — الوكيل يعرف متى يجهل

المشكلة الأعمق: النموذج يُجيب بنفس الثقة على سؤال متأكد منه وسؤال يخمّن فيه. الثقة غير المُعايَرة أخطر من الخطأ الصريح.

```python
class UncertaintyTracker:

    UNCERTAINTY_SUFFIX = """

بعد إجابتك، أضف هذا القسم بالضبط:

CONFIDENCE: [رقم بين 0.0 و 1.0]
UNCERTAIN_ABOUT: [ما الذي لست متأكداً منه في هذا الكود؟ أو "لا شيء"]
WOULD_VERIFY_WITH: [ما المصدر الذي ستتحقق منه لو كنت مطوراً بشرياً؟]
    """

    def parse_confidence(self, raw_output: str) -> dict:
        # استخراج قسم الثقة من نهاية الخرج
        confidence_match = re.search(
            r'CONFIDENCE:\s*([\d.]+).*?UNCERTAIN_ABOUT:\s*(.+?).*?WOULD_VERIFY_WITH:\s*(.+?)$',
            raw_output, re.DOTALL
        )
        if not confidence_match:
            return {"confidence": 0.5, "uncertain_about": "غير معروف", "verify_with": "غير محدد"}

        return {
            "confidence":     float(confidence_match.group(1)),
            "uncertain_about": confidence_match.group(2).strip(),
            "verify_with":    confidence_match.group(3).strip(),
            "code":           raw_output[:confidence_match.start()].strip(),
        }

    def record_outcome(self, run_id: str, file: str,
                       declared_confidence: float,
                       was_correct: bool,
                       db) -> None:
        """يُسجَّل بعد كل FIX: هل ثقة النموذج كانت مُعايَرة؟"""
        db.insert("uncertainty_history", {
            "run_id":              run_id,
            "file":                file,
            "declared_confidence": declared_confidence,
            "was_correct":         was_correct,
            "timestamp":           now(),
        })

    def calibration_report(self, db, min_samples: int = 20) -> dict:
        """
        إن كان النموذج يقول confidence=0.9 ويُخطئ 40% من الوقت
        → غير مُعايَر → ارفع عتبة المراجعة تلقائياً.
        """
        history = db.get_recent("uncertainty_history", limit=100)
        if len(history) < min_samples:
            return {"status": "insufficient_data"}

        declared = [r["declared_confidence"] for r in history]
        actual   = [float(r["was_correct"]) for r in history]
        error    = sum(abs(d - a) for d, a in zip(declared, actual)) / len(history)

        recommendation = None
        if error > 0.2:
            recommendation = {
                "action":  "increase_review_threshold",
                "message": f"النموذج واثق أكثر مما ينبغي — خطأ معايرة {error:.2f}",
                "new_threshold": "اطلب CLAUDE_REVIEW لكل ملف بغض النظر عن confidence",
            }

        return {
            "calibration_error": error,
            "status":       "well_calibrated" if error <= 0.2 else "overconfident",
            "recommendation": recommendation,
        }
```

**كيف يؤثر على حلقة التوليد:**

```python
def codegen_with_uncertainty(prompt: str, file: str,
                              generator: str, state: ThemeState) -> dict:
    tracker = UncertaintyTracker()
    augmented_prompt = prompt + tracker.UNCERTAINTY_SUFFIX
    raw = call_api(generator, augmented_prompt)
    parsed = tracker.parse_confidence(raw)

    # إن كانت الثقة منخفضة → أشعل CLAUDE_REVIEW تلقائياً بغض النظر عن باقي النتائج
    if parsed["confidence"] < 0.6:
        state["force_claude_review"].append({
            "file":           file,
            "reason":         f"confidence={parsed['confidence']} — النموذج غير متأكد",
            "uncertain_about": parsed["uncertain_about"],
        })

    # سجَّل في DecisionLog
    state["decision_log_instance"].record(
        node         = f"CODEGEN_{file}",
        decision     = f"توليد {file} بـ {generator}",
        alternatives = [],
        reason       = f"file_owner={generator} حسب FILE_ROUTING",
        assumptions  = [parsed["verify_with"]],
        risks        = [parsed["uncertain_about"]] if parsed["uncertain_about"] != "لا شيء" else [],
        state        = state,
    )

    return {"code": parsed["code"], "confidence": parsed["confidence"]}
```

---

### ٢٠.٦ إضافات للـ State

```python
# يُضاف لـ ThemeState:

# Assumption Checker
assumption_failures:   Dict[str, List[dict]]  # node → failures

# Critic Agent
critic_flags:          List[dict]             # تراكم من كل استدعاء

# Decision Log
decision_log:          List[dict]             # كل قرار مُسجَّل

# Uncertainty Tracker
force_claude_review:   List[dict]             # ملفات تستوجب مراجعة قسرية
uncertainty_history:   List[dict]             # للمعايرة عبر الزمن
```

---

### ٢٠.٧ ما يُضاف لحزمة التسليم

```
/docs/
├── decision-log.json     ← ✦ كل قرار + سببه + بدائله + مخاطره
├── critic-report.json    ← ✦ ما أثاره وكيل الناقد في الـ 3 نقاط
└── calibration-note.md   ← ✦ ملاحظة عن ثقة النموذج في هذا الـ Run
```

**decision-log.json** يُتيح للمطور الذي يشتري القالب أن يفهم لماذا اتُّخذ كل قرار — لا مجرد نتيجة معتمة.

---

## ملخص المنظومة — من المدخل إلى القالب الجاهز

```
المستخدم يملأ الواجهة
        ↓
NORMALIZER: theme_slug + identity.json + theme_constitution.md
        ↓
ENV_CHECK: Python + PHP + PHPStan + RAG + APIs كلها تعمل
        ↓
LANGSMITH_TRACE_INIT: Trace مفتوح لكل الـ Run
        ↓
MEMORY_LOAD: دروس سابقة + Golden Snapshots للـ domain
        ↓
CLUSTER_DOMAIN_SELECTOR: profiles/clusters + profiles/domains
        ↓
THEME_CONTRACT_GEN: العقد الملزم لـ Gemini وGLM معاً
        ↓
SEO_SCAFFOLD: inc/seo.php + Schema.org للـ domain
        ↓
WP_SCAFFOLD: شجرة المجلدات الكاملة + placeholders
        ↓
THEME_PLAN: spec-kit → spec.md + plan.md + tasks.md
        ↓
TOKEN_GEN + STYLE_VARIATION_ENGINE + EXPERIENCE_MODE_DECIDER
        ↓
FILE_LIST: كل ملف بـ generator (gemini/glm/both) + type (critical/standard)
        ↓
[عينة تمثيلية → HUMAN_CHECKPOINT_2 إن لزم]
        ↓
─────────── حلقة توليد كل ملف ────────────
ROUTE_FILE
→ ASSUMPTION_CHECKER (هل الافتراضات لا تزال صالحة؟)
→ GEMINI_CODEGEN أو GLM_CODEGEN
   + UNCERTAINTY_TRACKER (النموذج يُعلن ثقته + ما يجهله)
   + DECISION_LOG (لماذا هذا المسار؟)
→ OUTPUT_PARSER (تنظيف الخرج — قبل أي Gate)
→ SELF_CRITIQUE (النموذج يراجع نفسه)
→ FUNCTION_WHITELIST_GATE (صفر هلوسة)
→ WP_COMPLIANCE_SCAN
→ PHPSTAN_SCAN (صفر أخطاء PHP صامتة)
→ SECURITY_SCAN (صفر XSS/CSRF)
→ CLAUDE_REVIEW (RTL + A11y + UX) — إلزامي إن confidence < 0.6
→ CODERABBIT_REVIEW (WPCS)
→ FIX (patch-based إن لزم)
→ SEMANTIC_DIFF (صفر regression)
─────────── نهاية الحلقة ─────────────────
        ↓
COD_MODULE_BUILDER + COD_SECURITY_GATE (إن COD)
        ↓
WOO_EMAIL_RTL (إن Woo)
        ↓
ARABIC_NUMERICS_GATE
        ↓
DEMO_CONTENT_GENERATOR: محتوى عربي حقيقي للـ domain
        ↓
DEMO_IMAGE_ENGINE: صور WebP ≤ 200KB
        ↓
BRAND_ASSET_GENERATOR: screenshot + social-preview
        ↓
BUILD_VALIDATE + CHILD_THEME_GATE + HUMAN_CHECKPOINT_3 إن لزم
        ↓
WP_INSTALL_SMOKE_TEST: HTTP 200 + لا PHP errors
        ↓
TESTSPRITE_SCAN: UI + RTL + Woo + COD + Print + SEO + A11y
        ↓
OPS_GATES: artifact + cost + performance + quality كلها تتحقق
        ↓
DELIVERY_POLICY: يحسم نهائياً — نُسلّم أم نوقف؟
        ↓
PACKAGE: ZIP + docs + assets جاهز للبيع
        ↓
QUALITY_BADGE_GEN: شهادة الجودة في README + SVG
        ↓
DECISION_LOG → /docs/decision-log.json (كل قرار قابل للمراجعة)
CRITIC_REPORT → /docs/critic-report.json
CALIBRATION  → /docs/calibration-note.md
        ↓
MEMORY_SAVE: lessons (EPHEMERAL/CONTEXTUAL/PRINCIPLE) + prune_lessons
             المبادئ الثابتة → تُرقَّى لدستور الوكيل مباشرة
        ↓
LANGSMITH_TRACE_CLOSE: كل الـ Run موثَّق ومرئي
        ↓
قالب WordPress عربي احترافي جاهز للنشر وللبيع
```

---

*وثيقة المواصفات الشاملة — Implementation-Ready*
*آخر تحديث: مارس ٢٠٢٦*
