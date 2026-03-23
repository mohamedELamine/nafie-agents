# Tasks: analytics-agent
**Input**: `agents/analytics/docs/spec.md` + `plan.md` + `constitution.md`
**Implementation**: `/speckit.implement`

---

## Phase 1: Setup + Foundation

**Purpose**: بنية المشروع + Domain Model + قاعدة البيانات + Metric Definitions

- [X] T001 إنشاء `pyproject.toml` (langgraph, anthropic, fastapi, psycopg2-binary, redis[hiredis], resend, httpx, apscheduler)
- [X] T002 إنشاء `Dockerfile` (python:3.12-slim, non-root user, port 8000)
- [X] T003 إنشاء `.env.example` (CLAUDE_API_KEY, DATABASE_URL, REDIS_URL, RESEND_API_KEY, OWNER_EMAIL, LS_API_KEY, LS_STORE_ID, HELPSCOUT_API_KEY, ATTRIBUTION_WINDOW_DAYS=7)
- [X] T004 إنشاء `logging_config.py` (configure_logging + get_logger بصيغة `agent=analytics`)
- [X] T005 إنشاء `models.py`:
  - Enums: SignalType, SignalPriority, AttributionConfidence, AttributionChannel, AnalyticsType
  - Dataclasses: AnalyticsEvent, MetricSnapshot, Pattern, AnalyticsSignal, AttributionRecord, SignalOutcome, WeeklyReport
- [X] T006 إنشاء `metric_definitions.py` (METRIC_DEFINITIONS dict + get_metric_definition() + IMMEDIATE_THRESHOLDS)
- [X] T007 إنشاء `state.py` (AnalyticsState TypedDict + make_initial_state())
- [X] T008 [P] إنشاء `db/event_store.py` (save, exists, count_events, get_last_event, get_events, backfill_sale, get_events_by_type)
- [X] T009 [P] إنشاء `db/metric_store.py` (save_snapshot, get_snapshot, sum, aggregate_hourly_to_daily, get_period_metrics)
- [X] T010 [P] إنشاء `db/signal_store.py` (save_signal, sent_recently, mark_sent, get_signals_by_type)
- [X] T011 [P] إنشاء `db/attribution_store.py` (save_record, get_records_by_theme, get_records_by_channel, get_attribution_summary)
- [X] T012 [P] إنشاء `db/pattern_store.py` (save_pattern, get_recent_patterns, get_patterns_by_type)
- [X] T013 [P] إنشاء `db/report_store.py` (save_report, get_report, get_latest_report)
- [X] T014 إنشاء `db/migrations/001_analytics_tables.sql`:
  - `analytics_events` (event_id, event_type, source_agent, theme_slug, raw_data, occurred_at, received_at, processed)
  - `metric_snapshots` (metric_id, metric_key, theme_slug, channel, granularity, period_start, period_end, value, unit, computed_at)
  - `analytics_signals` (signal_id, signal_type, priority, target_agent, theme_slug, confidence, data, generated_at, sent_at)
  - `attribution_records` (sale_id, theme_slug, attributed_to, confidence, channels_touched, attribution_note, sale_date)
  - `signal_outcomes` (outcome_id, signal_id, before_value, after_value, success_score, evaluated_at)
  - `weekly_reports` (report_id, period_start, period_end, total_sales, total_revenue, highlights, concerns, generated_at)
  - `analytics_patterns` (pattern_id, pattern_type, analytics_type, confidence, supporting_metrics, detected_at, is_actionable)

---

## Phase 2: Services

**Purpose**: التكاملات الخارجية — Lemon Squeezy + HelpScout + Redis + Resend

- [X] T015 إنشاء `services/lemon_squeezy_client.py`:
  - `get_orders(since, use_occurred_at=True) → List[dict]`
  - `get_order(order_id) → dict`
  - `get_licenses(since) → List[dict]`
  - `get_store_stats() → dict`
- [X] T016 إنشاء `services/helpscout_client.py`:
  - `get_conversations(since, status) → List[dict]`
  - `get_conversation_stats(since) → dict`
- [X] T017 إنشاء `services/redis_bus.py` (publish, read_group, ack, ensure_consumer_group, build_analytics_event)
- [X] T018 إنشاء `services/resend_client.py` (send_owner_alert, send_weekly_report, send_critical_alert با retry=3)
- [X] T019 [P] إنشاء `services/product_registry.py` (get_all_published_slugs, get_launch_date — يقرأ من DB لا API)

---

## Phase 3: Workflows (4 طبقات)

**Purpose**: المنطق الكامل للمعالجة — Event Collection + Metrics + Patterns + Signals

- [X] T020 إنشاء `workflows/event_collector.py`:
  - `event_collector_node(event) → None` — تخزين + idempotency check
  - Attribution فوري عند NEW_SALE باستخدام `attribute_sale()`
  - `attribute_sale(sale_id, sale_date, theme_slug, amount_usd, license_tier) → AttributionRecord`
  - التفويض للـ Immediate Evaluator بعد كل حدث
- [X] T021 إنشاء `workflows/immediate_evaluator.py`:
  - `ImmediateEvaluator` class
  - `on_new_event(event)` — checks خفيفة على كل حدث
  - `run_scheduled_checks()` — كل 15 دقيقة
  - `_check_support_surge()`, `_check_no_sales_products()`, `_check_sales_drop()`, `_check_campaign_outputs()`
  - لا تكرار الإشارة إن أُرسلت خلال 24 ساعة
- [X] T022 إنشاء `workflows/metrics_engine.py`:
  - `metrics_engine_batch() → None` — يُشغَّل كل ساعة
  - `daily_aggregation() → None` — يجمّع hourly → daily (يومياً)
  - `weekly_aggregation() → None` — يجمّع daily → weekly
  - حساب كل مقياس بحسب METRIC_DEFINITIONS
  - Idempotency: لا إعادة حساب لنفس الفترة
- [X] T023 إنشاء `workflows/pattern_analyzer.py`:
  - `OperationalPatternAnalyzer` (تنبيهات): sales_drop_7d, support_surge_7d, build_quality_trend
  - `BusinessPatternAnalyzer` (قرارات): best_channel_30d, best_time_of_day, content_performance, license_tier_trend
  - `run_pattern_analysis() → List[Pattern]` — يشغّل الاثنين + فشل أحدهم لا يوقف الآخر
  - كل Pattern بـ confidence + supporting_metrics + is_actionable
- [X] T024 إنشاء `workflows/signal_generator.py`:
  - `generate_signals_from_patterns(patterns) → List[AnalyticsSignal]` — يومياً بعد Pattern Analyzer
  - `emit_immediate_signal(signal_type, theme_slug, data, target_agent)` — للإشارات الفورية
  - `send_to_target_agent(signal)` — نشر على Redis channel المناسب
  - `send_owner_critical_alert(signal_type, data)` — تنبيه حرج + retry 3
- [X] T025 إنشاء `workflows/report_generator.py`:
  - `generate_weekly_report(period_start, period_end) → WeeklyReport` — الأحد 08:00
  - `generate_monthly_report(month, year) → WeeklyReport` — أول الشهر 08:00
  - يستخدم metric_store + signal_store لبناء التقرير
  - يُرسل بـ Resend + يُطلق WEEKLY_REPORT_READY
- [X] T026 إنشاء `workflows/reconciliation.py`:
  - `reconcile_sales_data() → None` — يومياً
  - مقارنة Lemon Squeezy orders مع Redis events (occurred_at)
  - backfill التباين الصغير
  - `RECONCILIATION_MISMATCH` إن missing_in_redis > 5 أو extra_in_redis > 5

---

## Phase 4: Scheduler + API + Retention

**Purpose**: جدولة المهام الدورية + FastAPI + تنظيف البيانات

- [X] T027 إنشاء `scheduler.py` (APScheduler):
  - immediate_evaluator.run_scheduled_checks — كل 15 دقيقة
  - metrics_engine_batch — كل ساعة (0 * * * *)
  - daily_aggregation — يومياً 01:00
  - pattern_analyzer + signal_generator — يومياً 03:00
  - reconcile_sales_data — يومياً 02:00
  - weekly_report — الأحد 08:00 (0 8 * * 0)
  - monthly_report — أول الشهر 08:00 (0 8 1 * *)
  - retention_cleanup — الأحد 02:00 (events > 90 يوم، metrics > 1 سنة)
- [X] T028 إنشاء `api/main.py`:
  - FastAPI lifespan (init DB + services + scheduler + start event_collector listener)
  - GET /health
  - GET /dashboard (آخر signals + آخر metrics + summary)
  - GET /reports/{period} (weekly/monthly)
  - GET /signals?type=&agent=&since= (فلترة الإشارات)
  - POST /signals/{signal_id}/outcome (تسجيل نتيجة إشارة — Signal Outcome Feedback Loop)

---

**الإجمالي**: 28 مهمة | **[P]**: يمكن تشغيلها بالتوازي
