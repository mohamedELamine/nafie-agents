# Analytics Agent Constitution — نافع
## دستور وكيل التحليل v1.0

**Version**: 1.0.0 | **Ratified**: 2026-03-22

---

## I. الهوية — ما هذا الوكيل

وكيل التحليل هو طبقة الاستخبارات التشغيلية للمنظومة. يجمع الأحداث، يحوّلها إلى مقاييس، يستخرج أنماطاً، ويُرسل إشارات للوكلاء وتنبيهات لصاحب المشروع. **لا يُغيّر شيئاً بنفسه**.

---

## Core Principles

### I. Read-Only بالمطلق (غير قابل للتفاوض)
- لا تعديل على بيانات المنتجات أو التسويق أو الدعم
- لا استدعاء مباشر لأي API خارجي إلا للقراءة (Lemon Squeezy + HelpScout)
- الإجراء الوحيد المسموح: إرسال إشارة (ANALYTICS_SIGNAL) أو تنبيه (OWNER_ALERT)
- كل وكيل مُستلِم يقرر ما يفعل بالإشارة — وكيل التحليل لا يُلزم

### II. `occurred_at` للتحليل — `received_at` للتشخيص (غير قابل للتفاوض)
- كل تحليل يعتمد على `occurred_at` (وقت الحدث الحقيقي)
- `received_at` للتشخيص التقني فقط (تأخر الاستقبال)
- لا خلط بين الاثنين في أي حساب

### III. Lemon Squeezy مصدر الحقيقة للمبيعات (غير قابل للتفاوض)
- Redis مكمّل لا بديل
- عند التعارض: Lemon Squeezy يكسب دائماً
- المطابقة اليومية (Reconciliation) إلزامية

### IV. Attribution = تقريب لا حقيقة
- لا يوجد UTM tracking حقيقي في v1 — كل attribution هو تقدير
- `AttributionConfidence` مُعلَنة دائماً في كل إشارة
- لا ادعاء بدقة attribution بدون UTM parameters صريحة

### V. Granularity صريح في كل مقياس
- كل مقياس له `granularity` محدد: "hour" | "day" | "week" | "month"
- التجميع بالترتيب: hour → day → week → month (بالتجميع لا إعادة الحساب)
- لا مقياس بدون تحديد نافذته الزمنية

### VI. الفشل الجزئي لا يوقف الكل
- Pattern Analyzer يكمل رغم فشل detector واحد
- Metrics Engine لا يتوقف لفشل batch واحد
- كل طبقة مستقلة — تسجيل الخطأ والمتابعة

### VII. Real-time للإشارات العاجلة فقط
- Event Collector + Immediate Evaluator: مستمران
- Metrics Engine: كل ساعة (batch)
- Pattern Analyzer: يومياً 03:00
- تشغيل Pattern Analyzer على كل حدث: محظور — مكلف وغير مجدٍ

### VIII. Idempotency على كل حساب
- `metric_key + period_start + theme_slug` = مفتاح فريد للمقاييس
- `signal_type + theme_slug + period` = مفتاح فريد للإشارات
- لا إعادة حساب أو إرسال لنفس الفترة إن وُجدت مسبقاً

---

## II. القيود التشغيلية

```
المدخلات: Redis Streams (product-events, support-events, marketing-events, content-events, builder-events)
المخرجات: ANALYTICS_SIGNAL → Redis + OWNER_ALERT → Resend + Dashboard + Reports
المصادر الخارجية للقراءة: Lemon Squeezy API + HelpScout API
إجراءات آلية مسموحة: قراءة + تحليل + إرسال إشارة + تنبيه
إجراءات محظورة: تعديل أي بيانات، استدعاء API للكتابة، تجاوز وكيل آخر
```

---

## III. Governance

- هذا الدستور يسود على spec.md في حال التعارض
- الإشارات التي لا تُقدَّر ثقتها تُرسَل مع `confidence_low = true`
- التنبيهات الحرجة للمالك مضمونة بـ retry (3 محاولات) + fallback email
