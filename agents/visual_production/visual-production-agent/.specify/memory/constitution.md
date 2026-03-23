# Visual Production Agent Constitution — نافع
## دستور وكيل الإنتاج البصري v1.0

**Version**: 1.0.0 | **Ratified**: 2026-03-22

---

## I. الهوية — ما هذا الوكيل

وكيل الإنتاج البصري يُولّد مجموعة أصول مرئية كاملة (صور، hero، product_card، video preview) فور اعتماد القالب بشرياً. يعمل بالتوازي، يفحص الجودة آلياً، ويُسلّم للمراجعة البشرية قبل الإطلاق.

---

## Core Principles

### I. THEME_CONTRACT مصدر Prompts الوحيد
- كل Prompt يُبنى تلقائياً من THEME_CONTRACT (domain, cluster, colors, features)
- لا Prompts يدوية أو عشوائية
- Negative Prompts إلزامية في كل توليد: `no text, no watermarks, no logos, no people`

### II. Quality Gate قبل المراجعة البشرية (غير قابل للتفاوض)
- كل صورة تجتاز: أبعاد صحيحة + حجم < 2MB + لا artifacts واضحة
- صور لا تجتاز الـ Quality Gate → rejected فوراً، لا تصل للمراجعة
- Minimum viable set: hero_image (1) + product_card (1) + screenshot (3) — إن لم يكتمل → إشعار + انتظار

### III. Human Review إلزامي قبل THEME_ASSETS_READY
- لا يُطلَق THEME_ASSETS_READY إلا بعد موافقة بشرية
- VISUAL_REVIEW_REQUESTED يُرسل لصاحب المشروع مع Asset Manifest
- المالك يختار: approved / rejected / needs_revision

### IV. Multi-Generator بالتوازي
- Flux: الصور الواقعية (hero, product_card)
- Ideogram: النصوص العربية في الصور
- كل generator مستقل — فشل أحدهما لا يوقف الآخر
- Budget per theme: ≤ $2.00 (يُحسب قبل التوليد)

### V. WebP فقط للمخرجات النهائية
- كل صورة تُحوَّل إلى WebP بعد اجتياز Quality Gate
- quality=85، max_width=1920 للـ hero، max_width=800 للـ product_card
- لا PNG أو JPEG في المخرجات النهائية للمتجر

### VI. Retention Policy للأصول
- candidates (قيد المراجعة): 7 أيام
- rejected (مرفوضة): 30 يوماً للمراجعة اليدوية إن لزم
- approved (معتمدة): دائمة في storage
- لا حذف للأصول المعتمدة بلا إذن صريح

### VII. Idempotency على مستوى الـ Batch
- `theme_slug + version + asset_type` = مفتاح فريد
- إعادة التشغيل لا تُولّد أصولاً مكررة
- Batch checkpoint في Redis (TTL 48h)

---

## II. القيود التشغيلية

```
Budget per theme: ≤ $2.00
Generators: Flux + Ideogram (فقط)
Output format: WebP (quality=85)
Hero dimensions: 1920×1080
Product card: 800×600
Review timeout: 48 ساعة → إشعار تذكير
```

---

## III. Governance

- هذا الدستور يسود على spec.md في حال التعارض
- Quality Gate لا يُخفَّف — أي تغيير يحتاج وثيقة منفصلة
- Review إلزامي — لا إطلاق آلي للأصول بلا موافقة
