# CLAUDE.md

## Project

DevPulse — engineering intelligence dashboard tracking developer activity across GitHub repos. PR/review/cycle-time metrics, team benchmarks, trend analysis, workload balance, collaboration insights, goals, and optional AI analysis.

**Core invariants:**
- AI is off by default; all stats are computed deterministically from raw data
- GitHub is the source of truth for code activity; DevPulse never writes back to GitHub
- Linear is the primary issue/sprint tracker (Jira support planned). `is_primary_issue_source` flag on `integration_config` controls which issue table stats query.
- All synced data cached locally in PostgreSQL
- All backend I/O is async (SQLAlchemy async sessions, httpx.AsyncClient)

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async/asyncpg), Alembic, APScheduler
- **Database:** PostgreSQL 15+
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, shadcn/ui (base-nova), TanStack Query v5, Recharts 3, pnpm
- **Integrations:** GitHub REST API (read-only, App auth), Linear GraphQL API (primary issue tracker), Claude API (on-demand), Slack (bot token)
- **Testing:** pytest + pytest-asyncio, aiosqlite for in-memory test DB
- **Error monitoring:** Nordlabs convention — ErrorClassifier + ErrorReporter → Sentinel

## Architecture

```
React Frontend (Vite :5173)  ──/api proxy──>  FastAPI Backend (:8000)  ──>  PostgreSQL (:5432)
                                                     ↕
                                         GitHub / Linear / Claude APIs
```

### Backend Layout

```
backend/app/
├── api/              # FastAPI routers (thin — delegate to services)
├── models/
│   ├── database.py   # Async engine, session factory, Base, get_db()
│   └── models.py     # All ORM models (36 tables)
├── schemas/schemas.py # All Pydantic request/response models
├── services/         # Business logic (all async, accept AsyncSession as first param)
├── libs/errors.py    # Nordlabs error convention (ErrorCategory, Classifier, Sanitizer, Reporter)
├── logging/          # structlog setup + request context middleware
├── config.py         # pydantic-settings (all env vars)
├── rate_limit.py     # slowapi config
└── main.py           # App factory, CORS, middleware, router registration, APScheduler
```

### Frontend Layout

```
frontend/src/
├── pages/            # Route components (lazy-loaded)
│   ├── insights/     # Workload, Collaboration, Benchmarks, DORA, etc.
│   ├── sync/         # Sync wizard, progress, history
│   ├── ai/           # AI analysis wizard
│   └── settings/     # AI, Slack, Notification settings
├── components/       # UI components, charts/, ui/ (shadcn primitives)
├── hooks/            # TanStack Query hooks
├── utils/            # api.ts (apiFetch), types.ts, format.ts, logger.ts
└── lib/utils.ts      # cn() (clsx + tailwind-merge)
```

**Import alias:** `@/` maps to `src/`.

## Running

```bash
# Docker (recommended)
cp .env.example .env && docker compose up
# Backend: :8000 | Frontend: :3001 | DB: :5432

# Local dev
cd backend && pip install -r requirements.txt && alembic upgrade head && uvicorn app.main:app --reload
cd frontend && pnpm install && pnpm dev

# Tests (SQLite in-memory, no PostgreSQL needed)
cd backend && pip install -r requirements-test.txt && python -m pytest

# Migrations
cd backend && alembic revision --autogenerate -m "description" && alembic upgrade head

# Observability stack (opt-in)
docker compose --profile logging up
```

## Key Patterns

### Backend

- **Auth:** GitHub OAuth → JWT (4h). Roles: `admin` (full), `developer` (own data). `get_current_user()` → `AuthUser`, `require_admin()` → 403. `token_version` on developers invalidates JWTs on role change/deactivation.
- **Service pattern:** All async, `AsyncSession` as first param. Thin API routes delegate to services — no business logic in routes.
- **Upsert pattern:** SELECT by unique key → create if missing → overwrite mutable fields.
- **Date ranges:** `_default_range()` defaults to last 30 days if params are None.
- **Contribution categories:** `code_contributor`, `issue_contributor`, `non_contributor`, `system`. Controls stats inclusion. Roles are admin-configurable via `role_definitions` table.
- **Work categorization cascade:** label rules → issue type rules → title regex/prefix → cross-reference → AI (optional) → "unknown". Manual overrides (`source="manual"`) never overwritten. ReDoS protection on regex rules.
- **Sync:** `SyncContext` threads db/client/sync_event/logger. Per-repo commits + batch commits every 50 PRs. PostgreSQL advisory lock prevents concurrent syncs. Cancellation checked at repo boundaries and every 50-PR batch. `resolve_author()` auto-creates developers from GitHub user data.
- **AI guards:** All AI call sites check feature toggles → budget → cooldown before calling Claude. `AIFeatureDisabledError` → 403, `AIBudgetExceededError` → 429 (handled globally).
- **AI context enrichment:** 1:1 prep (`build_one_on_one_context`) and team health (`build_team_health_context`) include Linear sprint data when an active integration + developer mapping exists. `gather_sprint_context_for_developer()` adds active sprint, recent sprints, triage stats, estimation patterns. `gather_planning_health_context()` adds velocity trend, completion rate, scope creep, triage health, estimation accuracy, work alignment, at-risk projects. Both return `None` gracefully when Linear is not configured.
- **Encryption:** Shared Fernet in `services/encryption.py` for Slack tokens and Linear API keys. Requires `ENCRYPTION_KEY` env var.
- **Issue tracker integration:** Linear is the primary issue tracker. Generic `integration_config` table (type column) designed for future Jira support. Stats functions branch on `get_primary_issue_source()` to query `issues` (GitHub) or `external_issues` (Linear) table. `developer_identity_map` links developers to external system accounts.
- **Collaboration scores:** Materialized post-sync from 5 signals. Canonical pair ordering (`a_id < b_id`).
- **Notifications:** 16 alert types, dedup by `alert_key`, auto-resolution, per-user read/dismiss tracking with optional expiry.
- **Logging:** structlog with `event_type` taxonomy. JSON in prod, console in dev. `LoggingContextMiddleware` injects `request_id`.
- **Error handling:** `libs/errors.py` — classifies all exceptions into 8 categories, only reports `app_bug` to Sentinel after frequency threshold.
- **Rate limiting:** slowapi, default 120/min. Disabled via `RATE_LIMIT_ENABLED=false` in tests.

### Frontend

- **State:** TanStack Query (30s stale, 1 retry). JWT in `localStorage` key `devpulse_token`.
- **Styling:** shadcn/ui base-nova, CSS variables, Lucide icons. `sonner` for toasts.
- **Charts:** Recharts 3, `ResponsiveContainer`, CSS vars for colors, `useId()` for SVG gradient IDs.
- **Error handling:** `ErrorCard` + per-section `ErrorBoundary`. `StatCardSkeleton`/`TableSkeleton` for loading.
- **Code splitting:** All pages lazy-loaded via `React.lazy()`.
- **Nav:** Top nav (Dashboard, Executive, Insights, Goals, Admin dropdown). Insights + Admin use `SidebarLayout`. `isNavActive()` uses prefix matching.
- **Date range:** Global `DateRangeContext` in Layout header, consumed by all pages.
- **Trend deltas:** Current vs previous period. For lower-is-better metrics, green = decrease.

## Architecture Advisory

Consult `docs/architecture/` before adding new tables, routers, or services:

| File pattern | Relevant doc |
|-------------|--------------|
| `models/models.py` | `docs/architecture/DATA-MODEL.md` |
| `models/database.py` | `docs/architecture/SERVICE-LAYER.md` |
| `schemas/schemas.py` | `docs/architecture/API-DESIGN.md` |
| `main.py` | `docs/architecture/OVERVIEW.md` |
| `api/*.py` (new routers) | `docs/architecture/API-DESIGN.md` |
| `services/*.py` (new) | `docs/architecture/SERVICE-LAYER.md` |
| `migrations/versions/*.py` | `docs/architecture/DATA-MODEL.md` |
| `pages/*.tsx` (new pages) | `docs/architecture/FRONTEND.md` |

After structural changes, run `/architect <area>` to update docs.

## Reference Docs

- `docs/API.md` — Complete API reference
- `docs/architecture/` — Architecture documentation
- `DEVPULSE_SPEC.md` — Full technical specification
- `.env.example` + `backend/app/config.py` — All environment variables
