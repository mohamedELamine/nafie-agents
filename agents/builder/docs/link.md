# وكيل البناء (Builder Agent)

## الحالة: ✅ مكتمل البناء

وكيل البناء مكتمل في مشروع منفصل على Cowork.
يحتوي على المواصفة الكاملة في `final.md` (~4081 سطر).

## الدور في المنظومة

وكيل البناء هو المُنتِج الأساسي — يأخذ المدخلات ويُخرج قالب WordPress عربياً
احترافياً كاملاً جاهزاً للبيع.

## العقد الذي يُطلقه عند الاكتمال

```python
# الحدث الذي يُطلقه وكيل البناء عند انتهائه
EventType.THEME_BUILD_COMPLETED → payload = ThemeBuildCompletedPayload:
{
    "theme_slug":     str,
    "zip_path":       str,     # مسار ZIP القالب
    "docs_path":      str,     # مسار وثائق التسليم
    "quality_score":  float,   # 0.85+ مضمون
    "test_results":   dict,    # نتائج TestSprite
    "decision_log":  list,    # سجل قرارات البناء
    "build_time_sec": int,
    "theme_contract": dict,    # THEME_CONTRACT كامل (يشمل aesthetic_contract)
}
```

## التكامل مع المنظومة

```
طلب البناء ← وكيل المشرف [theme.build.requested]
       ↓
  وكيل البناء (pipeline كامل)
       ↓
نشر ← وكيل المنصة   [theme.build.completed]
بصريات ← وكيل الإنتاج البصري
محتوى ← وكيل المحتوى
```

## ما يحتاجه من المنظومة

لا يحتاج شيئاً من الوكلاء الآخرين أثناء البناء.
يعمل باستقلالية تامة ويُطلق حدثاً واحداً عند الانتهاء.

---

*للاطلاع على المواصفة الكاملة: راجع مشروع مصنع القوالب في Cowork*
