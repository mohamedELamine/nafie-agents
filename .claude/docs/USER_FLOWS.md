# Tashkeel Dashboard — User Flows Documentation

## 📋 نظرة عامة

هذا المستند يوثق جميع مسارات المستخدمين (User Flows) في لوحة تحكم Tashkeel.

**الممثلون الرئيسيون:**
- 👨‍💼 **Admin** — مدير النظام الكامل
- 👨‍🎨 **Theme Creator** — منشئ الثيمات
- 📊 **Analyst** — محلل البيانات والإحصائيات
- 📢 **Marketer** — مسؤول التسويق
- ✍️ **Content Editor** — محرر المحتوى
- 🎧 **Support Agent** — وكيل الدعم

---

## 1️⃣ Overview / الرئيسية

### السيناريو الأساسي: Admin يفتح Dashboard

```mermaid
graph TD
    A["Admin يدخل Dashboard"] --> B["تحميل البيانات"]
    B --> C["جلب Statistics من analytics-agent"]
    C --> D["عرض Activity Feed"]
    D --> E["عرض System Health"]
    E --> F["عرض Quick Actions"]
    F --> G{"اختيار إجراء"}
    G -->|View Analytics| H["انتقل إلى Analytics Section"]
    G -->|Manage Themes| I["انتقل إلى Themes Section"]
    G -->|View Campaigns| J["انتقل إلى Marketing Section"]
    G -->|Check Support| K["انتقل إلى Support Section"]
```

### العناصر المعروضة:

| العنصر | الوصف | المصدر |
|--------|-------|--------|
| **Key Metrics** | مبيعات اليوم، تنزيلات، عدد الثيمات النشطة | analytics-agent |
| **Top Themes** | أكثر 5 ثيمات تحميلاً هذا الأسبوع | analytics-agent |
| **Recent Sales** | آخر 10 عمليات شراء | payments API |
| **Activity Log** | آخر الإجراءات من جميع الوكلاء | event bus (Redis) |
| **System Status** | حالة الوكلاء والأنظمة | health check |
| **Pending Tasks** | ثيمات قيد المراجعة، تذاكر دعم جديدة | content-agent, support-agent |

### التفاعلات:
- ✅ Real-time updates (WebSocket من analytics-agent)
- ✅ Notifications (عند بيع جديدة، دعم عاجل)
- ✅ Quick filters (Today, This Week, This Month)

---

## 2️⃣ Themes Management

### السيناريو 1: إنشاء ثيمة جديدة (Theme Creator)

```mermaid
graph TD
    A["Creator: اضغط 'New Theme'"] --> B["فتح Create Theme Modal"]
    B --> C["ملء البيانات الأساسية"]
    C --> D["إضافة صور ولقطات شاشة"]
    D --> E["اختيار الفئات والعلامات"]
    E --> F["تحديد السعر والترخيص"]
    F --> G["عرض معاينة"]
    G --> H{"موافق؟"}
    H -->|No| C
    H -->|Yes| I["حفظ في DB"]
    I --> J["إرسال إشارة للمراجعة"]
    J --> K["content-agent: مراجعة"]
    K --> L{"موافق؟"}
    L -->|Rejected| M["إرسال ملاحظات للمنشئ"]
    L -->|Approved| N["Publish Theme"]
    N --> O["analytics-agent: تسجيل إضافة جديدة"]
    O --> P["marketing-agent: إعداد promotional post"]
    P --> Q["✅ Theme Live"]
```

### السيناريو 2: تعديل ثيمة موجودة

```mermaid
graph TD
    A["Creator: اختر ثيمة موجودة"] --> B["اضغط 'Edit'"]
    B --> C["تحميل بيانات الثيمة"]
    C --> D["تعديل المعلومات"]
    D --> E{"تغيير في المعلومات المحدودة فقط؟"}
    E -->|Yes| F["Save مباشرة"]
    E -->|No| G["إرسال للمراجعة مجدداً"]
    G --> H["content-agent: review changes"]
    H --> I["Update Theme"]
    I --> J["✅ Theme Updated"]
```

### السيناريو 3: حذف ثيمة (Admin فقط)

```mermaid
graph TD
    A["Admin: اختر ثيمة"] --> B["اضغط 'Delete'"]
    B --> C["تأكيد الحذف"]
    C --> D{"هل هناك عمليات شراء نشطة؟"}
    D -->|Yes| E["تحذير: لا يمكن حذف"]
    D -->|No| F["حذف من DB"]
    F --> G["حذف من Vercel Blob (صور)"]
    G --> H["analytics-agent: log deletion"]
    H --> I["✅ Theme Deleted"]
```

### معلومات الثيمة:

```
┌─ Basic Info
│  ├─ Name (عربي + English)
│  ├─ Description
│  ├─ Version
│  └─ Slug (URL-friendly)
│
├─ Visual
│  ├─ Thumbnail (رئيسي)
│  ├─ Screenshots (3-5)
│  ├─ Demo URL
│  └─ Preview Colors
│
├─ Categorization
│  ├─ Category (Business, Blog, E-commerce, etc.)
│  ├─ Tags (responsive, minimal, dark, RTL, etc.)
│  └─ Features (search, comments, social, etc.)
│
├─ Pricing & License
│  ├─ Price (USD)
│  ├─ License Type (GPL, MIT, Proprietary)
│  ├─ Support Duration
│  └─ Update Frequency
│
└─ Meta
   ├─ Creator
   ├─ Created Date
   ├─ Last Updated
   ├─ Status (draft, review, published, archived)
   └─ Download Count
```

---

## 3️⃣ Analytics & Insights

### السيناريو 1: Analyst يفتح Analytics Dashboard

```mermaid
graph TD
    A["Analyst: اضغط 'Analytics'"] --> B["تحميل Analytics Section"]
    B --> C["جلب بيانات من analytics-agent"]
    C --> D["عرض الرسوم البيانية"]
    D --> E["Select Date Range"]
    E --> F["تحديث الرسوم البيانية"]
    F --> G["عرض التحليلات"]
    G --> H{"ما الذي يهمك؟"}
    H -->|Sales| I["Sales Chart"]
    H -->|Downloads| J["Download Chart"]
    H -->|Trends| K["Trending Themes"]
    H -->|Attribution| L["Attribution by Channel"]
    H -->|User Behavior| M["User Cohorts"]
```

### الرسوم البيانية الرئيسية:

| الرسم البياني | البيانات | التحديث |
|-------------|---------|--------|
| **Sales Overview** | إجمالي الإيرادات، المتوسط، النمو | يومي |
| **Downloads Trend** | تنزيلات الثيمات عبر الوقت | يومي |
| **Top Themes** | أكثر الثيمات مبيعاً وتنزيلاً | يومي |
| **Revenue by Theme** | الإيرادات مقسمة حسب الثيمة | يومي |
| **Attribution** | من أين أتى العميل (direct, email, social) | يومي |
| **Funnel** | Landing → Browse → Purchase | يومي |
| **Customer Cohorts** | متى انضم العميل وسلوكه | أسبوعي |
| **Device/Browser** | آي الأجهزة والمتصفحات الشهيرة | يومي |

### السيناريو 2: إنشاء Report مخصص

```mermaid
graph TD
    A["Analyst: اضغط 'Create Report'"] --> B["Select Metrics"]
    B --> C["Select Date Range"]
    C --> D["Select Filters (Theme, Region, etc)"]
    D --> E["Preview Report"]
    E --> F{"موافق؟"}
    F -->|No| B
    F -->|Yes| G["Generate Report"]
    G --> H["Export as PDF/CSV"]
    H --> I["Share with Team"]
    I --> J["✅ Report Created"]
```

### السيناريو 3: Setting Up Alerts

```mermaid
graph TD
    A["Analyst: اضغط 'Alerts'"] --> B["Create New Alert"]
    B --> C["Select Metric (Sales, Downloads, etc)"]
    C --> D["Set Threshold"]
    D --> E["Set Condition (> or <)"]
    E --> F["Set Notification Channel (Email, Slack)"]
    F --> G["Save Alert"]
    G --> H["✅ Alert Active"]
    H --> I["When threshold crossed → Send Notification"]
```

---

## 4️⃣ Marketing & Campaigns

### السيناريو 1: Marketer ينشئ Campaign

```mermaid
graph TD
    A["Marketer: اضغط 'New Campaign'"] --> B["اختر نوع Campaign"]
    B --> C["Select Theme(s) to Promote"]
    C --> D["Write Campaign Content"]
    D --> E["اختر Channels"]
    E --> F["Schedule Publish Date"]
    F --> G["Preview Campaign"]
    G --> H{"موافق؟"}
    H -->|No| D
    H -->|Yes| I["Save Campaign"]
    I --> J{"Autonomous أم Manual؟"}
    J -->|Autonomous| K["Publish Immediately"]
    J -->|Manual| L["Await Approval"]
    K --> M["marketing-agent: publish"]
    L --> N["Admin: Review & Approve"]
    N --> O["marketing-agent: publish"]
    M --> P["✅ Campaign Live"]
    O --> P
```

### أنواع Campaigns:

```
1. EMAIL CAMPAIGN
   ├─ Subject
   ├─ Recipients (segmented by behavior)
   ├─ Email Template
   ├─ A/B Testing (Subject, Content)
   └─ Send Time

2. SOCIAL MEDIA CAMPAIGN
   ├─ Platform (Facebook, Instagram, TikTok)
   ├─ Caption (RTL Support)
   ├─ Images/Videos
   ├─ Hashtags
   ├─ Scheduling
   └─ Paid vs Organic

3. PRODUCT LAUNCH
   ├─ New Theme Announcement
   ├─ Features Highlight
   ├─ Promo Code Generation
   ├─ Landing Page Link
   └─ Launch Timeline

4. SEASONAL/SPECIAL
   ├─ Holiday Campaigns
   ├─ Flash Sales
   ├─ Bundle Deals
   └─ Limited Time Offers
```

### السيناريو 2: مراجعة Campaign Performance

```mermaid
graph TD
    A["Marketer: اختر Campaign"] --> B["عرض Results"]
    B --> C["اختر Metric"]
    C --> D{"أي متريك؟"}
    D -->|Impressions| E["عدد مرات الظهور"]
    D -->|Clicks| F["عدد النقرات"]
    D -->|Conversions| G["عدد المشتريات"]
    D -->|ROI| H["العائد على الاستثمار"]
    E --> I["عرض الرسم البياني"]
    F --> I
    G --> I
    H --> I
    I --> J["Compare with Other Campaigns"]
    J --> K["Export Report"]
```

### القنوات المسموحة:

```
🟢 AUTONOMOUS (Self-Execute)
├─ Facebook Organic Posts
├─ Instagram Organic Posts
├─ TikTok Organic Videos
└─ WhatsApp Messages

🟡 REQUIRES APPROVAL (Proposal → Admin Review)
├─ Google Ads
├─ Meta Paid Ads
├─ Email with Discounts
└─ Influencer Partnerships

❌ NOT ALLOWED
└─ Spam/Phishing/Misleading Content
```

---

## 5️⃣ Content Management

### السيناريو 1: Content Editor ينشئ مقالة

```mermaid
graph TD
    A["Editor: اضغط 'New Article'"] --> B["اختر النوع"]
    B --> C["اكتب العنوان (AR + EN)"]
    C --> D["اكتب المحتوى"]
    D --> E["إضافة صور"]
    E --> F["تحديد الثيمات المرتبطة"]
    F --> G["تحسين SEO"]
    G --> H["عرض معاينة"]
    H --> I{"موافق؟"}
    I -->|No| D
    I -->|Yes| J["Save Draft"]
    J --> K["Request Review"]
    K --> L["content-agent: review"]
    L --> M{"موافق؟"}
    M -->|Rejected| N["أرسل ملاحظات"]
    M -->|Approved| O["Publish Article"]
    O --> P["marketing-agent: promote"]
    P --> Q["✅ Article Live"]
```

### أنواع المحتوى:

```
1. BLOG POSTS
   ├─ Tutorial (how-to guides)
   ├─ Case Study (success stories)
   ├─ News (updates, releases)
   └─ Opinion (industry insights)

2. THEME DESCRIPTIONS
   ├─ Feature Highlights
   ├─ Installation Guide
   ├─ Customization Tips
   └─ FAQ

3. KNOWLEDGE BASE
   ├─ Getting Started
   ├─ Troubleshooting
   ├─ Best Practices
   └─ API Documentation

4. MARKETING COPY
   ├─ Landing Page Copy
   ├─ Email Content
   ├─ Social Media Posts
   └─ Ad Copy
```

### السيناريو 2: Review Workflow

```mermaid
graph TD
    A["Editor: Submit for Review"] --> B["content-agent receives signal"]
    B --> C["Check Criteria"]
    C --> D{"Language Quality?"}
    D -->|Fail| E["Return with errors"]
    D -->|Pass| F{"SEO Optimized?"}
    F -->|Fail| E
    F -->|Pass| G{"Brand Voice Match?"}
    G -->|Fail| E
    G -->|Pass| H["✅ Approved"]
    E --> I["Editor fixes"]
    I --> A
    H --> J["Publish"]
    J --> K["✅ Live"]
```

---

## 6️⃣ Support & Tickets

### السيناريو 1: Support Agent يفتح Tickets

```mermaid
graph TD
    A["Agent: اضغط 'Support'"] --> B["تحميل Queue"]
    B --> C["عرض Tickets"]
    C --> D["تصفية بحسب Status"]
    D --> E{"أي Ticket؟"}
    E -->|New| F["اختر Ticket جديد"]
    E -->|In Progress| G["اختر Ticket قيد المعالجة"]
    E -->|Urgent| H["اختر Ticket عاجل"]
    F --> I["اقرأ التفاصيل"]
    G --> I
    H --> I
    I --> J["Respond to Customer"]
    J --> K{"مستحل؟"}
    K -->|Yes| L["Close Ticket"]
    K -->|No| M["Keep Open"]
    M --> N["Escalate if needed"]
    N --> O["support-agent: log"]
```

### الحقول الرئيسية للـ Ticket:

| الحقل | الوصف |
|-------|-------|
| **ID** | معرف فريد |
| **Customer** | بيانات المشتري |
| **Subject** | موضوع المشكلة |
| **Description** | وصف مفصل |
| **Category** | (Installation, Bug, Feature Request, Billing) |
| **Priority** | (Low, Medium, High, Urgent) |
| **Status** | (New, In Progress, Waiting for Customer, Resolved, Closed) |
| **Assigned To** | وكيل الدعم المسؤول |
| **Created At** | تاريخ الإنشاء |
| **Updated At** | آخر تحديث |
| **Resolution** | شرح الحل |

### السيناريو 2: استخدام Knowledge Base

```mermaid
graph TD
    A["Agent: اضغط 'Knowledge Base'"] --> B["ابحث عن المشكلة"]
    B --> C["عرض النتائج"]
    C --> D["اختر المقالة المناسبة"]
    D --> E{"هل تحل المشكلة؟"}
    E -->|Yes| F["أرسل المقالة للعميل"]
    E -->|No| G["اكتب رد مخصص"]
    F --> H["Mark as Resolved"]
    G --> H
    H --> I["✅ Ticket Closed"]
```

### السيناريو 3: Escalation Process

```mermaid
graph TD
    A["Agent: لا يستطيع الحل"] --> B["اضغط 'Escalate'"]
    B --> C["اختر السبب"]
    C --> D["add notes for admin"]
    D --> E["Send to Admin Queue"]
    E --> F["Admin: reviews"]
    F --> G{"يمكن حل؟"}
    G -->|Yes| H["solve and respond"]
    G -->|No| I["refund or special handling"]
    H --> J["Notify customer"]
    I --> J
```

---

## 7️⃣ Payments & Transactions

### السيناريو 1: Viewing Transactions

```mermaid
graph TD
    A["Admin: اضغط 'Payments'"] --> B["تحميل Transactions"]
    B --> C["عرض قائمة Transactions"]
    C --> D["تصفية بحسب"]
    D --> E{"أي فلتر؟"}
    E -->|Date| F["Select Range"]
    E -->|Status| G["Success/Pending/Failed"]
    E -->|Amount| H["Select Range"]
    E -->|Customer| I["Search by Email"]
    F --> J["عرض النتائج"]
    G --> J
    H --> J
    I --> J
    J --> K["Click Transaction"]
    K --> L["View Details"]
```

### بيانات Transaction:

```
┌─ Transaction ID
├─ Date & Time
├─ Customer
│  ├─ Name
│  ├─ Email
│  └─ Country
│
├─ Item
│  ├─ Theme Name
│  ├─ License Type
│  └─ Support Duration
│
├─ Payment
│  ├─ Amount (USD)
│  ├─ Currency
│  ├─ Method (Credit Card, PayPal, etc)
│  └─ Status (Success, Pending, Failed, Refunded)
│
└─ Metadata
   ├─ Invoice URL
   ├─ Receipt Sent: Yes/No
   └─ Support Ticket: Link
```

### السيناريو 2: Handling Refund Request

```mermaid
graph TD
    A["Customer: Requests Refund"] --> B["Ticket Created"]
    B --> C["Admin: Review Request"]
    C --> D{"Check Refund Policy"}
    D -->|Within 30 days| E{"Legitimate reason?"}
    D -->|After 30 days| F["Deny Refund"]
    E -->|Yes| G["Process Refund"]
    E -->|No| F
    G --> H["Update Transaction Status"]
    H --> I["Send Email to Customer"]
    I --> J["✅ Refund Processed"]
    F --> K["Send Explanation to Customer"]
```

### السيناريو 3: Invoice Generation

```mermaid
graph TD
    A["Transaction Completed"] --> B["Generate Invoice"]
    B --> C["Store in Vercel Blob"]
    C --> D["Send Email to Customer"]
    D --> E["Log in system"]
    E --> F{"Customer requests duplicate?"]
    F -->|Yes| G["Retrieve from Blob"]
    F -->|No| H["✅ Complete"]
    G --> I["Send Email"]
    I --> H
```

---

## 🔄 Agent Interactions

### Communication Flows:

```
┌─────────────────────────────────────────────────┐
│              REDIS EVENT BUS                    │
└──────┬──────────────────────────────────────────┘
       │
   ┌───┴────┬─────────┬────────┬──────────┐
   │        │         │        │          │
   ▼        ▼         ▼        ▼          ▼
 ANALYTICS MARKETING CONTENT SUPPORT PLATFORM
 AGENT     AGENT     AGENT    AGENT     AGENT


SIGNALS (Analytics → Others):
- NEW_SALE: Sales Agent → Marketing (promote)
- THEME_TRENDING: Analytics → Marketing (create campaign)
- HIGH_REFUND_RATE: Analytics → Support (investigate)
- QUALITY_ISSUE: Analytics → Content (review theme)

COMMANDS (Dashboard → Agents):
- PUBLISH_THEME → Content Agent
- SCHEDULE_CAMPAIGN → Marketing Agent
- GENERATE_REPORT → Analytics Agent
- CREATE_ESCALATION → Support Agent
```

---

## 📊 Data Flow Architecture

```
Dashboard
   │
   ├─→ Vercel Functions (API Routes)
   │    └─→ Neon Postgres (State)
   │
   ├─→ Redis Event Bus (Real-time signals)
   │    ├─→ Analytics Agent (listens to events)
   │    ├─→ Marketing Agent (listens to ANALYTICS_SIGNAL)
   │    ├─→ Content Agent (listens to CONTENT_REQUESTED)
   │    └─→ Support Agent (listens to TICKET_CREATED)
   │
   ├─→ Vercel Blob (File Storage)
   │    └─→ Theme screenshots, invoices, etc.
   │
   └─→ Vercel Analytics (Metrics)
        └─→ Dashboard charts & reports
```

---

## ⚡ Priority Actions & Quick Wins

### الإجراءات ذات الأولوية:

1. **Immediate (P0)**
   - ✅ View Dashboard overview
   - ✅ Create/Edit/Delete themes
   - ✅ View basic analytics
   - ✅ Create & publish campaigns
   - ✅ Manage support tickets

2. **Short-term (P1)**
   - ✅ Custom reports
   - ✅ Alert system
   - ✅ Bulk operations
   - ✅ Export functionality
   - ✅ Team collaboration

3. **Medium-term (P2)**
   - 📋 Automation workflows
   - 📋 AI-powered recommendations
   - 📋 Advanced segmentation
   - 📋 Predictive analytics
   - 📋 Multi-language UI

---

## 🎯 Success Metrics

- ✅ Page load time < 2s
- ✅ All actions < 1s response time
- ✅ Real-time updates (< 5s)
- ✅ 99.9% uptime
- ✅ Zero data loss
- ✅ Audit trail for all actions
- ✅ Mobile responsive
- ✅ Accessibility (WCAG 2.1 AA)
