# Implementation Plan: visual-production-agent
**Branch**: `visual-production-agent-v1` | **Date**: 2026-03-22 | **Spec**: `agents/visual_production/docs/spec.md`

---

## Summary

وكيل يُولّد أصولاً مرئية كاملة لكل قالب بعد اعتماده. يبني Prompts من THEME_CONTRACT، يُشغّل Flux + Ideogram بالتوازي، يفحص الجودة، يحوّل إلى WebP، ويُرسل للمراجعة البشرية قبل إطلاق THEME_ASSETS_READY.

---

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: langgraph>=0.2.0, anthropic>=0.25.0, httpx>=0.27.0, Pillow>=10.0, fastapi>=0.110.0, psycopg2-binary, redis[hiredis], resend
**Storage**: PostgreSQL (asset_manifest, batch_log) + Local/S3 storage للأصول
**Testing**: pytest
**Target Platform**: Linux Docker container
**Performance Goals**: توليد batch كامل < 10 دقائق
**Constraints**: ≤ $2.00 per theme, WebP only output
**Scale/Scope**: كل THEME_APPROVED → batch واحد

---

## Constitution Check

| المبدأ | الحالة |
|--------|--------|
| THEME_CONTRACT مصدر الـ Prompts | ✓ PROMPT_BUILDER يستخدم CONTRACT فقط |
| Quality Gate قبل المراجعة | ✓ QUALITY_GATE node مستقل |
| Human Review إلزامي | ✓ REVIEW_GATE لا يُتجاوز |
| Budget ≤ $2.00 | ✓ BUDGET_CALCULATOR قبل التوليد |
| WebP فقط | ✓ POST_PROCESSOR يحوّل كل صورة |

---

## Project Structure

```
agents/visual_production/visual-production-agent/
├── pyproject.toml
├── Dockerfile
├── .env.example
├── logging_config.py
├── state.py                      # VisualState TypedDict
├── models.py                     # AssetManifest, GeneratedAsset, BatchStatus, PromptBundle
├── agent.py                      # build_visual_graph() + run_visual_pipeline()
│
├── db/
│   ├── __init__.py
│   ├── asset_manifest.py         # save, get, update_status, get_by_theme
│   └── batch_log.py              # save_batch, mark_completed, get_batch
│
├── services/
│   ├── __init__.py
│   ├── flux_client.py            # generate(prompt, negative_prompt, dimensions) → bytes
│   ├── ideogram_client.py        # generate_with_text(prompt, arabic_text) → bytes
│   ├── storage_client.py         # save(bytes, path) → url, get(path) → bytes
│   ├── image_processor.py        # to_webp(bytes, quality, max_width) → bytes, validate_dimensions()
│   ├── redis_bus.py
│   └── resend_client.py          # send_review_request, send_batch_complete
│
├── nodes/
│   ├── __init__.py
│   ├── contract_parser.py        # استخراج domain + cluster + colors + features من THEME_CONTRACT
│   ├── budget_calculator.py      # حساب التكلفة المتوقعة → رفض إن > $2.00
│   ├── prompt_builder.py         # بناء PromptBundle لكل asset_type (5 طبقات)
│   ├── multi_generator.py        # Flux + Ideogram بالتوازي (asyncio.gather)
│   ├── quality_gate.py           # فحص أبعاد + حجم + artifacts
│   ├── asset_selector.py         # اختيار أفضل مرشح لكل asset_type
│   ├── post_processor.py         # to_webp + resize + compress
│   ├── review_gate.py            # إرسال VISUAL_REVIEW_REQUESTED + انتظار قرار
│   ├── asset_publisher.py        # رفع للـ storage + تسجيل URLs
│   ├── batch_recorder.py         # حفظ AssetManifest كامل
│   └── manifest_builder.py       # بناء JSON manifest نهائي + إطلاق THEME_ASSETS_READY
│
├── listeners/
│   ├── __init__.py
│   └── visual_listener.py        # THEME_APPROVED → run_visual_pipeline()
│
└── api/
    ├── __init__.py
    └── main.py                   # /health + /review/{batch_key} + /assets/{batch_key}/decision
```

---

## Workflow Architecture

```
[contract_parser]
      │
      ▼
[budget_calculator]      ← رفض إن > $2.00
      │
      ▼
[prompt_builder]         ← 5 طبقات لكل asset_type
      │
      ▼
[multi_generator]        ← Flux + Ideogram بالتوازي
      │
      ▼
[quality_gate]           ← أبعاد + حجم + artifacts
      │
      ▼
[asset_selector]         ← أفضل مرشح لكل type
      │
      ▼
[post_processor]         ← WebP + resize + compress
      │
      ▼
[review_gate]            ← VISUAL_REVIEW_REQUESTED → انتظار بشري (48h)
      │
      ▼
[asset_publisher]        ← رفع للـ storage
      │
      ▼
[batch_recorder]
      │
      ▼
[manifest_builder]       ← THEME_ASSETS_READY
```

---

## Prompt Bundle Structure (5 طبقات)

```python
PromptBundle = {
    "hero_image":      {"positive": "...", "negative": "no text, no watermark..."},
    "product_card":    {"positive": "...", "negative": "..."},
    "screenshot_home": {"positive": "...", "negative": "..."},
    "screenshot_inner":{"positive": "...", "negative": "..."},
    "video_preview":   {"positive": "...", "negative": "..."},  # اختياري
}
```

## Event Contracts

**Inbound**: `THEME_APPROVED`
**Outbound**: `VISUAL_REVIEW_REQUESTED`, `THEME_ASSETS_READY`, `THEME_ASSETS_PARTIALLY_READY`
