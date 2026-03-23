# Tasks: marketing-agent
**Input**: `agents/marketing/docs/spec.md` + `plan.md` + `constitution.md`
**Implementation**: `/speckit.implement`

---

## Phase 1: Setup + Foundation

- [X] T001 `pyproject.toml` + `Dockerfile` + `.env.example` (FACEBOOK_PAGE_TOKEN, INSTAGRAM_TOKEN, TIKTOK_TOKEN, WHATSAPP_TOKEN, DATABASE_URL, REDIS_URL, ...)
- [X] T002 `logging_config.py` (agent=marketing)
- [X] T003 `models.py`: Campaign, ContentSnapshot, AssetSnapshot, ScheduledPost, MarketingChannel Enum, PublishResult
- [X] T004 `state.py`: MarketingState TypedDict + make_initial_state()
- [X] T005 [P] `db/marketing_calendar.py` (save_campaign, schedule_post, get_pending_posts, mark_published, mark_failed)
- [X] T006 [P] `db/campaign_log.py` (save_log, get_campaign_history, get_channel_stats)
- [X] T007 `db/migrations/001_marketing_tables.sql` (marketing_calendar, campaign_log, scheduled_posts)

---

## Phase 2: Services

- [X] T008 `services/facebook_client.py` (post_to_page, post_story, post_reel, get_page_insights)
- [X] T009 `services/instagram_client.py` (post_feed_image, post_reel, post_story, get_media_insights)
- [X] T010 `services/tiktok_client.py` (post_video, get_video_stats)
- [X] T011 [P] `services/whatsapp_client.py` (send_broadcast_template, get_template_status)
- [X] T012 [P] `services/redis_bus.py` (publish, build_event, checkpoint, consumer_group)
- [X] T013 [P] `services/resend_client.py` (send_campaign_launched, send_publish_failed, send_paid_channel_suggestion)

---

## Phase 3: Nodes (9 nodes)

- [X] T014 `nodes/readiness_aggregator.py` — make_readiness_aggregator_node(redis): تحقق من توفر content + assets + product_live + route_after_readiness()
- [X] T015 `nodes/asset_collector.py` — make_asset_collector_node(): تجميد ContentSnapshot + AssetSnapshot في state (لا تعديل بعدها)
- [X] T016 `nodes/analytics_consumer.py` — make_analytics_consumer_node(redis): استهلاك AUTO_APPLICABLE_SIGNALS (best_post_time, best_format, engagement_peak) — لا يمس USER_LOCKED_DECISIONS
- [X] T017 `nodes/channel_router.py` — make_channel_router_node(): تقسيم القنوات → autonomous_channels + paid_suggestions + route_after_channel()
- [X] T018 `nodes/paid_channel_gate.py` — make_paid_channel_gate_node(resend): بناء تقرير اقتراح + إشعار المالك (لا تنفيذ)
- [X] T019 `nodes/calendar_scheduler.py` — make_calendar_scheduler_node(db, redis): تسجيل في Marketing Calendar + checkpoint (TTL 72h) + تحديد وقت النشر بـ best_post_time
- [X] T020 `nodes/platform_publisher.py` — make_platform_publisher_node(facebook, instagram, tiktok, whatsapp): نشر على كل منصة بالتوازي، retry × 3
- [X] T021 `nodes/rejection_handler.py` — make_rejection_handler_node(resend): تسجيل الفشل + إشعار + إعادة جدولة أو تصعيد
- [X] T022 `nodes/campaign_recorder.py` — make_campaign_recorder_node(db, redis_bus): تسجيل النتائج + CAMPAIGN_LAUNCHED + POST_PUBLISHED

---

## Phase 4: Agent + Listeners + API

- [X] T023 `agent.py` — build_marketing_graph() + run_marketing_pipeline()
- [X] T024 `listeners/content_listener.py` — CONTENT_READY → تحديث campaign readiness
- [X] T025 [P] `listeners/assets_listener.py` — THEME_ASSETS_READY → تحديث campaign readiness
- [X] T026 [P] `listeners/analytics_listener.py` — ANALYTICS_SIGNAL (AUTO_APPLICABLE فقط) → تحديث scheduling params
- [X] T027 `api/main.py` (/health + /campaigns/{campaign_id} + /schedule/{campaign_id}/cancel)

---

**الإجمالي**: 27 مهمة
