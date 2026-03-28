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

### Data Flow

1. **GitHub App** authenticates via JWT → installation token (cached, auto-refreshed)
2. **Scheduled sync** (APScheduler) fetches repos → PRs → reviews → review comments → issues → issue comments
3. **Webhooks** provide real-time updates for PR/review/issue events
4. **Stats service** computes metrics on-demand from cached data (no materialized views)
5. **AI analysis** gathers context from stats/collaboration/goals, sends to Claude, stores structured result

### Backend Layout

```
backend/app/
├── api/              # FastAPI routers (thin delegation to services)
│   ├── auth.py       # JWT validation, get_current_user(), require_admin()
│   ├── oauth.py      # GitHub OAuth login/callback/me endpoints
│   ├── developers.py # Team registry CRUD
│   ├── stats.py      # Stats, benchmarks, trends, workload, collaboration endpoints
│   ├── goals.py      # Developer goals CRUD + progress + self-goal endpoints
│   ├── sync.py       # Sync trigger/status endpoints
│   ├── webhooks.py   # GitHub webhook receiver (HMAC-verified)
│   └── ai_analysis.py # AI analysis + 1:1 prep + team health endpoints
├── models/
│   ├── database.py   # Async engine, session factory, Base, get_db() dependency
│   └── models.py     # All 12 SQLAlchemy ORM models
├── schemas/
│   └── schemas.py    # All Pydantic request/response models and enums
├── services/
│   ├── github_sync.py    # GitHub App auth, rate limiting, upsert helpers, sync orchestration
│   ├── stats.py          # All metrics: developer, team, repo, benchmarks, trends, workload
│   ├── collaboration.py  # Collaboration matrix + insights (silos, bus factors, isolation)
│   ├── goals.py          # Goal CRUD, metric computation, auto-achievement
│   ├── risk.py           # PR risk scoring: per-PR assessment, team risk summary
│   └── ai_analysis.py    # Claude API integration, 1:1 prep briefs, team health checks
├── config.py         # pydantic-settings: all env vars
└── main.py           # FastAPI app factory, CORS, router registration, APScheduler
```

### Frontend Layout

```
frontend/src/
├── pages/            # Route components (Dashboard, TeamRegistry, DeveloperDetail, Repos, SyncStatus, AIAnalysis, Goals, Login, AuthCallback)
│   └── insights/     # Insights sub-pages (WorkloadOverview, CollaborationMatrix, Benchmarks, IssueQuality, CodeChurn)
├── components/
│   ├── Layout.tsx    # Sticky header, nav (with Insights dropdown group), global date range picker, quick-select date presets (7d/14d/30d/90d/quarter)
│   ├── StalePRsSection.tsx  # Shared stale PR table (used by Dashboard + WorkloadOverview)
│   ├── StatCard.tsx  # Reusable stat display card with optional trend delta and methodology tooltip
│   ├── StatCardSkeleton.tsx  # Skeleton loading variant for StatCard
│   ├── TableSkeleton.tsx     # Skeleton loading variant for table rows
│   ├── ErrorCard.tsx         # Reusable error state: icon, message, retry button
│   ├── ErrorBoundary.tsx     # React error boundary with "Try Again" and "Go to Dashboard" fallback
│   ├── GoalCreateDialog.tsx  # Shared goal creation dialog (used by Goals page + DeveloperDetail), exports metricKeyLabels
│   ├── DateRangePicker.tsx   # Calendar popover + quick-select presets (7d/14d/30d/90d/quarter)
│   ├── ai/           # AI analysis result renderers
│   │   ├── AnalysisResultRenderer.tsx  # Router: switches on analysis_type to select view
│   │   ├── OneOnOnePrepView.tsx        # Structured 1:1 brief: metrics table, talking points accordion, goal progress
│   │   ├── TeamHealthView.tsx          # Structured health check: score gauge, action items, flags
│   │   └── GenericAnalysisView.tsx     # Auto-renders scores + lists for communication/conflict/sentiment
│   ├── charts/       # Recharts-based data visualization components
│   │   ├── TrendChart.tsx         # AreaChart with regression line overlay and direction badge
│   │   ├── PercentileBar.tsx      # Horizontal bar showing developer position vs team p25/p50/p75
│   │   ├── ReviewQualityDonut.tsx # PieChart with quality tier segments and center score
│   │   └── GoalSparkline.tsx     # Compact LineChart with target ReferenceLine for goal progress
│   └── ui/           # shadcn/ui primitives (button, card, table, dialog, skeleton, calendar, popover, tooltip, accordion, etc.)
├── hooks/            # TanStack Query hooks (useAuth, useDevelopers, useStats [incl. useDeveloperStats, useTeamStats, useRepoStats, useDeveloperTrends, useWorkload, useBenchmarks, useCollaboration, useAllDeveloperStats, useStalePRs, useIssueCreatorStats, useRiskSummary, useCodeChurn], useSync, useAI, useGoals, useDateRange)
├── utils/
│   ├── api.ts        # apiFetch<T>() wrapper with Bearer auth from localStorage
│   └── types.ts      # TypeScript interfaces mirroring backend schemas
└── lib/utils.ts      # cn() utility (clsx + tailwind-merge)
```

**Import alias:** `@/` maps to `src/` (configured in vite.config.ts and tsconfig).

## Database Schema (12 tables)

| Table | Purpose | Key Relationships |
|-------|---------|-------------------|
| `developers` | Team registry with GitHub username, role, team, skills, app_role | Has many: pull_requests, reviews, issues, goals |
| `repositories` | GitHub repos with tracking toggle, default branch, tree truncation flag | Has many: pull_requests, issues, tree_files |
| `pull_requests` | PRs with pre-computed cycle times, approval tracking, and issue linkage | Belongs to: repo, author. Has many: reviews, review_comments, files |
| `pr_reviews` | Reviews with quality tier classification | Belongs to: pr, reviewer. Has many: comments |
| `pr_review_comments` | Inline code review comments | Belongs to: pr, review |
| `pr_files` | File-level changes per PR (filename, additions, deletions, status) | Belongs to: pull_request |
| `repo_tree_files` | Full repo file tree snapshot for stale directory detection | Belongs to: repository |
| `issues` | Issues with close-time computation and quality scoring | Belongs to: repo, assignee. Has many: comments |
| `issue_comments` | Issue comment bodies | Belongs to: issue |
| `sync_events` | Sync run audit log | Standalone |
| `ai_analyses` | AI analysis results (JSONB) | Standalone (scope_type + scope_id reference other tables) |
| `developer_goals` | Goal tracking with metric targets + `created_by` (self/admin) | Belongs to: developer |

**Key design decisions:**
- Author/reviewer FKs are **nullable** — external contributors not in the team registry get `NULL`
- PR cycle-time fields (`time_to_first_review_s`, `time_to_merge_s`, `time_to_approve_s`, `time_after_approve_s`) are pre-computed at sync time. Issue cycle-time field: `time_to_close_s`
- Approval tracking: `approved_at` (last APPROVED review), `approval_count` (>1 = re-review cycle), `merged_without_approval` (merged with zero approvals)
- Revert tracking: `is_revert` (boolean), `reverted_pr_number` (nullable int) — detected at sync time via title/body parsing + DB fallback
- `pr_reviews.quality_tier` is computed deterministically: `thorough` (>500 chars, or 3+ inline comments, or CHANGES_REQUESTED + >100 chars), `standard` (100-500 chars, or CHANGES_REQUESTED any length, or body contains code blocks), `rubber_stamp` (APPROVED + <20 chars + 0 inline comments), `minimal` (default)
- JSONB columns: `skills`, `labels`, `errors`, `result` (AI analysis output), `closes_issue_numbers` (PR → issue linkage via closing keywords)
- `developer_goals.created_by` — `"self"` or `"admin"` (server_default `"admin"`); developers can only modify their own self-created goals
- Issue quality scoring: `comment_count`, `body_length`, `has_checklist`, `state_reason`, `creator_github_username`, `milestone_title`, `milestone_due_on`, `reopen_count` — extracted from GitHub API at sync time. `reopen_count` incremented on closed→open state transition.
- Code churn tracking: `pr_files` populated from GitHub PR files API (1 call per PR during sync). `repo_tree_files` is a full snapshot via Trees API (1 call per repo, delete + re-insert). `default_branch` on `repositories` used for tree fetch. `tree_truncated` tracks if GitHub truncated the tree (>100K entries).
- No commit-level data — stats are PR-level only to stay within GitHub rate limits

## GitHub Integration

### GitHub App Setup

**Required permissions (all read-only):**
- Repository: Contents, Pull requests, Issues, Metadata
- Organization: Members

**Webhook events to subscribe:**
- `pull_request` — PR created/updated/merged/closed
- `pull_request_review` — review submitted
- `pull_request_review_comment` — inline code comment added/edited
- `issues` — issue created/updated/closed
- `issue_comment` — issue comment added (PR comments are skipped via `pull_request` key detection)

**Do NOT subscribe to:** `push` (commits are not tracked)

### Authentication Flow

1. `GitHubAuth` generates a 10-minute RS256 JWT signed with the app's private key
2. JWT is exchanged for an installation token via `POST /app/installations/{id}/access_tokens`
3. Installation token is cached and auto-refreshed 60 seconds before expiry
4. All GitHub API calls use `Authorization: Bearer {installation_token}`

### Webhook Verification

`verify_signature()` computes HMAC-SHA256 of raw request body using `GITHUB_WEBHOOK_SECRET`, then constant-time compares against `X-Hub-Signature-256` header.

### Sync Strategy

| Mode | Schedule | Scope | Mechanism |
|------|----------|-------|-----------|
| **Full sync** | Cron at `FULL_SYNC_CRON_HOUR` (default 2 AM) | All tracked repos, all PRs/issues | `run_sync("full")` |
| **Incremental sync** | Every `SYNC_INTERVAL_MINUTES` (default 15) | Changed since `last_synced_at` | `run_sync("incremental")` with `stop_before` pagination |
| **Webhook** | Real-time | Single event | `POST /api/webhooks/github` |

**Sync flow per repo:** fetch PRs → for each PR: upsert PR + fetch reviews + fetch review comments + recompute quality tiers + fetch PR files → fetch issues → fetch issue comments → sync repo tree → update `repo.last_synced_at`

**Rate limit handling:** checks `X-RateLimit-Remaining` header; sleeps until reset when < 100 remaining.

## API Structure

Authentication uses GitHub OAuth → JWT. Two roles: `admin` (full access) and `developer` (own data only).
Endpoints `/api/health`, `/api/webhooks/github`, and `/api/auth/*` are public. All others require a valid JWT.

### Auth Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/auth/login` | Returns GitHub OAuth authorize URL |
| `GET /api/auth/callback?code=` | OAuth code exchange → create/login user → JWT → redirect to frontend |
| `GET /api/auth/me` | Returns current user info (requires JWT) |

### Core Endpoints

| Group | Endpoints | Access |
|-------|-----------|--------|
| **Health** | `GET /api/health` | Public |
| **Developers** | `GET/POST /api/developers`, `GET/PATCH/DELETE /api/developers/{id}` | Admin (GET /{id} also developer self-access) |
| **Stats** | `GET /api/stats/developer/{id}`, `GET /api/stats/team`, `GET /api/stats/repo/{id}` | Developer: own stats + repo stats. Admin: all. |
| **Sync** | `POST /api/sync/full`, `POST /api/sync/incremental`, `GET /api/sync/repos`, `PATCH /api/sync/repos/{id}/track`, `GET /api/sync/events` | Admin only |
| **Webhooks** | `POST /api/webhooks/github` | Public (HMAC-verified) |
| **AI** | `POST /api/ai/analyze`, `GET /api/ai/history`, `GET /api/ai/history/{id}` | Admin only |

### Management Feature Endpoints (M1-M8)

| Feature | Endpoint | Description |
|---------|----------|-------------|
| **M1: Review Quality** | `GET /api/stats/developer/{id}` | `review_quality_breakdown` + `review_quality_score` in response |
| **M2: Benchmarks** | `GET /api/stats/benchmarks` | p25/p50/p75 percentiles across team |
| **M2: Percentiles** | `GET /api/stats/developer/{id}?include_percentiles=true` | Developer stats with team-relative percentile placement |
| **M3: Trends** | `GET /api/stats/developer/{id}/trends` | Period-bucketed stats with linear regression |
| **M4: Workload** | `GET /api/stats/workload` | Per-developer load indicators + automated alerts |
| **P2-01: Stale PRs** | `GET /api/stats/stale-prs` | Open PRs needing attention, sorted by staleness (no_review, changes_requested, approved_not_merged) |
| **P2-04: Issue Linkage** | `GET /api/stats/issue-linkage` | Issue-to-PR linkage stats via closing keywords (linked/unlinked counts, avg PRs per issue) |
| **P3-03: Issue Quality** | `GET /api/stats/issues/quality` | Issue quality scoring (body length, checklists, comment counts, reopen rate, not-planned %) |
| **P3-03: Issue Labels** | `GET /api/stats/issues/labels` | Label distribution across issues in period |
| **P3-04: Issue Creators** | `GET /api/stats/issues/creators` | Per-creator issue quality analytics with team averages, linkage metrics, and comment-before-PR counts |
| **P3-06: Code Churn** | `GET /api/stats/repo/{id}/churn` | File-level churn hotspots + stale directories per repo |
| **M5: Collaboration** | `GET /api/stats/collaboration` | Reviewer-author matrix + insights (silos, bus factors) |
| **M6: Goals** | `POST/GET /api/goals`, `PATCH /api/goals/{id}`, `GET /api/goals/{id}/progress` | Developer goal CRUD with auto-achievement |
| **P1-03: Self Goals** | `POST /api/goals/self`, `PATCH /api/goals/self/{id}` | Developer self-goal creation + update (own self-created goals only) |
| **M7: 1:1 Prep** | `POST /api/ai/one-on-one-prep` | AI-generated structured 1:1 meeting brief |
| **M8: Team Health** | `POST /api/ai/team-health` | AI-generated comprehensive team health assessment |
| **P3-05: PR Risk** | `GET /api/stats/pr/{id}/risk` | Single PR risk assessment (score, level, factors) |
| **P3-05: Risk Summary** | `GET /api/stats/risk-summary` | Team-level risk summary with scope/level filters |

See `docs/API.md` for full request/response contracts.

## Environment Variables

Defined in `backend/app/config.py` via pydantic-settings. Copy `.env.example` to `.env`.

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://devpulse:devpulse@localhost:5432/devpulse` | Async PostgreSQL connection |
| `GITHUB_APP_ID` | Yes | `0` | GitHub App numeric ID |
| `GITHUB_APP_PRIVATE_KEY_PATH` | Yes | `./github-app.pem` | Path to GitHub App RSA private key |
| `GITHUB_APP_INSTALLATION_ID` | Yes | `0` | GitHub App installation ID for the org |
| `GITHUB_WEBHOOK_SECRET` | Yes | `""` | HMAC secret for webhook signature verification |
| `GITHUB_ORG` | Yes | `""` | GitHub organization name (e.g. `my-company`) |
| `GITHUB_CLIENT_ID` | Yes | `""` | GitHub OAuth client ID (from GitHub App settings) |
| `GITHUB_CLIENT_SECRET` | Yes | `""` | GitHub OAuth client secret |
| `JWT_SECRET` | Yes | `""` | Secret for signing JWT tokens (min 32 chars recommended) |
| `DEVPULSE_INITIAL_ADMIN` | No | `""` | GitHub username auto-promoted to admin on first login |
| `FRONTEND_URL` | No | `http://localhost:5173` | Frontend URL for OAuth redirect |
| `ANTHROPIC_API_KEY` | For AI | `""` | Anthropic API key (only needed for AI features) |
| `SYNC_INTERVAL_MINUTES` | No | `15` | Incremental sync interval |
| `FULL_SYNC_CRON_HOUR` | No | `2` | Hour (UTC) for nightly full sync |

## Running

### Docker (recommended)

```bash
cp .env.example .env   # edit with your values — see env vars table above
docker compose up
```

| Service | URL | Notes |
|---------|-----|-------|
| Backend | http://localhost:8000 | FastAPI with auto-reload |
| Frontend | http://localhost:5173 | Vite dev server, proxies /api to backend |
| Database | localhost:5432 | PostgreSQL 15, user/pass/db: `devpulse` |

### Local development

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
pnpm install
pnpm dev
```

### Database migrations

```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Running tests

```bash
cd backend
pip install -r requirements-test.txt
python -m pytest                    # all tests
python -m pytest tests/unit/        # unit tests only
```

Tests use SQLite in-memory via aiosqlite (no PostgreSQL needed for testing).

## Key Patterns and Conventions

### Backend patterns
- **Auth:** GitHub OAuth → JWT (7-day expiry). Two roles: `admin` (full access), `developer` (own data only). Dependencies: `get_current_user()` returns `AuthUser`, `require_admin()` raises 403 if not admin. Per-endpoint injection (not router-level) for mixed-access routers.
- **Thin API routes:** Routes validate input and delegate to service functions — no business logic in routes
- **Service functions:** All async, accept `AsyncSession` as first param, return Pydantic models or ORM objects
- **Upsert pattern:** SELECT by unique key → create if not found → always overwrite mutable fields (idempotent)
- **Date range defaulting:** `_default_range()` helper — defaults to last 30 days if params are None
- **Review quality tiers:** Computed at sync time by `classify_review_quality()` (pure function), then recomputed after review comments are synced via `recompute_review_quality_tiers()`
- **Percentile band inversion:** For lower-is-better metrics (time_to_merge, time_to_first_review, review_turnaround), `_percentile_band()` inverts labels so `above_p75` always means "best"
- **Trend regression:** Simple OLS `_linear_regression()` with polarity-aware direction classification; <5% change = "stable"
- **Goal auto-achievement:** Checked on progress fetch — if metric meets target for 2 consecutive weekly periods, auto-marks as achieved
- **Issue-PR linkage:** `extract_closing_issue_numbers(body)` parses closing keywords (`close/closes/closed/fix/fixes/fixed/resolve/resolves/resolved #N`) from PR body at sync time, stores as `closes_issue_numbers` JSONB array. Linkage stats cross-reference by `(repo_id, issue_number)`.
- **Issue creator analytics:** `get_issue_creator_stats()` groups issues by `creator_github_username`, resolves identity via string join to `Developer.github_username` (no FK). For `avg_comment_count_before_pr`, cross-references `IssueComment.created_at` against earliest linked PR's `created_at` per issue. Returns `IssueCreatorStatsResponse` with per-creator list + team averages.
- **Draft PR filtering:** Open PR counts and workload metrics use `PullRequest.is_draft.isnot(True)` to exclude drafts (handles `NULL` safely). Drafts are counted separately via `prs_draft` / `drafts_open`. Stale PR alerts also exclude drafts.
- **Workload score:** Heuristic based on pending work only: `total_load = open_authored + open_reviewing + open_issues`. Completed reviews are output, not load — they are excluded from the score formula. Thresholds: `low` (0), `balanced` (1-5), `high` (6-12), `overloaded` (>12).
- **Revert detection:** `detect_revert()` parses title (`Revert "..."`) and body (`Reverts #NNN` / `Reverts owner/repo#NNN`). Falls back to DB title lookup via `_resolve_revert_pr_number()`. `prs_reverted` counts via self-join on `reverted_pr_number` + `repo_id`. Alert threshold: 5% revert rate.
- **PR risk scoring:** Pure function `compute_pr_risk()` in `services/risk.py` scores PRs across 10 weighted factors (size, author experience, review quality, merge patterns, branch naming). Score = min(1.0, sum of weights). Levels: low (0-0.3), medium (0.3-0.6), high (0.6-0.8), critical (0.8-1.0). `get_risk_summary()` bulk-fetches author merged counts and names to avoid N+1 queries. Drafts excluded. `is_merged` checked with `is True` (nullable bool).
- **AI analysis:** Data gathering → structured system prompt → Claude API call → JSON parse → store in `ai_analyses`. PR data for 1:1 briefs includes `html_url` for GitHub links.

### Frontend patterns
- **Global date range:** React Context (`DateRangeContext`) set in Layout header, consumed by all pages
- **Server state:** TanStack Query with 30s stale time, 1 retry
- **Auth:** GitHub OAuth login → JWT stored in `localStorage` key `devpulse_token`, injected by `apiFetch()` wrapper. `AuthContext` provides user info and role. Auto-redirect to `/login` on 401. Role-aware nav in Layout (admin sees all, developer sees own stats).
- **API proxy:** Vite dev server proxies `/api/*` → `http://localhost:8000`
- **Component library:** shadcn/ui with base-nova style, neutral base color, CSS variables, Lucide icons
- **Charts:** Recharts 3 wrapped in `components/charts/`. Use `ResponsiveContainer`, CSS variables for colors (`hsl(var(--primary))`), and `useId()` for unique SVG gradient IDs
- **Dashboard zones:** Alert strip (workload alerts + merged-without-approval warnings) → Stale PRs table (needs attention, color-coded by age/reason) → Team status grid (sortable table) → Period velocity (stat cards with trend deltas from previous period comparison)
- **Trend deltas:** Computed on the frontend by comparing current period stats vs same-duration previous period. For lower-is-better metrics (time_to_merge, time_to_first_review), green = decrease
- **Toast notifications:** `sonner` (bottom-right, 4s auto-dismiss, rich colors). All mutations wrapped with success/error toasts in hook files.
- **Error states:** `ErrorCard` component with icon + message + retry button. All query pages check `isError` and render `ErrorCard`. `ErrorBoundary` wraps page routes in `App.tsx`.
- **Skeleton loading:** `StatCardSkeleton` and `TableSkeleton` replace "Loading..." text. Use shadcn `Skeleton` primitive for custom inline skeletons.
- **Date range picker:** `DateRangePicker` component with quick-select presets (7d/14d/30d/90d/quarter) + dual Calendar popover for custom range selection. Uses `react-day-picker` + `date-fns`.
- **Methodology tooltips:** `StatCard` accepts an optional `tooltip` prop — renders a `HelpCircle` icon (Lucide) next to the title with a hover tooltip (`@base-ui/react/tooltip`). Every stat card on Dashboard and DeveloperDetail explains how the metric is computed. Section headers (Trends, Team Context) also have tooltips.
- **AI result rendering:** `AnalysisResultRenderer` switches on `analysis_type` to select a structured view component (`OneOnOnePrepView`, `TeamHealthView`, `GenericAnalysisView`). Falls back to formatted JSON for unknown types. Color convention: green (positive/on-track), amber (needs attention), red (concern/blocker).
- **Nav dropdown groups:** `Layout.tsx` supports `NavGroup` entries with `children` array — renders a click-to-open dropdown. Active state uses exact match or prefix match with `/` separator. Currently used for "Insights" group (Workload, Collaboration, Benchmarks, Issue Quality, Code Churn).
- **Insights pages:** Five admin-only pages under `/insights/*`. WorkloadOverview uses `useWorkload` + `useStalePRs` + shared `StalePRsSection`. CollaborationMatrix uses `useCollaboration` with a custom CSS grid heatmap. Benchmarks uses `useBenchmarks` + `useAllDeveloperStats` (batch `useQueries`) for the developer ranking. IssueQuality uses `useIssueCreatorStats` with per-creator table, min-issue-count filter, and red-badge highlighting for metrics >1.5x worse than team average. CodeChurn uses `useCodeChurn` with repo selector, hotspot table, and stale directory detection.
- **Batch developer stats:** `useAllDeveloperStats(ids, dateFrom, dateTo)` uses TanStack `useQueries` to fetch all developer stats in parallel with a single hook call, avoiding N+1 per-row hooks. Query keys match `useDeveloperStats` for cache sharing.

## Specification

- `DEVPULSE_SPEC.md` — Full technical specification (data models, API contracts, sync logic, implementation phases)
- `DEVPULSE_MANAGEMENT_FEATURES.md` — Management features spec (M1-M8: review quality, benchmarks, trends, workload, collaboration, goals, AI briefs)
- `docs/API.md` — Complete API reference with all endpoints, request/response schemas

## Task System

Task files live in `.claude/tasks/` (core spec), `.claude/tasks/management-improvements/` (M1-M8), and `.claude/tasks/improvements/` (P1-P4 phases).

**Core + Management tasks are completed:**
- Core: 01-12 (project scaffolding through frontend pages)
- Management Phase 1: M1 (review quality), M2 (benchmarks), M3 (trends), M4 (workload)
- Management Phase 2: M5 (collaboration matrix), M6 (developer goals)
- Management Phase 3: M7 (1:1 prep brief), M8 (team health check)

**Improvement tasks completed:**
- P1-05: Recharts + Trend Visualizations (charts, percentile bars, review quality donut on DeveloperDetail)
- P1-02: Actionable Dashboard (alert strip, team status grid, stat cards with trend deltas, date presets)
- P1-04: Structured AI Result Rendering (OneOnOnePrepView, TeamHealthView, GenericAnalysisView, tabbed AIAnalysis page, 1:1 prep button on DeveloperDetail)
- P1-07: Draft PR Filtering (draft PRs excluded from `prs_open`, workload counts, and stale alerts; workload score formula fixed)
- P1-03: Developer Self-Goal Creation (`POST /api/goals/self`, `PATCH /api/goals/self/{id}` endpoints; `GoalSelfCreate`/`GoalSelfUpdate` schemas; `created_by` column on `developer_goals`; developer-only access to own self-created goals)
- P1-08: Methodology Tooltips (HelpCircle + hover tooltip on every StatCard and section header explaining how each metric is computed)
- P2-03: Approved-At Timestamp & Post-Approval Merge Latency (approved_at, time_to_approve_s, time_after_approve_s, approval_count, merged_without_approval on PRs; approval metrics in stats, benchmarks, and workload alerts)
- P2-01: Stale PR List Endpoint (dedicated endpoint + Dashboard "Needs Attention" table with 3 staleness categories)
- P2-04: Approval Metrics Frontend (approval StatCards + percentile bars on DeveloperDetail, `merged_without_approval` alerts on Dashboard)
- P2-04: Issue-to-PR Linkage via Closing Keywords (`closes_issue_numbers` JSONB on PRs, `extract_closing_issue_numbers()` parser, `GET /api/stats/issue-linkage` endpoint)
- P2-05: PR Metadata Capture (`labels` JSONB, `merged_by_username`, `head_branch`, `base_branch`, `is_self_merged`, `html_url` on PRs; extracted from GitHub API during sync)
- P2-06: Revert PR Detection (`is_revert`, `reverted_pr_number` on PRs; `detect_revert()` with DB fallback; `prs_reverted`/`reverts_authored` in developer stats; `revert_rate` in team stats; `revert_spike` workload alert; frontend stat cards on DeveloperDetail + Dashboard)
- P2-09: Goals Management Page (dedicated `/goals` route with flat table view, developer filter dropdown for admins, shared `GoalCreateDialog` component, progress bars + sparklines per goal, status quick-actions, `useUpdateAdminGoal` hook)
- P2-07: Review Quality Algorithm Fix (multi-signal `classify_review_quality()`: CHANGES_REQUESTED promotes to standard/thorough, code blocks promote to standard, rubber_stamp requires 0 inline comments; recompute script; "Quick Approval" UI label)
- P2-08: Workload, Collaboration & Benchmarks Pages (3 new Insights pages under `/insights/*` with nav dropdown; WorkloadOverview with alerts + team grid + stale PRs; CollaborationMatrix with CSS heatmap + insights panel; Benchmarks with percentile table + developer ranking bars; shared `StalePRsSection` extracted from Dashboard; `useAllDeveloperStats` batch hook)
- P3-03: Issue Quality Scoring (8 new columns on `issues`: `comment_count`, `body_length`, `has_checklist`, `state_reason`, `creator_github_username`, `milestone_title`, `milestone_due_on`, `reopen_count`; sync extraction from GitHub API; reopen detection on closed→open transition; `GET /api/stats/issues/quality` + `GET /api/stats/issues/labels` endpoints)
- P3-04: Issue Creator Analytics (`GET /api/stats/issues/creators` batch endpoint; per-creator metrics: checklist %, reopened %, not-planned %, avg close time, avg PRs per issue, avg time to first PR, avg comments before PR; team averages for comparison; volume-based creator filtering; `/insights/issue-quality` page with red-badge highlighting for metrics >1.5x worse than average)
- P3-05: PR Risk Scoring (`backend/app/services/risk.py` with pure `compute_pr_risk()` function scoring 10 factors; `GET /api/stats/pr/{id}/risk` + `GET /api/stats/risk-summary` with scope/level filters; risk badges on stale PR table; "High-Risk PRs" Dashboard section; shared `riskLevelStyles`/`riskLevelLabels` in types.ts; 36 unit tests)
- P3-06: Code Churn Analysis (`pr_files` + `repo_tree_files` tables; `default_branch` + `tree_truncated` on `repositories`; sync of PR files from GitHub API + repo tree snapshot via Trees API; `PRFile` and `RepoTreeFile` models; `GET /api/stats/repo/{id}/churn` endpoint with hotspot files + stale directories; `/insights/code-churn` page with repo selector, hotspot table, stale dirs; `useCodeChurn` hook; 14 tests)
