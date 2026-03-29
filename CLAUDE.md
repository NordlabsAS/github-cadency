# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

DevPulse — an engineering intelligence dashboard that tracks developer activity across GitHub repositories for an organization. Provides PR/review/cycle-time metrics, team benchmarks, trend analysis, workload balance, collaboration insights, developer goals, and optional on-demand AI analysis via Claude API.

**Core invariants:**
- AI is off by default; all stats are computed deterministically from raw data
- GitHub is the single source of truth; DevPulse is read-only (never writes back to GitHub)
- All GitHub data is cached locally in PostgreSQL to handle rate limits
- All backend I/O is async (SQLAlchemy async sessions, httpx.AsyncClient)

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async with asyncpg), Alembic migrations
- **Database:** PostgreSQL 15+ (async via asyncpg)
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, shadcn/ui (base-nova style), TanStack Query v5, Recharts 3, pnpm
- **GitHub integration:** REST API via httpx, GitHub App auth (JWT + installation tokens)
- **AI:** Anthropic Claude API (claude-sonnet-4-0), on-demand only
- **Scheduling:** APScheduler AsyncIOScheduler (in-process, configured in FastAPI lifespan)
- **Testing:** pytest + pytest-asyncio (backend), aiosqlite for in-memory test DB

## Architecture

```
React Frontend (Vite :5173)  ──/api proxy──>  FastAPI Backend (:8000)  ──>  PostgreSQL (:5432)
                                                     ↕
                                              GitHub REST API (read-only)
                                                     ↕
                                              Claude API (on-demand AI analysis)
```

**Data flow:** GitHub App auth (JWT → installation token) → Scheduled sync fetches repos/PRs/reviews/issues → Webhooks for real-time updates → Stats service computes metrics on-demand → AI analysis optional.

### Backend Layout

```
backend/app/
├── api/              # FastAPI routers (thin delegation to services)
│   ├── auth.py, oauth.py        # JWT validation, GitHub OAuth
│   ├── developers.py, stats.py  # Team registry (CRUD + deactivation impact), all stats/benchmarks/trends/workload
│   ├── goals.py, sync.py        # Goals CRUD, sync trigger/status/cancel/detail
│   ├── relationships.py         # Developer relationships, org tree, works-with, over-tagged, communication scores
│   ├── webhooks.py              # GitHub webhook receiver (HMAC-verified)
│   └── ai_analysis.py           # AI analysis + 1:1 prep + team health
├── models/
│   ├── database.py   # Async engine, session factory, Base, get_db()
│   └── models.py     # All SQLAlchemy ORM models
├── schemas/schemas.py # All Pydantic request/response models and enums
├── services/
│   ├── github_sync.py    # GitHub App auth, rate limiting, upsert helpers, sync orchestration
│   ├── stats.py          # All metrics: developer, team, repo, benchmarks, trends, workload
│   ├── collaboration.py  # Collaboration matrix + insights (silos, bus factors, isolation)
│   ├── enhanced_collaboration.py  # Multi-signal collaboration scoring, works-with, over-tagged, communication scores
│   ├── relationships.py  # Developer relationship CRUD + org tree builder
│   ├── goals.py          # Goal CRUD, metric computation, auto-achievement
│   ├── risk.py           # PR risk scoring: per-PR assessment, team risk summary
│   ├── ai_analysis.py    # Claude API integration, 1:1 prep briefs, team health checks
│   ├── work_category.py  # Work categorization: label/title/AI classification
│   └── ai_settings.py    # AI feature toggles, budget, pricing, cooldown, usage tracking
├── config.py         # pydantic-settings: all env vars (see also .env.example)
└── main.py           # FastAPI app factory, CORS, router registration, APScheduler
```

### Frontend Layout

```
frontend/src/
├── pages/            # Route components (Dashboard, TeamRegistry, DeveloperDetail, Repos, etc.)
│   ├── insights/     # Insights sub-pages (Workload, Collaboration, Benchmarks, IssueQuality, OrgChart, etc.)
│   ├── sync/         # Sync wizard, progress, history, detail (SyncPage, SyncWizard, SyncDetailPage, SyncProgressView, etc.)
│   └── settings/     # Settings pages (AISettings)
├── components/
│   ├── Layout.tsx    # Sticky header, top nav (Dashboard, Executive, Team, Insights, Goals, Admin dropdown), date range picker
│   ├── SidebarLayout.tsx # Sidebar navigation for section groups (Insights, Admin)
│   ├── StatCard.tsx, StatCardSkeleton.tsx, TableSkeleton.tsx, ErrorCard.tsx, ErrorBoundary.tsx
│   ├── StalePRsSection.tsx, GoalCreateDialog.tsx, DeactivateDialog.tsx, DateRangePicker.tsx
│   ├── RelationshipsCard.tsx  # Relationship display/edit (reports_to, tech_lead, team_lead) on DeveloperDetail
│   ├── WorksWithSection.tsx   # Top collaborators with multi-signal score breakdown on DeveloperDetail
│   ├── ai/           # AI result renderers (AnalysisResultRenderer, OneOnOnePrepView, etc.)
│   ├── charts/       # TrendChart, PercentileBar, ReviewQualityDonut, GoalSparkline
│   └── ui/           # shadcn/ui primitives
├── hooks/            # TanStack Query hooks (useAuth, useDevelopers, useStats, useSync, useAI, useAISettings, useGoals, useDateRange, useRelationships)
├── utils/            # api.ts (apiFetch wrapper + ApiError class), types.ts (TS interfaces)
└── lib/utils.ts      # cn() utility (clsx + tailwind-merge)
```

**Import alias:** `@/` maps to `src/` (configured in vite.config.ts and tsconfig).

## Database Schema (18 tables)

| Table | Purpose |
|-------|---------|
| `developers` | Team registry with GitHub username, role, team, skills, app_role |
| `repositories` | GitHub repos with tracking toggle, default branch, tree truncation flag |
| `pull_requests` | PRs with pre-computed cycle times, approval tracking, issue linkage, head_sha, author_github_username for backfill |
| `pr_reviews` | Reviews with quality tier classification, reviewer_github_username for backfill |
| `pr_review_comments` | Inline code review comments with type classification |
| `pr_files` | File-level changes per PR (filename, additions, deletions, status) |
| `pr_check_runs` | CI/CD check runs per PR (name, conclusion, duration, attempt) |
| `repo_tree_files` | Full repo file tree snapshot for stale directory detection |
| `issues` | Issues with close-time computation, quality scoring, assignee_github_username for backfill |
| `issue_comments` | Issue comment bodies |
| `sync_events` | Sync run audit log with per-repo progress, granular step tracking, cancellation, resumability, structured errors, log_summary |
| `ai_analyses` | AI analysis results (JSONB) with split token tracking + cost |
| `ai_settings` | Singleton (id=1) AI feature toggles, budget, pricing config |
| `ai_usage_log` | Token usage tracking for work categorization AI calls |
| `deployments` | DORA deployment records from GitHub Actions workflow runs |
| `developer_goals` | Goal tracking with metric targets + `created_by` (self/admin) |
| `developer_relationships` | Org hierarchy: reports_to, tech_lead_of, team_lead_of (generic relationship table) |
| `developer_collaboration_scores` | Materialized multi-signal collaboration scores per developer pair per period |

**Key design decisions:**
- Author/reviewer FKs are **nullable** — but `resolve_author()` auto-creates developers from embedded GitHub user data during sync. Raw usernames stored in `author_github_username`/`reviewer_github_username`/`assignee_github_username` columns for efficient backfill. `resolve_author()` also auto-reactivates inactive developers found in GitHub activity (flush + warning log).
- PR cycle-time fields pre-computed at sync time; issue has `time_to_close_s`
- JSONB columns: `skills`, `labels`, `errors`, `result`, `closes_issue_numbers`, `repos_completed`, `repos_failed`, `log_summary`, `repo_ids`
- `developer_goals.created_by` — `"self"` or `"admin"`; developers can only modify their own self-created goals
- `developer_relationships` uses generic `(source_id, target_id, relationship_type)` — supports multiple concurrent relationships (e.g., Alice reports to Bob and has Carol as tech lead)
- `developer_collaboration_scores` uses canonical pair ordering (`a_id < b_id`) to avoid duplicates. Materialized post-sync from 5 signals: PR reviews, co-repo authoring, issue co-comments, @mentions, co-assignment. Weights: reviews 0.35, issue comments 0.20, co-repos 0.15, mentions 0.15, co-assigned 0.15
- `mentions` JSONB on `pr_review_comments` and `issue_comments` — extracted at sync time via `extract_mentions()` regex, same pattern as `classify_comment_type()`
- No commit-level data — stats are PR-level only to stay within GitHub rate limits

## Running

### Docker (recommended)
```bash
cp .env.example .env   # edit with your values
docker compose up
```
Backend: http://localhost:8000 | Frontend: http://localhost:3001 | DB: localhost:5432

### Local development
```bash
# Backend
cd backend && pip install -r requirements.txt && alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend && pnpm install && pnpm dev
```

### Migrations & tests
```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
pip install -r requirements-test.txt
python -m pytest                    # all tests (SQLite in-memory, no PostgreSQL needed)
python -m pytest tests/unit/        # unit tests only
```

## Key Patterns and Conventions

### Backend
- **Auth:** GitHub OAuth → JWT (7-day expiry). Roles: `admin` (full access), `developer` (own data only). `get_current_user()` → `AuthUser`, `require_admin()` → 403. Per-endpoint injection for mixed-access routers.
- **Thin API routes:** Validate input, delegate to service functions — no business logic in routes
- **Service functions:** All async, accept `AsyncSession` as first param
- **Upsert pattern:** SELECT by unique key → create if not found → always overwrite mutable fields
- **Date range defaulting:** `_default_range()` — defaults to last 30 days if params are None
- **Review quality tiers:** `classify_review_quality()` pure function at sync time, recomputed after review comments via `recompute_review_quality_tiers()`. Tiers: thorough, standard, rubber_stamp, minimal.
- **Comment type classification:** `classify_comment_type()` keyword-based: nit, blocker, architectural, question, praise, suggestion, general (default)
- **Percentile band inversion:** For lower-is-better metrics, `_percentile_band()` inverts labels so `above_p75` always means "best"
- **Trend regression:** Simple OLS `_linear_regression()` with polarity-aware direction; <5% change = "stable"
- **Draft PR filtering:** `PullRequest.is_draft.isnot(True)` excludes drafts from open counts, workload, stale alerts, deactivation impact
- **Developer deactivation:** `is_active` toggle via `PATCH /developers/{id}` (admin). `GET /developers/{id}/deactivation-impact` returns open PRs/issues/branches. `POST /developers` returns structured 409 `{code: "inactive_exists", developer_id, display_name}` when username exists but is inactive. `DELETE` remains as soft-delete for junk accounts. Sync auto-reactivates inactive devs with warning log. Frontend: active/inactive tabs on Team Registry, `DeactivateDialog` with impact preview, inactive badge on DeveloperDetail.
- **Workload score:** `total_load = open_authored + open_reviewing + open_issues`. Thresholds: low(0), balanced(1-5), high(6-12), overloaded(>12)
- **PR risk scoring:** Pure `compute_pr_risk()` in `services/risk.py`, 10 weighted factors, score 0-1. Levels: low/medium/high/critical
- **AI guards:** All AI call sites check feature toggles → budget → cooldown before calling Claude. `ai_settings` singleton controls everything.
- **Work categorization:** Label map → title regex → "unknown". Optional AI batch classification. Categories: feature, bugfix, tech_debt, ops, unknown.
- **Sync architecture:** `SyncContext` dataclass threads db/client/sync_event/logger through the sync chain. Per-repo `db.commit()` after each repo + batch commits every 50 PRs within large repos. JSONB columns mutated via `_append_jsonb()` helper (reassigns to trigger SQLAlchemy change detection). Rollback+merge pattern on per-repo failure preserves log_summary. Structured errors via `make_sync_error()`. Retry with exponential backoff on 502/503/504.
- **Sync granular progress:** `current_step` tracks the active phase within a repo (fetching_prs, processing_prs, fetching_issues, processing_issues, processing_issue_comments, syncing_file_tree, fetching_deployments). `current_repo_prs_total/done` and `current_repo_issues_total/done` provide item-level progress. Progress commits every 10 items; cleared between repos via `_clear_repo_progress()`.
- **Sync cancellation:** `cancel_requested` flag on `SyncEvent`, checked by `_check_cancel()` at repo boundaries and every 50-PR batch. Raises `SyncCancelled` → status becomes `"cancelled"` + `is_resumable=True`. `POST /sync/cancel` sets the flag; `POST /sync/force-stop` force-marks a stale sync as cancelled.
- **Sync API:** `POST /sync/start`, `POST /sync/resume/{id}`, `POST /sync/cancel`, `POST /sync/force-stop`, `POST /sync/contributors`, `GET /sync/status`, `GET /sync/events/{id}`, `GET /sync/events`, `POST /sync/discover-repos`, `GET /sync/repos`, `PATCH /sync/repos/{id}/track`. Concurrency guard (409). Scheduler uses `scheduled_sync()` wrapper.
- **Contributor sync:** `sync_org_contributors()` fetches `GET /orgs/{org}/members` and upserts developers. Runs automatically at start of every `run_sync()`, and standalone via `POST /sync/contributors`. Standalone contributor sync creates a `SyncEvent(sync_type="contributors")` for progress tracking and concurrency — visible via `GET /sync/status` and in sync history. Uses `repos_synced` to store new developer count. `resolve_author()` auto-creates developers from PR/review/issue user data during upsert; also auto-reactivates inactive developers found in GitHub activity (flush + warning log). `sync_org_contributors()` similarly reactivates inactive org members. `backfill_author_links()` bulk-updates NULL author/reviewer/assignee FKs using stored github usernames with EXISTS guard. Separate commits for resilience.
- **Sync statuses:** `started` → `completed` | `completed_with_errors` | `failed` | `cancelled`. `is_resumable=True` when failed/partial/cancelled.
- **Sync logging:** `log_summary` JSONB capped at 500 entries with priority eviction (drops oldest info first). Verbose per-step entries: "Fetching PRs", "Found N PRs", "Processed X/Y PRs", step markers for issues/comments/tree/deployments.
- **@Mention extraction:** `extract_mentions()` regex runs at sync time in `upsert_review_comment()` and `upsert_issue_comment()`. Populates `mentions` JSONB column. Zero extra API calls.
- **Collaboration recomputation:** `recompute_collaboration_scores()` runs post-sync after backfill. Non-blocking — if it fails, sync still completes. Materializes scores into `developer_collaboration_scores`.
- **Developer relationships:** Generic `developer_relationships` table with `set_relationship()` / `remove_relationship()` service functions. Org tree built from `reports_to` relationships. Types: `reports_to`, `tech_lead_of`, `team_lead_of`.
- **Over-tagged detection:** Flags developers whose combined PR/issue tag rate exceeds team avg + 1.5 stddev or 50% absolute. Severity: mild/moderate/severe.
- **Communication score:** [0-100] per developer from 4 components (25pts each): review engagement, comment depth, reach, responsiveness. Computed on-demand.
- **Relationships API:** `GET/POST/DELETE /developers/{id}/relationships`, `GET /org-tree`, `GET /developers/{id}/works-with`, `GET /stats/over-tagged`, `GET /stats/communication-scores`.

### Frontend
- **Global date range:** `DateRangeContext` set in Layout header, consumed by all pages
- **Server state:** TanStack Query with 30s stale time, 1 retry
- **Auth:** JWT in `localStorage` key `devpulse_token`, injected by `apiFetch()`. Auto-redirect to `/login` on 401.
- **API proxy:** Vite dev server proxies `/api/*` → `http://localhost:8000`
- **Component library:** shadcn/ui with base-nova style, neutral base color, CSS variables, Lucide icons
- **Charts:** Recharts 3 in `components/charts/`. Use `ResponsiveContainer`, CSS variables for colors, `useId()` for unique SVG gradient IDs
- **Trend deltas:** Frontend compares current vs previous period. For lower-is-better metrics, green = decrease
- **Toast notifications:** `sonner` (bottom-right, 4s auto-dismiss). All mutations wrapped with success/error toasts.
- **Error/loading:** `ErrorCard` + `ErrorBoundary` for errors. `StatCardSkeleton` + `TableSkeleton` for loading.
- **AI result rendering:** `AnalysisResultRenderer` switches on `analysis_type` → structured view. Colors: green (positive), amber (attention), red (concern).
- **Nav structure:** Top nav has 4 links + Admin dropdown. Insights (`/insights/*`) and Admin (`/admin/*`) sections render with `SidebarLayout` (sticky left sidebar + content). Admin group: Team (`/admin/team`), Repos (`/admin/repos`), Sync (`/admin/sync`), AI Analysis (`/admin/ai`), AI Settings (`/admin/ai/settings`). `isNavActive()` uses prefix matching for section links. Bare section URLs redirect to first sub-page. `/team` redirects to `/admin/team`; `/team/:id` (developer detail) remains top-level.
- **Contributor sync progress:** Team Registry page polls `useSyncStatus()` and shows a progress banner when `sync_type === "contributors"` is active. Completion banner (success/failure) fades after 10s via `useRef` transition detection. Developer list auto-refreshes on sync completion. Button disabled when any sync is active.
- **Developer deactivation UI:** Team Registry has Active/Inactive toggle tabs. Active tab: Edit + Deactivate buttons per row. Deactivate opens `DeactivateDialog` which fetches `GET /developers/{id}/deactivation-impact` to show open PRs, issues, and branches before confirming. Inactive tab: dimmed rows with Reactivate button. Creating a developer with an inactive username triggers structured 409 caught via `ApiError` with reactivation prompt. `DeveloperDetail` shows "Inactive" badge when `is_active=false`.
- **Sync detail page:** `/admin/sync/:id` — `SyncDetailPage` shows live progress (reuses `SyncProgressView`), per-repo result cards, errors, filterable log. `useSyncEvent(id)` hook with adaptive polling (3s when active, stops when done). `SyncProgressView` renders a simpler view for `sync_type === "contributors"` (no repo progress bars, no cancel button).
- **Sync log filtering:** `SyncLogViewer` supports level filter (All/Info/Warn/Error), repo dropdown, auto-scroll toggle. Used in both `SyncProgressView` and `SyncDetailPage`.
- **Batch developer stats:** `useAllDeveloperStats()` uses `useQueries` for parallel fetch, cache-shared with `useDeveloperStats`.
- **Relationships card:** `RelationshipsCard` on DeveloperDetail shows reports_to/tech_lead/team_lead with add/remove dialogs (admin only). Uses `useRelationships`, `useCreateRelationship`, `useDeleteRelationship` hooks.
- **Works With section:** `WorksWithSection` on DeveloperDetail shows top 8 collaborators with multi-signal score breakdown. Uses `useWorksWith` hook.
- **Org Chart page:** `/insights/org-chart` — tree visualization from `useOrgTree`. Expandable nodes, "not in hierarchy" section. Added to Insights sidebar.
- **AI settings page:** `/admin/ai/settings` admin-only page with master switch, per-feature toggle cards, budget config, pricing config, usage stacked area chart, cooldown setting. Auto-saves on change (debounced 500ms). `useAISettings` hook fetches settings, `useUpdateAISettings` patches.
- **AI dedup banners:** When AI mutation returns `reused: true`, history items show a "cached" badge and a blue info banner with "Regenerate" button (`force=true`). Cost estimates shown in AI trigger dialogs via `useAICostEstimate`.
- **AI budget warning:** AIAnalysis page shows amber banner when `budget_pct_used >= budget_warning_threshold` with link to AI Settings. Investment page checks `feature_work_categorization` before toggling AI classify.

## Architecture Advisory

When modifying files that affect system architecture, consult `docs/architecture/` before making changes:

| File pattern | Concern | Relevant doc |
|-------------|---------|--------------|
| `backend/app/models/models.py` | Database schema | `docs/architecture/DATA-MODEL.md` |
| `backend/app/models/database.py` | Connection/session patterns | `docs/architecture/SERVICE-LAYER.md` |
| `backend/app/schemas/schemas.py` | API contracts | `docs/architecture/API-DESIGN.md` |
| `backend/app/main.py` | App init, middleware, scheduler | `docs/architecture/OVERVIEW.md` |
| `backend/app/api/*.py` (new routers) | API design patterns | `docs/architecture/API-DESIGN.md` |
| `backend/app/services/*.py` (new services) | Service layer patterns | `docs/architecture/SERVICE-LAYER.md` |
| `backend/migrations/versions/*.py` | Migration patterns | `docs/architecture/DATA-MODEL.md` |
| `frontend/src/pages/*.tsx` (new pages) | Routing/nav structure | `docs/architecture/FRONTEND.md` |

**Before adding new tables, routers, or services:** Read the relevant architecture doc to follow established patterns. After completing structural changes, run `/architect <area>` to update documentation.

## Reference Docs

- `docs/API.md` — Complete API reference with all endpoints and request/response schemas
- `docs/architecture/` — Interconnected architecture documentation (generated by `/architect`)
- `DEVPULSE_SPEC.md` — Full technical specification
- `DEVPULSE_MANAGEMENT_FEATURES.md` — Management features spec (M1-M8)
- `.env.example` + `backend/app/config.py` — All environment variables
