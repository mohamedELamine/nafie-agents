---
description: "Phase 1: Project Setup"
---

# Phase 1: Setup

**Goal**: تهيئة بيئة المشروع وملفات الإعداد
**Prerequisites**: لا شيء — يمكن البدء فوراً
**Checkpoint**: `pip install -r requirements.txt` يعمل بدون أخطاء

---

## Tasks

- [ ] T001 إنشاء `pyproject.toml` مع metadata (name=platform-agent, python=3.12)
  - الملف: `agents/platform/platform-agent/pyproject.toml`

- [ ] T002 [P] إنشاء `.env.example` بكل متغيرات البيئة
  - الملف: `agents/platform/platform-agent/.env.example`
  - المحتوى (من spec.md § ٢٢):
    ```
    LS_API_KEY=
    LS_STORE_ID=
    LS_WEBHOOK_SECRET=
    WP_SITE_URL=https://nafic.com
    WP_API_USER=platform_agent
    WP_API_PASSWORD=
    RESEND_API_KEY=
    STORE_EMAIL_FROM=نافع <hello@nafic.com>
    STORE_URL=https://nafic.com
    DATABASE_URL=postgresql://user:pass@localhost/platform_db
    REDIS_URL=redis://localhost:6379
    CLAUDE_API_KEY=
    OWNER_EMAIL=
    HUMAN_REVIEW_TIMEOUT_HOURS=48
    ASSET_INITIAL_WAIT_HOURS=4
    ASSET_EXTENSION_HOURS=4
    MAX_REVISION_CYCLES=3
    LOG_LEVEL=INFO
    ```

- [ ] T003 [P] إنشاء `Dockerfile` للوكيل
  - الملف: `agents/platform/platform-agent/Dockerfile`
  - يعتمد على: python:3.12-slim
  - يُشغّل: `uvicorn platform_agent.api.main:app`

- [ ] T004 [P] إنشاء `logging_config.py`
  - الملف: `agents/platform/platform-agent/logging_config.py`
  - يُعيّن LOG_LEVEL من البيئة
  - format موحد مع timestamp و agent_name

- [ ] T005 تحديث `docker-compose.yml` الجذري لإضافة platform_agent service

**Checkpoint ✅**: `python -c "import platform_agent"` يعمل
