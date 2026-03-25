# Visual Production Agent

Smart visual asset generator for themes. Generates hero images, product cards, and screenshots automatically after theme approval.

## Features

- **Multi-Generator**: Flux for images + Ideogram for Arabic text
- **Quality Gate**: Automatic quality checking before human review
- **Budget Control**: ≤ $2.00 per theme
- **WebP Output**: Optimized image format
- **Human Review**: Mandatory approval before publishing

## Architecture

### Core Principles

1. **THEME_CONTRACT مصدر Prompts الوحيد** - Prompts built from contract data only
2. **Quality Gate قبل المراجعة** - Automatic quality checking
3. **Human Review إلزامي** - No publishing without approval
4. **Budget ≤ $2.00** - Per theme limit
5. **WebP فقط** - Optimized output format

### Workflow

```
[contract_parser] → [budget_calculator] → [prompt_builder] 
    → [multi_generator] → [quality_gate] → [asset_selector] 
    → [post_processor] → [review_gate] → [asset_publisher] 
    → [batch_recorder] → [manifest_builder]
```

### Nodes

- **ContractParser**: Extract domain, cluster, colors, features from contract
- **BudgetCalculator**: Estimate and validate costs
- **PromptBuilder**: Build prompts with 5 layers (base + domain + cluster + style + negative)
- **MultiGenerator**: Parallel Flux + Ideogram generation
- **QualityGate**: Check dimensions, size, quality
- **AssetSelector**: Select best candidates for required types
- **PostProcessor**: Convert to WebP + resize + compress
- **ReviewGate**: Save checkpoint + send review request
- **AssetPublisher**: Upload to storage
- **BatchRecorder**: Save batch manifest
- **ManifestBuilder**: Build final JSON + publish event

## Installation

```bash
# Clone repository
git clone <repository-url>
cd visual-production-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
vim .env
```

### Environment Variables

```env
# API Keys
FLUX_API_KEY=your_flux_api_key
IDEOGRAM_API_KEY=your_ideogram_api_key
CLAUDE_API_KEY=your_claude_api_key
RESEND_API_KEY=re_...-...

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=visual_production

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Storage
STORAGE_PATH=/app/storage
STORAGE_TYPE=local

# Application
DEBUG=false
ENVIRONMENT=development
BUDGET_LIMIT_USD=2.00
```

## Running the Agent

### Development Mode

```bash
python main.py
```

### Production Mode

```bash
# Build Docker image
docker build -t visual-production-agent .

# Run container
docker run -d --name visual-agent \
  -e FLUX_API_KEY=... \
  -e IDEOGRAM_API_KEY=... \
  -p 8000:8000 \
  visual-production-agent
```

## API Endpoints

- `GET /` - Service info
- `GET /health` - Health check
- `POST /review/{batch_key}` - Approve or close a review checkpoint
- `GET /assets/{batch_key}/manifest` - Get asset manifest
- `POST /visual/pipeline` - Manually trigger pipeline

## Event Flow

### Inbound Event

```
THEME_APPROVED → visual_listener → run_visual_pipeline()
```

### Outbound Events

```
VISUAL_REVIEW_REQUESTED → Email to owner
THEME_ASSETS_READY → Publish to asset-events stream after approval
```

## Database Schema

### asset_manifest

- `batch_id` (unique)
- `theme_slug`
- `version`
- `total_cost`
- `status`
- `assets_json` (list of assets)

### asset_assets

- `asset_id`
- `manifest_id` (FK)
- `type`
- `url`
- `dimensions`
- `size_kb`
- `quality_score`
- `status`

### visual_review_queue

- `batch_id` (unique)
- `theme_slug`
- `version`
- `manifest_json`
- `review_decision`
- `reviewed_at`

## Configuration

### Budget Per Theme

- **Hero Image**: $0.02 (Flux)
- **Product Card**: $0.03 (Ideogram with Arabic)
- **Screenshots**: $0.02 each (Flux)
- **Max Total**: $2.00

### Image Specifications

- **Hero Image**: 1920×1080, WebP @85% quality
- **Product Card**: 800×600, WebP @85% quality
- **Screenshots**: 1200×800, WebP @85% quality

### Quality Gate Requirements

- **Dimensions**: ≥ 400×300 pixels
- **Size**: ≤ 2MB
- **Quality**: ≥ 0.5 (heuristic score)

## Production Checklist

- [ ] Configure all API keys
- [ ] Set up PostgreSQL database
- [ ] Configure Redis instance
- [ ] Configure storage backend (local/S3)
- [ ] Set up Resend for email notifications
- [ ] Configure environment variables
- [ ] Test pipeline with sample theme contract
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy for assets
- [ ] Set up SSL/TLS for API

## Troubleshooting

### Budget Exceeded

- Verify FLUX_API_KEY and IDEOGRAM_API_KEY
- Check pricing per image generation
- Adjust BUDGET_LIMIT_USD if needed

### Quality Gate Failures

- Check Flux/Ideogram API responses
- Verify image processing configuration
- Review quality estimation logic

### Storage Issues

- Ensure STORAGE_PATH is writable
- Check disk space
- Verify storage backend configuration

### Database Connection Issues

- Verify PostgreSQL is running
- Check database credentials
- Ensure migration has been run

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Linting

```bash
black agents/visual_production/visual-production-agent/
ruff check agents/visual_production/visual-production-agent/
```

### Type Checking

```bash
mypy agents/visual_production/visual-production-agent/
```

## License

MIT License - see LICENSE file for details
