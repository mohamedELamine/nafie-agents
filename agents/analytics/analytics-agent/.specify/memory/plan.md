# Implementation Plan: analytics-agent
**Branch**: `analytics-agent-v1` | **Date**: 2026-03-22 | **Spec**: `agents/analytics/docs/spec.md`

---

## Summary

وكيل تحليل يعمل كطبقة استخبارات تشغيلية للمنظومة: يجمع الأحداث، يحوّلها إلى مقاييس بـ granularity محدد، يستخرج نمطين (Operational + Business)، يُولّد إشارات للوكلاء وتنبيهات لصاحب المشروع — معالجة Real-time للإشارات العاجلة وBatch للقياس العميق. **لا يُغيّر شيئاً بنفسه.**

---

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: langgraph>=0.2.0, anthropic>=0.25.0, fastapi>=0.110.0, psycopg2-binary, redis[hiredis], resend, httpx (Lemon Squeezy + HelpScout)
**Storage**: PostgreSQL (analytics_events, metric_snapshots, patterns, signals, attribution_records, signal_outcomes, weekly_reports)
**Testing**: pytest
**Target Platform**: Linux Docker container
**Processing Schedule**: event_collector (مستمر) + immediate_evaluator (كل 15 دقيقة) + metrics_batch (كل ساعة) + pattern_batch (يومياً 03:00) + weekly_report (الأحد 08:00)

---

## Constitution Check

| المبدأ | الحالة |
|--------|--------|
| Read-Only بالمطلق | ✓ لا API كتابة، لا تعديل بيانات |
| `occurred_at` للتحليل | ✓ كل حساب يعتمد occurred_at |
| Lemon Squeezy مصدر الحقيقة | ✓ Reconciliation يومي + primary_wins |
| Attribution = تقريب | ✓ AttributionConfidence مُعلَن دائماً |
| Granularity صريح | ✓ METRIC_DEFINITIONS يحدد granularity لكل مقياس |
| الفشل الجزئي لا يوقف الكل | ✓ كل طبقة مستقلة |
| Idempotency | ✓ metric_key + period_start + theme_slug = مفتاح فريد |

---

## Project Structure

```
agents/analytics/analytics-agent/
├── pyproject.toml
├── Dockerfile
├── .env.example
├── logging_config.py
├── models.py                   # Domain Model: AnalyticsEvent, MetricSnapshot, Pattern, Signal, Attribution
├── state.py                    # AnalyticsState TypedDict لكل workflow
├── metric_definitions.py       # METRIC_DEFINITIONS registry + get_metric_definition()
│
├── db/
│   ├── __init__.py
│   ├── event_store.py          # save, exists, count_events, get_last_event, get_events, backfill
│   ├── metric_store.py         # save_snapshot, get_snapshot, sum, aggregate_hourly_to_daily
│   ├── pattern_store.py        # save_pattern, get_recent_patterns
│   ├── signal_store.py         # save_signal, sent_recently, mark_sent
│   ├── attribution_store.py    # save_record, get_records_by_theme, get_records_by_channel
│   └── report_store.py         # save_report, get_report
│
├── services/
│   ├── __init__.py
│   ├── lemon_squeezy_client.py # get_orders(since, use_occurred_at), get_licenses, get_order
│   ├── helpscout_client.py     # get_conversations(since, status), get_conversation_stats
│   ├── redis_bus.py            # publish, read_group, ack, ensure_consumer_group
│   ├── resend_client.py        # send_owner_alert, send_weekly_report
│   └── product_registry.py    # get_all_published_slugs, get_launch_date (يقرأ من DB)
│
├── workflows/
│   ├── __init__.py
│   ├── event_collector.py      # event_collector_node() + Attribution فوري عند NEW_SALE
│   ├── immediate_evaluator.py  # ImmediateEvaluator class + run_scheduled_checks() كل 15 دق
│   ├── metrics_engine.py       # metrics_engine_batch() كل ساعة + daily_aggregation يومياً
│   ├── pattern_analyzer.py     # OperationalPatternAnalyzer + BusinessPatternAnalyzer يومياً
│   ├── signal_generator.py     # generate_signals_from_patterns() + emit_immediate_signal()
│   ├── report_generator.py     # generate_weekly_report() + generate_monthly_report()
│   └── reconciliation.py       # reconcile_sales_data() يومياً مع Lemon Squeezy
│
├── api/
│   ├── __init__.py
│   └── main.py                 # FastAPI: /health + /dashboard + /reports/{period} + /signals
│
└── scheduler.py                # APScheduler: تسجيل كل المهام الدورية
```

---

## Processing Architecture (4 طبقات)

```
┌─────────────────────────────────────────────────────┐
│  طبقة ١ — Event Collector + Immediate Evaluator     │
│  مستمر — كل حدث وارد + micro-checks كل 15 دقيقة   │
├─────────────────────────────────────────────────────┤
│  طبقة ٢ — Metrics Engine (Batch — كل ساعة)         │
│  hour → day → week → month (تجميع لا إعادة حساب)   │
├─────────────────────────────────────────────────────┤
│  طبقة ٣ — Pattern Analyzer (Batch — يومياً 03:00)  │
│  Operational (تنبيهات) + Business (قرارات)          │
├─────────────────────────────────────────────────────┤
│  طبقة ٤ — Signal Generator + Reports               │
│  ANALYTICS_SIGNAL → Redis + OWNER_ALERT → Resend   │
└─────────────────────────────────────────────────────┘
```

---

## Signal Types

```python
# Operational (فورية/يومية)
NO_OUTPUT_ALERT          # قالب بلا مبيعات 30 يوم
SALES_DROP_ALERT         # انخفاض > 50% مقارنة بالأسبوع الماضي
SUPPORT_SURGE_ALERT      # 10+ تذاكر مُصعَّدة / 24 ساعة
CAMPAIGN_NO_OUTPUT       # حملة بلا منشور بعد 24 ساعة
RECURRING_QUALITY_ISSUE  # ≥3 مشاكل جودة نفس النوع
RECONCILIATION_MISMATCH  # تباين كبير مع Lemon Squeezy

# Business (للوكلاء — أسبوعية/شهرية)
BEST_TIME            → marketing_agent
BEST_CHANNEL         → marketing_agent
LOW_SALES            → marketing_agent + platform_agent
CAMPAIGN_RESULT      → marketing_agent
CONTENT_PERFORMANCE  → content_agent
BEST_CONTENT_TYPE    → content_agent
PRICING_SIGNAL       → platform_agent
PRODUCT_SIGNAL       → platform_agent
BUILD_FEEDBACK       → builder_agent
SUPPORT_PATTERN      → support_agent
```

---

## Error Codes

```python
ANL_001 = "EVENT_DUPLICATE"
ANL_002 = "OCCURRED_AT_MISSING"     # استخدام received_at كـ fallback مع تحذير
ANL_101 = "METRIC_NOT_DEFINED"
ANL_102 = "METRIC_PERIOD_EXISTS"    # idempotency — لا إعادة حساب
ANL_201 = "PATTERN_PARTIAL_FAILURE" # detector فشل — الباقي يكمل
ANL_301 = "SIGNAL_SEND_FAILED"
ANL_401 = "LS_RECONCILIATION_FAILED"
ANL_501 = "OWNER_ALERT_FAILED"      # retry 3 مرات + fallback email
ANL_601 = "REPORT_GENERATION_FAILED"
```

---

## Event Contracts

**Inbound**: `NEW_SALE`, `LICENSE_ISSUED`, `NEW_PRODUCT_LIVE`, `THEME_UPDATED_LIVE`, `SUPPORT_TICKET_RESOLVED`, `SUPPORT_TICKET_ESCALATED`, `RECURRING_ISSUE_DETECTED`, `KNOWLEDGE_BASE_UPDATED`, `POST_PUBLISHED`, `CAMPAIGN_LAUNCHED`, `CONTENT_PRODUCED`, `THEME_BUILT`, `THEME_APPROVED`

**Outbound**: `ANALYTICS_SIGNAL`, `WEEKLY_REPORT_READY`, `MONTHLY_REPORT_READY`, `OWNER_CRITICAL_ALERT`
