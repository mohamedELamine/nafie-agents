# /security-review

مراجعة أمنية شاملة على وكيل أو ملف محدد.

## الاستخدام

```
/security-review                              # فحص كامل للمشروع
/security-review agents/marketing/            # فحص وكيل marketing
/security-review agents/analytics/db/         # فحص طبقة DB
```

## ما يفحصه

- Hardcoded secrets في الكود و .env.example
- SQL injection عبر f-strings في psycopg2
- Connection leaks (connections بلا pool)
- Endpoints بلا authentication
- OWASP Top 10

## مستويات الخطورة

🔴 **CRITICAL** — يوقف كل شيء فوراً (credentials مكشوفة، SQL injection)
🟠 **HIGH** — يُصلَح قبل الدفع (missing auth، bare except)
🟡 **MEDIUM** — يُتابع في sprint القادم

## تنبيه

إذا وُجد CRITICAL، يُفترض أنك تُوقف العمل وتُصلح أولاً.
إذا كانت credentials مكشوفة فعلياً → أعِد توليدها الآن.
