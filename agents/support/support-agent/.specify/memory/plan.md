# Implementation Plan: support-agent
**Branch**: `support-agent-v1` | **Date**: 2026-03-22 | **Spec**: `agents/support/docs/spec.md`

---

## Summary

وكيل دعم ذكي يعمل على HelpScout + Facebook Comments، يُحلل هوية العميل وينوي رده في طبقتين مستقلتين (Intent + Risk)، يُجيب من Knowledge Base (Qdrant)، ويُصعّد ما لا يعرفه. مبني على LangGraph StateGraph بنمط closure factories.

---

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: langgraph>=0.2.0, anthropic>=0.25.0, qdrant-client>=1.9.0, fastapi>=0.110.0, psycopg2-binary, redis[hiredis], resend
**Storage**: PostgreSQL (execution_log, escalation_log, knowledge_log) + Qdrant (knowledge base vectors)
**Testing**: pytest
**Target Platform**: Linux Docker container
**Performance Goals**: < 5 دقائق للرد الآلي
**Constraints**: لا ردود بدون مصدر، confidence < 0.50 → تصعيد فوري
**Scale/Scope**: تذاكر HelpScout + تعليقات Facebook

---

## Constitution Check

| المبدأ | الحالة |
|--------|--------|
| Honesty-First: لا رد بلا مصدر | ✓ RETRIEVAL_PLANNER يتطلب source قبل ANSWER_GENERATOR |
| HARD_POLICY_GATE: billing/legal تصعيد فوري | ✓ node مستقل يُوقف الـ flow |
| Two-Layer Classification | ✓ COMBINED_CLASSIFIER يُنتج intent + risk_flags منفصلين |
| Idempotency | ✓ ticket_id + platform = مفتاح فريد |
| لا كشف عن البنية الداخلية | ✓ ANSWER_GENERATOR محصور بـ system prompt |

---

## Project Structure

```
agents/support/support-agent/
├── pyproject.toml
├── Dockerfile
├── .env.example
├── logging_config.py
├── state.py                    # SupportState TypedDict
├── models.py                   # Domain Model: Ticket, Identity, Classification, Answer
├── agent.py                    # build_support_graph() + run_support_pipeline()
│
├── db/
│   ├── __init__.py
│   ├── execution_log.py        # تسجيل كل معالجة
│   ├── escalation_log.py       # تسجيل التصعيدات
│   └── knowledge_log.py        # تسجيل تحديثات KB
│
├── services/
│   ├── __init__.py
│   ├── claude_client.py        # COMBINED_CLASSIFIER + ANSWER_GENERATOR + ANSWER_VALIDATOR
│   ├── qdrant_client.py        # Knowledge Base retrieval (3 collections)
│   ├── helpscout_client.py     # Mailbox API: get_conversation, reply, close, assign
│   ├── facebook_client.py      # Graph API: get_comments, reply_comment
│   ├── redis_bus.py            # pub/sub + streams
│   └── resend_client.py        # إشعارات التصعيد
│
├── nodes/
│   ├── __init__.py
│   ├── ticket_receiver.py      # استقبال + تحويل للـ SupportTicket
│   ├── identity_resolver.py    # IDENTITY_RESOLVER: email + order + license
│   ├── combined_classifier.py  # COMBINED_CLASSIFIER: intent + risk_flags (طبقتان)
│   ├── hard_policy_gate.py     # HARD_POLICY_GATE: billing/legal → تصعيد فوري
│   ├── retrieval_planner.py    # RETRIEVAL_PLANNER: بناء استعلامات Qdrant
│   ├── answer_generator.py     # ANSWER_GENERATOR: رد مع disclaimer + مصادر
│   ├── answer_validator.py     # ANSWER_VALIDATOR: confidence + factual check
│   ├── confidence_router.py    # routing بحسب confidence_score
│   ├── reply_sender.py         # REPLY_SENDER: إرسال للمنصة المناسبة
│   ├── escalation_handler.py   # ESCALATION_HANDLER: تصعيد مع context كامل
│   ├── safe_reply_sender.py    # إرسال رد التصعيد للعميل
│   ├── recurring_detector.py   # RECURRING_ISSUE_DETECTED: ≥3 نفس المشكلة
│   └── ticket_recorder.py      # حفظ النتيجة + تحديث KB
│
├── listeners/
│   ├── __init__.py
│   ├── helpscout_webhook.py    # استقبال webhooks HelpScout
│   └── event_listener.py       # NEW_PRODUCT_LIVE + LICENSE_ISSUED
│
└── api/
    ├── __init__.py
    └── main.py                 # FastAPI: /health + /webhooks/helpscout + /webhooks/facebook
```

---

## Workflow Architecture

```
[ticket_receiver]
      │
      ▼
[identity_resolver]      ← email + order_id + license_key من HelpScout
      │
      ▼
[combined_classifier]    ← intent_category + risk_flags (طبقتان مستقلتان)
      │
      ▼
[hard_policy_gate]       ← billing/legal/refund → escalation_handler مباشرة
      │
      ▼
[retrieval_planner]      ← بناء 3 استعلامات Qdrant متوازية
      │
      ▼
[answer_generator]       ← Claude + KB results + disclaimer
      │
      ▼
[answer_validator]       ← confidence_score + factual check
      ├── confidence < 0.50 → [escalation_handler]
      ├── revision < 2    → [answer_generator] (إعادة)
      │
      ▼
[reply_sender]           ← HelpScout أو Facebook
      │
      ▼
[recurring_detector]     ← إن ≥3 نفس المشكلة → RECURRING_ISSUE_DETECTED
      │
      ▼
[ticket_recorder]        ← execution_log + تحديث KB إن مفيدة
```

---

## Error Codes

```python
SUP_001 = "UNKNOWN_PLATFORM"
SUP_101 = "IDENTITY_UNRESOLVED"
SUP_201 = "HARD_POLICY_TRIGGER"    # billing/legal
SUP_301 = "KB_RETRIEVAL_FAILED"
SUP_401 = "LOW_CONFIDENCE"         # < 0.50
SUP_402 = "MAX_REVISIONS_REACHED"  # ≥ 2 إعادة
SUP_501 = "REPLY_SEND_FAILED"
SUP_601 = "ESCALATION_FAILED"      # فشل التصعيد نفسه
```

---

## Event Contracts

**Inbound**: `new_conversation` (HelpScout webhook), `NEW_PRODUCT_LIVE`, `LICENSE_ISSUED`
**Outbound**: `SUPPORT_TICKET_RESOLVED`, `SUPPORT_TICKET_ESCALATED`, `RECURRING_ISSUE_DETECTED`, `KNOWLEDGE_BASE_UPDATED`
