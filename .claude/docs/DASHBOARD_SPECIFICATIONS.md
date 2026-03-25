# Tashkeel Dashboard — Technical Specifications

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Next.js 16 Frontend                    │
│          (React 19 + shadcn/ui + TailwindCSS)           │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐   ┌────────────┐  ┌───────────┐
    │ Vercel  │   │ Neon       │  │ Vercel    │
    │Functions│   │ Postgres   │  │ Blob      │
    │ (API)   │   │ (Database) │  │ (Storage) │
    └────┬────┘   └─────┬──────┘  └─────┬─────┘
         │              │               │
         └──────────────┼───────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
         ▼              ▼              ▼
    ┌─────────┐  ┌───────────┐  ┌──────────┐
    │ Event   │  │ Agents    │  │Vercel    │
    │ Bus     │  │(Analytics,│  │Analytics │
    │(Redis)  │  │Marketing, │  │(Metrics) │
    └─────────┘  │Content..) │  └──────────┘
                 └───────────┘
```

---

## 📋 API Endpoints

### Base URL
```
https://tashkeel.dev/api/v1
```

### Authentication
```
Headers:
  Authorization: Bearer {JWT_TOKEN}
  X-User-ID: {USER_ID}
  Content-Type: application/json
```

---

## 🎨 Themes Management Endpoints

### GET /themes
List all themes with pagination and filtering

**Query Parameters:**
```json
{
  "page": 1,
  "limit": 20,
  "status": "published|draft|review|archived",
  "category": "string",
  "search": "string",
  "sort_by": "name|downloads|revenue|created_at",
  "sort_order": "asc|desc"
}
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "theme_001",
      "name": "Modern Minimal",
      "slug": "modern-minimal",
      "description": "A clean and minimal theme...",
      "version": "1.2.3",
      "category": "Business",
      "tags": ["responsive", "minimal", "dark"],
      "status": "published",
      "creator": {
        "id": "user_001",
        "name": "Mohammed Ali",
        "email": "mohammed@tashkeel.dev"
      },
      "pricing": {
        "price": 49.99,
        "currency": "USD",
        "license_type": "MIT",
        "support_duration_months": 12
      },
      "media": {
        "thumbnail": "https://blob.vercel-storage.com/...",
        "screenshots": ["url1", "url2", "url3"],
        "demo_url": "https://demo.tashkeel.dev/modern-minimal"
      },
      "stats": {
        "downloads": 15234,
        "revenue": 45234.50,
        "rating": 4.8,
        "reviews": 234
      },
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2026-03-20T14:22:00Z"
    }
  ],
  "pagination": {
    "total": 234,
    "page": 1,
    "limit": 20,
    "pages": 12
  }
}
```

### GET /themes/{theme_id}
Get detailed information about a specific theme

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "theme_001",
    "name": "Modern Minimal",
    "slug": "modern-minimal",
    "description": "...",
    // ... (same structure as list item)
    "features": [
      "Mobile Responsive",
      "RTL Support",
      "Dark Mode",
      "WooCommerce Ready"
    ],
    "installation_instructions": "...",
    "changelog": [
      {
        "version": "1.2.3",
        "date": "2026-03-20",
        "changes": ["Fixed RTL bug", "Added dark mode"]
      }
    ],
    "support_contact": "support@tashkeel.dev"
  }
}
```

### POST /themes
Create a new theme

**Request Body:**
```json
{
  "name": "Modern Minimal",
  "description": "A clean and minimal theme",
  "category": "Business",
  "tags": ["responsive", "minimal"],
  "version": "1.0.0",
  "price": 49.99,
  "license_type": "MIT",
  "features": ["Mobile Responsive", "Dark Mode"],
  "demo_url": "https://demo.tashkeel.dev/modern-minimal"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "theme_002",
    "name": "Modern Minimal",
    "status": "draft",
    "created_at": "2026-03-25T10:30:00Z"
  }
}
```

### PUT /themes/{theme_id}
Update an existing theme

**Request Body:**
```json
{
  "name": "Modern Minimal v2",
  "version": "2.0.0",
  "price": 59.99,
  "features": ["Mobile Responsive", "Dark Mode", "AI Integration"]
}
```

### DELETE /themes/{theme_id}
Delete a theme (Admin only)

**Requirements:**
- Theme must not have active purchases
- User must have admin role

### POST /themes/{theme_id}/publish
Publish a theme

**Triggers:**
- `THEME_PUBLISHED` signal → analytics-agent, marketing-agent

### POST /themes/{theme_id}/submit-review
Submit theme for review

**Triggers:**
- `THEME_SUBMITTED_FOR_REVIEW` signal → content-agent

### POST /themes/{theme_id}/upload-media
Upload theme media (images)

**Request (FormData):**
```
file: File
type: "thumbnail" | "screenshot"
```

---

## 📊 Analytics Endpoints

### GET /analytics/overview
Get analytics dashboard overview

**Query Parameters:**
```json
{
  "date_from": "2026-03-01",
  "date_to": "2026-03-31",
  "granularity": "day|week|month"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period": {
      "from": "2026-03-01",
      "to": "2026-03-31"
    },
    "metrics": {
      "total_revenue": 45234.50,
      "revenue_growth_percent": 15.2,
      "total_downloads": 12450,
      "download_growth_percent": 23.4,
      "total_users": 5432,
      "new_users": 432,
      "active_themes": 24,
      "average_rating": 4.7
    },
    "daily_data": [
      {
        "date": "2026-03-01",
        "revenue": 1234.50,
        "downloads": 234,
        "new_users": 45
      }
    ]
  }
}
```

### GET /analytics/themes
Get per-theme analytics

**Query Parameters:**
```json
{
  "date_from": "2026-03-01",
  "date_to": "2026-03-31",
  "theme_id": "optional",
  "limit": 10
}
```

### GET /analytics/attribution
Get attribution data (where sales come from)

**Response:**
```json
{
  "success": true,
  "data": {
    "channels": {
      "direct": {
        "count": 50,
        "revenue": 2500,
        "percent": 25
      },
      "email": {
        "count": 100,
        "revenue": 5000,
        "percent": 50
      },
      "social": {
        "count": 50,
        "revenue": 2500,
        "percent": 25
      }
    }
  }
}
```

### GET /analytics/trends
Get trending themes

**Query Parameters:**
```json
{
  "period": "week|month|all",
  "metric": "downloads|revenue|new_users",
  "limit": 10
}
```

### POST /analytics/reports
Create a custom report

**Request Body:**
```json
{
  "name": "March Sales Report",
  "metrics": ["revenue", "downloads", "new_users"],
  "date_from": "2026-03-01",
  "date_to": "2026-03-31",
  "filters": {
    "category": "Business",
    "min_rating": 4.0
  },
  "export_format": "pdf|csv|json"
}
```

---

## 📢 Marketing Endpoints

### GET /campaigns
List all campaigns

**Query Parameters:**
```json
{
  "page": 1,
  "limit": 20,
  "status": "draft|scheduled|published|archived",
  "type": "email|social|paid|product_launch"
}
```

### POST /campaigns
Create a new campaign

**Request Body:**
```json
{
  "name": "Launch Modern Minimal V2",
  "type": "social",
  "theme_ids": ["theme_001"],
  "channels": ["facebook", "instagram", "tiktok"],
  "content": {
    "title": "Introducing Modern Minimal V2",
    "description": "Cleaner. Faster. More Beautiful.",
    "images": ["url1", "url2"],
    "hashtags": "#تشكيل #ثيمات #ورديبريس"
  },
  "scheduling": {
    "publish_date": "2026-03-25",
    "publish_time": "10:00 AM",
    "timezone": "UTC"
  },
  "status": "draft"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "campaign_001",
    "status": "draft",
    "created_at": "2026-03-25T10:30:00Z"
  }
}
```

### POST /campaigns/{campaign_id}/publish
Publish campaign

**Triggers (based on Law VI):**
- Autonomous channels (Facebook, Instagram, TikTok, WhatsApp) → Execute immediately
- Paid channels (Google Ads, Meta Paid) → Send to admin queue for approval

### GET /campaigns/{campaign_id}/performance
Get campaign performance metrics

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "campaign_001",
    "impressions": 50000,
    "clicks": 2500,
    "click_rate": 5.0,
    "conversions": 250,
    "conversion_rate": 10.0,
    "revenue": 12500,
    "roi": 125.0,
    "cost": 100.0
  }
}
```

---

## ✍️ Content Management Endpoints

### GET /articles
List articles

**Query Parameters:**
```json
{
  "page": 1,
  "limit": 20,
  "status": "published|draft|review|archived",
  "type": "blog|tutorial|case_study|knowledge_base",
  "language": "en|ar"
}
```

### POST /articles
Create new article

**Request Body:**
```json
{
  "title_en": "Getting Started with Modern Minimal",
  "title_ar": "البدء مع قالب Modern Minimal",
  "content_en": "...",
  "content_ar": "...",
  "type": "tutorial",
  "related_themes": ["theme_001"],
  "featured_image": "url",
  "status": "draft"
}
```

### POST /articles/{article_id}/submit-review
Submit article for review

**Triggers:**
- `ARTICLE_SUBMITTED_FOR_REVIEW` signal → content-agent

### POST /articles/{article_id}/publish
Publish article

**Triggers:**
- `ARTICLE_PUBLISHED` signal → marketing-agent (for promotion)

---

## 🎧 Support Endpoints

### GET /support/tickets
List support tickets

**Query Parameters:**
```json
{
  "page": 1,
  "limit": 20,
  "status": "new|in_progress|waiting|resolved|closed",
  "priority": "low|medium|high|urgent",
  "assigned_to": "user_id"
}
```

### POST /support/tickets
Create support ticket

**Request Body:**
```json
{
  "customer_email": "john@example.com",
  "subject": "Theme activation not working",
  "description": "Detailed description...",
  "category": "installation|bug|feature_request|billing",
  "priority": "high",
  "related_theme_id": "theme_001",
  "related_transaction_id": "txn_001"
}
```

### GET /support/tickets/{ticket_id}
Get ticket details with conversation

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "ticket_001",
    "subject": "Theme activation not working",
    "status": "in_progress",
    "priority": "high",
    "customer": {
      "name": "John Smith",
      "email": "john@example.com",
      "country": "US",
      "joined_at": "2025-01-15"
    },
    "assigned_to": {
      "id": "user_001",
      "name": "Ahmed Hassan"
    },
    "messages": [
      {
        "id": "msg_001",
        "sender": "customer",
        "content": "I can't activate the theme...",
        "created_at": "2026-03-25T10:30:00Z"
      },
      {
        "id": "msg_002",
        "sender": "agent",
        "content": "Let me help you troubleshoot...",
        "created_at": "2026-03-25T10:35:00Z"
      }
    ],
    "created_at": "2026-03-25T10:30:00Z",
    "updated_at": "2026-03-25T10:35:00Z"
  }
}
```

### POST /support/tickets/{ticket_id}/reply
Send response to ticket

**Request Body:**
```json
{
  "message": "Thank you for your patience...",
  "status": "in_progress|waiting|resolved|closed",
  "send_knowledge_article": "article_id (optional)"
}
```

### POST /support/tickets/{ticket_id}/escalate
Escalate ticket to admin

**Triggers:**
- `TICKET_ESCALATED` signal → admin queue

---

## 💳 Payments Endpoints

### GET /payments/transactions
List transactions

**Query Parameters:**
```json
{
  "page": 1,
  "limit": 20,
  "status": "success|pending|failed|refunded",
  "date_from": "2026-03-01",
  "date_to": "2026-03-31",
  "min_amount": 0,
  "max_amount": 10000
}
```

### GET /payments/transactions/{transaction_id}
Get transaction details

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "txn_001",
    "date": "2026-03-25T14:32:00Z",
    "status": "success",
    "amount": 49.99,
    "currency": "USD",
    "customer": {
      "name": "John Smith",
      "email": "john@example.com"
    },
    "item": {
      "theme_name": "Modern Minimal",
      "theme_id": "theme_001",
      "version": "1.2.3",
      "license_type": "MIT",
      "support_duration_months": 12
    },
    "payment_method": {
      "type": "credit_card",
      "last_four": "4242",
      "brand": "Visa"
    },
    "gateway": "Stripe",
    "invoice_url": "https://tashkeel.dev/invoices/INV-001",
    "refund_available_until": "2026-04-24"
  }
}
```

### POST /payments/transactions/{transaction_id}/refund
Process refund

**Request Body:**
```json
{
  "reason": "Customer request",
  "partial_amount": null  // null for full refund
}
```

**Triggers:**
- `TRANSACTION_REFUNDED` signal → analytics-agent, support-agent

### GET /payments/invoices/{invoice_id}
Get/download invoice

---

## 🔄 Real-Time Updates (WebSocket)

### Connection

```javascript
// Client-side
const socket = io('wss://tashkeel.dev/socket', {
  auth: {
    token: JWT_TOKEN
  }
});

// Subscribe to events
socket.on('analytics:updated', (data) => {
  // Update dashboard
});

socket.on('campaign:published', (data) => {
  // Notify user
});
```

### Emitted Events

```
analytics:metrics_updated
├─ revenue, downloads, users
├─ triggered every hour
└─ payload: {metrics, timestamp}

campaign:published
├─ triggered when campaign goes live
└─ payload: {campaign_id, channels}

ticket:new
├─ triggered on new support ticket
└─ payload: {ticket_id, priority}

theme:status_changed
├─ triggered when theme status changes
└─ payload: {theme_id, old_status, new_status}

article:review_needed
├─ triggered when article submitted for review
└─ payload: {article_id}
```

---

## 📊 Database Schema

### Table: themes

```sql
CREATE TABLE themes (
  id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  description TEXT,
  version VARCHAR(50),
  category VARCHAR(100),
  status ENUM('draft', 'review', 'published', 'archived'),
  creator_id UUID REFERENCES users(id),
  price DECIMAL(10, 2),
  license_type VARCHAR(50),
  downloads_count INT DEFAULT 0,
  revenue DECIMAL(15, 2) DEFAULT 0,
  rating DECIMAL(3, 2),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### Table: campaigns

```sql
CREATE TABLE campaigns (
  id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  type ENUM('email', 'social', 'paid', 'product_launch'),
  status ENUM('draft', 'scheduled', 'published', 'archived'),
  content JSONB,
  channels JSONB,  -- ['facebook', 'instagram', 'tiktok']
  publish_date TIMESTAMP,
  impressions INT DEFAULT 0,
  clicks INT DEFAULT 0,
  conversions INT DEFAULT 0,
  revenue DECIMAL(15, 2),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### Table: support_tickets

```sql
CREATE TABLE support_tickets (
  id UUID PRIMARY KEY,
  ticket_number VARCHAR(20) UNIQUE,
  customer_email VARCHAR(255),
  subject VARCHAR(500),
  description TEXT,
  status ENUM('new', 'in_progress', 'waiting', 'resolved', 'closed'),
  priority ENUM('low', 'medium', 'high', 'urgent'),
  assigned_to UUID REFERENCES users(id),
  theme_id UUID REFERENCES themes(id),
  transaction_id UUID REFERENCES transactions(id),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### Table: transactions

```sql
CREATE TABLE transactions (
  id UUID PRIMARY KEY,
  transaction_number VARCHAR(20) UNIQUE,
  customer_email VARCHAR(255),
  theme_id UUID REFERENCES themes(id),
  amount DECIMAL(10, 2),
  currency VARCHAR(3),
  status ENUM('success', 'pending', 'failed', 'refunded'),
  payment_method VARCHAR(100),
  gateway VARCHAR(50),  -- 'Stripe', 'PayPal'
  gateway_id VARCHAR(255),
  invoice_url VARCHAR(500),
  refunded_at TIMESTAMP,
  refund_reason VARCHAR(500),
  occurred_at TIMESTAMP,  -- Per Law I
  received_at TIMESTAMP,  -- Per Law I
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

---

## 🔐 Security & Permissions

### Role-Based Access Control (RBAC)

```
Admin
├─ Full access to all features
├─ Can create/delete users
├─ Can access all analytics
├─ Can approve campaigns
└─ Can refund transactions

Theme Creator
├─ Can create/edit own themes
├─ Can view own analytics
├─ Can't delete published themes
└─ Can't access payments

Marketer
├─ Can create campaigns
├─ Can view analytics
├─ Can't refund transactions
├─ Can't delete content
└─ Can't moderate support tickets

Content Editor
├─ Can create/edit articles
├─ Can submit for review
├─ Can't publish directly
├─ Can view analytics
└─ Can't access payments

Support Agent
├─ Can view/respond to tickets
├─ Can view knowledge base
├─ Can't create campaigns
├─ Can't access analytics
└─ Can't refund (unless escalated)

Analyst
├─ Read-only access to analytics
├─ Can create custom reports
├─ Can't modify anything
└─ Can't access payments
```

### Endpoint Protection

```
All endpoints require:
1. Valid JWT token
2. User role check
3. Rate limiting (100 req/min per user)
4. Audit logging

Sensitive endpoints require:
1. 2FA for refunds
2. Admin approval for campaign publishing (paid)
3. Email verification for account changes
```

---

## ⚡ Performance Requirements

| Metric | Target |
|--------|--------|
| Page Load Time | < 2s |
| API Response Time | < 500ms |
| Real-time Update Latency | < 5s |
| Database Query Time | < 100ms |
| Search Results | < 1s |
| File Upload | < 30s for 10MB |

---

## 🧪 Testing Strategy

### Unit Tests
- API endpoint handlers
- Utility functions
- Form validations

### Integration Tests
- API + Database
- Event Bus (Redis)
- Agent signals

### E2E Tests
- Complete user flows
- Campaign creation & publishing
- Payment processing
- Support ticket handling

### Performance Tests
- Load testing (1000 concurrent users)
- Database query optimization
- API response time benchmarks

---

## 📱 Responsive Breakpoints

```
Mobile:    < 768px   (single column, hamburger menu)
Tablet:    768-1024px (2-3 columns)
Desktop:   > 1024px   (full layout)
```

---

## 🌍 Localization (i18n)

**Supported Languages:**
- English (en-US)
- Arabic (ar-SA)

**Translated Elements:**
- All UI text
- Error messages
- Form labels
- Help text
- Email templates

**RTL Support:**
- Automatic for Arabic
- CSS variables for direction
- Flexbox + Grid adapts automatically

---

## 🚀 Deployment Checklist

- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] Redis cache configured
- [ ] Vercel Blob storage configured
- [ ] Email service (Resend) configured
- [ ] Payment gateway (Stripe) configured
- [ ] Analytics tracking enabled
- [ ] Security headers configured
- [ ] CORS configured
- [ ] Rate limiting enabled
- [ ] Monitoring & logging configured
- [ ] Backup strategy in place
