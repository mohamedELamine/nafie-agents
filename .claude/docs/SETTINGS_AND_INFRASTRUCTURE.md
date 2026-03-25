# Tashkeel Dashboard — Settings & Infrastructure Configuration

## 📋 نظرة عامة

هذا المستند يوثق جميع الإعدادات والتكوينات للمشروع — من بنية الفضاء العمل إلى المفاتيح الحساسة والتكامل مع الخدمات الخارجية.

**آخر تحديث:** 2026-03-25
**الإصدار:** 1.0.0

---

## 1️⃣ نموذج الفضاء العمل (Workspace Model)

### البنية الهرمية

```
Platform (Tashkeel)
├── Organization
│   ├── Workspace 1
│   │   ├── Team Members
│   │   ├── Themes
│   │   ├── Campaigns
│   │   ├── Articles
│   │   ├── Transactions
│   │   ├── Support Tickets
│   │   └── Settings
│   │
│   └── Workspace 2
│       └── (...)
│
└── Super Admin Dashboard
    └── (manages all organizations/workspaces)
```

### Database Schema: Workspaces

```sql
CREATE TABLE organizations (
  id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  logo_url VARCHAR(500),
  created_at TIMESTAMP,
  created_by UUID REFERENCES users(id),
  updated_at TIMESTAMP
);

CREATE TABLE workspaces (
  id UUID PRIMARY KEY,
  organization_id UUID REFERENCES organizations(id),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  status ENUM('active', 'suspended', 'deleted'),
  redis_prefix VARCHAR(50),
  db_shard INT,
  created_at TIMESTAMP,
  created_by UUID REFERENCES users(id),
  updated_at TIMESTAMP,
  UNIQUE(organization_id, slug)
);

CREATE TABLE workspace_members (
  id UUID PRIMARY KEY,
  workspace_id UUID REFERENCES workspaces(id),
  user_id UUID REFERENCES users(id),
  role VARCHAR(50),  -- admin, creator, marketer, editor, support, analyst
  permissions JSONB,
  invited_at TIMESTAMP,
  joined_at TIMESTAMP,
  invited_by UUID REFERENCES users(id),
  UNIQUE(workspace_id, user_id)
);
```

### العزل متعدد المستأجرين (Multi-tenancy)

```typescript
// lib/multi-tenancy.ts

export async function getWorkspaceContext(req: Request) {
  const workspaceId = extractWorkspaceIdFromAuth(req);

  return {
    workspaceId,
    userId: extractUserIdFromAuth(req),
    role: getUserRole(userId, workspaceId),
    redisPrefix: `ws_${workspaceId}:`,
    dbSchema: getWorkspaceDBSchema(workspaceId)
  };
}

// استخدام الـ context في كل request
export const middleware = async (req: Request) => {
  const ctx = await getWorkspaceContext(req);
  req.locals.workspace = ctx;
};
```

---

## 2️⃣ المصادقة والتفويض (Authentication & Authorization)

### الأدوار (Roles)

```typescript
enum UserRole {
  SUPER_ADMIN = 'super_admin',        // المنصة كاملة
  ADMIN = 'admin',                     // workspace كامل
  CREATOR = 'creator',                 // إنشاء/تعديل themes
  MARKETER = 'marketer',              // إنشاء campaigns
  EDITOR = 'editor',                  // محتوى + مقالات
  SUPPORT = 'support',                // إدارة تذاكر الدعم
  ANALYST = 'analyst',                // analytics read-only
  FINANCE = 'finance'                 // payments + refunds
}
```

### Permissions Matrix

```typescript
const rolePermissions: Record<UserRole, string[]> = {
  super_admin: ['*'],
  admin: [
    'workspace:manage',
    'users:invite',
    'users:delete',
    'roles:assign',
    'themes:publish',
    'campaigns:approve',
    'payments:refund',
    'settings:view',
    'settings:edit',
    'audit:view',
    'agents:manage'
  ],
  creator: [
    'themes:create',
    'themes:edit',
    'themes:view_own',
    'media:upload',
    'analytics:view_own',
    'support:contact'
  ],
  marketer: [
    'campaigns:create',
    'campaigns:schedule',
    'campaigns:view',
    'analytics:view',
    'templates:view',
    'media:upload'
  ],
  editor: [
    'articles:create',
    'articles:edit',
    'articles:submit_review',
    'media:upload',
    'kb:view',
    'kb:contribute'
  ],
  support: [
    'tickets:view',
    'tickets:respond',
    'tickets:assign',
    'kb:view',
    'customers:view',
    'refunds:request'
  ],
  analyst: [
    'analytics:view',
    'reports:generate',
    'reports:export',
    'alerts:view'
  ],
  finance: [
    'payments:view',
    'refunds:process',
    'invoices:view',
    'invoices:send',
    'reconciliation:view'
  ]
};
```

### JWT Payload

```json
{
  "sub": "user_123",
  "workspace_id": "ws_456",
  "organization_id": "org_789",
  "role": "admin",
  "permissions": ["workspace:manage", "users:invite"],
  "iat": 1711353600,
  "exp": 1711440000,
  "iss": "tashkeel-auth",
  "aud": "tashkeel-dashboard"
}
```

---

## 3️⃣ بيئات التشغيل (Environments)

### البيئات الثلاث

```yaml
DEVELOPMENT:
  database: postgresql://localhost:5432/tashkeel_dev
  redis: redis://localhost:6379/0
  blob_storage: local filesystem
  stripe_mode: test
  stripe_key: sk_test_...
  resend_api_key: re_test_...
  log_level: debug

STAGING:
  database: postgresql://neon-staging.vercel-storage.com/tashkeel_staging
  redis: redis://upstash-staging.redis.upstash.io
  blob_storage: Vercel Blob (staging bucket)
  stripe_mode: test
  stripe_key: sk_test_...
  resend_api_key: re_test_...
  log_level: info

PRODUCTION:
  database: postgresql://neon-production.vercel-storage.com/tashkeel
  redis: redis://upstash-prod.redis.upstash.io
  blob_storage: Vercel Blob (production bucket)
  stripe_mode: live
  stripe_key: sk_live_...
  resend_api_key: re_live_...
  log_level: warn
```

### بيانات Environment Configuration في DB

```sql
CREATE TABLE environment_configs (
  id UUID PRIMARY KEY,
  environment VARCHAR(50),  -- 'dev', 'staging', 'prod'
  key VARCHAR(100) NOT NULL,
  value TEXT NOT NULL,
  encrypted BOOLEAN DEFAULT false,
  updated_at TIMESTAMP,
  updated_by UUID REFERENCES users(id),
  UNIQUE(environment, key)
);
```

---

## 4️⃣ الخدمات الخارجية و API Keys (External Services)

### Configuration Table

```sql
CREATE TABLE external_services (
  id UUID PRIMARY KEY,
  service_name VARCHAR(100) NOT NULL,
  environment VARCHAR(50),  -- 'dev', 'staging', 'prod'
  api_key_encrypted VARCHAR(500),
  api_secret_encrypted VARCHAR(500),
  webhook_secret_encrypted VARCHAR(500),
  webhook_url VARCHAR(500),
  status ENUM('active', 'inactive', 'revoked'),
  last_used_at TIMESTAMP,
  created_at TIMESTAMP,
  created_by UUID REFERENCES users(id),
  updated_at TIMESTAMP,
  updated_by UUID REFERENCES users(id),
  UNIQUE(service_name, environment)
);

CREATE TABLE api_key_audit_log (
  id UUID PRIMARY KEY,
  service_id UUID REFERENCES external_services(id),
  action VARCHAR(50),  -- 'created', 'used', 'rotated', 'revoked'
  user_id UUID REFERENCES users(id),
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMP
);
```

### المفاتيح المطلوبة (v1)

| الخدمة | المفتاح | الوصف | مطلوب؟ |
|--------|--------|-------|--------|
| **Stripe** | `STRIPE_SECRET_KEY` | معالجة الدفع | ✅ |
| | `STRIPE_PUBLIC_KEY` | الـ frontend key | ✅ |
| | `WEBHOOK_SECRET_STRIPE` | التحقق من الـ webhooks | ✅ |
| **Resend** | `RESEND_API_KEY` | إرسال البريد | ✅ |
| | `WEBHOOK_SECRET_EMAIL` | Email webhooks | ✅ |
| **Redis** | `REDIS_URL` | Event bus + cache | ✅ |
| **Vercel Blob** | `BLOB_READ_WRITE_TOKEN` | تخزين الملفات | ✅ |
| **Replicate** | `REPLICATE_API_TOKEN` | AI image generation (اختياري) | ⚠️ |
| **OpenAI** | `OPENAI_API_KEY` | AI features (اختياري) | ⚠️ |
| **Anthropic** | `ANTHROPIC_API_KEY` | Claude API (اختياري) | ⚠️ |

### تخزين المفاتيح الآمن

```typescript
// lib/secrets.ts
import { AES, enc } from 'crypto-js';

const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY!;

export async function storeSecret(
  serviceName: string,
  environment: string,
  key: string,
  value: string,
  userId: string
) {
  const encrypted = AES.encrypt(value, ENCRYPTION_KEY).toString();

  await db.externalServices.create({
    service_name: serviceName,
    environment,
    key,
    api_key_encrypted: encrypted,
    created_by: userId,
    status: 'active'
  });

  // Log
  await auditLog.create({
    action: 'secret_stored',
    entity: 'external_service',
    entity_id: serviceName,
    user_id: userId
  });
}

export async function getSecret(
  serviceName: string,
  environment: string
): Promise<string> {
  const record = await db.externalServices.findUnique({
    where: {
      service_name_environment: {
        service_name: serviceName,
        environment
      }
    }
  });

  if (!record) throw new Error(`Secret not found: ${serviceName}`);

  const decrypted = AES.decrypt(
    record.api_key_encrypted,
    ENCRYPTION_KEY
  ).toString(enc.Utf8);

  return decrypted;
}

// Masking في UI
export function maskSecret(value: string): string {
  return `${value.slice(0, 4)}****${value.slice(-4)}`;
}
```

---

## 5️⃣ Redis و Event Bus

### Redis Configuration

```typescript
// config/redis.ts

export const redisConfig = {
  dev: {
    url: 'redis://localhost:6379/0',
    prefix: 'dev:',
    ttls: {
      analytics_cache: 300,        // 5 min
      dashboard_aggregate: 60,     // 1 min
      session_cache: 3600,         // 1 hour
      transient_job_meta: 86400,   // 24 hours
      feature_flags: 300           // 5 min
    }
  },
  staging: {
    url: process.env.REDIS_URL_STAGING!,
    prefix: 'staging:',
    ttls: { /* same as dev */ }
  },
  production: {
    url: process.env.REDIS_URL!,
    prefix: 'prod:',
    ttls: { /* same as dev */ }
  }
};

// مثال على الاستخدام
const redis = Redis.fromUrl(redisConfig[env].url);

// Set key with TTL
await redis.set(
  `${prefix}analytics:overview:ws_123`,
  JSON.stringify(data),
  'EX',
  redisConfig[env].ttls.analytics_cache
);

// Get key
const cached = await redis.get(`${prefix}analytics:overview:ws_123`);
```

### Event Bus Channels

```typescript
// config/event-bus.ts

export const eventChannels = {
  // Domain channels
  'events:themes': 'Theme events',
  'events:campaigns': 'Campaign events',
  'events:analytics': 'Analytics events',
  'events:support': 'Support ticket events',
  'events:payments': 'Payment events',
  'events:content': 'Content events',
  'events:visual': 'Visual asset events',
  'events:system': 'System events',

  // Agent command channels
  'agent:analytics:commands': 'Commands for analytics agent',
  'agent:marketing:commands': 'Commands for marketing agent',
  'agent:content:commands': 'Commands for content agent',
  'agent:support:commands': 'Commands for support agent',
  'agent:visual:commands': 'Commands for visual production agent',

  // Agent result channels
  'agent:analytics:results': 'Results from analytics agent',
  'agent:marketing:results': 'Results from marketing agent',
  'agent:content:results': 'Results from content agent',
  'agent:support:results': 'Results from support agent',
  'agent:visual:results': 'Results from visual production agent'
};
```

### Event Contracts

```typescript
// types/events.ts

// Theme Events
export interface ThemeCreatedEvent {
  type: 'theme.created';
  id: string;
  workspace_id: string;
  theme_id: string;
  name: string;
  created_by: string;
  timestamp: string;
}

export interface ThemePublishedEvent {
  type: 'theme.published';
  id: string;
  workspace_id: string;
  theme_id: string;
  name: string;
  version: string;
  timestamp: string;
}

export interface ThemeSubmittedForReviewEvent {
  type: 'theme.submitted_for_review';
  id: string;
  workspace_id: string;
  theme_id: string;
  submitted_by: string;
  timestamp: string;
}

// Campaign Events
export interface CampaignPublishedEvent {
  type: 'campaign.published';
  id: string;
  workspace_id: string;
  campaign_id: string;
  channels: string[];
  status: 'autonomous' | 'pending_approval';
  timestamp: string;
}

// Payment Events
export interface TransactionRefundedEvent {
  type: 'transaction.refunded';
  id: string;
  workspace_id: string;
  transaction_id: string;
  amount: number;
  reason: string;
  timestamp: string;
}

// Support Events
export interface TicketCreatedEvent {
  type: 'ticket.created';
  id: string;
  workspace_id: string;
  ticket_id: string;
  priority: string;
  timestamp: string;
}

// Visual Events
export interface AssetProcessRequestEvent {
  type: 'asset.process_request';
  id: string;
  workspace_id: string;
  asset_id: string;
  asset_url: string;
  process_type: 'optimize' | 'generate_og' | 'resize' | 'ai_generate';
  params: Record<string, any>;
  timestamp: string;
}

export interface AssetProcessDoneEvent {
  type: 'asset.process_done';
  id: string;
  workspace_id: string;
  asset_id: string;
  process_type: string;
  result_url: string;
  status: 'success' | 'failed';
  error?: string;
  timestamp: string;
}

// Publish event
export async function publishEvent(event: ThemePublishedEvent) {
  const redis = getRedis();
  await redis.publish(
    'events:themes',
    JSON.stringify(event)
  );
}

// Subscribe to events
export function subscribeToEvents(channel: string, callback: (event: any) => void) {
  const redis = getRedis();
  const subscriber = redis.duplicate();

  subscriber.subscribe(channel, (message) => {
    const event = JSON.parse(message);
    callback(event);
  });

  return subscriber;
}
```

---

## 6️⃣ Agent Registry و Settings

### Agent Registry

```sql
CREATE TABLE agent_registry (
  id UUID PRIMARY KEY,
  agent_name VARCHAR(100) UNIQUE NOT NULL,
  agent_type VARCHAR(50),  -- analytics, marketing, content, support, visual, platform
  status ENUM('active', 'inactive', 'maintenance'),
  endpoint_url VARCHAR(500),
  redis_channel VARCHAR(100),
  health_check_interval INT DEFAULT 60,
  timeout_seconds INT DEFAULT 30,
  max_retries INT DEFAULT 3,
  version VARCHAR(50),
  last_health_check TIMESTAMP,
  last_health_status ENUM('healthy', 'degraded', 'unhealthy'),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

-- مثال على البيانات
INSERT INTO agent_registry (agent_name, agent_type, redis_channel) VALUES
('analytics-agent', 'analytics', 'agent:analytics:commands'),
('marketing-agent', 'marketing', 'agent:marketing:commands'),
('content-agent', 'content', 'agent:content:commands'),
('support-agent', 'support', 'agent:support:commands'),
('visual-production-agent', 'visual', 'agent:visual:commands'),
('platform-agent', 'platform', 'agent:platform:commands');
```

### Analytics Agent Settings

```typescript
export const analyticsAgentConfig = {
  enabled: true,

  // Processing
  batch_size: 100,
  batch_interval_seconds: 30,

  // Caching
  cache_ttl: {
    overview_metrics: 300,      // 5 min
    trend_data: 900,            // 15 min
    report_data: 3600           // 1 hour
  },

  // Real-time
  websocket_enabled: true,
  update_interval_ms: 5000,

  // Metrics storage
  metrics_to_store: [
    'revenue',
    'downloads',
    'users',
    'ratings',
    'conversions'
  ],

  // Retention
  retention_days: 365,

  // Thresholds
  alert_thresholds: {
    revenue_drop_percent: 20,
    download_spike_percent: 50,
    chargeback_rate: 1.0
  }
};
```

### Marketing Agent Settings

```typescript
export const marketingAgentConfig = {
  enabled: true,

  // Campaign limits
  max_campaigns_per_day: 5,
  max_scheduled_campaigns: 20,

  // Autonomous channels (auto-publish)
  autonomous_channels: [
    'facebook_organic',
    'instagram_organic',
    'tiktok_organic',
    'whatsapp_approved'
  ],

  // Channels requiring approval
  approval_required_channels: [
    'google_ads',
    'meta_paid_ads',
    'email_with_discount'
  ],

  // Scheduling
  default_timezone: 'UTC',
  schedule_conflict_detection: true,

  // Performance
  auto_pause_on_low_conversion: false,
  conversion_threshold_percent: 5,

  // Content validation
  min_caption_length: 10,
  max_caption_length: 2200,
  hashtag_validation: true
};
```

### Content Agent Settings

```typescript
export const contentAgentConfig = {
  enabled: true,

  // Automatic review
  auto_review: true,
  auto_score: true,

  // Quality thresholds
  quality_score_bands: {
    publishable_min: 90,
    revise_min: 75,
    reject_max: 75
  },

  // Checks
  language_quality_check: true,
  plagiarism_check: true,
  seo_check: true,
  brand_voice_check: true,

  // Content requirements
  min_word_count: {
    blog: 600,
    tutorial: 800,
    case_study: 1000,
    kb_article: 300,
    social_post: 10
  },

  // Translation
  auto_translate: false,
  translation_engine: 'manual_with_review'
};
```

### Support Agent Settings

```typescript
export const supportAgentConfig = {
  enabled: true,

  // Assignment
  auto_assign_strategy: 'category_then_least_loaded',
  auto_assign_enabled: true,

  // SLA
  sla: {
    low: 172800,      // 48 hours
    medium: 86400,    // 24 hours
    high: 28800,      // 8 hours
    urgent: 3600      // 1 hour
  },

  // Auto-close
  auto_close_after_days: 7,
  auto_close_notify_before_hours: 24,

  // Escalation
  escalation_threshold: 15,  // max open tickets

  // AI suggestions
  ai_suggestions_enabled: true,
  ai_suggestion_threshold: 0.75
};
```

### Visual Production Agent Settings

```typescript
export const visualAgentConfig = {
  enabled: true,

  // Image processing
  image_processing: {
    engine: 'sharp',
    max_image_size_mb: 50,
    allowed_formats: ['jpg', 'png', 'webp', 'gif'],
    auto_optimize: true,
    auto_webp_convert: true
  },

  // Video processing
  video_processing: {
    enabled: true,
    engine: 'ffmpeg',
    max_video_size_mb: 500,
    allowed_formats: ['mp4', 'webm', 'mov'],
    timeout_seconds: 300
  },

  // OG image generation
  og_generation: {
    enabled: true,
    width: 1200,
    height: 630,
    default_template: 'modern'
  },

  // AI image generation (optional)
  ai_generation: {
    enabled: false,
    provider: 'replicate',  // or 'flux', 'lovealb', etc
    model: 'stable-diffusion-3',
    max_images_per_request: 3
  },

  // Job limits
  max_concurrent_jobs: 5,
  job_timeout_seconds: 120,

  // Storage
  storage: {
    optimized_suffix: '_optimized',
    og_suffix: '_og',
    thumb_suffix: '_thumb'
  }
};
```

---

## 7️⃣ Background Jobs & Queue

### Job Queue Configuration

```typescript
// config/jobs.ts

export const jobQueueConfig = {
  // Using Trigger.dev or similar
  provider: 'trigger.dev',
  base_url: process.env.TRIGGER_API_URL,
  api_key: process.env.TRIGGER_API_KEY,

  // Job timeouts (in seconds)
  timeouts: {
    email_send: 120,
    report_generate: 900,
    image_optimize: 300,
    video_convert: 600,
    ai_image_generate: 600,
    cache_warm: 300,
    webhook_retry: 60,
    campaign_publish: 60,
    refund_process: 120,
    invoice_generate: 60
  },

  // Retry policy
  retry_policy: {
    max_attempts: 3,
    initial_delay_ms: 1000,
    max_delay_ms: 60000,
    backoff_multiplier: 2
  },

  // Concurrency limits
  concurrency: {
    email_send: 10,
    report_generate: 3,
    image_optimize: 5,
    video_convert: 2,
    ai_image_generate: 2,
    webhook_retry: 5,
    refund_process: 2,
    campaign_publish: 3
  }
};
```

### Job Types & Definitions

```typescript
// types/jobs.ts

export interface JobBase {
  id: string;
  type: string;
  workspace_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  priority: 'low' | 'normal' | 'high';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  retry_count: number;
  metadata: Record<string, any>;
}

// Email job
export interface EmailSendJob extends JobBase {
  type: 'email_send';
  payload: {
    to: string;
    template: string;
    variables: Record<string, any>;
    from?: string;
  };
}

// Report generation
export interface ReportGenerateJob extends JobBase {
  type: 'report_generate';
  payload: {
    report_type: string;
    metrics: string[];
    date_from: string;
    date_to: string;
    format: 'pdf' | 'csv' | 'json';
  };
}

// Image optimization
export interface ImageOptimizeJob extends JobBase {
  type: 'image_optimize';
  payload: {
    image_url: string;
    target_width?: number;
    target_height?: number;
    quality?: number;
    format?: string;
  };
}

// OG image generation
export interface OGGenerateJob extends JobBase {
  type: 'og_generate';
  payload: {
    title: string;
    description?: string;
    image_url?: string;
    url: string;
    type: 'article' | 'product' | 'campaign';
  };
}

// Video conversion
export interface VideoConvertJob extends JobBase {
  type: 'video_convert';
  payload: {
    video_url: string;
    output_format: string;
    resolution?: '720p' | '1080p' | '4k';
  };
}

// AI image generation
export interface AIImageGenerateJob extends JobBase {
  type: 'ai_image_generate';
  payload: {
    prompt: string;
    style?: string;
    count: number;
    size?: string;
  };
}

// Publish campaign
export interface CampaignPublishJob extends JobBase {
  type: 'campaign_publish';
  payload: {
    campaign_id: string;
    channels: string[];
  };
}

// Process refund
export interface RefundProcessJob extends JobBase {
  type: 'refund_process';
  payload: {
    transaction_id: string;
    amount: number;
    reason: string;
  };
}

// Generate invoice
export interface InvoiceGenerateJob extends JobBase {
  type: 'invoice_generate';
  payload: {
    transaction_id: string;
    format: 'pdf' | 'html';
  };
}

// Webhook retry
export interface WebhookRetryJob extends JobBase {
  type: 'webhook_retry';
  payload: {
    webhook_id: string;
    event: string;
    payload: Record<string, any>;
  };
}

// Scheduled jobs (cron)
export interface ScheduledJob extends JobBase {
  type: 'scheduled_job';
  payload: {
    job_key: string;
    schedule: string;  // cron expression
    next_run?: string;
  };
}
```

### Job Execution

```typescript
// lib/jobs.ts
import { invokeTrigger } from '@trigger.dev/sdk/v3';

export async function enqueueJob<T extends JobBase>(job: T) {
  const jobKey = `${job.workspace_id}:${job.type}:${job.id}`;

  return await invokeTrigger(jobKey, {
    payload: job.payload,
    options: {
      timeout: jobQueueConfig.timeouts[job.type as keyof typeof jobQueueConfig.timeouts],
      priority: job.priority,
      metadata: {
        workspace_id: job.workspace_id,
        job_id: job.id
      }
    }
  });
}

export async function trackJobStatus(jobId: string) {
  // Retrieve job status from queue
  // Update DB with status
  // Emit status event via WebSocket
}

export async function cancelJob(jobId: string) {
  // Cancel if not started
  // Cleanup if started
}
```

---

## 8️⃣ Feature Flags

### Feature Flags Table

```sql
CREATE TABLE feature_flags (
  id UUID PRIMARY KEY,
  flag_key VARCHAR(100) UNIQUE NOT NULL,
  description TEXT,
  enabled BOOLEAN DEFAULT false,

  -- Targeting
  target_workspaces JSONB,     -- ['ws_123', 'ws_456'] or null for all
  target_roles JSONB,          -- ['admin', 'creator'] or null for all
  target_percentage INT,       -- 0-100, null for all/none
  target_environments JSONB,   -- ['staging', 'production']

  -- Rollout
  rollout_enabled BOOLEAN DEFAULT false,
  rollout_percentage INT DEFAULT 100,
  rollout_schedule JSONB,      -- gradual rollout config

  created_at TIMESTAMP,
  created_by UUID REFERENCES users(id),
  updated_at TIMESTAMP,
  updated_by UUID REFERENCES users(id)
);

INSERT INTO feature_flags (flag_key, description, enabled) VALUES
('marketing_autonomous_publish', 'Allow autonomous campaign publishing', true),
('analytics_v2_dashboard', 'New analytics dashboard', false),
('ai_content_review', 'AI-powered content review', false),
('support_auto_assign', 'Automatic ticket assignment', true),
('content_translation_assist', 'AI translation assistance', false),
('payments_refund_enabled', 'Allow refund processing', true),
('reports_export_pdf', 'PDF export for reports', true),
('websocket_realtime', 'WebSocket real-time updates', true),
('visual_ai_generation', 'AI image generation', false);
```

### Feature Flag Evaluation

```typescript
// lib/feature-flags.ts

export async function isFeatureEnabled(
  flagKey: string,
  context: {
    workspace_id: string;
    user_id: string;
    user_role: string;
    environment: string;
  }
): Promise<boolean> {
  // Try cache first
  const cached = await redis.get(`flags:${flagKey}:${context.workspace_id}`);
  if (cached !== null) return cached === 'true';

  // Get flag from DB
  const flag = await db.featureFlags.findUnique({
    where: { flag_key: flagKey }
  });

  if (!flag || !flag.enabled) return false;

  // Check target environment
  if (flag.target_environments &&
      !flag.target_environments.includes(context.environment)) {
    return false;
  }

  // Check target roles
  if (flag.target_roles &&
      !flag.target_roles.includes(context.user_role)) {
    return false;
  }

  // Check target workspaces
  if (flag.target_workspaces &&
      !flag.target_workspaces.includes(context.workspace_id)) {
    return false;
  }

  // Check rollout percentage
  if (flag.rollout_percentage < 100) {
    const hash = hashUserId(context.user_id, flagKey);
    const percentage = Math.abs(hash % 100);
    if (percentage >= flag.rollout_percentage) {
      return false;
    }
  }

  // Cache result
  await redis.setex(`flags:${flagKey}:${context.workspace_id}`, 300, 'true');

  return true;
}
```

---

## 9️⃣ Audit Logging

### Audit Log Schema

```sql
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY,
  workspace_id UUID REFERENCES workspaces(id),
  user_id UUID REFERENCES users(id),
  action VARCHAR(100),      -- 'create', 'update', 'delete', etc
  entity_type VARCHAR(50),  -- 'theme', 'campaign', 'user', etc
  entity_id VARCHAR(255),

  -- Changes
  old_values JSONB,
  new_values JSONB,
  changes_summary TEXT,

  -- Request context
  ip_address INET,
  user_agent TEXT,

  -- Sensitivity
  sensitivity_level ENUM('normal', 'sensitive', 'critical'),

  created_at TIMESTAMP,
  INDEX idx_workspace_created (workspace_id, created_at),
  INDEX idx_user_created (user_id, created_at)
);

CREATE TABLE audit_log_retention (
  entity_type VARCHAR(50) PRIMARY KEY,
  retention_days INT,  -- 30 for operational, 365 for critical
  created_at TIMESTAMP
);
```

### Audit Log Functions

```typescript
// lib/audit.ts

export async function logAction(
  action: AuditAction,
  context: {
    workspace_id: string;
    user_id: string;
    ip_address: string;
    user_agent: string;
  }
) {
  await db.auditLogs.create({
    workspace_id: context.workspace_id,
    user_id: context.user_id,
    action: action.type,
    entity_type: action.entity,
    entity_id: action.entity_id,
    old_values: action.old_values,
    new_values: action.new_values,
    changes_summary: generateSummary(action),
    ip_address: context.ip_address,
    user_agent: context.user_agent,
    sensitivity_level: determineSensitivity(action)
  });

  // If critical, also publish event
  if (action.critical) {
    await publishEvent({
      type: 'audit.critical_action',
      workspace_id: context.workspace_id,
      action,
      timestamp: new Date().toISOString()
    });
  }
}
```

---

## 🔟 Monitoring & Health Checks

### System Health Table

```sql
CREATE TABLE system_health_checks (
  id UUID PRIMARY KEY,
  service_name VARCHAR(100),
  environment VARCHAR(50),
  status ENUM('healthy', 'degraded', 'unhealthy'),
  latency_ms INT,
  error_rate_percent DECIMAL(5, 2),
  error_message TEXT,
  last_check TIMESTAMP,
  INDEX idx_service_env_time (service_name, environment, last_check)
);

-- Services to monitor
-- - database
-- - redis
-- - blob_storage
-- - stripe
-- - resend
-- - agents (each)
-- - api_gateway
-- - queue_system
-- - websocket
```

### Health Check Implementation

```typescript
// lib/health.ts

export async function checkSystemHealth() {
  const checks = {
    database: checkDatabase(),
    redis: checkRedis(),
    blob: checkBlobStorage(),
    stripe: checkStripe(),
    resend: checkResend(),
    agents: checkAgents(),
    queue: checkQueue()
  };

  const results = await Promise.allSettled(Object.values(checks));

  const health = {
    overall: results.every(r => r.status === 'fulfilled' && r.value.healthy),
    checks: results.map((r, i) => ({
      service: Object.keys(checks)[i],
      ...r.value
    }))
  };

  // Store in DB
  for (const check of health.checks) {
    await db.systemHealthChecks.create({
      service_name: check.service,
      environment: process.env.NODE_ENV,
      status: check.healthy ? 'healthy' : 'unhealthy',
      latency_ms: check.latency,
      error_rate_percent: check.error_rate,
      error_message: check.error
    });
  }

  // Alert if critical
  if (!health.overall) {
    await alertSlack('System health degraded', health);
  }

  return health;
}
```

---

## 1️⃣1️⃣ Rate Limiting & Security

### Rate Limit Configuration

```typescript
// config/rate-limits.ts

export const rateLimitConfig = {
  // Per user
  user: {
    requests_per_minute: 120,
    requests_per_hour: 10000
  },

  // Per IP
  ip: {
    requests_per_minute: 300,
    requests_per_hour: 50000
  },

  // Per endpoint
  endpoints: {
    'POST /api/v1/auth/login': {
      requests_per_minute: 5,
      requests_per_hour: 50
    },
    'POST /api/v1/payments/refund': {
      requests_per_minute: 2,
      requests_per_hour: 20
    },
    'POST /api/v1/media/upload': {
      requests_per_minute: 10,
      requests_per_hour: 100
    },
    'GET /api/v1/reports/export': {
      requests_per_minute: 5,
      requests_per_hour: 50
    },
    'POST /api/v1/campaigns/publish': {
      requests_per_minute: 1,
      requests_per_hour: 10
    }
  },

  // Per role
  roles: {
    admin: { multiplier: 2.0 },      // 2x limits
    creator: { multiplier: 1.0 },
    analyst: { multiplier: 0.5 }     // 0.5x limits
  }
};
```

### Rate Limit Middleware

```typescript
// middleware/rate-limit.ts
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

const ratelimit = new Ratelimit({
  redis: Redis.fromEnv(),
  limiter: Ratelimit.slidingWindow(100, '1 m')
});

export async function rateLimitMiddleware(req: Request, res: Response) {
  const identifier = req.user?.id || req.ip;

  const { success, pending } = await ratelimit.limit(identifier);

  res.header('X-RateLimit-Limit', '100');
  res.header('X-RateLimit-Remaining', remaining.toString());

  if (!success) {
    return res.status(429).json({
      error: 'Too many requests',
      retry_after: '60 seconds'
    });
  }
}
```

---

## 1️⃣2️⃣ CORS & Security Headers

```typescript
// config/security.ts

export const securityConfig = {
  cors: {
    allowed_origins: [
      'https://tashkeel.dev',
      'https://staging.tashkeel.dev',
      'http://localhost:3000'  // dev only
    ],
    allowed_methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    allowed_headers: ['Content-Type', 'Authorization'],
    credentials: true,
    max_age: 86400
  },

  headers: {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'"
  }
};
```

---

## Summary Table

| المكون | البيئات | الحالة |
|-------|--------|-------|
| Multi-workspace | ✅ All | Configured |
| RBAC | ✅ All | 8 roles defined |
| Environments | dev, staging, prod | ✅ Separated |
| External Services | 9 services | ✅ Encrypted storage |
| Redis | Per-environment | ✅ Configured |
| Event Bus | 5 domain channels | ✅ Defined |
| Agent Registry | 6 agents | ✅ Registered |
| Job Queue | 10 job types | ✅ Configured |
| Feature Flags | 9 flags | ✅ Ready |
| Audit Logging | All actions | ✅ Enabled |
| Health Monitoring | 7 services | ✅ Checks defined |
| Rate Limiting | User/IP/Endpoint | ✅ Configured |

---

## الخطوة التالية

هذا الملف يحتوي على **إعدادات شاملة** لبناء Tashkeel. في المرحلة التالية يمكنك:

1. **البدء في التنفيذ** — Phase 1 من roadmap
2. **إضافة configurations إضافية** — backups, migrations, CDN
3. **كتابة tests** — integration + end-to-end
4. **توثيق العمليات** — playbooks للفريق

اختر الخطوة التالية! 🚀
