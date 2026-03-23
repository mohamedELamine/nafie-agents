# /code-review

راجع الكود المُقدَّم أو الملفات المُحدَّدة باستخدام وكيل المراجعة.

## الاستخدام

```
/code-review                          # مراجعة آخر التغييرات (git diff)
/code-review agents/analytics/        # مراجعة مجلد محدد
/code-review agents/marketing/marketing-agent/nodes/platform_publisher.py
```

## ما يحدث

1. يُشغِّل `code-reviewer` agent على الملفات المُحدَّدة
2. يُنتج تقريراً مُصنَّفاً (CRITICAL / HIGH / MEDIUM / LOW)
3. يُعطي قراراً نهائياً: موافق / تحذير / مرفوض

## ملاحظات

- إذا وجد CRITICAL: يتوقف ويُبلِّغ — لا يكمل حتى الإصلاح
- يستدعي `security-reviewer` تلقائياً عند وجود auth أو DB أو APIs خارجية
- النتيجة تُحفَظ في campaign log
