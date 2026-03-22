# منظومة قوالب WordPress العربية — Arabic Themes Ecosystem

## نظرة عامة

منظومة أعمال متكاملة مدفوعة بالذكاء الاصطناعي لإنتاج وبيع وصيانة قوالب WordPress العربية الاحترافية. تتألف من سبعة وكلاء متخصصين يتنسقهم مشرف مركزي، يعملون عبر حافلة أحداث Redis المشتركة.

---

## معمارية المنظومة

```
┌──────────────────────────────────────────────────────────────────┐
│                    وكيل المدير العام (Supervisor)                 │
│              يستقبل الأحداث · يوجّه · يراقب · يتدخل             │
└──────────────┬───────────────────────────────────────────────────┘
               │                Redis Event Bus
    ┌──────────┼──────────────────────────────────────┐
    │          │          │          │          │      │
    ▼          ▼          ▼          ▼          ▼      ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌──────┐
│البناء │ │المنصة │ │الدعم  │ │المحتوى│ │التسويق│ │التحليل│
│Builder│ │Platform│ │Support│ │Content│ │Market.│ │Analyt.│
└───────┘ └───────┘ └───────┘ └───────┘ └───────┘ └──────┘
                                                        │
                                               ┌────────────────┐
                                               │الإنتاج البصري  │
                                               │Visual Production│
                                               └────────────────┘
```

---

## الوكلاء

| الوكيل | المجلد | الحالة | المهمة |
|--------|--------|--------|--------|
| وكيل البناء | `agents/builder/` | ✅ مكتمل (راجع مجلده) | توليد قوالب WordPress عربية |
| وكيل المنصة | `agents/platform/` | 🔨 قيد البناء | إدارة متجر WooCommerce |
| وكيل الدعم | `agents/support/` | 🔨 قيد البناء | دعم العملاء بالعربية |
| وكيل المحتوى | `agents/content/` | 🔨 قيد البناء | إنتاج المحتوى التسويقي |
| وكيل التسويق | `agents/marketing/` | 🔨 قيد البناء | الحملات والتواصل الاجتماعي |
| وكيل التحليل | `agents/analytics/` | 🔨 قيد البناء | التقارير والذكاء التجاري |
| وكيل الإنتاج البصري | `agents/visual_production/` | 🔨 قيد البناء | توليد المرئيات والفيديو |
| وكيل المدير العام | `supervisor/` | 🔨 قيد البناء | التنسيق والإشراف |

---

## البنية التقنية

- **التنسيق:** LangGraph (كل وكيل رسم بياني مستقل)
- **الاتصال:** Redis Pub/Sub (حافلة الأحداث)
- **النماذج:** Claude API · Gemini · GLM · Flux 2 Pro · Ideogram V3 · Kling AI · Pika Labs
- **الواجهة:** FastAPI
- **التخزين:** PostgreSQL (بيانات الأعمال) + Redis (الأحداث والحالة المؤقتة)
- **المراقبة:** LangSmith
- **التنشر:** VPS (Docker Compose)

---

## بنية المجلدات

```
arabic-themes-ecosystem/
├── README.md                          # هذا الملف
├── docker-compose.yml                 # تعريف الخدمات
├── .env.example                       # متغيرات البيئة
├── requirements.txt                   # المتطلبات Python
│
├── core/                              # النواة المشتركة
│   ├── state.py                       # BusinessState المشترك
│   ├── redis_bus.py                   # حافلة الأحداث
│   ├── base_agent.py                  # الفئة الأساسية
│   ├── contracts.py                   # العقود بين الوكلاء
│   └── memory.py                      # الذاكرة المشتركة
│
├── supervisor/                        # وكيل المدير العام
│   ├── agent.py
│   ├── nodes/
│   └── docs/spec.md                   # المواصفة الكاملة
│
├── agents/
│   ├── builder/                       # وكيل البناء (مكتمل)
│   │   └── docs/link.md               # رابط للمشروع الأصلي
│   ├── platform/                      # وكيل المنصة
│   │   ├── agent.py
│   │   ├── nodes/
│   │   └── docs/spec.md
│   ├── support/                       # وكيل الدعم
│   │   ├── agent.py
│   │   ├── nodes/
│   │   └── docs/spec.md
│   ├── content/                       # وكيل المحتوى
│   │   ├── agent.py
│   │   ├── nodes/
│   │   └── docs/spec.md
│   ├── marketing/                     # وكيل التسويق
│   │   ├── agent.py
│   │   ├── nodes/
│   │   └── docs/spec.md
│   ├── analytics/                     # وكيل التحليل
│   │   ├── agent.py
│   │   ├── nodes/
│   │   └── docs/spec.md
│   └── visual_production/             # وكيل الإنتاج البصري
│       ├── agent.py
│       ├── nodes/
│       └── docs/spec.md
│
├── infrastructure/
│   ├── redis/redis.conf
│   ├── nginx/nginx.conf
│   └── systemd/                       # خدمات systemd
│
├── docs/
│   ├── architecture.md                # المعمارية الكاملة
│   ├── deployment.md                  # دليل النشر على VPS
│   └── agents-overview.md             # نظرة عامة على الوكلاء
│
└── scripts/
    ├── start.sh                       # تشغيل المنظومة
    ├── stop.sh                        # إيقاف المنظومة
    └── health-check.sh                # فحص صحة الوكلاء
```

---

## تشغيل المنظومة

```bash
# نسخ متغيرات البيئة
cp .env.example .env
# تعديل .env بمفاتيح API الخاصة بك

# تشغيل المنظومة كاملة
docker-compose up -d

# أو تشغيل وكيل بعينه
docker-compose up -d supervisor platform support
```

---

## الوثائق التفصيلية

- [`docs/architecture.md`](docs/architecture.md) — المعمارية الكاملة والتدفق
- [`docs/deployment.md`](docs/deployment.md) — دليل النشر خطوة بخطوة
- [`supervisor/docs/spec.md`](supervisor/docs/spec.md) — مواصفة وكيل المدير العام
- كل وكيل له مواصفته الكاملة في `agents/<agent>/docs/spec.md`

---

*منظومة قوالب WordPress العربية — آخر تحديث: مارس ٢٠٢٦*
