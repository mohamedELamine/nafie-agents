# Marketing Agent

وكيل نشر ذكي: يجمع محتوى + أصول + بيانات قالب، يبني حملة متكاملة، يجدول النشر على Facebook/Instagram/TikTok/WhatsApp، ويقترح (دون تنفيذ) على القنوات المدفوعة.

## Architecture

```
agents/marketing/marketing-agent/
├── pyproject.toml / Dockerfile / .env.example / logging_config.py
├── models.py                   # Campaign, ContentSnapshot, AssetSnapshot, ScheduledPost
├── state.py                    # MarketingState TypedDict
├── agent.py                    # build_marketing_graph() + run_marketing_pipeline()
├── db/
│   ├── marketing_calendar.py   # save_campaign, schedule_post, get_scheduled, mark_published
│   └── campaign_log.py         # save_log, get_campaign_history, get_channel_stats
├── services/
│   ├── facebook_client.py      # post_page, post_story, post_reel
│   ├── instagram_client.py     # post_feed, post_story, post_reel
│   ├── tiktok_client.py        # post_video, post_story
│   ├── whatsapp_client.py      # send_broadcast, send_template
│   ├── redis_bus.py
│   └── resend_client.py
├── nodes/
│   ├── readiness_aggregator.py # بوابة اكتمال الحملة
│   ├── asset_collector.py      # جمع المحتوى + الأصول
│   ├── analytics_consumer.py   # استهلاك AUTO_APPLICABLE_SIGNALS
│   ├── channel_router.py       # AUTONOMOUS vs PAID_ONLY
│   ├── calendar_scheduler.py   # جدولة في Marketing Calendar
│   ├── platform_publisher.py   # النشر الفعلي
│   ├── rejection_handler.py    # إشعار + إعادة جدولة
│   ├── paid_channel_gate.py    # مقترح فقط للقنوات المدفوعة
│   └── campaign_recorder.py    # تسجيل النتائج
├── listeners/
│   ├── content_listener.py     # CONTENT_READY
│   ├── assets_listener.py      # THEME_ASSETS_READY
│   └── analytics_listener.py   # ANALYTICS_SIGNAL (AUTO_APPLICABLE)
└── api/
    └── main.py                 # /health + /campaigns + /schedule/{campaign_id}/cancel
```

## Workflow Architecture

```
[readiness_aggregator]  ← يتحقق: content + assets + product live
       │
       ▼
[asset_collector]       ← يجمّد: ContentSnapshot + AssetSnapshot
       │
       ▼
[analytics_consumer]    ← يُطبّق AUTO_APPLICABLE_SIGNALS (best_time, best_channel)
       │
       ▼
[channel_router]        ← AUTONOMOUS vs PAID_ONLY
       ├── paid → [paid_channel_gate]  ← مقترح + إشعار
       │
       ▼
[calendar_scheduler]    ← يُسجّل في Marketing Calendar
       │
       ▼
[platform_publisher]    ← ينشر على Facebook/Instagram/TikTok/WhatsApp
       ├── فشل → [rejection_handler] ← retry × 3
       │
       ▼
[campaign_recorder]     ← CAMPAIGN_LAUNCHED / POST_PUBLISHED
```

## Event Contracts

**Inbound Streams**: `content-events`, `asset-events`, `analytics:signals`
**Inbound Events**: `CONTENT_READY`, `THEME_ASSETS_READY`, `ANALYTICS_SIGNAL`
**Outbound Stream**: `marketing-events`
**Outbound Events**: `CAMPAIGN_LAUNCHED`, `POST_PUBLISHED`

## Setup

### Prerequisites
- Python 3.12+
- PostgreSQL 14+
- Redis 6+
- Facebook Page Access Token
- Instagram Access Token
- TikTok Access Token
- WhatsApp Business Access Token

### Installation

```bash
# Install dependencies
pip install -e .

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Run migrations
psql -U marketing -d marketing_db -f db/migrations/001_marketing_tables.sql
```

### Running

```bash
# Start API server
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Or from the repository root
python agents/marketing/agent.py
```

## API Endpoints

### Health & Status
- `GET /health` - Health check

### Campaign Management
- `POST /campaigns` - Create a new campaign
- `GET /campaigns/{campaign_id}` - Get campaign details
- `POST /campaigns/{campaign_id}/schedule` - Start the marketing pipeline
- `GET /campaigns/{campaign_id}/status` - Get campaign status and stats
- `POST /schedule/{campaign_id}/cancel` - Cancel scheduled posts

## Constitution

The marketing agent operates under these core principles:

1. **Content Snapshot before Scheduling**: Content is frozen at scheduling time - no changes after
2. **AUTONOMOUS_CHANNELS Only for Execution**: 
   - Autonomous channels: Facebook Page, Instagram, TikTok, WhatsApp Business
   - Suggested channels (no execution): Google Ads, Meta Paid Ads
3. **USER_LOCKED_DECISIONS Protected**: Never modified by agent
4. **READINESS_AGGREGATOR: Completion Check**: 
   - Requires: content + assets + product live (within 48h)
   - Partial launch prohibited
5. **Idempotency**: No duplicate posts on same platform
6. **Analytics-Driven**: Only AUTO_APPLICABLE_SIGNALS applied, never USER_LOCKED_DECISIONS

## Runtime Notes

- `best_time` now updates scheduling windows.
- `best_channel` now updates selected channels instead of mutating formats.
- Listeners read from shared Redis streams and use `MARKETING_DATABASE_URL` or `DATABASE_URL` when available.

## Database Schema

### Tables
- `marketing_calendar` - Campaign definitions
- `scheduled_posts` - Individual posts with scheduling details
- `campaign_log` - Event tracking

## License

MIT
