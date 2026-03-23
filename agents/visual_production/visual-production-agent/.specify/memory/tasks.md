# Tasks: visual-production-agent
**Input**: `agents/visual_production/docs/spec.md` + `plan.md` + `constitution.md`
**Implementation**: `/speckit.implement`

---

## Phase 1: Setup + Foundation

- [x] T001 إنشاء `pyproject.toml` (langgraph, anthropic, httpx, Pillow, fastapi, psycopg2-binary, redis, resend)
- [x] T002 إنشاء `Dockerfile` + `.env.example` (FLUX_API_KEY, IDEOGRAM_API_KEY, STORAGE_PATH, BUDGET_LIMIT_USD=2.00, CLAUDE_API_KEY, ...)
- [x] T003 إنشاء `logging_config.py` (agent=visual_production)
- [x] T004 إنشاء `models.py`:
  - `AssetType` Enum (hero_image, product_card, screenshot_home, screenshot_inner, video_preview)
  - `AssetStatus` Enum (generating, quality_check, approved, rejected, published)
  - `GeneratedAsset` dataclass (asset_id, type, url, dimensions, size_kb, quality_score, status)
  - `PromptBundle` dataclass (asset_type, positive, negative, generator)
  - `AssetManifest` dataclass (batch_id, theme_slug, assets, total_cost, status)
  - `BatchStatus` dataclass (batch_id, theme_slug, started_at, budget_used, assets_count)
- [x] T005 إنشاء `state.py` (VisualState TypedDict + make_initial_state())
- [x] T006 [P] إنشاء `db/asset_manifest.py` (save_manifest, get_manifest, update_asset_status, get_by_theme)
- [x] T007 [P] إنشاء `db/batch_log.py` (save_batch, mark_completed, mark_failed, get_batch)
- [x] T008 إنشاء `db/migrations/001_visual_tables.sql` (asset_manifest, batch_log, visual_review_queue)

---

## Phase 2: Services

- [x] T009 إنشاء `services/flux_client.py`:
  - `generate(prompt, negative_prompt, width, height) → bytes`
  - `estimate_cost(asset_count) → float`
  - Retry × 3 عند timeout
- [x] T010 إنشاء `services/ideogram_client.py`:
  - `generate_with_text(prompt, arabic_text, dimensions) → bytes`
  - استخدامه للـ assets التي تحتاج نص عربي
- [x] T011 إنشاء `services/image_processor.py`:
  - `to_webp(image_bytes, quality=85) → bytes`
  - `validate_dimensions(bytes, expected_width, expected_height) → bool`
  - `resize(bytes, max_width) → bytes`
  - `estimate_quality(bytes) → float` (0-1، يكشف artifacts بسيطة)
- [x] T012 [P] إنشاء `services/storage_client.py` (save_asset, get_asset_url, delete_asset)
- [x] T013 [P] إنشاء `services/redis_bus.py` (publish, publish_stream, build_event, checkpoint save/get/delete)
- [x] T014 [P] إنشاء `services/resend_client.py` (send_visual_review_request, send_batch_failed_alert)

---

## Phase 3: Nodes (12 node)

- [x] T015 `nodes/contract_parser.py` — make_contract_parser_node(): استخراج domain + cluster + colors + features + woo/cod flags
- [x] T016 `nodes/budget_calculator.py` — make_budget_calculator_node(): حساب تكلفة متوقعة (Flux price × count + Ideogram price × count) → رفض إن > $2.00 (VIS_BUDGET_EXCEEDED)
- [x] T017 `nodes/prompt_builder.py` — make_prompt_builder_node(claude): بناء PromptBundle لكل asset_type من THEME_CONTRACT (5 طبقات: base + domain + cluster + style + negative)
- [x] T018 `nodes/multi_generator.py` — make_multi_generator_node(flux, ideogram): توليد متوازٍ بـ asyncio.gather، كل generator مستقل، فشل أحدهما لا يوقف الآخر
- [x] T019 `nodes/quality_gate.py` — make_quality_gate_node(processor): فحص كل asset (أبعاد + حجم < 2MB + quality_score) → approved/rejected + route_after_quality()
- [x] T020 `nodes/asset_selector.py` — make_asset_selector_node(): اختيار أفضل مرشح لكل type، تحقق من minimum_viable_set (hero+card+3screenshots)
- [x] T021 `nodes/post_processor.py` — make_post_processor_node(processor): to_webp + resize + compress لكل asset معتمد
- [x] T022 `nodes/review_gate.py` — make_review_gate_node(db, resend, redis): حفظ checkpoint + إرسال VISUAL_REVIEW_REQUESTED + route_after_review()
- [x] T023 `nodes/asset_publisher.py` — make_asset_publisher_node(storage): رفع كل asset للـ storage + تسجيل URL في manifest
- [x] T024 `nodes/batch_recorder.py` — make_batch_recorder_node(db): حفظ AssetManifest كامل + تكلفة فعلية
- [x] T025 `nodes/manifest_builder.py` — make_manifest_builder_node(redis_bus): بناء JSON manifest نهائي + publish THEME_ASSETS_READY أو THEME_ASSETS_PARTIALLY_READY

---

## Phase 4: Agent + Listener + API

- [x] T026 إنشاء `agent.py` — build_visual_graph(): 11 node + conditional edges + compile()
- [x] T027 إنشاء `listeners/visual_listener.py` — يستمع على `product-events` (THEME_APPROVED) → run_visual_pipeline()
- [x] T028 إنشاء `api/main.py`:
  - GET `/health`
  - POST `/review/{batch_key}` — قرار المراجعة: `{"decision": "approved"|"rejected"|"needs_revision", "notes": "..."}`
  - GET `/assets/{batch_key}/manifest` — عرض الـ manifest

---

**الإجمالي**: 28 مهمة
