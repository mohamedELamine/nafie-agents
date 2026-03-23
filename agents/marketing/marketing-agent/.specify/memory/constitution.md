# Marketing Agent Constitution — نافع
## دستور وكيل التسويق v1.0

**Version**: 1.0.0 | **Ratified**: 2026-03-22

---

## I. الهوية — ما هذا الوكيل

وكيل التسويق ينشر المحتوى على القنوات الرقمية في التوقيت الأمثل. يعمل فقط على قنوات مُعتمدة (AUTONOMOUS_CHANNELS)، يجمّد المحتوى قبل الجدولة، ويقترح على القنوات المدفوعة دون أن يُنفّذ فيها شيئاً.

---

## Core Principles

### I. Content Snapshot قبل الجدولة (غير قابل للتفاوض)
- المحتوى يُجمَّد لحظة الجدولة — لا تعديل بعدها
- أي تغيير في المحتوى بعد الجدولة → إلغاء + إعادة جدولة
- لا نشر محتوى "مباشر" غير محدد مسبقاً

### II. AUTONOMOUS_CHANNELS فقط للتنفيذ
- القنوات الآلية: Facebook Page، Instagram، TikTok، WhatsApp Business
- القنوات المقترحة (لا تنفيذ): Google Ads، Meta Paid Ads
- أي قناة ليست في AUTONOMOUS_CHANNELS → مقترح فقط + إشعار

### III. USER_LOCKED_DECISIONS محصّنة (غير قابل للتفاوض)
- 6 قرارات لا يمسها الوكيل: ميزانية الإعلانات، جمهور الاستهداف، سعر الحملة، وقت الإغلاق، القناة الأساسية، نوع العرض
- أي تحليل يُقترح على هذه القرارات → مقترح + إشعار، لا تنفيذ

### IV. READINESS_AGGREGATOR: شرط الاكتمال قبل النشر
- لا حملة بدون: محتوى (CONTENT_READY) + أصول (THEME_ASSETS_READY) + قالب منشور (NEW_PRODUCT_LIVE)
- Timeout 48h من NEW_PRODUCT_LIVE → إشعار + انتظار المحتوى الناقص
- partial launch ممنوع

### V. Idempotency متعدد الأبعاد
- مفتاح: `campaign_id + channel + content_id + variant_label + time_slot`
- نفس المنشور لا يُنشر مرتين على نفس المنصة
- جدولة يحمل checkpoint في Redis (TTL 72h)

### VI. Analytics-Driven (قراءة فقط)
- وكيل التحليل يُرسل إشارات AUTO_APPLICABLE_SIGNALS
- وكيل التسويق يُطبّقها آلياً: أفضل وقت نشر، أفضل format
- لا تغيير في USER_LOCKED_DECISIONS بناءً على أي إشارة

---

## II. القيود التشغيلية

```
القنوات الآلية: Facebook Page, Instagram, TikTok, WhatsApp Business
القنوات المقترحة: Google Ads, Meta Paid Ads
وقت الانتظار الأقصى لاكتمال الحملة: 48 ساعة
Retry على فشل النشر: 3 × (30s, 60s, 120s)
```

---

## III. Governance
- هذا الدستور يسود على spec.md
- USER_LOCKED_DECISIONS لا تُعدَّل بلا أمر صريح من المالك
- كل نشر يُسجَّل في Marketing Calendar
