# Implementation Plan: marketing-agent
**Branch**: `marketing-agent-v1` | **Date**: 2026-03-22 | **Spec**: `agents/marketing/docs/spec.md`

---

## Summary

وكيل نشر ذكي: يجمع محتوى + أصول + بيانات قالب، يبني حملة متكاملة، يجدول النشر على Facebook/Instagram/TikTok/WhatsApp، ويقترح (دون تنفيذ) على القنوات المدفوعة.

---

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: langgraph>=0.2.0, fastapi>=0.110.0, psycopg2-binary, redis[hiredis], httpx, resend
**Storage**: PostgreSQL (marketing_calendar, campaign_log) + Redis (checkpoints, schedules)
**External APIs**: Facebook Graph API, Instagram API, TikTok API, WhatsApp Business API
**Performance Goals**: نشر خلال < 2 دقائق من وقت الجدولة المحدد

---

## Project Structure

```
agents/marketing/marketing-agent/
├── pyproject.toml / Dockerfile / .env.example / logging_config.py
├── state.py                    # MarketingState TypedDict
├── models.py                   # Campaign, ContentSnapshot, AssetSnapshot, ScheduledPost
├── agent.py                    # build_marketing_graph()
├── db/
│   ├── marketing_calendar.py   # save_campaign, schedule_post, get_scheduled, mark_published
│   └── campaign_log.py         # save_log, get_campaign_history
├── services/
│   ├── facebook_client.py      # post_page, post_story, post_reel
│   ├── instagram_client.py     # post_feed, post_story, post_reel
│   ├── tiktok_client.py        # post_video, post_story
│   ├── whatsapp_client.py      # send_broadcast, send_template
│   ├── redis_bus.py
│   └── resend_client.py
├── nodes/
│   ├── readiness_aggregator.py # بوابة اكتمال الحملة
│   ├── asset_collector.py      # جمع المحتوى + الأصول + تجميدهما
│   ├── channel_router.py       # AUTONOMOUS_CHANNELS فقط
│   ├── calendar_scheduler.py   # جدولة في Marketing Calendar
│   ├── platform_publisher.py   # النشر الفعلي
│   ├── rejection_handler.py    # إشعار + إعادة جدولة
│   ├── paid_channel_gate.py    # مقترح فقط للقنوات المدفوعة
│   ├── analytics_consumer.py   # استهلاك AUTO_APPLICABLE_SIGNALS
│   └── campaign_recorder.py    # تسجيل النتائج
├── listeners/
│   ├── content_listener.py     # CONTENT_READY
│   ├── assets_listener.py      # THEME_ASSETS_READY
│   └── analytics_listener.py   # ANALYTICS_SIGNAL (AUTO_APPLICABLE فقط)
└── api/
    └── main.py                 # /health + /campaigns + /schedule/{campaign_id}
```

---

## Workflow Architecture

```
[readiness_aggregator]  ← يتحقق: content + assets + product live
      │
      ▼
[asset_collector]       ← يجمّد: ContentSnapshot + AssetSnapshot
      │
      ▼
[analytics_consumer]    ← يُطبّق AUTO_APPLICABLE_SIGNALS (best_time, best_format)
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

**Inbound**: `CONTENT_READY`, `THEME_ASSETS_READY`, `ANALYTICS_SIGNAL`
**Outbound**: `CAMPAIGN_LAUNCHED`, `POST_PUBLISHED`
