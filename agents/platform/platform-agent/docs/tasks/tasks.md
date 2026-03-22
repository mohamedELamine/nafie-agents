---
description: "قائمة مهام وكيل المنصة — Platform Agent Implementation"
---

# Tasks: Platform Agent

**Input**: `agents/platform/docs/spec.md` (v3)
**Architecture**: `docs/architecture.md` (nafic_system_overview_v2)
**Skeleton**: `agents/platform/platform-agent/`

---

## نظرة عامة على المراحل

| المرحلة | الملف | الحالة |
|---------|-------|--------|
| Phase 1: Setup | phase1_setup.md | ⬜ |
| Phase 2: Foundation | phase2_foundation.md | ⬜ |
| Phase 3: Launch Workflow | phase3_launch_workflow.md | ⬜ |
| Phase 4: Update Workflow | phase4_update_workflow.md | ⬜ |
| Phase 5: Commerce Consumer | phase5_commerce_consumer.md | ⬜ |

---

## ترتيب التنفيذ

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundation) ← يجب أن تكتمل قبل أي شيء آخر
    ↓
Phase 3 + Phase 4 يمكن التوازي
    ↓
Phase 5
```

---

## قواعد مطلقة يجب على GLM-5 الالتزام بها

1. `wp_post_id` من Registry فقط — لا من الأحداث الواردة أبداً
2. `idempotency_guard` decorator على كل node
3. `schema_version: "1.0"` في كل حدث مُطلَق
4. HTTPS فقط للـ WordPress API
5. Saga لا Atomic — الـ rollback محاولة لا ضمان
6. INCONSISTENT_STATE يوقف كل شيء — لا استئناف آلي
7. السعر لا يُمس بعد النشر — أبداً
