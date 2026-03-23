# Python Patterns Skill — نافع

## الوصف
أنماط Python المُعتمَدة في مشروع نافع. استخدم هذه الأنماط عند كتابة أي كود Python جديد أو مراجعة كود موجود.

---

## القواعد الأساسية

### 1. Immutability أولاً
```python
# ❌ Mutation
def add_channel(state: MarketingState, channel: str) -> None:
    state.selected_channels.append(channel)  # mutation!

# ✅ إنشاء كائن جديد
def add_channel(state: MarketingState, channel: str) -> MarketingState:
    return MarketingState(
        **state.dict(),
        selected_channels=[*state.selected_channels, channel],
    )
```

### 2. Context Managers للموارد
```python
# ❌ resource leak
conn = get_connection()
result = do_work(conn)
conn.close()  # لو حدث exception → لن تُنفَّذ

# ✅ context manager
with get_conn() as conn:
    result = do_work(conn)
    # conn تُغلق تلقائياً حتى عند الاستثناء
```

### 3. Type Hints على كل دالة عامة
```python
from typing import Optional, List, Dict, Any
from datetime import datetime
import psycopg2

def save_metric(
    conn: psycopg2.extensions.connection,
    metric_key: str,
    value: float,
    period_start: datetime,
    theme_slug: Optional[str] = None,
) -> bool:
    """Save metric snapshot. Returns True if saved, False if already exists."""
    ...
```

### 4. Error Handling صريح
```python
# ❌ يخفي الأخطاء
try:
    result = process()
except Exception:
    pass

# ✅ صريح ومُسجَّل
try:
    result = process()
except psycopg2.DatabaseError as e:
    logger.error(f"DB error in save_metric: {e}", exc_info=True)
    raise
except ValueError as e:
    logger.warning(f"Invalid metric data: {e}")
    return False
```

### 5. Dataclasses بدل Dicts للبيانات المُهيكَلة
```python
# ❌ dict غير typed — لا تحقق، لا autocomplete
event = {
    "event_id": str(uuid4()),
    "event_type": "NEW_SALE",
    "occurred_at": datetime.utcnow(),
}

# ✅ dataclass
from dataclasses import dataclass, field

@dataclass
class AnalyticsEvent:
    event_id: str
    event_type: str
    occurred_at: datetime
    theme_slug: Optional[str] = None
    received_at: datetime = field(default_factory=datetime.utcnow)
```

### 6. Logging بدل Print
```python
# ❌ print
print(f"Processing event {event_id}")

# ✅ logger
from logging_config import get_logger
logger = get_logger("nodes.event_collector")
logger.info(f"Processing event {event_id}")
logger.debug(f"Event data: {event_data}")  # لا يظهر في production
```

### 7. Constants بدل Magic Numbers/Strings
```python
# ❌ magic strings
if hours_since > 48:
    ...

if signal_type == "no_output_alert":
    target = "marketing_agent"

# ✅ constants
CAMPAIGN_TIMEOUT_HOURS = 48

SIGNAL_TARGET_MAP = {
    "no_output_alert":        "marketing_agent",
    "support_surge_alert":    "support_agent",
    "recurring_quality_issue": "builder_agent",
}
```

### 8. Idempotency على العمليات الحرجة
```python
# ✅ نمط idempotency في DB
cursor.execute("""
    INSERT INTO metric_snapshots (metric_key, period_start, value)
    VALUES (%s, %s, %s)
    ON CONFLICT (metric_key, period_start) DO NOTHING
""", (key, period_start, value))

# ✅ فحص قبل الحساب
if snapshot_exists(conn, key, granularity, period_start):
    logger.debug(f"Snapshot already exists, skipping: {key}")
    return
```

---

## حجم الكود المقبول

| الوحدة | الحد الأقصى |
|--------|------------|
| دالة | 50 سطر |
| ملف | 800 سطر |
| parameters لدالة | 5 |
| تداخل | 4 مستويات |

---

## نمط الـ Node في نافع

كل node في LangGraph يتبع هذا النمط:

```python
def make_my_node(dependency) -> callable:
    """Factory: returns the node function with injected dependencies."""

    def my_node(state: MyState) -> Dict[str, Any]:
        """Node logic."""
        try:
            if not state.current_item:
                return {"success": False, "reason": "no_item"}

            with get_conn() as conn:
                result = store.do_work(conn, state.current_item)

            logger.info(f"Node completed: {result}")
            return {"success": True, "result": result}

        except Exception as e:
            logger.error(f"Error in my_node: {e}", exc_info=True)
            return {"success": False, "reason": str(e)}

    return my_node
```
