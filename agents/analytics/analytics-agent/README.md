# Analytics Agent

وكيل تحليل يعمل كطبقة استخبارات تشغيلية للمنظومة: يجمع الأحداث، يحوّلها إلى مقاييس بـ granularity محدد، يستخرج أنماطًا تشغيلية وتجارية، ويولّد إشارات للوكلاء وتنبيهات لصاحب المشروع. لا يغيّر الأنظمة المصدرية مباشرة، لكنه يكتب إلى جداول التحليل الخاصة به ويصدر إشارات مشتركة عبر Redis Streams.

## Architecture

```
agents/analytics/analytics-agent/
├── pyproject.toml          # Project configuration
├── Dockerfile              # Container definition
├── .env.example            # Environment variables template
├── logging_config.py       # Logging configuration
├── models.py               # Domain models
├── state.py                # AnalyticsState TypedDict
├── metric_definitions.py   # Metric definitions registry
│
├── db/                     # Database layer
│   ├── __init__.py
│   ├── event_store.py      # Event persistence
│   ├── metric_store.py     # Metric snapshots
│   ├── signal_store.py     # Signal management
│   ├── attribution_store.py
│   ├── pattern_store.py
│   ├── report_store.py
│   └── outcome_store.py
│
├── services/               # External integrations
│   ├── __init__.py
│   ├── lemon_squeezy_client.py
│   ├── helpscout_client.py
│   ├── redis_bus.py
│   ├── resend_client.py
│   └── product_registry.py
│
├── workflows/              # Processing layers
│   ├── __init__.py
│   ├── event_collector.py  # Real-time event collection
│   ├── immediate_evaluator.py  # 15-min checks
│   ├── metrics_engine.py   # Hourly metrics
│   ├── pattern_analyzer.py # Daily patterns
│   ├── signal_generator.py # Signal generation
│   ├── report_generator.py # Weekly reports
│   ├── reconciliation.py   # Daily sales reconciliation
│   └── attribution.py
│
├── api/                    # FastAPI endpoints
│   ├── __init__.py
│   └── main.py
│
├── scheduler.py            # APScheduler
└── pytest.ini              # Test configuration
```

## Processing Layers

### Layer 1: Event Collector + Immediate Evaluator
- **Frequency**: Real-time + every 15 minutes
- **Purpose**: Process incoming events + micro-checks
- **Actions**: Store events, attribute sales, emit immediate signals to `analytics:signals`

### Layer 2: Metrics Engine
- **Frequency**: Every hour
- **Purpose**: Aggregate metrics (hour → day → week)
- **Actions**: Calculate metrics, save snapshots

### Layer 3: Pattern Analyzer
- **Frequency**: Daily at 03:00
- **Purpose**: Identify patterns and insights
- **Actions**: Operational patterns (alerts) + Business patterns (insights)

### Layer 4: Signal Generator + Reports
- **Frequency**: Daily + Weekly
- **Purpose**: Generate signals + reports
- **Actions**: Emit signals to agents via shared stream, send reports to owner

## Shared Contracts

### Inbound Streams
- `product-events`
- `support-events`
- `marketing-events`
- `content-events`
- `asset-events`

### Outbound Streams
- `analytics:signals`

### Shared Event Types
- `ANALYTICS_SIGNAL`
- `CONTENT_PRODUCED`
- `POST_PUBLISHED`
- `CAMPAIGN_LAUNCHED`
- `THEME_ASSETS_READY`

## Signal Types

### Operational Signals (Immediate)
- `NO_OUTPUT_ALERT` - Products with no sales for 30 days
- `SALES_DROP_ALERT` - Sales drop > 50% from previous week
- `SUPPORT_SURGE_ALERT` - 10+ support tickets in 24 hours
- `CAMPAIGN_NO_OUTPUT` - Campaign with no posts for 24 hours
- `RECURRING_QUALITY_ISSUE` - ≥3 issues of same type
- `RECONCILIATION_MISMATCH` - Data discrepancy > 5

### Business Signals (Weekly)
- `BEST_TIME` - Best day/time for sales
- `BEST_CHANNEL` - Best performing channel
- `LOW_SALES` - Sales below threshold
- `CAMPAIGN_RESULT` - Campaign performance
- `CONTENT_PERFORMANCE` - Content effectiveness
- `BEST_CONTENT_TYPE` - Best content type
- `PRICING_SIGNAL` - Pricing insights
- `PRODUCT_SIGNAL` - Product insights
- `BUILD_FEEDBACK` - Builder feedback
- `SUPPORT_PATTERN` - Support patterns

## Setup

### Prerequisites
- Python 3.12+
- PostgreSQL 14+
- Redis 6+

### Installation

```bash
# Install dependencies
pip install -e .

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Run migrations
psql -U analytics -d analytics_db -f db/migrations/001_analytics_tables.sql
```

### Running

```bash
# Start scheduler (main process)
python scheduler.py

# Or from the repository root
python agents/analytics/agent.py

# Or run as API
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health & Status
- `GET /health` - Health check

### Dashboard
- `GET /dashboard` - Latest signals, patterns, and metrics summary

### Reports
- `GET /reports/weekly/{period}` - Get weekly report
- `GET /reports/monthly/{month}/{year}` - Get monthly report

### Signals
- `GET /signals?type=&agent=&since=` - List signals with filters
- `POST /signals/{signal_id}/outcome` - Record signal outcome

### Metrics
- `GET /metrics?period_start=&period_end=&granularity=` - Get metrics
- `GET /metrics/definitions` - Get all metric definitions

### Events
- `GET /events?event_type=&since=&limit=` - List events

### Attribution
- `GET /attribution/summary?days=` - Get attribution summary

## Environment Variables

```bash
CLAUDE_API_KEY=your-claude-api-key
DATABASE_URL=postgresql://analytics:password@localhost:5432/analytics_db
REDIS_URL=redis://localhost:6379/0
RESEND_API_KEY=your-resend-api-key
OWNER_EMAIL=owner@example.com
LS_API_KEY=your-lemon-squeezy-api-key
LS_STORE_ID=your-lemon-squeezy-store-id
HELPSCOUT_API_KEY=your-helpscout-api-key
ATTRIBUTION_WINDOW_DAYS=7
```

## Constitution

The analytics agent operates under these core principles:

1. **No Upstream Mutation**: Never mutates source systems, but writes its own events, metrics, patterns, and signals
2. **occurred_at for Analysis**: Always use occurred_at for calculations
3. **Lemon Squeezy is Truth**: Reconciliation is mandatory, Lemon Squeezy wins
4. **Attribution is Approximation**: Always declare confidence
5. **Explicit Granularity**: Every metric has defined granularity
6. **Partial Failure Does Not Stop All**: Each layer is independent
7. **Real-time for Critical Only**: Only immediate checks are real-time
8. **Idempotency**: No reprocessing of completed periods

## Database Schema

### Tables
- `analytics_events` - Event logs
- `metric_snapshots` - Metric values over time
- `analytics_patterns` - Detected patterns
- `analytics_signals` - Generated signals
- `attribution_records` - Sale attribution
- `signal_outcomes` - Signal feedback
- `weekly_reports` - Weekly reports

## Notes

- `emit_immediate_signal()` now preserves immediate priority for urgent alerts such as reconciliation mismatches.
- Shared delivery to downstream agents happens through `send_to_target_agent()` on the `analytics:signals` stream.

## License

MIT
