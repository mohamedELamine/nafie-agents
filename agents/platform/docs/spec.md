# وكيل المنصة — وكيل إدارة المتجر والنشر
## وثيقة المواصفات الشاملة v3 — النسخة النهائية الموحدة

> تجمع هذه النسخة: v2 الأساسية + Patch v2.1 + التصحيحات المعمارية الإضافية.
> هي المرجع التنفيذي المعتمد — لا رجوع لأي نسخة سابقة.

---

## فهرس المحتويات

1. نظرة عامة ومبادئ جوهرية
2. موقع الوكيل في المنظومة الكاملة
3. البنية التحتية
4. الكيانات الجوهرية — Domain Model
5. Product Registry — السجل الدائم مع Provenance
6. Idempotency Strategy
7. Workflow الأول — Product Launch
8. Workflow الثاني — Product Update
9. Workflow الثالث — Commerce Event Consumer
10. هيكل التراخيص — VIP كمنتج مستقل
11. PAGE_WRITER — JSON المنظم + Gutenberg Renderer
12. Saga-Based Publish Flow
13. Event-Driven Asset Collection
14. Asset Timeout Policy
15. Human Review Gate
16. Eligibility Policy
17. Changelog Contract
18. Event Contract Schemas
19. أمان WordPress API
20. Error Codes Catalog
21. بنية الـ State
22. متغيرات البيئة
23. دستور الوكيل
24. قائمة التحقق النهائية

---

## ١. المبادئ غير القابلة للتفاوض

- الاعتماد البشري أولاً — لا تحرك قبل THEME_APPROVED
- المراجعة قبل النشر — صفحة المنتج لا تُنشر دون موافقة صريحة
- السعر لا يُمس بعد البيع — أبداً
- Idempotency في كل خطوة — التكرار لا يُنتج منتجاً مكرراً
- Saga لا Atomic — النشر عبر نظامين خارجيين لا يضمن ذرية حقيقية
- INCONSISTENT_STATE يُوقف العمل — لا استئناف قبل حل يدوي
- Changelog عقد ملزم — نص حر مرفوض
- schema_version في كل حدث — التوافقية مضمونة عبر الزمن
- wp_post_id من Registry فقط — لا من الأحداث الواردة
- الفشل الصامت ممنوع — كل خطأ له كود محدد

---

## ٢. البنية التحتية

```
WordPress (REST API)     ← صفحات المنتج — Custom Post Type
Lemon Squeezy (API)      ← المنتجات + التراخيص + الدفع + الضرائب
Resend (API)             ← البريد المخصص بهوية المتجر
Redis (Pub/Sub)          ← حافلة الأحداث بين الوكلاء
PostgreSQL               ← Registry + Idempotency + Inconsistent States
```

---

## ٣. الكيانات الجوهرية

```python
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

@dataclass
class ThemeRecord:
    # الهوية
    theme_slug: str; theme_name_ar: str; domain: str; cluster: str
    # WordPress
    wp_post_id: int; wp_post_url: str
    # Lemon Squeezy
    ls_product_id: str; single_variant_id: str; unlimited_variant_id: str
    # الإصدار
    current_version: str; status: str
    published_at: datetime; last_updated_at: datetime
    # Provenance — التتبع الكامل
    contract_version: str; build_id: str
    approved_event_id: str; launch_idempotency_key: str
    last_update_event_id: Optional[str] = None
    last_update_idempotency_key: Optional[str] = None

@dataclass
class ChangelogSchema:
    summary_ar:  str       # ملخص عربي قصير
    items_ar:    List[str] # قائمة التغييرات
    type:        str       # "patch" | "minor" | "major"
    is_security: bool      # هل أمني؟
```

---

## ٤. Product Registry

```sql
CREATE TABLE theme_registry (
    theme_slug              VARCHAR(100) PRIMARY KEY,
    theme_name_ar           TEXT         NOT NULL,
    domain                  VARCHAR(50)  NOT NULL,
    cluster                 VARCHAR(50)  NOT NULL,
    wp_post_id              INTEGER      UNIQUE NOT NULL,
    wp_post_url             TEXT         NOT NULL,
    ls_product_id           VARCHAR(50)  UNIQUE NOT NULL,
    single_variant_id       VARCHAR(50)  NOT NULL,
    unlimited_variant_id    VARCHAR(50)  NOT NULL,
    current_version         VARCHAR(20)  NOT NULL,
    status                  VARCHAR(20)  NOT NULL DEFAULT 'published',
    published_at            TIMESTAMP    NOT NULL DEFAULT NOW(),
    last_updated_at         TIMESTAMP    NOT NULL DEFAULT NOW(),
    contract_version             VARCHAR(10),
    build_id                     VARCHAR(100),
    approved_event_id            VARCHAR(100),
    launch_idempotency_key       VARCHAR(200),
    last_update_event_id         VARCHAR(100),
    last_update_idempotency_key  VARCHAR(200)
);

CREATE TABLE vip_registry (
    id            SERIAL      PRIMARY KEY,
    ls_product_id VARCHAR(50) UNIQUE NOT NULL,
    ls_variant_id VARCHAR(50) UNIQUE NOT NULL,
    theme_slugs   TEXT[]      NOT NULL DEFAULT '{}',
    created_at    TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE TABLE inconsistent_states (
    record_id   VARCHAR(100) PRIMARY KEY,
    theme_slug  VARCHAR(100) NOT NULL,
    wp_state    VARCHAR(20)  NOT NULL,
    ls_state    VARCHAR(20)  NOT NULL,
    detected_at TIMESTAMP    NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolution  TEXT
);

CREATE TABLE execution_log (
    idempotency_key     VARCHAR(200) PRIMARY KEY,
    event_type          VARCHAR(50)  NOT NULL,
    theme_slug          VARCHAR(100) NOT NULL,
    version             VARCHAR(20)  NOT NULL,
    status              VARCHAR(30)  NOT NULL,
    started_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMP,
    last_completed_node VARCHAR(50),
    error_code          VARCHAR(50)
);
```

### قاعدة حرجة: wp_post_id لا يُحمل في الأحداث

```python
"""
wp_post_id مصدره الوحيد: Product Registry.
لا يُدرج في THEME_UPDATED أو أي حدث آخر.
إدراجه في الحدث يكسر مبدأ Registry كمصدر وحيد للحقيقة.
"""
```

---

## ٥. Idempotency Strategy

```python
def build_idempotency_key(event_type, theme_slug, version):
    return f"{event_type}:{theme_slug}:{version}"

def idempotency_guard(node_name: str):
    """Decorator يمنع إعادة تنفيذ خطوة مكتملة"""
    def decorator(func):
        def wrapper(state):
            key = f"{state['idempotency_key']}:{node_name}"
            existing = db.fetchone(
                "SELECT status FROM execution_log WHERE idempotency_key = %s", [key]
            )
            if existing and existing["status"] == "completed":
                state["logs"].append(f"[SKIP] {node_name} مكتمل مسبقاً")
                return state
            # تسجيل البدء
            db.execute("""
                INSERT INTO execution_log (idempotency_key,event_type,theme_slug,version,status,last_completed_node)
                VALUES (%s,%s,%s,%s,'running',%s)
                ON CONFLICT (idempotency_key) DO UPDATE SET status='running',last_completed_node=EXCLUDED.last_completed_node
            """, [key, state["event_type"], state["theme_slug"], state["version"], node_name])
            result = func(state)
            db.execute("UPDATE execution_log SET status='completed',completed_at=NOW() WHERE idempotency_key=%s", [key])
            return result
        return wrapper
    return decorator
```

---

## ٦. Workflow الأول — Product Launch

### الخريطة

```
[LAUNCH_ENTRY]
      │
[INCONSISTENCY_CHECK] ──► حالة غير محلولة → [BLOCKED]
      │
[CONTRACT_PARSER]
      │
[ASSET_WAITER] ──► غير جاهزة → checkpoint → END (يستأنف عند THEME_ASSETS_READY)
      │
[PRODUCT_CREATOR]
      │
[LICENSE_CONFIGURATOR]
      │
[VIP_CATALOG_UPDATER]
      │
[PAGE_WRITER] ◄──┐ (مع ملاحظات)
      │           │
[PAGE_RENDERER]  │
      │           │
[HUMAN_REVIEW_GATE] ──► needs_revision ──────────────────────┘
      │                  rejected → [CANCEL]
      │ approved
[SAGA_PUBLISHER] ──► فشل + rollback فشل → [INCONSISTENCY_RECORDER]
      │
[REGISTRY_RECORDER] ← يُسجّل Provenance كاملاً
      │
[LAUNCH_ANNOUNCER]
      │
     END
```

### LAUNCH_ENTRY

```python
@idempotency_guard("LAUNCH_ENTRY")
def launch_entry_node(state):
    event = state["incoming_event"]
    if not validate_event_schema_version(event):
        state["status"] = PlatformStatus.FAILED
        state["error_code"] = PlatformError.PLT_UNSUPPORTED_EVENT_SCHEMA
        return state
    state["theme_slug"]        = event["data"]["theme_slug"]
    state["version"]           = event["data"]["theme_contract"]["build_version"]
    state["theme_contract"]    = event["data"]["theme_contract"]
    state["package_path"]      = event["data"]["package_path"]
    state["approved_event_id"] = event["event_id"]
    state["idempotency_key"]   = build_idempotency_key("launch", state["theme_slug"], state["version"])
    if registry.exists(state["theme_slug"]):
        state["status"] = PlatformStatus.FAILED
        state["error_code"] = PlatformError.PLT_DUPLICATE_LAUNCH
    return state
```

### INCONSISTENCY_CHECK

```python
@idempotency_guard("INCONSISTENCY_CHECK")
def inconsistency_check_node(state):
    if registry.has_unresolved_inconsistency(state["theme_slug"]):
        state["status"]     = PlatformStatus.INCONSISTENT_EXTERNAL_STATE
        state["error_code"] = PlatformError.PLT_INCONSISTENT_EXTERNAL_STATE
        notify_human_of_inconsistency(state["theme_slug"])
    return state
```

### SAGA_PUBLISHER

```python
@idempotency_guard("SAGA_PUBLISHER")
def saga_publisher_node(state):
    """
    Saga Pattern: خطوتان مترابطتان مع Compensating Actions.
    لا ضمان ذرية حقيقية — best-effort consistency.
    """
    wp_post_id = None; ls_activated = False
    try:
        wp_response  = wp_client.post("/wp-json/wp/v2/ar_theme_product", build_wp_post_data(state))
        wp_post_id   = wp_response["id"]
        ls_client.update_product(state["ls_product_id"], {"status": "published"})
        ls_activated = True
        state["wp_post_id"] = wp_post_id
        state["wp_post_url"] = wp_response["link"]
        return state
    except Exception as e:
        wp_ok = True; ls_ok = True
        if wp_post_id and not ls_activated:
            try: wp_client.delete(f"/wp-json/wp/v2/ar_theme_product/{wp_post_id}")
            except: wp_ok = False
        if ls_activated and not wp_post_id:
            try: ls_client.update_product(state["ls_product_id"], {"status": "draft"})
            except: ls_ok = False
        if not wp_ok or not ls_ok:
            # فشل التراجع → حالة غير متسقة تستوجب تدخلاً يدوياً
            registry.record_inconsistent_state(
                state["theme_slug"],
                "published" if wp_post_id else "not_published",
                "active" if ls_activated else "draft",
            )
            state["status"]     = PlatformStatus.INCONSISTENT_EXTERNAL_STATE
            state["error_code"] = PlatformError.PLT_INCONSISTENT_EXTERNAL_STATE
            notify_human_of_inconsistency(state["theme_slug"])
            return state
        state["status"] = PlatformStatus.FAILED
        state["error_code"] = PlatformError.PLT_SAGA_PUBLISH_FAILED
        return state
```

### معالجة INCONSISTENT_EXTERNAL_STATE

```
١. INCONSISTENCY_CHECK يمنع أي workflow جديد لهذا القالب
٢. إشعار فوري لصاحب المشروع مع تفاصيل الحالتين
٣. لا استئناف آلي — الحل يدوي فقط
٤. بعد الحل: صاحب المشروع يُطلق THEME_APPROVED من جديد
```

---

## ٧. Workflow الثاني — Product Update

### الخريطة

```
[UPDATE_ENTRY]
      │
[CHANGELOG_VALIDATOR] ──► غير صالح → [ERROR]
      │
[REGISTRY_LOADER] ──► غير موجود → [ERROR]
      │  (wp_post_id يأتي من هنا — لا من الحدث)
[WP_CONTENT_UPDATER]
      │
[LS_FILE_UPDATER]
      │
[ELIGIBILITY_FILTER]
      │
[NOTIFICATION_SENDER]
      │
[VERSION_RECORDER] ← يُحدِّث Registry مع event_id و idempotency_key
      │
[UPDATE_ANNOUNCER]
      │
     END
```

### CHANGELOG_VALIDATOR

```python
@idempotency_guard("CHANGELOG_VALIDATOR")
def changelog_validator_node(state):
    if not validate_changelog(state["changelog"]):
        state["status"]     = PlatformStatus.FAILED
        state["error_code"] = PlatformError.PLT_CHANGELOG_INVALID
        state["error"]      = "صيغة changelog غير مطابقة للعقد الملزم"
    return state
```

### REGISTRY_LOADER

```python
@idempotency_guard("REGISTRY_LOADER")
def registry_loader_node(state):
    """wp_post_id يأتي من هنا فقط — لا من الحدث الوارد."""
    record = registry.get(state["theme_slug"])
    if not record:
        state["status"]     = PlatformStatus.FAILED
        state["error_code"] = PlatformError.PLT_REGISTRY_NOT_FOUND
        return state
    state["ls_product_id"]        = record["ls_product_id"]
    state["ls_single_variant"]    = record["single_variant_id"]
    state["ls_unlimited_variant"] = record["unlimited_variant_id"]
    state["wp_post_id"]           = record["wp_post_id"]
    state["wp_post_url"]          = record["wp_post_url"]
    state["previous_version"]     = record["current_version"]
    return state
```

---

## ٨. Workflow الثالث — Commerce Event Consumer

```python
class CommerceEventConsumer:
    """خدمة دائمة مستقلة — لا تتقاطع مع Workflows الأخرى"""

    def handle_webhook(self, payload: bytes, signature: str):
        if not self._verify_signature(payload, signature):
            raise SecurityError(PlatformError.PLT_WEBHOOK_SIGNATURE_INVALID)
        event   = json.loads(payload)
        handler = self.WEBHOOK_HANDLERS.get(event["meta"]["event_name"])
        if handler: handler(event)

    def _verify_signature(self, payload, signature):
        expected = hmac.new(LS_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)
```

---

## ٩. هيكل التراخيص — VIP كمنتج مستقل

```
Lemon Squeezy Store
├── Product: كل قالب
│   ├── Variant: Single Site  (29$)
│   └── Variant: Unlimited    (79$)
│
└── Product: VIP Bundle ← منتج مستقل تماماً
    └── Variant: VIP Lifetime (299$)
        theme_slugs: [...] يتوسع عند كل قالب جديد
```

```python
# عند شراء VIP → entitlement لكل theme_slugs في vip_registry
# عند قالب جديد → يُضاف تلقائياً لـ vip_registry.theme_slugs
PRICING = {
    "single":    {"price": 29,  "activations": 1,    "duration": "1y"},
    "unlimited": {"price": 79,  "activations": None, "duration": "1y"},
    "vip":       {"price": 299, "activations": None, "duration": "lifetime"},
}
```

---

## ١٠. PAGE_WRITER — JSON + Gutenberg Renderer

### الأقسام مشروطة بـ THEME_CONTRACT

```python
def get_required_sections(contract: dict) -> List[str]:
    sections = ["hero","features","target_audience","quality_section","pricing_section","faq","cta"]
    if contract.get("woocommerce_enabled"): sections.append("woocommerce_features")
    if contract.get("cod_enabled"):         sections.append("cod_features")
    return sections
```

### PAGE_RENDERER مع Validation

```python
@idempotency_guard("PAGE_RENDERER")
def page_renderer_node(state):
    required = get_required_sections(state["theme_contract"])
    rendered = render_page_to_gutenberg(state["draft_page_content"], state["ls_variants"], required)
    validation = validate_gutenberg_markup(rendered, required)
    if not validation["valid"]:
        state["status"]     = PlatformStatus.FAILED
        state["error_code"] = PlatformError.PLT_PAGE_RENDER_FAILED
        state["error"]      = f"أقسام مفقودة: {validation['missing_sections']}"
        return state
    state["page_blocks"] = rendered
    return state

def validate_gutenberg_markup(blocks: str, required_sections: List[str]) -> dict:
    if not isinstance(blocks, str) or not blocks.strip():
        return {"valid": False, "missing_sections": required_sections}
    if "<!-- wp:" not in blocks:
        return {"valid": False, "missing_sections": ["invalid_markup"]}
    missing = [s for s in required_sections if f'data-section="{s}"' not in blocks]
    return {"valid": len(missing) == 0, "missing_sections": missing}
```

### RENDERING_POLICY

```python
RENDERING_POLICY = {
    "input":    "structured JSON only",
    "output":   "valid Gutenberg block markup",
    "forbidden": [
        "raw free-form HTML as final publish payload",
        "LLM-generated block markup مباشرة دون renderer ثابت",
    ],
}
```

---

## ١١. Saga-Based Publish Flow

```python
PUBLISH_STRATEGY = {
    "pattern":        "saga",
    "guarantee":      "best-effort consistency with compensating rollback",
    "not_guaranteed": "true atomicity across external systems",
}
```

انظر تفاصيل SAGA_PUBLISHER في القسم ٦.

---

## ١٢. Event-Driven Asset Collection

```python
ASSET_REQUIRED_MINIMUM = {
    "required":    ["screenshot"],          # لا نشر بدونه مطلقاً
    "recommended": ["hero_image", "preview_images"],
    "optional":    ["promo_video"],
}
```

---

## ١٣. Asset Timeout Policy

```python
ASSET_TIMEOUT_POLICY = {
    "initial_wait_hours":  4,
    "extension_hours":     4,   # تمديد واحد فقط
    "max_total_hours":     8,
    "max_extensions":      1,
    "after_final_timeout": "cancel_launch_automatically",
}

"""
بعد initial_wait (4 ساعات):
  → إشعار لصاحب المشروع بالخيارات:
    - proceed_with_available_assets (إن screenshot موجود)
    - extend_wait_once
    - cancel_launch

بعد final_timeout (8 ساعات إجمالاً):
  → إلغاء تلقائي — لا خيارات إضافية
  → لا نشر دون screenshot مطلقاً حتى مع القرار البشري
"""
```

---

## ١٤. Human Review Gate

```python
MAX_REVISION_CYCLES = 3

def route_after_review(state):
    d = state["human_decision"]
    if d == "approved_as_is":      return "PAGE_RENDERER"
    if d == "approved_with_edits":
        state["draft_page_content"] = apply_edits(state["draft_page_content"], state["human_edits"])
        return "PAGE_RENDERER"
    if d in ("needs_revision_minor","needs_revision_major"):
        if state["revision_count"] >= MAX_REVISION_CYCLES:
            notify_revision_limit_reached(state); return "LAUNCH_HOLD"
        state["revision_count"] += 1; return "PAGE_WRITER"
    if d == "rejected": return "LAUNCH_CANCEL"
```

---

## ١٥. Eligibility Policy

```python
def eligible_for_update_email(buyer, changelog, theme_slug, new_version) -> bool:
    if notification_log.exists(buyer["email"], theme_slug, new_version):
        return False
    # التحديثات الأمنية تتجاوز opt_in
    if changelog["is_security"]:
        return buyer["license_status"]=="active" and buyer["updates_entitlement"] is True
    return (
        buyer["license_status"]      == "active"
        and buyer["updates_entitlement"] is True
        and buyer["email_opt_in"]        is True
    )
```

---

## ١٦. Changelog Contract

```python
def validate_changelog(changelog: dict) -> bool:
    if not isinstance(changelog, dict): return False
    required = {"summary_ar","items_ar","type","is_security"}
    if not required.issubset(changelog.keys()): return False
    if not changelog.get("summary_ar","").strip(): return False
    if not isinstance(changelog.get("items_ar"), list) or len(changelog["items_ar"])==0: return False
    if changelog["type"] not in {"patch","minor","major"}: return False
    if not isinstance(changelog["is_security"], bool): return False
    return True
```

---

## ١٧. Event Contract Schemas

```python
SUPPORTED_EVENT_SCHEMA_VERSIONS = {"1.0"}

def validate_event_schema_version(event: dict) -> bool:
    return event.get("schema_version") in SUPPORTED_EVENT_SCHEMA_VERSIONS

def build_event(event_type, source, data, correlation_id=None) -> dict:
    return {
        "event_id":       str(uuid.uuid4()),
        "event_type":     event_type,
        "schema_version": "1.0",
        "source":         source,
        "occurred_at":    datetime.utcnow().isoformat(),
        "correlation_id": correlation_id,
        "data":           data,
    }
```

### THEME_APPROVED (مُستقبَل)
```json
{
  "event_id":"uuid","event_type":"THEME_APPROVED","schema_version":"1.0",
  "source":"owner","occurred_at":"2025-03-16T09:00:00Z","correlation_id":null,
  "data":{"theme_slug":"restaurant_modern","theme_contract":{},"package_path":"/builds/...","approved_by":"owner"}
}
```

### THEME_UPDATED (مُستقبَل) — بدون wp_post_id عمداً
```json
{
  "event_id":"uuid","event_type":"THEME_UPDATED","schema_version":"1.0",
  "source":"builder_agent","occurred_at":"2025-03-17T10:00:00Z",
  "data":{
    "theme_slug":"restaurant_modern","previous_version":"20250316-0001","new_version":"20250317-0002",
    "package_path":"/builds/v2.zip","ls_product_id":"123456",
    "changelog":{"summary_ar":"إصلاح RTL","items_ar":["إصلاح RTL"],"type":"patch","is_security":false}
  }
}
```

### THEME_ASSETS_READY (مُستقبَل)
```json
{
  "event_id":"uuid","event_type":"THEME_ASSETS_READY","schema_version":"1.0",
  "source":"visual_agent","occurred_at":"2025-03-16T10:30:00Z",
  "data":{"theme_slug":"restaurant_modern","assets":{"screenshot":"/...","hero_image":"/..."}}
}
```

### NEW_PRODUCT_LIVE (مُطلَق)
```json
{
  "event_id":"uuid","event_type":"NEW_PRODUCT_LIVE","schema_version":"1.0",
  "source":"platform_agent","occurred_at":"2025-03-16T12:00:00Z",
  "data":{"theme_slug":"restaurant_modern","theme_name_ar":"قالب المطعم الحديث",
    "wp_post_url":"https://ar-themes.com/themes/...","ls_product_id":"123456",
    "pricing":{"single":29,"unlimited":79,"vip":299},"final_score":91}
}
```

### THEME_UPDATED_LIVE (مُطلَق)
```json
{
  "event_id":"uuid","event_type":"THEME_UPDATED_LIVE","schema_version":"1.0",
  "source":"platform_agent","occurred_at":"2025-03-17T11:00:00Z",
  "data":{"theme_slug":"restaurant_modern","new_version":"20250317-0002","is_security":false,"buyers_notified":42}
}
```

---

## ١٨. أمان WordPress API

```python
WP_SECURITY_REQUIREMENTS = [
    "مستخدم Editor مخصص — لا Admin",
    "Application Password في .env — لا في الكود",
    "HTTPS فقط — رفض HTTP",
    "Whitelist: ar_theme_product فقط",
    "Sanitize كل محتوى قبل الحفظ",
    "Rate limiting: 60 طلب/دقيقة",
    "Audit log لكل عملية نشر أو تعديل",
    "Media upload: WebP فقط، حد أقصى 2MB",
]
```

---

## ١٩. Error Codes Catalog

```python
class PlatformError:
    # إطلاق
    PLT_DUPLICATE_LAUNCH            = "PLT_101"
    PLT_ASSET_MISSING               = "PLT_102"
    PLT_ASSET_TIMEOUT               = "PLT_103"
    PLT_ASSET_FINAL_TIMEOUT         = "PLT_104"
    PLT_LS_PRODUCT_CREATE_FAILED    = "PLT_201"
    PLT_WP_PUBLISH_FAILED           = "PLT_301"
    PLT_SAGA_PUBLISH_FAILED         = "PLT_302"
    PLT_INCONSISTENT_EXTERNAL_STATE = "PLT_303"
    PLT_REGISTRY_WRITE_FAILED       = "PLT_401"
    PLT_REVIEW_TIMEOUT              = "PLT_501"
    PLT_MAX_REVISIONS_REACHED       = "PLT_502"
    PLT_PAGE_JSON_INVALID           = "PLT_601"
    PLT_PAGE_RENDER_FAILED          = "PLT_602"
    # تحديث
    PLT_REGISTRY_NOT_FOUND          = "PLT_701"
    PLT_VERSION_ALREADY_DEPLOYED    = "PLT_702"
    PLT_WP_UPDATE_FAILED            = "PLT_703"
    PLT_LS_FILE_UPDATE_FAILED       = "PLT_704"
    PLT_CHANGELOG_INVALID           = "PLT_803"
    PLT_UNSUPPORTED_EVENT_SCHEMA    = "PLT_804"
    # إشعارات
    PLT_NOTIFICATION_TOTAL_FAILURE  = "PLT_901"
    PLT_NOTIFICATION_PARTIAL_FAILURE= "PLT_902"
    # أمان
    PLT_WEBHOOK_SIGNATURE_INVALID   = "PLT_1001"
    PLT_WP_AUTH_FAILED              = "PLT_1002"
    PLT_LS_AUTH_FAILED              = "PLT_1003"
```

---

## ٢٠. بنية الـ State

```python
class LaunchState(TypedDict):
    idempotency_key: str; event_type: str; theme_slug: str; version: str
    approved_event_id: str; incoming_event: Dict; theme_contract: Dict
    parsed: Dict; package_path: str
    collected_assets: Dict; has_video: bool
    asset_timeout_warning: bool; extension_used: bool
    ls_product_id: Optional[str]; ls_variants: List[Dict]
    vip_product_id: Optional[str]
    wp_post_id: Optional[int]; wp_post_url: Optional[str]
    draft_page_content: Optional[Dict]; page_blocks: Optional[str]
    revision_count: int; human_decision: Optional[str]
    human_edits: Optional[Dict]; revision_notes: Optional[str]
    status: PlatformStatus; error_code: Optional[str]
    error: Optional[str]; logs: List[str]

class UpdateState(TypedDict):
    idempotency_key: str; event_type: str; event_id: str
    theme_slug: str; new_version: str; previous_version: Optional[str]
    ls_product_id: Optional[str]; ls_single_variant: Optional[str]
    ls_unlimited_variant: Optional[str]
    wp_post_id: Optional[int]; wp_post_url: Optional[str]
    package_path: str; changelog: Dict
    eligible_buyers: List[Dict]; notification_results: Optional[Dict]
    status: PlatformStatus; error_code: Optional[str]
    error: Optional[str]; logs: List[str]
```

---

## ٢١. متغيرات البيئة

```env
LS_API_KEY=...
LS_STORE_ID=...
LS_WEBHOOK_SECRET=...
WP_SITE_URL=https://ar-themes.com
WP_API_USER=platform_agent
WP_API_PASSWORD=...
RESEND_API_KEY=...
STORE_EMAIL_FROM=قوالب عربية <hello@ar-themes.com>
STORE_URL=https://ar-themes.com
DATABASE_URL=postgresql://user:pass@localhost/platform_db
REDIS_URL=redis://localhost:6379
CLAUDE_API_KEY=sk-ant-...
HUMAN_REVIEW_TIMEOUT_HOURS=48
ASSET_INITIAL_WAIT_HOURS=4
ASSET_EXTENSION_HOURS=4
MAX_REVISION_CYCLES=3
LOG_LEVEL=INFO
```

---

## ٢٢. دستور الوكيل

```
القواعد المطلقة:
١. لا أتحرك قبل THEME_APPROVED
٢. لا أنشر دون موافقة صريحة
٣. لا أمس السعر بعد النشر
٤. لا أقترب من معاملات الدفع
٥. Idempotency في كل خطوة
٦. Saga لا Atomic — التراجع محاولة لا ضمان
٧. INCONSISTENT_STATE يوقف كل شيء
٨. Changelog عقد ملزم — نص حر مرفوض
٩. wp_post_id من Registry فقط
١٠. كل حدث يحمل schema_version
```

---

## ٢٣. قائمة التحقق النهائية

### Product Launch

```
□ schema_version الحدث صالحة
□ idempotency_key مُنشأ — لا تكرار
□ لا حالة INCONSISTENT غير محلولة
□ REQUIRED_SECTIONS مشروطة بـ THEME_CONTRACT
□ screenshot موجود قبل أي نشر
□ VIP منتج مستقل — لا variant داخل المنتج
□ PAGE_WRITER: JSON صالح بكل الأقسام
□ PAGE_RENDERER: Gutenberg markup صالح
□ SAGA_PUBLISHER: إن فشل التراجع → INCONSISTENT مُسجَّل
□ REGISTRY_RECORDER: ThemeRecord مع Provenance كامل
□ NEW_PRODUCT_LIVE بـ schema_version + event_id
```

### Product Update

```
□ Changelog مطابق للعقد الملزم
□ wp_post_id جُلب من Registry — لا من الحدث
□ السعر لم يُمس
□ الأمني يتجاوز opt_in
□ VERSION_RECORDER: Registry مُحدَّث مع event_id و idempotency_key
□ THEME_UPDATED_LIVE بـ schema_version + event_id
```

### Commerce Event Consumer

```
□ Webhook signature مُتحقَّق منه أولاً
□ كل حدث صادر: schema_version + event_id + occurred_at
□ لا تدخل في الدفع أو الاسترداد
```
