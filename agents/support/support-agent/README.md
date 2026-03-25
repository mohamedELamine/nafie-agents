# Support Agent

وكيل دعم ذكي يركّز حاليًا على HelpScout وFacebook ضمن نفس مسار التصنيف والاسترجاع والرد، بينما Phone support ما يزال غير مكتمل wiring بعد.

## Features

- **Primary Flow**: HelpScout webhook -> classify -> retrieve -> answer / escalate
- **Two-Layer Classification**: Intent + Risk analysis using Claude
- **Knowledge Base**: Qdrant-powered retrieval system
- **Smart Escalation**: Automatic escalation when confidence < 0.50
- **Constitutional Principles**: Built-in guidelines for responsible AI
- **Redis Integration**: Emits support updates and escalations through the shared bus

## Architecture

### Nodes

1. **TicketReceiver**: Initializes state and fetches ticket details
2. **IntentClassifier**: Classifies intent using Claude
3. **KnowledgeRetriever**: Retrieves answers from Qdrant based on intent
4. **DisclaimerAdder**: Adds mandatory Arabic disclaimer
5. **RiskFlagger**: Identifies risk factors and overall risk level
6. **TicketUpdater**: Updates ticket in HelpScout
7. **EscalationHandler**: Handles escalated tickets with email notifications

### Constitutional Principles

- **Honesty-First**: Always disclose AI nature in responses
- **HARD_POLICY_GATE**: Escalate billing and legal questions
- **Two-Layer Classification**: Intent + Risk for comprehensive analysis
- **Knowledge-First**: Always use knowledge base for answers

## Installation

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Qdrant 1.6+
- Redis 7+
- Anthropic API key

### Setup

```bash
# Clone repository
git clone <repository-url>
cd support-agent

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

Create a `.env` file with the following configuration:

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=support_agent

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key

# HelpScout
HELPSCOUT_API_KEY=your-helpscout-api-key
HELPSCOUT_APP_ID=your-helpscout-app-id

# Resend (for escalation emails)
RESEND_API_KEY=re_...-...

# Qdrant
QDRANT_URL=http://localhost:6333

# Facebook (optional / partial flow)
META_ACCESS_TOKEN=...

# Application
DEBUG=false
ENVIRONMENT=development
```

## Running the Application

### Run the Agent

```bash
python agents/support/agent.py
```

### Run the API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run Database Migrations

```bash
./db/migrations/run.sh
```

### Current Implementation Notes

- HelpScout and Facebook now share the same triage pipeline.
- Qdrant retrieval now supports OpenAI-compatible embeddings via `OPENAI_API_KEY` or `SUPPORT_EMBEDDING_*`; deterministic embeddings remain only as a local fallback.
- The agent uses Claude, not OpenAI.

## API Endpoints

- `GET /` - Service info
- `GET /health` - Health check
- `POST /webhooks/helpscout` - Handle HelpScout webhooks
- `POST /webhooks/facebook` - Handle Facebook webhooks
- `WS /ws/tickets` - WebSocket for real-time updates

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Type Checking

```bash
mypy agents/support/support-agent/
```

### Linting

```bash
black agents/support/support-agent/
ruff check agents/support/support-agent/
```

## Project Structure

```
support-agent/
├── agents/
│   └── support/
│       └── support-agent/
│           ├── models.py           # Domain models and enums
│           ├── state.py            # State management
│           ├── services/           # Service clients
│           ├── nodes/              # Graph nodes
│           ├── listeners.py        # Event listeners
│           ├── api/                # FastAPI application
│           ├── main.py             # Entry point
│           └── config.py           # Configuration
├── db/                              # Database modules
├── qdrant/                          # Qdrant setup scripts
└── .env.example                     # Environment template
```

## Production Deployment

### Docker Deployment

```bash
docker compose up -d support
```

### Dockerfile

The project includes a `Dockerfile` for containerization. Build and run with:

```bash
docker build -t support-agent .
docker run -d --name support-agent support-agent
```

## Troubleshooting

### Database Connection Issues

Make sure PostgreSQL is running and credentials are correct:

```bash
docker run -d --name postgres \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=support_agent \
  -p 5432:5432 postgres:14
```

### Redis Connection Issues

Make sure Redis is running:

```bash
docker run -d --name redis \
  -p 6379:6379 redis:7-alpine
```

### Qdrant Connection Issues

Make sure Qdrant is running and `QDRANT_URL` points to it:

```bash
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant:latest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details
