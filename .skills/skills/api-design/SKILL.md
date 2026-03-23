# API Design Skill — نافع (FastAPI)

## الوصف
معايير تصميم APIs في مشروع نافع. تستخدم هذه المهارة عند إضافة endpoints جديدة أو مراجعة APIs موجودة.

---

## قواعد FastAPI في نافع

### 1. بنية الـ Endpoint
```python
# ✅ النمط الكامل
@app.post("/campaigns", response_model=CampaignStatusResponse, status_code=201)
async def create_campaign(campaign: CampaignCreate) -> Dict[str, Any]:
    """Create a new marketing campaign.

    Args:
        campaign: Campaign creation data (validated by Pydantic)

    Returns:
        Created campaign with generated ID and status

    Raises:
        HTTPException 422: Invalid input (تلقائي من Pydantic)
        HTTPException 500: Database error
    """
    try:
        campaign_id = f"campaign_{int(datetime.utcnow().timestamp())}"

        with get_conn() as conn:
            marketing_calendar.save_campaign(conn, {...})

        logger.info(f"Created campaign: {campaign_id}")
        return {...}

    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 2. Pydantic Models للـ Input/Output
```python
# Input validation (تلقائي من Pydantic)
class CampaignCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    theme_slug: str = Field(..., pattern=r'^[a-z0-9-]+$')
    start_date: datetime
    end_date: datetime

    @validator('end_date')
    def end_after_start(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v

# Response model (يمنع كشف بيانات داخلية)
class CampaignStatusResponse(BaseModel):
    campaign_id: str
    status: str
    start_date: datetime
    end_date: datetime
    # لا DB-internal fields هنا!
```

### 3. معالجة الأخطاء المتسقة
```python
# ✅ استخدم HTTPException بشكل متسق
@app.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    try:
        with get_conn() as conn:
            campaign = marketing_calendar.get_campaign_by_id(conn, campaign_id)

        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        return campaign

    except HTTPException:
        raise  # أعِد رفع HTTPException بدون تعديل
    except Exception as e:
        logger.error(f"Error getting campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 4. Lifespan للـ Resources
```python
# ✅ init/cleanup صحيح
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_pool(minconn=2, maxconn=10)
    logger.info("Agent started")
    yield
    # Shutdown
    close_pool()
    logger.info("Agent stopped")

app = FastAPI(lifespan=lifespan)
```

---

## معايير الـ API في نافع

### تسمية الـ Endpoints
| العملية | HTTP Method | المسار |
|---------|-------------|--------|
| إنشاء | POST | `/resources` |
| قراءة واحد | GET | `/resources/{id}` |
| قراءة قائمة | GET | `/resources` |
| تحديث | PATCH | `/resources/{id}` |
| حذف | DELETE | `/resources/{id}` |
| إجراء خاص | POST | `/resources/{id}/action` |

### HTTP Status Codes
| الحالة | الكود |
|-------|-------|
| إنشاء ناجح | 201 |
| عملية ناجحة | 200 |
| غير موجود | 404 |
| بيانات خاطئة | 422 |
| خطأ داخلي | 500 |

### الـ Endpoints الإلزامية في كل وكيل
```python
@app.get("/health")  # للـ health checks
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
```

---

## ما لا تفعله

```python
# ❌ لا تكشف stack trace للمستخدم
raise HTTPException(status_code=500, detail=traceback.format_exc())

# ✅ رسالة عامة + log داخلي
logger.error(f"Internal error: {e}", exc_info=True)
raise HTTPException(status_code=500, detail="Internal server error")

# ❌ لا تستخدم __import__ داخل دوال
conn = __import__("psycopg2").connect("postgresql://...")

# ✅ imports في أعلى الملف + connection pool
from ..db.connection import get_conn
with get_conn() as conn: ...
```
