# Tasks: support-agent
**Input**: `agents/support/docs/spec.md` + `plan.md` + `constitution.md`
**Implementation**: `/speckit.implement`

---

## Phase 1: Setup + Foundation

**Purpose**: بنية المشروع + Domain Model + قاعدة البيانات + الخدمات الخارجية

- [x] T001 إنشاء `pyproject.toml` (langgraph, anthropic, qdrant-client, fastapi, psycopg2-binary, redis, resend)
- [x] T002 إنشاء `Dockerfile` (python:3.12-slim, non-root user, port 8000)
- [x] T003 إنشاء `.env.example` (CLAUDE_API_KEY, QDRANT_URL, HELPSCOUT_API_KEY, FACEBOOK_PAGE_TOKEN, DATABASE_URL, REDIS_URL, RESEND_API_KEY, OWNER_EMAIL, CONFIDENCE_THRESHOLD=0.50)
- [x] T004 إنشاء `logging_config.py` (configure_logging + get_logger بصيغة `agent=support`)
- [x] T005 إنشاء `models.py` (SupportTicket, Identity, IntentClassification, RiskFlags, RetrievalResult, SupportAnswer, EscalationRecord + Enums: Platform, IntentCategory, RiskLevel)
- [x] T006 إنشاء `state.py` (SupportState TypedDict + make_initial_state())
- [x] T007 [P] إنشاء `db/execution_log.py` (mark_started, mark_completed, mark_failed, check_completed)
- [x] T008 [P] إنشاء `db/escalation_log.py` (save_escalation, get_escalation_history)
- [x] T009 [P] إنشاء `db/knowledge_log.py` (save_update, get_recent_updates)
- [x] T010 إضافة جداول SQL لـ support_execution_log + support_escalation_log + support_knowledge_log في migration

---

## Phase 2: Services

**Purpose**: التكاملات الخارجية — Qdrant + HelpScout + Facebook + Claude

- [x] T011 إنشاء `services/qdrant_client.py`:
  - 3 collections: `theme_docs`, `general_faqs`, `resolved_tickets`
  - `search(query, collection, limit)` → List[RetrievalResult]
  - `upsert_document(collection, doc_id, text, metadata)` للتحديث
  - `search_parallel(queries)` → نتائج 3 collections بالتوازي
- [x] T012 إنشاء `services/claude_client.py`:
  - `classify_intent_and_risk(ticket_text, identity) → (IntentClassification, RiskFlags)` — طبقتان مستقلتان
  - `generate_answer(ticket, retrieval_results, identity) → SupportAnswer` مع disclaimer إلزامي
  - `validate_answer(answer, retrieval_results) → (float, List[str])` — confidence + issues
- [x] T013 إنشاء `services/helpscout_client.py`:
  - `get_conversation(conversation_id) → dict`
  - `reply(conversation_id, body, is_html)` — إرسال رد
  - `close_conversation(conversation_id)`
  - `assign_conversation(conversation_id, assignee_id)`
  - `add_note(conversation_id, body)` — للتصعيد الداخلي
- [x] T014 [P] إنشاء `services/facebook_client.py`:
  - `get_comment(comment_id) → dict`
  - `reply_comment(comment_id, message)` — رد على تعليق
  - `get_page_comments(page_id, since) → List[dict]`
- [x] T015 [P] إنشاء `services/redis_bus.py` (publish, publish_stream, build_event, ensure_consumer_group, read_group, ack)
- [x] T016 [P] إنشاء `services/resend_client.py` (send_escalation_alert, send_recurring_issue_alert)

---

## Phase 3: Nodes (14 node)

**Purpose**: منطق المعالجة الكاملة

- [x] T017 `nodes/ticket_receiver.py` — make_ticket_receiver_node(): تحويل webhook payload → SupportTicket + تحقق من المنصة
- [x] T018 `nodes/identity_resolver.py` — make_identity_resolver_node(helpscout): استخراج email + order_id + license_key → Identity
- [x] T019 `nodes/combined_classifier.py` — make_combined_classifier_node(claude): intent_category + risk_flags في استدعاء واحد منفصل المخرجات
- [x] T020 `nodes/hard_policy_gate.py` — make_hard_policy_gate_node(): billing/legal/refund → route_to_escalation مباشرة (SUP_201) + route_after_policy()
- [x] T021 `nodes/retrieval_planner.py` — make_retrieval_planner_node(qdrant): بناء 3 استعلامات متوازية → RetrievalResults من theme_docs + general_faqs + resolved_tickets
- [x] T022 `nodes/answer_generator.py` — make_answer_generator_node(claude): توليد SupportAnswer مع disclaimer + مصادر محددة (لا إجابة بلا مصدر)
- [x] T023 `nodes/answer_validator.py` — make_answer_validator_node(claude): confidence_score (0-1) + factual_issues + route_after_validation()
- [x] T024 `nodes/confidence_router.py` — route_after_confidence(): < 0.50 → escalation، revision < 2 → generator، else → reply_sender
- [x] T025 `nodes/reply_sender.py` — make_reply_sender_node(helpscout, facebook): إرسال للمنصة المناسبة بحسب ticket.platform
- [x] T026 `nodes/escalation_handler.py` — make_escalation_handler_node(helpscout, resend): تصعيد مع context (سبب + رسالة أصلية + identity) + إشعار المالك
- [x] T027 `nodes/safe_reply_sender.py` — make_safe_reply_sender_node(helpscout, facebook): رد دبلوماسي للعميل عند التصعيد
- [x] T028 `nodes/recurring_detector.py` — make_recurring_detector_node(db, redis_bus): فحص ≥3 نفس المشكلة خلال 7 أيام → RECURRING_ISSUE_DETECTED مع EvidenceContract
- [x] T029 `nodes/ticket_recorder.py` — make_ticket_recorder_node(db, qdrant): حفظ execution_log + upsert في resolved_tickets إن confidence > 0.80

---

## Phase 4: Agent + Listeners + API

**Purpose**: ربط كل شيء + واجهة الاستماع + FastAPI

- [x] T030 إنشاء `agent.py` — build_support_graph() + run_support_pipeline() مع كامل الـ edges والـ conditional routing
- [x] T031 إنشاء `listeners/helpscout_webhook.py` — استقبال POST من HelpScout + HMAC verification + تشغيل pipeline
- [x] T032 [P] إنشاء `listeners/event_listener.py` — استماع على product-events (NEW_PRODUCT_LIVE → تحديث KB، LICENSE_ISSUED → تحديث identity)
- [x] T033 إنشاء `api/main.py` — FastAPI lifespan (init services + start listeners) + POST /webhooks/helpscout + POST /webhooks/facebook + GET /health

---

## Phase 5: Qdrant Schema + Migration

**Purpose**: إعداد قاعدة المعرفة الأولية

- [x] T034 إنشاء `db/migrations/001_support_tables.sql` (support_execution_log, support_escalation_log, support_knowledge_log)
- [x] T035 إنشاء `scripts/init_qdrant.py` — إنشاء 3 collections (theme_docs, general_faqs, resolved_tickets) بـ vector_size=1536
- [x] T036 إنشاء `scripts/seed_faqs.py` — تحميل الـ FAQs الأولية من ملف JSON

---

**الإجمالي**: 36 مهمة | **[P]**: يمكن تشغيلها بالتوازي
