# Claros Logging & Observability — Portable Spec

This folder contains everything needed to replicate the Claros structured logging and observability system in another project.

## What's Inside

```
logging-export/
├── README.md                  # This file — full implementation guide
├── source/                    # Python source files (copy & rename package)
│   ├── __init__.py            # Package public API
│   ├── logging.py             # configure_logging() + get_logger()
│   ├── middleware.py          # Request context middleware (FastAPI/Starlette)
│   └── audit.py               # Compliance audit event emitter
├── tests/                     # Test suite
│   ├── test_logging.py
│   └── test_audit.py
├── infrastructure/            # Docker log pipeline configs
│   ├── promtail-config.yml    # Log collection + label extraction
│   ├── loki-config.yml        # Log storage (90-day retention)
│   └── prometheus.yml         # Metrics scraping (cAdvisor + Loki)
└── pyproject.toml             # Dependencies reference
```

---

## Architecture Overview

```
App stdout (JSON logs)
  → Docker JSON log driver
    → Promtail (Docker SD, JSON extraction, label promotion)
      → Loki (append-only, 90-day retention)
        → Grafana (LogQL dashboards)
```

All logging goes to **stdout** as structured JSON. No file appenders, no syslog. Containers collect stdout natively; Promtail ships it to Loki.

---

## Stack

| Layer              | Technology           | Purpose                          |
|--------------------|----------------------|----------------------------------|
| Structured logging | structlog (Python)   | JSON log output, context binding |
| Log collection     | Promtail             | Docker SD, field extraction      |
| Log storage        | Grafana Loki         | Append-only, 90-day retention    |
| Dashboards         | Grafana              | LogQL queries                    |
| Metrics            | Prometheus + cAdvisor | Container resource metrics       |

---

## Step-by-Step Implementation

### 1. Install the Package

Only runtime dependency is `structlog>=24.1`. Copy the `source/` folder into your project and rename the package (e.g., `myproject_observability`).

```toml
# pyproject.toml
dependencies = ["structlog>=24.1"]

[project.optional-dependencies]
otel = [
    "opentelemetry-api>=1.22",
    "opentelemetry-sdk>=1.22",
    "opentelemetry-exporter-otlp>=1.22",
]
```

### 2. Configure Logging at Startup

Call `configure_logging()` at **module level** in your app's entrypoint — before any logger is created:

```python
import os
from myproject_observability import configure_logging, get_logger

configure_logging(
    json_output=os.getenv("LOG_FORMAT") == "json",  # JSON in prod, console in dev
    level=os.getenv("LOG_LEVEL", "INFO"),
)

log = get_logger(__name__)
```

**Processor chain** (order matters):

| # | Processor | What it does |
|---|-----------|-------------|
| 1 | `merge_contextvars` | Injects request-scoped fields (request_id, method, path) into every log line |
| 2 | `add_log_level` | Adds `level` field |
| 3 | `StackInfoRenderer` | Renders stack traces when present |
| 4 | `TimeStamper(fmt="iso")` | Adds ISO 8601 `timestamp` field |
| 5 | `JSONRenderer` or `ConsoleRenderer` | JSON for prod, pretty-print for dev |

The `merge_contextvars` processor is the **key architectural decision** — it means any log statement anywhere in the request lifecycle automatically carries request context without explicit parameter threading.

### 3. Add the Request Context Middleware

Register `LoggingContextMiddleware` as the **innermost** middleware (closest to your route handlers):

```python
from myproject_observability.middleware import LoggingContextMiddleware

app = FastAPI()
# Other middleware first (CORS, rate limiting, etc.)
app.add_middleware(LoggingContextMiddleware)
```

What it does per request:
1. Generates an 8-char UUID prefix as `request_id`
2. Clears contextvars and binds `request_id`, `method`, `path`
3. After response, emits `request.completed` with `status` and `duration_ms`
4. Sets `X-Request-ID` response header

This single middleware gives you automatic request tracing across all log statements.

### 4. Use the Logger

```python
from myproject_observability import get_logger

log = get_logger(__name__)

# Always use keyword arguments for structured fields
log.info("Document indexed", event_type="business.entity_created", doc_id=str(doc_id), org_id=org_id)
log.warning("Rate limit near threshold", event_type="system.rate_limit", org_id=org_id, current=count)
log.error("Provider timeout", event_type="ai.timeout", provider="anthropic", duration_ms=5200)
```

### 5. Adopt the Event Type Taxonomy

Every log call should include an `event_type` keyword argument. Four namespaces:

| Namespace      | Use for                        | Examples                                                          |
|----------------|--------------------------------|-------------------------------------------------------------------|
| `system.*`     | Infrastructure, startup, errors | `system.startup`, `system.shutdown`, `system.db_error`            |
| `security.*`   | Auth, RBAC, access events       | `security.login_failed`, `security.role_denied`                   |
| `business.*`   | Domain entity operations        | `business.entity_created`, `business.entity_updated`              |
| `ai.*`         | LLM/AI operations               | `ai.embedding`, `ai.completions`, `ai.embedding_failed`          |

For compliance audit trails, use `audit.*` via the dedicated emitter (see next section).

### 6. Wire Up Audit Events

For any create/update/delete on important entities, emit a compliance audit event:

```python
from myproject_observability import emit_audit_event

emit_audit_event(
    event_type="audit.document.created",
    actor_id=user.sub,
    actor_email=user.email,
    org_id=org_id,
    entity_type="document",
    entity_id=str(doc_id),
    action="created",
    app="myapp",
    metadata={"title": body.title},
)
```

**Design rules:**
- All keyword-only arguments (no positional args)
- **Never raises** — entire body wrapped in `try/except`. Audit failures must never block user operations
- Uses dedicated logger name (`<project>.audit`) for Loki filtering
- Optional fields emit as `null`, never omitted — consistent JSON shape
- `entity_id` auto-cast to `str` (accepts UUIDs)

**SOC 2 field mapping** (CC6.1/CC7.2):
- **Who**: `actor_id`, `actor_email`, `actor_role`
- **What**: `entity_type`, `entity_id`, `action`, `event_type`
- **Where**: `app`, `org_id`
- **When**: auto-added by structlog `TimeStamper`
- **Context**: `metadata`, `ip_address`, `request_id`

### 7. Production JSON Log Shape

In production (`LOG_FORMAT=json`), every log line is a single JSON object on stdout:

```json
{
  "event": "request.completed",
  "level": "info",
  "timestamp": "2026-03-31T12:00:00.123456Z",
  "request_id": "a3f2c1b4",
  "method": "POST",
  "path": "/api/documents",
  "status": 201,
  "duration_ms": 42.3,
  "event_type": "system.http",
  "org_id": "uuid-here"
}
```

Audit events include additional fields:

```json
{
  "event": "audit.document.created",
  "level": "info",
  "timestamp": "2026-03-31T12:00:00.123456Z",
  "event_type": "audit.document.created",
  "actor_id": "user-uuid",
  "actor_email": "alice@example.com",
  "actor_role": "admin",
  "org_id": "org-uuid",
  "entity_type": "document",
  "entity_id": "doc-uuid",
  "action": "created",
  "app": "myapp",
  "metadata": {"title": "Q1 Report"},
  "ip_address": null,
  "request_id": "a3f2c1b4"
}
```

### 8. Deploy the Log Pipeline

#### Promtail

Copy `infrastructure/promtail-config.yml` and adjust the container name regex to match your services. Key design decisions:

- `level` and `event_type` are promoted to **Loki labels** (indexed, fast filtering)
- `org_id` stays as a **parsed field only** — avoids high-cardinality label explosion in multi-tenant deployments
- Query org-specific logs with: `{event_type=~"audit\\..*"} | json | org_id="<uuid>"`

#### Loki

Copy `infrastructure/loki-config.yml`. Defaults:
- TSDB index, filesystem storage
- 90-day retention (`retention_period: 2160h`)
- 10 MB/s ingestion, 20 MB/s burst
- Single-node (scale up by switching to S3 + memberlist ring)

#### Grafana Dashboards

Build four dashboards using LogQL:

| Dashboard | Key queries |
|-----------|-------------|
| **App Health** | `{service=~"$app"} \| json \| status >= 500` for 5xx rate; `unwrap duration_ms` from `request.completed` for p95 latency |
| **Business Metrics** | `{event_type=~"ai\\..*"}` for AI call counts; `{event_type=~"audit\\..*"}` for audit volume |
| **Database Health** | cAdvisor container CPU/memory/network via Prometheus |
| **Rate Limiting** | Redis rate limit hit/miss counters |

### 9. Full main.py Integration Example

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from myproject_observability import configure_logging, get_logger
from myproject_observability.middleware import LoggingContextMiddleware

configure_logging(
    json_output=os.getenv("LOG_FORMAT") == "json",
    level=os.getenv("LOG_LEVEL", "INFO"),
)
log = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting up", event_type="system.startup")
    yield
    log.info("Shutting down", event_type="system.shutdown")

def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.add_middleware(LoggingContextMiddleware)
    return app

app = create_app()
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_FORMAT` | (unset) | Set to `json` for production JSON output |
| `LOG_LEVEL` | `INFO` | Python log level: DEBUG, INFO, WARNING, ERROR |

---

## Checklist

- [ ] Copy `source/` and rename package to `<yourproject>_observability`
- [ ] Update the audit logger name in `audit.py` (change `claros.audit` to `<yourproject>.audit`)
- [ ] Call `configure_logging()` at module level in each service entrypoint
- [ ] Add `LoggingContextMiddleware` as the innermost middleware
- [ ] Adopt `event_type` taxonomy on all log calls (`system.*`, `security.*`, `business.*`, `ai.*`)
- [ ] Wire `emit_audit_event()` into all create/update/delete endpoints
- [ ] Deploy Promtail with Docker SD and JSON extraction
- [ ] Deploy Loki with 90-day retention
- [ ] Build Grafana dashboards using `request.completed` events as primary data source
