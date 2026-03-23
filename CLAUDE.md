# نافع — Arabic Themes Ecosystem
## دليل Claude لهذا المشروع

---

## هيكل المشروع

```
agents/
├── analytics/marketing-agent/   ← تحليل + إشارات فقط (read-only)
├── marketing/marketing-agent/   ← نشر على AUTONOMOUS_CHANNELS
└── [وكلاء أخرى]

.claude/
├── agents/                      ← sub-agents متخصصة
│   ├── security-reviewer.md     ← مراجعة أمنية
│   ├── python-reviewer.md       ← مراجعة Python
│   └── code-reviewer.md         ← مراجعة عامة
└── commands/                    ← slash commands
    ├── /code-review
    ├── /security-review
    └── /checkpoint

.skills/skills/                  ← مهارات مخصصة للمشروع
├── security-review/
├── python-patterns/
└── api-design/
```

---

## القواعد الدستورية (غير قابلة للتفاوض)

### I. قانون occurred_at
- `occurred_at` للتحليل والمقارنات
- `received_at` للتشخيص فقط
- **لا تعكس هذا أبداً**

### II. قانون Connection Pool
- كل اتصال بـ DB يمر بـ `get_conn()` context manager
- لا `psycopg2.connect()` مباشرة في الكود
- لا hardcoded URLs

### III. قانون Idempotency
- كل عملية كتابة في DB: `ON CONFLICT DO NOTHING`
- كل signal: `signal_sent_recently()` قبل الإرسال
- كل metric: `snapshot_exists()` قبل الحساب

### IV. قانون Immutability
- لا mutation على objects موجودة
- أنشئ كائناً جديداً دائماً

### V. قانون الوكيل التحليلي (Read-Only)
- analytics-agent لا يُعدِّل DB خارج نطاقه
- يُرسل إشارات فقط — لا يُنفِّذ إجراءات

### VI. قانون القنوات المسموح بها
- AUTONOMOUS_CHANNELS فقط للتنفيذ: Facebook، Instagram، TikTok، WhatsApp
- Google Ads، Meta Paid Ads: مقترحات فقط + إشعار

---

## معايير الكود

### ملفات Python
- دالة ≤ 50 سطر
- ملف ≤ 800 سطر
- تداخل ≤ 4 مستويات
- Type hints على كل دالة عامة
- Logger دائماً (`from logging_config import get_logger`)

### نمط كل Node
```python
def make_node_name(dependency) -> callable:
    def node_fn(state) -> Dict[str, Any]:
        try:
            with get_conn() as conn:
                ...
            return {"success": True, ...}
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"success": False, "reason": str(e)}
    return node_fn
```

### SQL دائماً Parameterized
```python
# ✅ صحيح
cursor.execute("SELECT * FROM t WHERE key = %s", (key,))
# ❌ خطأ
cursor.execute(f"SELECT * FROM t WHERE key = '{key}'")
```

---

## Agents المتاحة

استدعِ هذه الـ agents عند الحاجة:

| الـ Agent | متى تستدعيه |
|-----------|------------|
| `security-reviewer` | قبل أي دفع لـ production أو عند شك بثغرة |
| `python-reviewer` | مراجعة ملف Python جديد أو مُعدَّل |
| `code-reviewer` | مراجعة شاملة قبل دمج وكيل جديد |

---

## Event Contracts

**Inbound لـ analytics-agent:**
`NEW_SALE`, `SUPPORT_TICKET_OPENED`, `SUPPORT_TICKET_ESCALATED`,
`POST_PUBLISHED`, `CAMPAIGN_LAUNCHED`, `THEME_QUALITY_REPORT`

**Outbound من analytics-agent:**
`ANALYTICS_SIGNAL` → target_agent حسب `SIGNAL_TARGET_MAP`

**Inbound لـ marketing-agent:**
`CONTENT_READY`, `THEME_ASSETS_READY`, `ANALYTICS_SIGNAL`

**Outbound من marketing-agent:**
`CAMPAIGN_LAUNCHED`, `POST_PUBLISHED`

---

## عند اكتشاف مشكلة أمنية

1. أوقف العمل فوراً
2. استدعِ `security-reviewer` agent
3. لا تدفع أي كود حتى الإصلاح
4. إذا كانت credentials مكشوفة → أعِد توليدها الآن
5. ابحث عن نفس المشكلة في بقية الوكلاء
