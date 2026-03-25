# Visual Production Agent — Detailed Specification

## 📋 نظرة عامة

Visual Production Agent هو وكيل متخصص يتعامل مع جميع عمليات معالجة الصور والفيديوهات والإنشاء الديناميكي للمحتوى البصري.

**المسؤوليات الأساسية:**
- ✅ ضغط وتحسين الصور (Image optimization)
- ✅ إنشاء صور OG ديناميكية
- ✅ إعادة تحجيم الصور لقنوات مختلفة
- ✅ معالجة الفيديوهات (conversion, trimming, resizing)
- ✅ إنشاء صور AI-generated (اختياري)
- ✅ إنشاء thumbnails وصور معاينة

---

## 🎯 Use Cases الكاملة

### 1️⃣ Theme Publishing

عندما مُنشئ الثيمة ينشر ثيمة جديدة:

```
THEME PUBLISHED EVENT
        ↓
visual_production_agent receives:
        ↓
Process Steps:
  1. Compress screenshots (JPEG 85% quality)
  2. Generate thumbnail (400x300)
  3. Generate preview images (1024x768)
  4. Create OG image (1200x630)
  5. Upload all to Vercel Blob
  6. Return URLs
        ↓
Emit: ASSET_PROCESS_DONE
        ↓
Update theme record with asset URLs
```

**API من Platform/Dashboard:**
```typescript
await visual.processThemeAssets({
  theme_id: 'theme_001',
  screenshots: ['url1', 'url2', 'url3'],
  theme_name: 'Modern Minimal',
  theme_description: 'Clean and minimal WordPress theme'
});
```

### 2️⃣ Campaign Creation

عندما المسوّق ينشئ حملة تسويقية:

```
CAMPAIGN CREATED
        ↓
marketing_agent requests from visual_agent:
        ↓
Process Steps:
  1. Resize images for each platform:
     - Facebook: 1200x628
     - Instagram: 1080x1350 (portrait) + 1080x1080 (square)
     - TikTok: 1080x1920 (vertical)
  2. Generate social media sizes
  3. Generate OG image for landing page
  4. Optional: AI-generate additional images (if enabled)
        ↓
Return URLs for each platform
```

**API من Marketing Agent:**
```typescript
await visual.generateSocialImages({
  campaign_id: 'campaign_001',
  title: 'Launch Modern Minimal V2',
  description: 'Cleaner. Faster. More Beautiful.',
  base_image: 'url_to_image',
  platforms: ['facebook', 'instagram', 'tiktok'],
  ai_generation: false
});
```

### 3️⃣ Article/Blog Publishing

عندما Content Agent ينشر مقالة:

```
ARTICLE PUBLISHED
        ↓
content_agent requests from visual_agent:
        ↓
Process Steps:
  1. Generate OG image from article title/excerpt
  2. Generate preview image for blog listing
  3. Optimize uploaded images (if any)
  4. Convert large images to WebP
  5. Create thumbnails for image gallery
        ↓
Return optimized URLs
```

**API من Content Agent:**
```typescript
await visual.generateArticleAssets({
  article_id: 'article_001',
  title: 'Getting Started with Modern Minimal',
  excerpt: 'Learn how to install and customize...',
  featured_image_url: 'url',
  gallery_images: ['url1', 'url2'],
  language: 'ar'
});
```

### 4️⃣ Report Generation

عندما Analytics Agent ينشئ تقرير PDF:

```
REPORT GENERATION JOB
        ↓
analytics_agent requests:
        ↓
Process Steps:
  1. Generate chart images (PNG):
     - Revenue trend chart
     - Download distribution pie chart
     - User growth area chart
  2. Embed charts in PDF template
  3. Optimize PDF size
  4. Return PDF URL
        ↓
Email report to user
```

**API من Analytics Agent:**
```typescript
await visual.generateReportAssets({
  report_id: 'report_001',
  report_type: 'monthly_summary',
  charts: [
    { type: 'line', title: 'Revenue Trend', data: [...] },
    { type: 'pie', title: 'Downloads', data: [...] }
  ],
  include_watermark: true
});
```

### 5️⃣ Direct Image Upload

عندما المستخدم يرفع صورة:

```
USER UPLOAD IMAGE
        ↓
dashboard POST /api/v1/media/upload
        ↓
Process Steps:
  1. Validate file size (max 50MB)
  2. Validate file type (jpg, png, gif, webp)
  3. Optimize image quality
  4. Convert to WebP format
  5. Create thumbnail (200x200)
  6. Upload to Blob
        ↓
Return URLs (original + thumbnail)
```

**API من Dashboard:**
```typescript
const { data } = await visual.uploadAndOptimizeImage({
  file: imageFile,
  workspace_id: 'ws_123',
  type: 'theme_screenshot'  // or: 'campaign_asset', 'article_image'
});

// data = {
//   original_url: 'https://...',
//   webp_url: 'https://...',
//   thumbnail_url: 'https://...',
//   metadata: { width, height, size }
// }
```

---

## 🛠️ الأدوات المستخدمة (Tools & Services)

### Image Processing

#### 1. Sharp (Primary)
```bash
npm install sharp
```

**الاستخدام:**
```typescript
import sharp from 'sharp';

// Compress screenshot
await sharp(imagePath)
  .jpeg({ quality: 85, progressive: true })
  .toFile('compressed.jpg');

// Create thumbnail
await sharp(imagePath)
  .resize(400, 300, { fit: 'cover' })
  .toFile('thumb.jpg');

// Convert to WebP
await sharp(imagePath)
  .webp({ quality: 80 })
  .toFile('image.webp');

// Multiple sizes (responsive)
const sizes = [400, 800, 1200];
for (const size of sizes) {
  await sharp(imagePath)
    .resize(size, size, { fit: 'inside' })
    .toFile(`image-${size}.jpg`);
}
```

**المميزات:**
- ✅ سريع جداً (C++ binding)
- ✅ معالجة batch
- ✅ دعم كل الصيغ
- ✅ لا يتطلب memory كبيرة

---

### Video Processing

#### 1. FFmpeg
```bash
# Install FFmpeg locally
brew install ffmpeg  # macOS
apt-get install ffmpeg  # Ubuntu
```

**الاستخدام:**
```typescript
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

// Convert video format
await execAsync(
  `ffmpeg -i input.mov -codec:v libx264 -preset medium output.mp4`
);

// Resize video
await execAsync(
  `ffmpeg -i input.mp4 -vf scale=1280:720 output.mp4`
);

// Generate thumbnail at 5 seconds
await execAsync(
  `ffmpeg -i input.mp4 -ss 00:00:05 -vframes 1 thumb.jpg`
);

// Trim video (first 30 seconds)
await execAsync(
  `ffmpeg -i input.mp4 -t 30 -c copy output.mp4`
);
```

**المميزات:**
- ✅ معالجة فيديو احترافية
- ✅ تحويل بين الصيغ
- ✅ إعادة تحجيم وضغط
- ✅ استخراج thumbnails

---

### Dynamic Image Generation (OG Images)

#### 1. Satori (Vercel)
```bash
npm install satori html2canvas
```

**الاستخدام:**
```typescript
import satori from 'satori';
import { Resvg } from 'resvg-js';

const svg = await satori(
  <div style={{ background: 'white', width: '100%', height: '100%' }}>
    <h1>{title}</h1>
    <p>{description}</p>
    <img src={brandLogo} />
  </div>,
  {
    width: 1200,
    height: 630,
    fonts: [
      {
        name: 'Geist',
        data: fontData,
        weight: 600
      }
    ]
  }
);

const png = new Resvg(svg).render().asPng();
```

**المميزات:**
- ✅ OG images من JSX/React
- ✅ دعم custom fonts
- ✅ سريع جداً
- ✅ بدون headless browser

---

### AI Image Generation (Optional - v1.5+)

#### 1. Replicate (Primary Choice)
```bash
npm install replicate
```

**الاستخدام:**
```typescript
import Replicate from 'replicate';

const replicate = new Replicate({
  auth: process.env.REPLICATE_API_TOKEN
});

// Generate image with Stable Diffusion 3
const output = await replicate.run(
  'stability-ai/stable-diffusion-3',
  {
    input: {
      prompt: 'A modern WordPress theme design, clean and minimal',
      num_outputs: 1
    }
  }
);

// output = ['https://cdn.replicate.com/...image.png']
```

---

#### 2. Flux (Alternative - Better Quality)
```bash
# Not yet on Replicate, but available on other platforms
```

**خصائص Flux:**
- ⭐ أفضل جودة من Stable Diffusion 3
- ⚡ أسرع من DALL-E 3
- 💰 أرخص من DALL-E
- ⚠️ لا يزال في مرحلة بيتا

---

#### 3. Lovealb (Not Recommended)
- ❌ قليل التوثيق
- ❌ API غير مستقرة
- ⏳ غير مدعوم حالياً

---

#### 4. Nanobanana Pro (Not Recommended)
- ❌ غير معروف
- ❌ لا توثيق رسمي
- ⏳ غير مدعوم حالياً

---

### Summary: Tools Selection

```
IMAGE PROCESSING:
├── Sharp (Primary) ✅
└── For edge cases: ImageMagick

VIDEO PROCESSING:
├── FFmpeg (Primary) ✅
└── (Optional: AWS MediaConvert for scale)

OG IMAGE GENERATION:
├── Satori (Primary) ✅
└── (No alternatives needed for v1)

AI IMAGE GENERATION (Optional):
├── Replicate (Primary when enabled) ✅
├── Flux (Future when available)
└── OpenAI DALL-E 3 (Expensive, skip)
```

---

## 📊 Architecture

```
Dashboard / Other Agents
        ↓
    Visual API
        ↓
┌─────────────────────────────┐
│  Visual Production Agent     │
├─────────────────────────────┤
│                             │
│  Task Router                │
│  ├─ Image Optimize          │
│  ├─ Video Convert           │
│  ├─ OG Generate             │
│  ├─ AI Generate             │
│  └─ Upload & Store          │
│                             │
└─────────────────────────────┘
        ↓
┌──────────────────────────────────┐
│   Processing Tools               │
├──────────────────────────────────┤
│ Sharp      → Image compression   │
│ FFmpeg     → Video processing    │
│ Satori     → OG image generation │
│ Replicate  → AI image generation │
│ Vercel Blob→ Storage             │
└──────────────────────────────────┘
        ↓
Redis Event Bus (publish results)
```

---

## 🔌 API Endpoints

### Upload & Optimize Image

```typescript
POST /api/v1/visual/upload
{
  file: File,
  workspace_id: string,
  type: 'theme_screenshot' | 'campaign_asset' | 'article_image',
  optimize: boolean,  // default: true
  create_thumbnail: boolean  // default: true
}

Response:
{
  success: true,
  data: {
    original_url: string,
    webp_url: string,
    thumbnail_url: string,
    metadata: {
      width: number,
      height: number,
      size: number,
      format: string
    }
  }
}
```

### Generate OG Image

```typescript
POST /api/v1/visual/generate-og
{
  workspace_id: string,
  title: string,
  description?: string,
  image_url?: string,
  type: 'article' | 'product' | 'campaign',
  language?: 'en' | 'ar'
}

Response:
{
  success: true,
  data: {
    og_image_url: string,
    og_image_data: {
      width: 1200,
      height: 630,
      format: 'png'
    }
  }
}
```

### Generate Social Images

```typescript
POST /api/v1/visual/generate-social-images
{
  workspace_id: string,
  campaign_id: string,
  base_image_url: string,
  title: string,
  platforms: string[],  // ['facebook', 'instagram', 'tiktok']
  ai_generate?: boolean
}

Response:
{
  success: true,
  data: {
    facebook: {
      url: string,
      size: { width: 1200, height: 628 }
    },
    instagram: {
      square: { url: string, size: { width: 1080, height: 1080 } },
      portrait: { url: string, size: { width: 1080, height: 1350 } }
    },
    tiktok: {
      url: string,
      size: { width: 1080, height: 1920 }
    }
  }
}
```

### Generate Report Assets

```typescript
POST /api/v1/visual/generate-report-assets
{
  workspace_id: string,
  report_id: string,
  charts: Array<{
    type: 'line' | 'bar' | 'pie' | 'area',
    title: string,
    data: any
  }>,
  include_watermark?: boolean
}

Response:
{
  success: true,
  data: {
    chart_images: {
      [chart_id]: string  // URLs
    },
    pdf_url?: string
  }
}
```

---

## 📋 Jobs Queue

### visual_optimize Job

```typescript
interface VisualOptimizeJob extends JobBase {
  type: 'visual_optimize';
  payload: {
    image_url: string,
    target_width?: number,
    target_height?: number,
    quality?: 85,
    format?: 'jpg' | 'webp' | 'png'
  };
}

// Execution
const job = enqueueJob({
  type: 'visual_optimize',
  workspace_id,
  payload: {
    image_url: 'https://...',
    quality: 85,
    format: 'webp'
  }
});
```

### visual_generate_og Job

```typescript
interface VisualGenerateOGJob extends JobBase {
  type: 'visual_generate_og';
  payload: {
    title: string,
    description?: string,
    image_url?: string,
    type: 'article' | 'product' | 'campaign'
  };
}
```

### visual_resize Job

```typescript
interface VisualResizeJob extends JobBase {
  type: 'visual_resize';
  payload: {
    image_url: string,
    sizes: Array<{
      name: string,
      width: number,
      height: number
    }>
  };
}
```

### visual_video_convert Job

```typescript
interface VisualVideoConvertJob extends JobBase {
  type: 'visual_video_convert';
  payload: {
    video_url: string,
    output_format: 'mp4' | 'webm' | 'mov',
    resolution?: '720p' | '1080p' | '4k'
  };
}
```

### visual_ai_generate Job

```typescript
interface VisualAIGenerateJob extends JobBase {
  type: 'visual_ai_generate';
  payload: {
    prompt: string,
    style?: string,
    count: number,
    provider: 'replicate' | 'flux'
  };
}
```

---

## 🔄 Event Bus Integration

### Channels

```typescript
// Domain channel
'events:visual'

// Agent command channel
'agent:visual:commands'

// Agent result channel
'agent:visual:results'
```

### Events

#### ASSET_PROCESS_REQUEST
```typescript
{
  type: 'asset.process_request',
  id: string,
  workspace_id: string,
  asset_id: string,
  asset_url: string,
  process_type: 'optimize' | 'generate_og' | 'resize' | 'ai_generate',
  params: Record<string, any>,
  timestamp: string,
  source_agent: string  // 'marketing-agent', 'content-agent', etc
}
```

#### ASSET_PROCESS_DONE
```typescript
{
  type: 'asset.process_done',
  id: string,
  workspace_id: string,
  asset_id: string,
  process_type: string,
  result_url: string,
  result_urls?: Record<string, string>,  // for multiple outputs
  status: 'success' | 'failed',
  error?: string,
  metadata: {
    processing_time_ms: number,
    file_size: number,
    dimensions: { width, height }
  },
  timestamp: string
}
```

#### OG_GENERATED
```typescript
{
  type: 'og.generated',
  id: string,
  workspace_id: string,
  entity_type: 'article' | 'product' | 'campaign',
  entity_id: string,
  og_image_url: string,
  timestamp: string
}
```

#### IMAGE_OPTIMIZED
```typescript
{
  type: 'image.optimized',
  id: string,
  workspace_id: string,
  original_url: string,
  optimized_url: string,
  webp_url?: string,
  thumbnail_url?: string,
  metadata: {
    original_size: number,
    optimized_size: number,
    compression_ratio: number
  },
  timestamp: string
}
```

#### VIDEO_PROCESSED
```typescript
{
  type: 'video.processed',
  id: string,
  workspace_id: string,
  video_url: string,
  output_url: string,
  format: string,
  duration_seconds: number,
  timestamp: string
}
```

#### VISUAL_ERROR
```typescript
{
  type: 'visual.error',
  id: string,
  workspace_id: string,
  process_type: string,
  asset_id: string,
  error_message: string,
  error_code: string,
  timestamp: string
}
```

---

## ⚙️ Configuration

```typescript
export const visualAgentConfig = {
  enabled: true,

  // Storage
  blob_bucket: 'tashkeel-visual-assets',
  asset_base_url: 'https://blob.vercel-storage.com/...',

  // Image processing
  image: {
    engine: 'sharp',
    max_size_mb: 50,
    allowed_formats: ['jpg', 'png', 'webp', 'gif'],
    compression: {
      quality: 85,
      progressive: true
    },
    generate_webp: true,
    generate_thumbnail: true,
    thumbnail_sizes: [200, 400, 800]
  },

  // Video processing
  video: {
    enabled: true,
    engine: 'ffmpeg',
    max_size_mb: 500,
    allowed_formats: ['mp4', 'webm', 'mov'],
    timeout_seconds: 300,
    ffmpeg_path: process.env.FFMPEG_PATH || 'ffmpeg'
  },

  // OG image generation
  og_generation: {
    enabled: true,
    width: 1200,
    height: 630,
    template: 'modern',
    fonts: {
      primary: 'Geist Sans',
      fallback: 'sans-serif'
    }
  },

  // AI image generation
  ai_generation: {
    enabled: process.env.VISUAL_AI_ENABLED === 'true',
    provider: 'replicate',  // or 'flux'
    model: 'stability-ai/stable-diffusion-3',
    max_images_per_request: 3,
    timeout_seconds: 300
  },

  // Job processing
  jobs: {
    max_concurrent: 5,
    timeout_seconds: 120,
    retry_policy: {
      max_attempts: 3,
      backoff_multiplier: 2
    }
  },

  // Caching
  cache: {
    og_images_ttl: 86400,  // 24 hours
    optimized_images_ttl: 604800  // 7 days
  }
};
```

---

## 🚀 Deployment Checklist

- [ ] FFmpeg installed on production server (or use managed service)
- [ ] Vercel Blob token configured
- [ ] REPLICATE_API_TOKEN set (if AI enabled)
- [ ] FFMPEG_PATH environment variable set
- [ ] Sharp native bindings compiled for Linux (if needed)
- [ ] Temporary directory writable (for FFmpeg processing)
- [ ] Rate limiting configured for upload endpoint
- [ ] File size limits enforced
- [ ] Antivirus scan for uploads (future)
- [ ] CDN cache headers configured

---

## 📈 Performance Targets

| Operation | Target | Actual |
|-----------|--------|--------|
| Image optimize (5MB) | < 2s | TBD |
| Generate OG image | < 1s | TBD |
| Generate social images (4 sizes) | < 3s | TBD |
| Video convert (10MB) | < 30s | TBD |
| AI image generate | < 60s | TBD |

---

## Security Considerations

- ✅ File type validation (whitelist, not blacklist)
- ✅ File size limits
- ✅ Malware scanning (future)
- ✅ No execution of uploaded files
- ✅ Secure temporary file cleanup
- ✅ Rate limiting on upload endpoints
- ✅ Access control by workspace
