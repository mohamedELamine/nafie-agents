# Tashkeel Dashboard — Implementation Roadmap

## 📋 Overview

This document outlines the phased implementation plan for the Tashkeel Dashboard, breaking down the project into manageable phases with clear deliverables, dependencies, and timeline estimates.

---

## 🎯 Phase 1: Foundation & Infrastructure (Weeks 1-2)

### Objectives
- Set up Next.js 16 project with shadcn/ui
- Configure Vercel, Neon PostgreSQL, and Blob storage
- Create base API layer with authentication
- Establish database schema and migrations

### Deliverables

#### 1.1 Project Setup
- [ ] Initialize Next.js 16 project
  - Template: `npx create-next-app@latest tashkeel-dashboard`
  - TypeScript enabled
  - App Router configured

- [ ] Install dependencies
  ```bash
  npm install shadcn-ui @radix-ui/react-* tailwindcss @vercel/og swr
  npm install @neondatabase/serverless @upstash/redis
  npm install next-auth jose
  npm install zod react-hook-form
  ```

- [ ] Configure environment variables
  ```env
  NEXT_PUBLIC_API_URL=https://tashkeel.dev/api/v1
  DATABASE_URL=postgresql://user:pass@...
  REDIS_URL=redis://...
  JWT_SECRET=...
  STRIPE_SECRET_KEY=...
  STRIPE_PUBLIC_KEY=...
  RESEND_API_KEY=...
  ```

- [ ] Set up ESLint, Prettier, TypeScript
  - Strict mode enabled
  - 80 character line length

#### 1.2 shadcn/ui Setup
- [ ] Initialize shadcn/ui
  ```bash
  npx shadcn-ui@latest init
  ```

- [ ] Add essential components
  - Button, Input, Textarea, Select, Checkbox, Radio
  - Card, Dialog, Drawer, Toast
  - Tabs, Table, Sidebar, Badge
  - Form, Label, Error messages
  - Charts (recharts integration)

#### 1.3 Authentication Layer
- [ ] Create auth middleware
  - JWT validation
  - Role-based access control (RBAC)
  - Route protection with `proxy.ts`

- [ ] Implement user session management
  - Login endpoint
  - Token refresh mechanism
  - Logout functionality

- [ ] Create permission system
  ```typescript
  type Role = 'admin' | 'creator' | 'marketer' | 'editor' | 'support' | 'analyst';

  const permissions: Record<Role, string[]> = {
    admin: ['*'],
    creator: ['themes:create', 'themes:edit', 'analytics:read'],
    // ...
  };
  ```

#### 1.4 Database Schema
- [ ] Create migration files using Neon
  ```sql
  -- migrations/001_initial_schema.sql
  CREATE TABLE users (...)
  CREATE TABLE themes (...)
  CREATE TABLE campaigns (...)
  CREATE TABLE support_tickets (...)
  CREATE TABLE transactions (...)
  ```

- [ ] Set up database connection pool
  ```typescript
  // lib/db.ts
  import { neon } from '@neondatabase/serverless';

  export const sql = neon(process.env.DATABASE_URL!);
  ```

- [ ] Create seed data (test themes, users, etc.)

#### 1.5 API Base Layer
- [ ] Create API route structure
  ```
  app/api/v1/
  ├── themes/
  ├── analytics/
  ├── campaigns/
  ├── articles/
  ├── support/
  └── payments/
  ```

- [ ] Set up request/response handlers with error handling
  ```typescript
  // lib/api-response.ts
  export function success(data: any) { /* ... */ }
  export function error(message: string, code: string) { /* ... */ }
  ```

- [ ] Implement request validation
  ```typescript
  import { z } from 'zod';

  const createThemeSchema = z.object({
    name: z.string().min(3),
    description: z.string().optional(),
    // ...
  });
  ```

- [ ] Add logging and monitoring
  ```typescript
  // lib/logger.ts
  export const logger = createLogger('tashkeel-dashboard');
  ```

#### 1.6 Vercel Integration
- [ ] Configure project in Vercel dashboard
  - Link GitHub repository
  - Set production domain
  - Configure edge functions

- [ ] Set up CI/CD pipeline
  - GitHub Actions for testing & deployment
  - Preview deployments on PRs

### Timeline: **2 weeks**

### Team: 1-2 developers

### Dependencies: None

---

## 🏗️ Phase 2: Core Dashboard & Overview (Weeks 3-4)

### Objectives
- Implement main dashboard layout
- Create overview/metrics cards
- Build real-time data updates
- Integrate with analytics-agent

### Deliverables

#### 2.1 Main Layout & Navigation
- [ ] Create main dashboard layout
  - Header with logo, search, notifications
  - Sidebar with navigation menu
  - Responsive on mobile (hamburger menu)

- [ ] Implement sidebar navigation
  ```typescript
  // components/sidebar.tsx
  const navItems = [
    { href: '/dashboard', label: 'Overview', icon: Dashboard },
    { href: '/themes', label: 'Themes', icon: Palette },
    // ...
  ];
  ```

- [ ] Add breadcrumb navigation
- [ ] Implement dark/light mode toggle

#### 2.2 Overview Page
- [ ] Create key metrics cards
  - Total Revenue
  - Total Downloads
  - Active Users
  - Average Rating

- [ ] Build revenue trend chart
  - Line chart with dates
  - Support date range selector
  - Show growth percentage

- [ ] Display top themes section
  - Top 5 themes by downloads/revenue
  - Quick preview links
  - Click to view details

- [ ] Create recent sales table
  - Last 10 transactions
  - Customer name, amount, date
  - Click to view details

- [ ] Build activity log
  - Recent events from all agents
  - Filterable by type
  - Real-time updates

#### 2.3 Real-time Updates
- [ ] Set up WebSocket connection
  ```typescript
  // lib/websocket.ts
  import { io } from 'socket.io-client';

  export const socket = io(process.env.NEXT_PUBLIC_WS_URL!);
  ```

- [ ] Subscribe to analytics events
  ```typescript
  socket.on('analytics:metrics_updated', (data) => {
    // Update dashboard cards
  });
  ```

- [ ] Implement auto-refresh mechanism
  - Polls every 60 seconds if WebSocket unavailable
  - Shows last update timestamp

#### 2.4 API Endpoints Implementation
- [ ] `GET /api/v1/analytics/overview`
  - Returns key metrics
  - Supports date range filtering

- [ ] `GET /api/v1/analytics/themes`
  - Returns top themes
  - Paginated results

- [ ] `GET /api/v1/analytics/transactions`
  - Returns recent sales
  - Sortable and filterable

- [ ] `GET /api/v1/analytics/activity-log`
  - Returns recent events
  - Real-time updates via WebSocket

#### 2.5 Analytics Integration
- [ ] Connect dashboard to analytics-agent
  - Receive `ANALYTICS_SIGNAL` events
  - Update metrics in real-time
  - Store in Redis cache for performance

- [ ] Implement data caching
  ```typescript
  // lib/cache.ts
  export async function getCachedMetrics(key: string) {
    // Try cache first
    // Fall back to DB query
    // Update cache
  }
  ```

### Timeline: **2 weeks**

### Team: 2 developers

### Dependencies: Phase 1 complete

---

## 🎨 Phase 3: Themes Management (Weeks 5-6)

### Objectives
- Implement complete theme management CRUD
- Create theme editor with media upload
- Add review workflow
- Integrate with content-agent

### Deliverables

#### 3.1 Themes List View
- [ ] Create themes listing page
  - Grid view (3-4 columns)
  - List view (table format)
  - Compact view (cards)

- [ ] Implement filtering
  - By status (published, draft, review, archived)
  - By category
  - By price range
  - By rating

- [ ] Add sorting options
  - By name, downloads, revenue, date
  - Ascending/descending

- [ ] Build search functionality
  - Full-text search on name & description
  - Real-time results
  - Highlight matches

- [ ] Implement pagination
  - Show 20 per page
  - Jump to page
  - First/Last buttons

#### 3.2 Theme Detail Editor
- [ ] Create multi-step theme editor
  - Step 1: Basic info (name, slug, description)
  - Step 2: Visual (thumbnail, screenshots, colors)
  - Step 3: Pricing (price, license, support)
  - Step 4: SEO (meta description, keywords)

- [ ] Build form validation
  ```typescript
  const themeSchema = z.object({
    name: z.string().min(3).max(255),
    slug: z.string().regex(/^[a-z0-9-]+$/),
    price: z.number().min(0).max(9999),
    // ...
  });
  ```

- [ ] Implement auto-save
  - Save draft every 30 seconds
  - Show unsaved indicator
  - Warn on page leave

#### 3.3 Media Management
- [ ] Create file upload component
  - Drag-and-drop support
  - Progress indicator
  - File size validation (max 5MB per image)

- [ ] Integrate Vercel Blob storage
  ```typescript
  // lib/blob.ts
  import { put } from '@vercel/blob';

  export async function uploadFile(file: File) {
    const blob = await put(file.name, file, { access: 'public' });
    return blob.url;
  }
  ```

- [ ] Build media gallery
  - Thumbnail previews
  - Drag to reorder
  - Remove button
  - View full size

#### 3.4 Theme Review Workflow
- [ ] Create review submission
  - Button to "Submit for Review"
  - Shows submitted date
  - Can't edit while in review

- [ ] Build review status indicator
  - Draft → Submitted → Approved/Rejected
  - Shows reviewer comments
  - Appeal mechanism

- [ ] Signal integration
  - Send `THEME_SUBMITTED_FOR_REVIEW` to content-agent
  - Listen for `THEME_REVIEW_COMPLETE` events
  - Update status automatically

#### 3.5 Quick Actions
- [ ] Implement bulk actions
  - Select multiple themes
  - Bulk archive/publish/delete
  - Confirmation dialog

- [ ] Add duplicate theme
  - Copy existing theme as draft
  - Rename automatically (Theme Name v2)

- [ ] Create preview button
  - Opens demo in new tab
  - Shows theme on sample WordPress site

### Timeline: **2 weeks**

### Team: 2 developers

### Dependencies: Phase 1, 2 complete

---

## 📊 Phase 4: Analytics & Reporting (Weeks 7-8)

### Objectives
- Build comprehensive analytics dashboard
- Create custom report generator
- Implement alert system
- Add export functionality

### Deliverables

#### 4.1 Analytics Dashboard
- [ ] Create main analytics page
  - Date range selector (Today, Week, Month, Custom)
  - Metric selector (Sales, Downloads, Users, Revenue)
  - Granularity selector (Day, Week, Month)

- [ ] Build interactive charts
  - Revenue trend line chart
  - Downloads trend
  - User growth
  - Device/Browser breakdown (pie chart)

- [ ] Implement table views
  - Per-theme analytics
  - Per-channel analytics
  - Per-period comparison

- [ ] Add comparison features
  - Compare 2 periods
  - Compare 2 themes
  - Year-over-year comparison

#### 4.2 Custom Reports
- [ ] Create report builder
  - Select metrics to include
  - Select date range
  - Add filters (category, theme, region)
  - Choose layout (dashboard, table, chart)

- [ ] Implement report templates
  - "Monthly Sales Report"
  - "Theme Performance Report"
  - "Custom Report"

- [ ] Build report scheduling
  - Schedule weekly/monthly reports
  - Send via email
  - Store in archive

#### 4.3 Alert System
- [ ] Create alert builder
  - Select metric (sales, downloads, rating drop)
  - Set threshold
  - Choose notification channel (email, SMS, in-app)

- [ ] Implement alert history
  - View past alerts
  - View triggered status
  - Acknowledge alerts

- [ ] Add silence functionality
  - Temporarily silence alerts
  - Silence until threshold is met again

#### 4.4 Export Functionality
- [ ] Implement CSV export
  - Export chart data
  - Export table data
  - Custom columns

- [ ] Add PDF export
  - Beautiful formatted PDF reports
  - Include charts & tables
  - Branded header/footer

- [ ] Create email export
  - Send report via email
  - Schedule regular sends
  - Add recipients

### Timeline: **2 weeks**

### Team: 2 developers

### Dependencies: Phase 1, 2 complete

---

## 📢 Phase 5: Marketing & Campaigns (Weeks 9-10)

### Objectives
- Build campaign creation wizard
- Implement multi-channel publishing
- Create campaign analytics
- Add approval workflow for paid campaigns

### Deliverables

#### 5.1 Campaign Builder
- [ ] Create campaign type selector
  - Email campaign
  - Social media campaign
  - Google Ads campaign
  - Product launch

- [ ] Build content editor
  - WYSIWYG editor for email
  - Social media caption editor with RTL support
  - Image/video upload
  - Preview on different devices

- [ ] Implement theme selector
  - Multi-select themes to promote
  - Preview theme details

#### 5.2 Scheduling & Publishing
- [ ] Create scheduling interface
  - Select publish date/time
  - Select platforms
  - Set repeat schedule (daily, weekly, etc.)

- [ ] Implement autonomous publishing
  - For organic social: publish immediately
  - For paid: send to admin approval queue
  - For email: send when scheduled time arrives

- [ ] Add scheduling queue
  - Show scheduled campaigns
  - Edit before publish (within window)
  - Cancel scheduled campaigns

#### 5.3 Campaign Analytics
- [ ] Build campaign detail page
  - Impressions, clicks, conversions
  - CTR, conversion rate, ROI
  - Performance by platform
  - Performance trend over time

- [ ] Implement A/B testing interface
  - Create variations (subject line, content)
  - Split traffic 50/50
  - Compare results
  - Winner selection

#### 5.4 Approval Workflow
- [ ] Create approval queue
  - List pending campaigns
  - Filter by type, date, status

- [ ] Build approval interface
  - Preview campaign
  - Approve or reject with comments
  - Suggest edits

- [ ] Implement notifications
  - Notify marketer when approved/rejected
  - Notify admin of pending approvals

### Timeline: **2 weeks**

### Team: 2 developers

### Dependencies: Phase 1, 2, agent sync complete

---

## ✍️ Phase 6: Content Management (Weeks 11-12)

### Objectives
- Build article/blog creation interface
- Implement content review workflow
- Create knowledge base
- Add SEO optimization tools

### Deliverables

#### 6.1 Article Editor
- [ ] Create rich text editor
  - Markdown support
  - Code highlighting
  - Embed images/videos
  - Table support

- [ ] Implement bilingual editing
  - Edit English & Arabic side-by-side
  - Character count
  - RTL support for Arabic

- [ ] Build SEO tools
  - Meta description
  - Keywords/tags
  - OG image
  - Slug optimization

#### 6.2 Content Workflow
- [ ] Create draft saving
  - Auto-save every 30 seconds
  - Show last saved timestamp
  - Version history

- [ ] Implement review submission
  - Submit for review
  - Add reviewer notes
  - Track review progress

- [ ] Build publishing interface
  - Schedule publish date
  - Publish immediately
  - Set as featured

#### 6.3 Knowledge Base
- [ ] Create KB structure
  - Categories and subcategories
  - Search within KB
  - Related articles

- [ ] Implement helpfulness voting
  - Was this helpful? Yes/No
  - Feedback collection
  - Track most helpful articles

- [ ] Add KB analytics
  - Most viewed articles
  - Articles with low helpfulness
  - Search queries

### Timeline: **2 weeks**

### Team: 2 developers

### Dependencies: Phase 1, 2 complete

---

## 🎧 Phase 7: Support Management (Weeks 13-14)

### Objectives
- Build ticket management system
- Create support queue
- Implement ticket routing
- Add knowledge base integration

### Deliverables

#### 7.1 Ticket Queue
- [ ] Create ticket listing
  - Grouped by status
  - Filtered by priority
  - Sorted by age/priority

- [ ] Implement ticket detail view
  - Customer information
  - Conversation history
  - Related transactions
  - Assigned agent

#### 7.2 Ticket Management
- [ ] Build response composer
  - Rich text editor
  - Template suggestions
  - Attachment support
  - @mention team members

- [ ] Implement ticket status workflow
  - New → In Progress → Waiting → Resolved → Closed
  - Status change history
  - Auto-close after 7 days inactivity

- [ ] Create assignment system
  - Assign to team member
  - Auto-assignment based on load
  - Reassign as needed

#### 7.3 Knowledge Base Integration
- [ ] Add KB search in ticket interface
  - Suggest articles for customer issue
  - One-click send to customer
  - Track article effectiveness

- [ ] Create response templates
  - Common responses
  - Auto-populate with ticket data
  - Template categories

#### 7.4 Escalation System
- [ ] Implement escalation workflow
  - Escalate to manager
  - Escalate to admin
  - Escalation history

- [ ] Create escalation queue
  - Priority handling
  - Assignment to specialists
  - Notification system

### Timeline: **2 weeks**

### Team: 2 developers

### Dependencies: Phase 1, 2 complete

---

## 💳 Phase 8: Payments & Transactions (Weeks 15-16)

### Objectives
- Build transaction listing & search
- Implement refund processing
- Create invoice management
- Add financial reporting

### Deliverables

#### 8.1 Transaction Management
- [ ] Create transaction listing
  - Sortable table
  - Multiple filters
  - Search by customer/transaction ID

- [ ] Build transaction detail view
  - Customer information
  - Item details
  - Payment method
  - Invoice link

- [ ] Implement refund processing
  - Partial/full refund option
  - Reason selection
  - Refund confirmation
  - Update transaction status

#### 8.2 Invoice Management
- [ ] Create invoice generator
  - Automatic invoice on purchase
  - PDF download
  - Email to customer
  - Resend link

- [ ] Build invoice archive
  - Search invoices
  - Download historical invoices
  - Regenerate PDFs

#### 8.3 Financial Reporting
- [ ] Create revenue reports
  - Daily/weekly/monthly revenue
  - Revenue by theme
  - Revenue by payment method
  - Refund rate tracking

- [ ] Implement reconciliation
  - Compare DB records with Stripe
  - Flag discrepancies
  - Manual reconciliation interface

#### 8.4 Payment Settings
- [ ] Create payment configuration
  - Stripe API keys
  - Tax settings
  - Supported countries
  - Supported payment methods

### Timeline: **2 weeks**

### Team: 1-2 developers

### Dependencies: Phase 1 complete

---

## 🔧 Phase 9: Settings & Admin (Weeks 17-18)

### Objectives
- Build settings pages
- Implement user management
- Create team/organization settings
- Add security controls

### Deliverables

#### 9.1 General Settings
- [ ] Create settings layout
  - Tabs for different settings
  - Save indicators
  - Undo changes

- [ ] Implement profile settings
  - Edit name, email
  - Change password
  - Two-factor authentication

#### 9.2 Team Management
- [ ] Create team member list
  - Add/remove members
  - Assign roles
  - Manage permissions

- [ ] Build role management
  - Create custom roles
  - Set permissions per role
  - Audit role usage

#### 9.3 Organization Settings
- [ ] Create org settings page
  - Company name, logo, description
  - Default currency, timezone
  - Branding settings

- [ ] Build integrations page
  - Connected services (Stripe, Resend, etc.)
  - Connection status
  - Disconnect option

#### 9.4 Security Settings
- [ ] Create security page
  - API key management
  - Webhook configuration
  - IP whitelisting
  - Session management

- [ ] Implement audit logging
  - View all admin actions
  - Filter by type, user, date
  - Export audit log

### Timeline: **2 weeks**

### Team: 1-2 developers

### Dependencies: Phase 1 complete

---

## 🧪 Phase 10: Testing & Polish (Weeks 19-20)

### Objectives
- Comprehensive testing
- Performance optimization
- UI/UX refinement
- Documentation

### Deliverables

#### 10.1 Testing
- [ ] Write unit tests
  - API endpoints (50+ tests)
  - Utility functions
  - Form validation

- [ ] Write integration tests
  - Database + API
  - Event Bus integration
  - Agent communication

- [ ] Write E2E tests
  - Critical user flows
  - Campaign creation → publishing
  - Payment processing
  - Support ticket handling

- [ ] Performance testing
  - Load testing (1000 concurrent users)
  - Database query optimization
  - API response time benchmarks

#### 10.2 Performance Optimization
- [ ] Optimize bundle size
  - Code splitting
  - Lazy loading
  - Tree shaking

- [ ] Optimize images
  - Compress media files
  - Use WebP format
  - Responsive images

- [ ] Optimize database queries
  - Add indexes
  - Use query caching
  - Avoid N+1 queries

#### 10.3 UI/UX Refinement
- [ ] Accessibility audit
  - WCAG 2.1 AA compliance
  - Screen reader testing
  - Keyboard navigation

- [ ] Mobile responsiveness
  - Test on various devices
  - Touch interaction
  - Performance on slow networks

- [ ] Design polish
  - Consistent spacing
  - Color consistency
  - Typography refinement
  - Hover/focus states

#### 10.4 Documentation
- [ ] Write API documentation
  - Endpoint reference
  - Example requests/responses
  - Error codes

- [ ] Create user guides
  - Getting started
  - Feature walkthroughs
  - FAQ

- [ ] Document code
  - JSDoc comments
  - README files
  - Architecture guide

### Timeline: **2 weeks**

### Team: 2-3 developers + QA

### Dependencies: All previous phases complete

---

## 📅 Timeline Summary

| Phase | Duration | Start | End | Status |
|-------|----------|-------|-----|--------|
| 1. Foundation | 2 weeks | Week 1 | Week 2 | Planning |
| 2. Dashboard | 2 weeks | Week 3 | Week 4 | Planning |
| 3. Themes | 2 weeks | Week 5 | Week 6 | Planning |
| 4. Analytics | 2 weeks | Week 7 | Week 8 | Planning |
| 5. Marketing | 2 weeks | Week 9 | Week 10 | Planning |
| 6. Content | 2 weeks | Week 11 | Week 12 | Planning |
| 7. Support | 2 weeks | Week 13 | Week 14 | Planning |
| 8. Payments | 2 weeks | Week 15 | Week 16 | Planning |
| 9. Settings | 2 weeks | Week 17 | Week 18 | Planning |
| 10. Testing | 2 weeks | Week 19 | Week 20 | Planning |

**Total Duration: 20 weeks (5 months)**

---

## 👥 Team Composition

### Optimal Team
- 1 **Tech Lead** (full-time) — Architecture, code review, mentoring
- 2 **Full-Stack Developers** (full-time) — Feature implementation
- 1 **Frontend Developer** (full-time) — UI/UX, styling, responsiveness
- 1 **Backend Developer** (full-time) — API design, database, integrations
- 1 **QA Engineer** (half-time, ramping to full-time in phase 10)
- 1 **DevOps Engineer** (0.5-time) — CI/CD, deployment, monitoring

### Minimal Team
- 1 **Tech Lead** (full-time)
- 2 **Full-Stack Developers** (full-time)
- 1 **QA/Documentation** (part-time, ramping up)

**Duration with minimal team: 12-15 weeks**

---

## 🚀 Go-Live Checklist

Before public launch:

- [ ] All phases complete and tested
- [ ] Performance benchmarks met
- [ ] Security audit completed
- [ ] Load testing passed
- [ ] Documentation complete
- [ ] Team trained
- [ ] Monitoring & alerts configured
- [ ] Backup strategy in place
- [ ] Incident response plan prepared
- [ ] Legal review (terms, privacy, etc.)
- [ ] Marketing materials ready
- [ ] Support team trained

---

## 📝 Next Steps

1. **Week 1 Meeting:** Approve roadmap and resource allocation
2. **Finalize tech stack:** Confirm tool choices with team
3. **Set up infrastructure:** Vercel, Neon, Redis, Stripe accounts
4. **Create detailed sprint plans:** Break each phase into 1-week sprints
5. **Begin Phase 1:** Foundation & Infrastructure
