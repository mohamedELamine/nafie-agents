# Security Review Skill — نافع

## الوصف
مراجعة أمنية شاملة لكود Python multi-agent. تستخدم هذه المهارة عند:
- مراجعة وكيل جديد قبل الإطلاق
- الشك في وجود ثغرة
- بعد أي تغيير يمسّ auth أو DB أو APIs خارجية

---

## خطوات التنفيذ

### الخطوة 1: فحص الأسرار المكشوفة
ابحث في كل ملف Python وفي `.env.example` عن:

```python
# أنماط خطيرة للبحث عنها
grep -r "password\s*=" agents/ --include="*.py"
grep -r "api_key\s*=" agents/ --include="*.py"
grep -r "postgresql://" agents/ --include="*.py"
grep -r "redis://" agents/ --include="*.py"
```

✅ القاعدة: كل سر يجب أن يكون في `os.environ.get("KEY")` — لا قيم مباشرة.

---

### الخطوة 2: فحص SQL Injection

ابحث عن f-strings في SQL queries:

```python
# ❌ خطر مباشر
cursor.execute(f"SELECT * FROM events WHERE type = '{event_type}'")

# ✅ آمن
cursor.execute("SELECT * FROM events WHERE type = %s", (event_type,))
```

---

### الخطوة 3: فحص Connection Pool

تحقق أن **كل** استخدام لـ DB يمر بـ `get_conn()`:

```python
# ❌ خطر: connection leak + hardcoded URL
conn = psycopg2.connect("postgresql://user:pass@host/db")
result = do_work(conn)
# conn لم تُغلق!

# ✅ صحيح
with get_conn() as conn:
    result = do_work(conn)
```

---

### الخطوة 4: فحص Authentication

لكل FastAPI endpoint:
- هل يتطلب تحققاً؟
- هل هو public بشكل مقصود؟

```python
# ✅ endpoints تتطلب auth
@app.post("/campaigns/{campaign_id}/schedule")
async def schedule_campaign(campaign_id: str, token: str = Depends(verify_token)):
    ...

# ✅ endpoints public مقصودة
@app.get("/health")
async def health_check():
    ...
```

---

### الخطوة 5: فحص Error Handling

```python
# ❌ يخفي الأخطاء الأمنية
try:
    authenticate(user, password)
except:
    pass  # CRITICAL: يُخفي auth failures

# ✅ صحيح
try:
    authenticate(user, password)
except AuthError as e:
    logger.warning(f"Auth failed for user {user_id}: {e}")
    raise HTTPException(status_code=401)
```

---

## نتيجة الفحص

أنتج تقريراً بهذا التنسيق:

```markdown
## Security Review — [اسم الوكيل]

### 🔴 CRITICAL
- [وصف + السطر + الإصلاح المقترح]

### 🟠 HIGH
- [قائمة]

### 🟡 MEDIUM
- [قائمة]

### القرار: [موافق / مرفوض]

إذا كانت هناك CRITICAL:
> ⚠️ أوقف العمل. أصلح الثغرات أولاً. إذا كانت credentials مكشوفة → أعِد توليدها الآن.
```
