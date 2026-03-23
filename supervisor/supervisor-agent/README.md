# Supervisor Agent

Supervisor agent for coordinating large-scale workflows with event-driven architecture, conflict resolution, and health monitoring.

## Features

- **Event-Driven Architecture**: All communication via Redis Pub/Sub + Streams
- **Multi-Agent Coordination**: Orchestrate 8 specialized agents
- **Conflict Resolution**: Automatic detection and resolution
- **Health Monitoring**: Real-time agent health checks
- **Policy Enforcement**: Budget, quality, and rate limiting policies
- **Audit Logging**: Complete transaction history (append-only)
- **State Machine**: Explicit workflow transitions

## Architecture

### Core Components

1. **Agent Registry**: Central registry of all available agents with criticality levels and degraded fallback modes
2. **Workflow Orchestrator**: Manages multi-step workflows with state machine transitions
3. **Conflict Resolver**: Detects and resolves signal contradictions, budget conflicts, dependency failures
4. **Health Monitor**: Periodic health checks with degraded mode application
5. **Policy Enforcer**: Validates and enforces budget, quality, and rate policies

### Workflows

- **Theme Launch**: builder → visual → platform → [support || marketing || analytics]
- **Theme Update**: builder → [visual?] → platform
- **Seasonal Campaign**: marketing → [content || analytics]
- **System Recovery**: health_check → apply_degraded → notify_owner
- **Batch Content**: content → [support KB update]

### Constitutional Principles

1. **Not Single Point of Failure**: Agents work independently, supervisor only coordinates
2. **Agent Registry Truth**: No hardcoded agent knowledge
3. **Explicit State Machine**: Strict transition rules
4. **Event-Based Authority**: No direct function calls
5. **Complete Audit Log**: Every action logged permanently
6. **User Locked Decisions**: Protected domains (pricing, product deletion, crisis response, campaign stop, budget change)
7. **Defined Degradation Policy**: No blind fallbacks
8. **Limited Self-Healing**: Detect and notify, implement fallback
9. **Graceful Redis Failure**: Local logging + immediate owner notification

## Installation

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Redis 7+
- Resend account for email alerts

### Setup

```bash
# Clone repository
git clone <repository-url>
cd supervisor/supervisor-agent

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
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/supervisor

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Resend (for alerts)
RESEND_API_KEY=re_...-...

# Owner contact
OWNER_EMAIL=admin@yourdomain.com

# Heartbeat settings
HEARTBEAT_TIMEOUT_SEC=120
HEALTH_CHECK_INTERVAL_SEC=60

# Application
DEBUG=false
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## Running the Agent

### Development Mode

```bash
python main.py
```

### Production Mode

```bash
# Build Docker image
docker build -t supervisor-agent .

# Run container
docker run -d --name supervisor-agent \
  -e DATABASE_URL=postgresql://postgres:postgres@localhost:5432/supervisor \
  -e RESEND_API_KEY=... \
  -e OWNER_EMAIL=... \
  -p 8000:8000 \
  supervisor-agent
```

### Run Database Migrations

```bash
psql -U postgres -d supervisor < db/migrations/001_supervisor_tables.sql
```

## API Endpoints

- `GET /` - Service info
- `GET /health` - Health check
- `GET /workflows` - List active workflows
- `GET /workflows/{instance_id}` - Get workflow details
- `POST /workflows` - Start new workflow
- `DELETE /workflows/{instance_id}` - Cancel workflow
- `GET /agents/health` - Get all agent health
- `GET /audit` - Audit log with filters
- `GET /policies` - Get active policies
- `PUT /policies/{policy_id}` - Update policy

## Database Schema

### workflow_instances
- instance_id (PK)
- workflow_type
- business_key (unique)
- theme_slug
- current_step, total_steps
- status
- started_at, completed_at
- failed_step, failure_reason
- retry_count
- context (JSONB)
- step_history

### supervisor_audit_log
- log_id (PK)
- category
- action
- target
- workflow_id
- correlation_id
- details (JSONB)
- outcome
- created_at

### conflict_records
- conflict_id (PK)
- conflict_type
- agents_involved (TEXT array)
- description
- resolution
- resolved_at
- escalated
- created_at

### agent_health
- agent_name (PK)
- status
- last_heartbeat
- queue_depth, active_jobs
- error_rate
- mode
- last_checked
- issues (TEXT array)

### policy_rules
- policy_id (PK)
- rule_type
- condition (JSONB)
- action
- value
- active
- created_at
- expires_at

### override_log
- override_id (PK)
- supervisor_decision
- overridden_agent
- original_signal (JSONB)
- override_reason
- applied_at
- outcome

## Error Codes

- `SUP_001`: Agent not registered
- `SUP_101`: Invalid workflow transition
- `SUP_102`: Workflow already terminal
- `SUP_103`: Workflow business key exists (idempotency)
- `SUP_201`: Conflict unresolvable
- `SUP_301`: User locked decision attempted
- `SUP_401`: Heartbeat timeout
- `SUP_402`: Agent health critical
- `SUP_501`: Redis failure
- `SUP_601`: Policy enforcement failed

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Linting

```bash
black agents/supervisor-agent/
ruff check agents/supervisor-agent/
```

### Type Checking

```bash
mypy agents/supervisor-agent/
```

## Configuration

### User Locked Decisions (Protected Domains)

- `pricing` - Product pricing
- `product_deletion` - Product deletion
- `targeting_change` - Targeting changes
- `crisis_response` - Crisis response
- `campaign_stop` - Campaign stop
- `budget_change` - Budget changes

### Available Agents

| Agent | Criticality | Role |
|-------|-------------|------|
| builder | HIGH | Theme builder |
| visual_production | HIGH | Visual assets |
| platform | CRITICAL | Platform deployment |
| support | HIGH | Support operations |
| content | MEDIUM | Content creation |
| marketing | MEDIUM | Marketing campaigns |
| analytics | MEDIUM | Analytics tracking |
| visual_audio | LOW | Visual/audio assets |

### Default Policies

- `daily_visual_budget`: Limit visual production to $10/day
- `daily_theme_limit`: Max 3 themes per day
- `api_cost_critical`: Alert at $100/day
- `quality_threshold`: Block launch if quality < 70%

## Troubleshooting

### Database Connection Issues

```bash
# Verify PostgreSQL is running
pg_isready -h localhost -p 5432

# Create database
psql -U postgres -c "CREATE DATABASE supervisor;"

# Run migrations
psql -U postgres -d supervisor < db/migrations/001_supervisor_tables.sql
```

### Redis Connection Issues

```bash
# Verify Redis is running
redis-cli ping

# Check consumer groups
redis-cli XGROUP CREATE streams:supervisor_events supervisor 0
```

### Agent Health Issues

- Check `agents/health` endpoint
- Verify HEARTBEAT events from agents
- Check agent registry entries

## License

MIT License - see LICENSE file for details
