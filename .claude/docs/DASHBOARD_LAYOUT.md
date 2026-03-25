# Tashkeel Dashboard — Visual Layout & Components

## 📐 Main Dashboard Layout

```
╔════════════════════════════════════════════════════════════════════╗
║                        TASHKEEL DASHBOARD                          ║
╠════════════════════════════════════════════════════════════════════╣
║ 🏠 Logo  │ Search  │ Notifications 🔔 │ Help ? │ User 👤 │ Settings ⚙  ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  ┌─────────────────┐    ┌──────────────────────────────────────┐ ║
║  │  SIDEBAR        │    │  MAIN CONTENT AREA                   │ ║
║  │  ═════════════  │    │  ════════════════════════════════════ │ ║
║  │                 │    │                                      │ ║
║  │ 📊 Overview     │    │  [ OVERVIEW / ANALYTICS / THEMES ]   │ ║
║  │ 🎨 Themes       │    │                                      │ ║
║  │ 📈 Analytics    │    │  ┌──────────────────────────────┐   │ ║
║  │ 📢 Marketing    │    │  │ KEY METRICS (4 cards)        │   │ ║
║  │ ✍️  Content     │    │  │                              │   │ ║
║  │ 🎧 Support      │    │  │ Sales | Downloads | Users    │   │ ║
║  │ 💳 Payments     │    │  │ Growth %                     │   │ ║
║  │ ⚙️  Settings    │    │  └──────────────────────────────┘   │ ║
║  │                 │    │                                      │ ║
║  │ ◀ Collapse      │    │  ┌──────────────────────────────┐   │ ║
║  │                 │    │  │ CHART: Revenue Trend         │   │ ║
║  │                 │    │  │  (Time-series chart)         │   │ ║
║  │                 │    │  │                              │   │ ║
║  │                 │    │  └──────────────────────────────┘   │ ║
║  │                 │    │                                      │ ║
║  │                 │    │  ┌────────────────┬────────────────┐ ║
║  │                 │    │  │ TOP THEMES (5) │ RECENT SALES(5)│ ║
║  │                 │    │  │                │                │ ║
║  │                 │    │  │ 1. Theme-A     │ Sale #1234     │ ║
║  │                 │    │  │ 2. Theme-B     │ Sale #1233     │ ║
║  │                 │    │  │ 3. Theme-C     │ Sale #1232     │ ║
║  │                 │    │  └────────────────┴────────────────┘ ║
║  │                 │    │                                      │ ║
║  │                 │    │  ┌──────────────────────────────┐   │ ║
║  │                 │    │  │ ACTIVITY LOG                 │   │ ║
║  │                 │    │  │ - Admin published Theme-X    │   │ ║
║  │                 │    │  │ - Campaign #1 sent (200k)    │   │ ║
║  │                 │    │  │ - New article published      │   │ ║
║  │                 │    │  └──────────────────────────────┘   │ ║
║  │                 │    │                                      │ ║
║  └─────────────────┘    └──────────────────────────────────────┘ ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## 🎨 Theme Management Page

### 1. Themes List View

```
╔═══════════════════════════════════════════════════════════════════╗
║  Themes Management                                     [+ New]    ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  Filters: [Category ▼] [Status ▼] [Price ▼]  Search: [_____]    ║
║  View:    [Grid] [List] [Compact]    Sort: [Name ▼]             ║
║                                                                   ║
║  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐       ║
║  │ Theme A        │ │ Theme B        │ │ Theme C        │       ║
║  │ [IMG]          │ │ [IMG]          │ │ [IMG]          │       ║
║  │                │ │                │ │                │       ║
║  │ Modern Minimal │ │ E-Commerce Pro │ │ Blog Elegant   │       ║
║  │ Status: Active │ │ Status: Active │ │ Status: Review │       ║
║  │ Downloads: 234 │ │ Downloads: 456 │ │ Downloads: 12  │       ║
║  │ Revenue: $2.3k │ │ Revenue: $5.6k │ │ Revenue: $120  │       ║
║  │                │ │                │ │                │       ║
║  │ [Edit] [Delete]│ │ [Edit] [Delete]│ │ [Edit] [Delete]│       ║
║  │ [Preview]      │ │ [Preview]      │ │ [Preview]      │       ║
║  └────────────────┘ └────────────────┘ └────────────────┘       ║
║                                                                   ║
║  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐       ║
║  │ Theme D        │ │ Theme E        │ │ Theme F        │       ║
║  │ ...            │ │ ...            │ │ ...            │       ║
║  └────────────────┘ └────────────────┘ └────────────────┘       ║
║                                                                   ║
║  Showing 1-6 of 24  [< Prev] [1] [2] [3] [4] [Next >]           ║
╚═══════════════════════════════════════════════════════════════════╝
```

### 2. Theme Detail Editor

```
╔═══════════════════════════════════════════════════════════════════╗
║  Edit Theme: Modern Minimal          [← Back] [Save] [Preview] [Delete]
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  TABS: [Basic] [Visual] [Pricing] [SEO] [Analytics]              ║
║  ═════════════════════════════════════════════════════════════════║
║                                                                   ║
║  ┌─ BASIC INFO ──────────────────────────────────────────────────┐║
║  │                                                               │║
║  │  Name (EN):      [Modern Minimal                        ]     │║
║  │  Name (AR):      [قالب أنيق حديث                          ]   │║
║  │                                                               │║
║  │  Slug:           [modern-minimal                       ]     │║
║  │                  (Auto-generated, edit if needed)            │║
║  │                                                               │║
║  │  Description:    [────────────────────────────────────]       │║
║  │                  [A clean and minimal WordPress theme]       │║
║  │                  [────────────────────────────────────]       │║
║  │                                                               │║
║  │  Version:        [1.2.3        ]                              │║
║  │  Creator:        [Mohammed Ali]                              │║
║  │                                                               │║
║  │  Status:         [● Active  ○ Archived  ○ Draft]             │║
║  │                                                               │║
║  └───────────────────────────────────────────────────────────────┘║
║                                                                   ║
║  ┌─ VISUAL ──────────────────────────────────────────────────────┐║
║  │                                                               │║
║  │  Thumbnail:      [Choose File] [Upload]  [Preview]           │║
║  │                  Current: modern-minimal-thumb.jpg           │║
║  │                                                               │║
║  │  Screenshots:    [Screenshot 1] [Screenshot 2] [Screenshot 3] │║
║  │                  [Choose File] [+Add More]                    │║
║  │                                                               │║
║  │  Demo URL:       [https://demo.tashkeel.dev/modern-minimal]   │║
║  │                                                               │║
║  │  Preview Colors: [#FFFFFF] [#000000] [#FF6B6B] [#4ECDC4]     │║
║  │                  [+ Add Color]                                │║
║  │                                                               │║
║  └───────────────────────────────────────────────────────────────┘║
║                                                                   ║
║  ┌─ PRICING ────────────────────────────────────────────────────┐║
║  │                                                               │║
║  │  Price (USD):    [49.99        ]                              │║
║  │  License:        [○ GPL  ● MIT  ○ Proprietary]                │║
║  │  Support:        [○ 6 months  ● 1 year  ○ Lifetime]          │║
║  │                                                               │║
║  │  Features:       ☑ Mobile Responsive                         │║
║  │                  ☑ RTL Support                               │║
║  │                  ☑ Dark Mode                                 │║
║  │                  ☑ WooCommerce Ready                         │║
║  │                  ☐ Multisite                                 │║
║  │                                                               │║
║  └───────────────────────────────────────────────────────────────┘║
║                                                                   ║
║  [Save Changes] [Cancel] [Preview]  [Submit for Review] [More]   ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## 📊 Analytics Dashboard

```
╔═══════════════════════════════════════════════════════════════════╗
║  Analytics                           Date: [Jan 1 - Jan 31, 2026] ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  Metrics:  [All] [Sales] [Downloads] [Users] [Custom]            ║
║                                                                   ║
║  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐    ║
║  │ Total Sales     │ │ Total Downloads │ │ Total Users     │    ║
║  │ $45,230         │ │ 12,450          │ │ 5,432           │    ║
║  │ ↑ 15% from last │ │ ↑ 23% from last │ │ ↑ 8% from last  │    ║
║  │                 │ │                 │ │                 │    ║
║  │ [View Details]  │ │ [View Details]  │ │ [View Details]  │    ║
║  └─────────────────┘ └─────────────────┘ └─────────────────┘    ║
║                                                                   ║
║  ┌─────────────────────────────────────────────────────────────┐ ║
║  │                                                               │ ║
║  │  REVENUE TREND                                               │ ║
║  │  $50k │                                                       │ ║
║  │  $40k │     ╱╲        ╱╲                                      │ ║
║  │  $30k │    ╱  ╲      ╱  ╲      ╱╲                            │ ║
║  │  $20k │   ╱    ╲____╱    ╲____╱  ╲                           │ ║
║  │  $10k │  ╱                       ╲                            │ ║
║  │  $0   │ ╱                         ╲╱                          │ ║
║  │        └─────────────────────────────────────────────────    │ ║
║  │        Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov │ ║
║  │                                                               │ ║
║  └─────────────────────────────────────────────────────────────┘ ║
║                                                                   ║
║  ┌─────────────────────────────────────────────────────────────┐ ║
║  │ TOP THEMES                                                  │ ║
║  │                                                              │ ║
║  │ 1. Modern Minimal      15,234 downloads    $45,234 revenue  │ ║
║  │    ███████████████░░░░ 76% of total                         │ ║
║  │                                                              │ ║
║  │ 2. E-Commerce Pro      8,234 downloads     $24,234 revenue  │ ║
║  │    ████████░░░░░░░░░░ 41% of total                         │ ║
║  │                                                              │ ║
║  │ 3. Blog Elegant        4,234 downloads     $12,234 revenue  │ ║
║  │    ████░░░░░░░░░░░░░░ 21% of total                         │ ║
║  │                                                              │ ║
║  └─────────────────────────────────────────────────────────────┘ ║
║                                                                   ║
║  [Export Report] [Save Report] [Schedule] [Share]               ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## 📢 Marketing Campaign Builder

```
╔═══════════════════════════════════════════════════════════════════╗
║  Create Marketing Campaign          [← Back] [Save Draft] [Publish]
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  STEP: 1/4  Type → Content → Schedule → Review                   ║
║  ═════════════════════════════════════════════════════════════════║
║                                                                   ║
║  SELECT CAMPAIGN TYPE:                                           ║
║                                                                   ║
║  ┌─────────────────────────────────────────────────────────────┐ ║
║  │                                                               │ ║
║  │  ○ Email Campaign                                            │ ║
║  │    Send to users who match criteria (segment)                │ ║
║  │                                                              │ ║
║  │  ● Social Media Campaign                                     │ ║
║  │    Post on Facebook, Instagram, TikTok (Autonomous)          │ ║
║  │                                                              │ ║
║  │  ○ Google Ads Campaign                                       │ ║
║  │    Requires approval (non-autonomous)                        │ ║
║  │                                                              │ ║
║  │  ○ Product Launch                                            │ ║
║  │    Coordinated multi-channel launch                          │ ║
║  │                                                              │ ║
║  └─────────────────────────────────────────────────────────────┘ ║
║                                                                   ║
║  ┌─ STEP 2: CONTENT ───────────────────────────────────────────┐ ║
║  │                                                               │ ║
║  │  Campaign Name:       [Launch Modern Minimal V2              ]│ ║
║  │                                                               │ ║
║  │  Select Themes:       [Choose...]                            │ ║
║  │                       ☑ Modern Minimal                       │ ║
║  │                       ☐ E-Commerce Pro                       │ ║
║  │                       ☐ Blog Elegant                         │ ║
║  │                                                               │ ║
║  │  Instagram Caption:   [────────────────────────────────────]│ ║
║  │                       [🎨 Introducing Modern Minimal V2!]    │ ║
║  │                       [Cleaner. Faster. More Beautiful.]     │ ║
║  │                       [────────────────────────────────────]│ ║
║  │                       (RTL support enabled)                  │ ║
║  │                                                               │ ║
║  │  Images:              [Upload Image] [+Add More]             │ ║
║  │                       Image 1: modern-v2-hero.jpg            │ ║
║  │                       [Preview] [Remove]                    │ ║
║  │                                                               │ ║
║  │  Hashtags:            [#تشكيل #ثيمات #ورديبريس           ]│ ║
║  │                                                               │ ║
║  │  CTA Button:          [Get Modern Minimal]                   │ ║
║  │  CTA Link:            [https://tashkeel.dev/themes/...]      │ ║
║  │                                                               │ ║
║  └───────────────────────────────────────────────────────────────┘║
║                                                                   ║
║  ┌─ STEP 3: SCHEDULE ──────────────────────────────────────────┐ ║
║  │                                                               │ ║
║  │  Platform:            ☑ Facebook   ☑ Instagram   ☑ TikTok   │ ║
║  │                                                               │ ║
║  │  Publish Date:        [2026-03-25]                           │ ║
║  │  Publish Time:        [10:00 AM]                             │ ║
║  │                                                               │ ║
║  │  Auto-Repeat:         ○ Daily  ○ Weekly  ● No repeat         │ ║
║  │                                                               │ ║
║  │  Status:              ○ Draft  ● Scheduled  ○ Published      │ ║
║  │                                                               │ ║
║  └───────────────────────────────────────────────────────────────┘║
║                                                                   ║
║  [← Previous] [Next →] [Save Draft] [Cancel]                     ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## 🎧 Support Ticket Management

```
╔═══════════════════════════════════════════════════════════════════╗
║  Support Tickets          [+ New Ticket] [Knowledge Base]         ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  Filters: [Status] [Priority] [Assigned To] [Date]               ║
║  Queue: [All (45)] [New (12)] [In Progress (18)] [Resolved (15)]║
║                                                                   ║
║  ┌────────────────────────────────────────────────────────────┐ ║
║  │ [NEW] [URGENT]  #1234 - Theme activation not working      │ ║
║  │                 Customer: john@example.com                │ ║
║  │                 Assigned: Ahmed Hassan                    │ ║
║  │                 Created: 2 hours ago                      │ ║
║  │                 Category: Installation                    │ ║
║  │                 ➜ Click to open                          │ ║
║  └────────────────────────────────────────────────────────────┘ ║
║                                                                   ║
║  ┌────────────────────────────────────────────────────────────┐ ║
║  │ [IN PROGRESS] [HIGH]  #1233 - Refund request             │ ║
║  │                       Customer: sarah@example.com        │ ║
║  │                       Assigned: Fatima Saleh             │ ║
║  │                       Created: 5 hours ago               │ ║
║  │                       Category: Billing                  │ ║
║  │                       ➜ Click to open                    │ ║
║  └────────────────────────────────────────────────────────────┘ ║
║                                                                   ║
║  ┌────────────────────────────────────────────────────────────┐ ║
║  │ [RESOLVED] [LOW]  #1232 - CSS customization help         │ ║
║  │                   Customer: david@example.com            │ ║
║  │                   Assigned: Ahmed Hassan                 │ ║
║  │                   Resolved: 1 day ago                    │ ║
║  │                   Category: Support                      │ ║
║  │                   ➜ Click to open                        │ ║
║  └────────────────────────────────────────────────────────────┘ ║
║                                                                   ║
║  Showing 1-3 of 45  [< Prev] [1] [2] [3] ... [15] [Next >]      ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

### Ticket Detail View

```
╔═══════════════════════════════════════════════════════════════════╗
║  Ticket #1234: Theme activation not working                      ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  Status: [🔴 NEW]  Priority: [🔴 URGENT]  Category: Installation ║
║  Assigned To: [Ahmed Hassan] [Change Assignment]                 ║
║                                                                   ║
║  ┌─ CUSTOMER INFO ───────────────────────────────────────────┐  ║
║  │ Name:    John Smith                                        │  ║
║  │ Email:   john@example.com                                  │  ║
║  │ Country: United States                                     │  ║
║  │ Joined:  2025-01-15                                        │  ║
║  │ Purchases: 2 (Modern Minimal, E-Commerce Pro)             │  ║
║  │                                                             │  ║
║  └─────────────────────────────────────────────────────────────┘  ║
║                                                                   ║
║  ┌─ CONVERSATION ────────────────────────────────────────────┐  ║
║  │                                                             │  ║
║  │  [Customer] - 2 hours ago                                  │  ║
║  │  ─────────────────────────────────────────────────────     │  ║
║  │  Hi, I purchased Modern Minimal but it's not showing in   │  ║
║  │  My Themes on WordPress. I've tried redownloading but     │  ║
║  │  nothing works. Can you help?                             │  ║
║  │                                                             │  ║
║  │                                                             │  ║
║  │  [Agent (Ahmed)] - 30 mins ago                             │  ║
║  │  ──────────────────────────────────────────────────────    │  ║
║  │  Hi John,                                                  │  ║
║  │  Thanks for reaching out. Let's troubleshoot this:        │  ║
║  │  1. Can you confirm your WordPress version?              │  ║
║  │  2. Have you checked the "Installed Themes" section?     │  ║
║  │  Let me know and we'll get this sorted!                  │  ║
║  │                                                             │  ║
║  │  [Attach knowledge article: "Theme Won't Activate"]        │  ║
║  │                                                             │  ║
║  └─────────────────────────────────────────────────────────────┘  ║
║                                                                   ║
║  ┌─ RESPONSE FIELD ──────────────────────────────────────────┐  ║
║  │                                                             │  ║
║  │  Your Reply:  [────────────────────────────────────────]   │  ║
║  │               [Type your response...                   ]    │  ║
║  │               [────────────────────────────────────────]    │  ║
║  │                                                             │  ║
║  │  [Attach File] [Add Template] [Attach Article]             │  ║
║  │                                                             │  ║
║  │  Status: [New ▼]  Assigned: [Ahmed Hassan ▼]              │  ║
║  │                                                             │  ║
║  │  [Send Reply] [Save as Draft] [Close Ticket] [Escalate]    │  ║
║  │                                                             │  ║
║  └─────────────────────────────────────────────────────────────┘  ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## 💳 Payment & Transactions Page

```
╔═══════════════════════════════════════════════════════════════════╗
║  Payments & Transactions             [Export CSV] [Reconcile]    ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  Summary:                                                        ║
║  Total Revenue (This Month): $12,450                             ║
║  Total Transactions: 234                                         ║
║  Successful: 232 (99.1%)  Failed: 2 (0.9%)                      ║
║                                                                   ║
║  Filters: [Date Range] [Status] [Payment Method] [Amount]        ║
║                                                                   ║
║  ┌────────────┬───────────────┬─────────┬──────────┬───────────┐║
║  │ Date & ID  │ Customer      │ Item    │ Amount   │ Status    ║
║  ├────────────┼───────────────┼─────────┼──────────┼───────────┤║
║  │ 2026-03-25 │ John Smith    │ Modern  │ $49.99   │ ✓ Success ║
║  │ #TXN-1234  │ john@ex.com   │ Minimal │ (USD)    │           ║
║  │            │               │ v1.2.3  │          │           ║
║  │            │               │ 1 year  │          │ [Details] ║
║  ├────────────┼───────────────┼─────────┼──────────┼───────────┤║
║  │ 2026-03-25 │ Sarah Johnson │ E-Comm  │ $79.99   │ ✓ Success ║
║  │ #TXN-1233  │ sarah@ex.com  │ Pro     │ (USD)    │           ║
║  │            │               │ v2.0.1  │          │           ║
║  │            │               │ 1 year  │          │ [Details] ║
║  ├────────────┼───────────────┼─────────┼──────────┼───────────┤║
║  │ 2026-03-24 │ Mike Davis    │ Blog    │ $39.99   │ ✓ Success ║
║  │ #TXN-1232  │ mike@ex.com   │ Elegant │ (USD)    │           ║
║  │            │               │ v1.1.0  │          │           ║
║  │            │               │ 1 year  │          │ [Details] ║
║  └────────────┴───────────────┴─────────┴──────────┴───────────┘║
║                                                                   ║
║  Showing 1-3 of 234  [< Prev] [1] [2] [3] ... [78] [Next >]     ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

### Transaction Detail Modal

```
╔═══════════════════════════════════════════════════════════════════╗
║  Transaction Details #TXN-1234                        [Close ✕]  ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  ┌─ TRANSACTION ─────────────────────────────────────────────┐  ║
║  │ ID:                  TXN-1234                              │  ║
║  │ Date & Time:         2026-03-25 14:32 UTC                 │  ║
║  │ Status:              ✓ SUCCESS                            │  ║
║  │ Amount:              $49.99 USD                            │  ║
║  │ Payment Method:      Visa ending in 4242                  │  ║
║  │ Gateway:             Stripe                               │  ║
║  │ Gateway ID:          ch_1234567890                        │  ║
║  └─────────────────────────────────────────────────────────────┘  ║
║                                                                   ║
║  ┌─ CUSTOMER ────────────────────────────────────────────────┐  ║
║  │ Name:                John Smith                            │  ║
║  │ Email:               john@example.com                      │  ║
║  │ Country:             United States                         │  ║
║  │ Address:             123 Main St, New York, NY 10001       │  ║
║  └─────────────────────────────────────────────────────────────┘  ║
║                                                                   ║
║  ┌─ ITEM PURCHASED ──────────────────────────────────────────┐  ║
║  │ Theme:               Modern Minimal                        │  ║
║  │ Version:             v1.2.3                                │  ║
║  │ License Type:        MIT                                   │  ║
║  │ Support Duration:    1 Year (expires 2027-03-25)          │  ║
║  │ Price:               $49.99                                │  ║
║  │ Tax (0%):            $0.00                                 │  ║
║  │ Total:               $49.99                                │  ║
║  └─────────────────────────────────────────────────────────────┘  ║
║                                                                   ║
║  ┌─ INVOICE ────────────────────────────────────────────────┐  ║
║  │ Invoice URL:  https://tashkeel.dev/invoices/INV-1234      │  ║
║  │ [Download PDF] [Send to Customer] [View]                  │  ║
║  └─────────────────────────────────────────────────────────────┘  ║
║                                                                   ║
║  ┌─ ACTIONS ────────────────────────────────────────────────┐  ║
║  │ [Refund] [Send Receipt] [Create Support Ticket]           │  ║
║  │                                                             │  ║
║  │ ⓘ Refund is available until 2026-04-24 (within 30 days)   │  ║
║  └─────────────────────────────────────────────────────────────┘  ║
║                                                                   ║
║                                    [Close] [Print] [Download]    ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## 🎨 Sidebar Navigation (Expanded)

```
┌──────────────────────────────┐
│         TASHKEEL             │
│         تشكيل               │
├──────────────────────────────┤
│                              │
│ 📊 OVERVIEW                  │
│    └─ Dashboard              │
│    └─ Activity Log           │
│    └─ Reports                │
│                              │
│ 🎨 THEMES                    │
│    └─ All Themes             │
│    └─ Create New             │
│    └─ Categories             │
│    └─ Pending Review         │
│    └─ Archived               │
│                              │
│ 📈 ANALYTICS                 │
│    └─ Overview               │
│    └─ Sales Metrics          │
│    └─ Download Trends        │
│    └─ Attribution            │
│    └─ Custom Reports         │
│    └─ Alerts                 │
│                              │
│ 📢 MARKETING                 │
│    └─ Campaigns              │
│    └─ Email Campaigns        │
│    └─ Social Posts           │
│    └─ Performance            │
│    └─ Scheduled              │
│    └─ Templates              │
│                              │
│ ✍️  CONTENT                   │
│    └─ Blog Posts             │
│    └─ Create Article         │
│    └─ In Review              │
│    └─ Published              │
│    └─ Knowledge Base         │
│                              │
│ 🎧 SUPPORT                   │
│    └─ Tickets                │
│    └─ New (12)               │
│    └─ In Progress (18)       │
│    └─ Knowledge Base         │
│    └─ Templates              │
│    └─ Reports                │
│                              │
│ 💳 PAYMENTS                  │
│    └─ Transactions           │
│    └─ Invoices               │
│    └─ Refunds                │
│    └─ Reconciliation         │
│    └─ Reports                │
│                              │
│ ⚙️  SETTINGS                  │
│    └─ General                │
│    └─ Team Members           │
│    └─ Integrations           │
│    └─ Webhooks               │
│    └─ API Keys               │
│    └─ Billing                │
│    └─ Security               │
│                              │
│ ─────────────────────────────│
│                              │
│ 👤 Mohammed Ali              │
│    admin@tashkeel.dev        │
│    [Profile] [Logout]        │
│                              │
│ 🌙 [Dark Mode Toggle]        │
│                              │
│ ◀ [Collapse Sidebar]         │
│                              │
└──────────────────────────────┘
```

---

## 🎯 Mobile Responsive Breakpoints

### Mobile (< 768px)
- Sidebar → Hidden (toggle via hamburger ☰)
- Single column layout
- Simplified cards (fewer details)
- Touch-friendly buttons (48px minimum)

### Tablet (768px - 1024px)
- Sidebar → Collapsible
- 2-column grid for cards
- Medium density tables

### Desktop (> 1024px)
- Sidebar → Always visible
- 3-4 column grid
- Full-density tables
- Side panels for detail views

---

## 🔧 Component Library (shadcn/ui)

```
Buttons:      [Primary] [Secondary] [Outline] [Ghost] [Destructive]
Forms:        Input, Textarea, Select, Checkbox, Radio, Switch
Tables:       Table with sorting, filtering, pagination
Modals:       Dialog, AlertDialog, Drawer (mobile)
Notifications: Toast, Sheet
Navigation:   Tabs, Breadcrumb, Sidebar
Data:         Badge, Progress, Skeleton, Spinner
Layout:       Card, Container, Flex, Grid
Typography:   Headings, Body, Code, Lists
```

---

## 🌐 Internationalization (i18n)

- **Primary**: English (EN)
- **Secondary**: Arabic (AR)
- **RTL Support**: Automatic for Arabic
- **Date Formats**: Localized
- **Currency**: USD (with locale formatting)
- **Language Switcher**: Top-right corner

---

## 📱 Example: Mobile Layout

```
╔═══════════════════════════════════════╗
║ ☰ Tashkeel    🔔 🎨 👤             ║
╠═══════════════════════════════════════╣
║                                       ║
║  ┌─────────────────────────────────┐  ║
║  │ Revenue: $45,230 ↑ 15%         │  ║
║  └─────────────────────────────────┘  ║
║                                       ║
║  ┌─────────────────────────────────┐  ║
║  │ Downloads: 12,450 ↑ 23%        │  ║
║  └─────────────────────────────────┘  ║
║                                       ║
║  ┌─────────────────────────────────┐  ║
║  │ TOP THEMES                      │  ║
║  │ 1. Modern Minimal        $45.2k │  ║
║  │ 2. E-Commerce Pro        $24.2k │  ║
║  │ 3. Blog Elegant          $12.2k │  ║
║  └─────────────────────────────────┘  ║
║                                       ║
║  [Quick Actions]                      ║
║  [+ New Theme]  [+ Campaign]          ║
║  [+ Article]    [View All]            ║
║                                       ║
╚═══════════════════════════════════════╝
```

---

## 📋 Accessibility (WCAG 2.1 AA)

- ✅ Keyboard navigation (Tab, Enter, Arrow keys)
- ✅ Screen reader support (ARIA labels)
- ✅ Color contrast (4.5:1 for text)
- ✅ Focus indicators (visible outlines)
- ✅ Semantic HTML
- ✅ Form labels & error messages
- ✅ Alternative text for images
- ✅ Skip navigation links
