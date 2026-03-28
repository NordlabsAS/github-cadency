# DevPulse Strategic Deep Dive Analysis

**Date:** 2026-03-28
**Method:** 7 parallel analysis agents examining Team Lead workflows, IC Developer experience, PR/Review process, Issue/Task management, QA/Quality patterns, Frontend UX, and competitive landscape.

---

## The 30-Second Summary

DevPulse has a **solid backend foundation** — the data pipeline, sync engine, and metric computation are well-architected. But after analyzing from 7 different perspectives, the tool has a critical identity problem: **it's built as a management surveillance tool but needs to be a team productivity platform.** The backend computes far more than the frontend shows, and the most valuable features for both managers AND developers are either missing or invisible.

---

## Table of Contents

1. [The Root Problem: Identity Crisis](#1-the-root-problem-identity-crisis)
2. [Top 10 Critical Gaps](#2-top-10-critical-gaps)
3. [Management Friction Detection](#3-management-friction-detection-novel-feature)
4. [Competitive Positioning](#4-competitive-positioning)
5. [Implementation Roadmap](#5-implementation-roadmap)
6. [Detailed Findings by Perspective](#6-detailed-findings-by-perspective)

---

## 1. The Root Problem: Identity Crisis

### What DevPulse Is Today

A read-only GitHub analytics dashboard with a single admin token, raw JSON AI output, and 7 number cards on the homepage. ~80% of backend features have zero UI representation.

### What It Should Be

A **team productivity platform** that serves three audiences simultaneously:

| Audience | Primary Need | Current State |
|----------|-------------|---------------|
| **Team Lead** | "What needs my attention today?" | Wall of 7 aggregate numbers, no alerts visible |
| **IC Developer** | "Am I improving? Am I blocked?" | Cannot self-authenticate, no personal insights |
| **Director/VP** | "Is this team healthy and shipping?" | No executive-level reporting |

---

## 2. Top 10 Critical Gaps

### #1: No Developer Self-Access (Structural)

**The Problem:** Every endpoint requires a single `DEVPULSE_ADMIN_TOKEN`. Developers cannot see their own data. This makes DevPulse feel like surveillance, not a tool.

**The Fix:** Add a `personal_token` column to the `developers` table. Generate a read-only UUID per developer that scopes access to their own stats, goals, and trends. This single change transforms the tool's relationship with the team.

**Impact:** Enables developers to set their own goals, see their own trends, and trust the tool. Without this, every other developer-facing improvement is moot.

**Files to change:**
- `backend/app/api/auth.py` — add secondary auth path resolving developer ID from personal token
- `backend/app/models/models.py` — add `personal_token` column to `developers`
- `backend/app/api/goals.py` — add `POST /api/goals/self` for developer-scoped goal creation
- `backend/app/api/stats.py` — restrict developer-token access to own ID only

---

### #2: The Dashboard Is Not Actionable

**The Problem:** 7 stat cards with no trends, no alerts, no drill-down, no links to investigate anomalies. A team lead opens this and learns nothing actionable.

**The Fix:** Three-zone dashboard:
- **Zone 1 — "Needs Attention"**: Stale PRs waiting >48h, overloaded developers, expiring goals. (Backend `WorkloadAlert` already computes this — just needs rendering)
- **Zone 2 — Team Status Grid**: One row per developer with workload badge, open PRs, PRs waiting for review, link to detail page
- **Zone 3 — Period Velocity**: The existing 7 numbers but with delta arrows ("+15% vs last period")

**Files to change:**
- `frontend/src/pages/Dashboard.tsx` — rebuild with three-zone layout
- `frontend/src/hooks/useStats.ts` — add `useWorkload` hook
- `frontend/src/utils/types.ts` — add `WorkloadResponse`, `WorkloadAlert` types

---

### #3: Zero Data Visualization

**The Problem:** No charting library exists in the frontend. Every data point is a number in a card or table cell. The backend computes trends, benchmarks, percentile distributions, collaboration matrices, workload levels, and review quality breakdowns — **none are visualized**.

**Missing visualizations:**

| Backend Feature | Data Produced | Visualization Needed | Currently Shown |
|---|---|---|---|
| M3 Trends | Period-bucketed stats with regression | Line/area chart per metric | Nothing |
| M2 Benchmarks | p25/p50/p75 for 5+ metrics | Box-and-whisker or percentile bar | Nothing |
| M2 Percentiles | Per-developer percentile placement | Percentile gauge or rank bar | Nothing |
| M5 Collaboration | Reviewer/author matrix + insights | Heatmap grid or directed graph | Nothing |
| M4 Workload | Per-dev load level + alerts | Horizontal bar chart + alert list | Nothing |
| M1 Review Quality | Quality tier breakdown | Donut chart or stacked bar | Nothing |
| M6 Goals | Progress time-series | Progress bar + sparkline | Nothing |

**The Fix:** Add Recharts and build trend sparklines, percentile gauges, collaboration heatmap, workload bars, and review quality donuts.

**Files to change:**
- `frontend/package.json` — add `recharts`
- `frontend/src/pages/DeveloperDetail.tsx` — add trends chart, review quality donut, percentile bars
- New pages: `/insights/workload`, `/insights/collaboration`, `/insights/benchmarks`, `/goals`

---

### #4: No PR Blocker Detection

**The Problem:** The system cannot answer "which PRs are stuck and who is blocking them?" It counts PRs waiting for first review, but cannot identify:
- PRs stale after `CHANGES_REQUESTED` (author hasn't responded)
- PRs approved but not merged (sitting for days after approval)
- Who was requested as reviewer but hasn't responded
- Draft PRs inflating all open PR counts (`is_draft` stored but never queried)

**The Fix:**
- New `GET /api/stats/stale-prs` endpoint returning per-PR age, author, reviewer count, and GitHub URL
- Capture `requested_reviewers` from the GitHub API (already in the response, never stored)
- Compute `approved_at` from existing review data (`MAX(submitted_at) WHERE state = 'APPROVED'`) — no new API calls
- Filter `is_draft` from all workload calculations

**Files to change:**
- `backend/app/models/models.py` — add `requested_reviewers` JSONB column to `pull_requests`
- `backend/app/services/github_sync.py` — capture `requested_reviewers` and `merged_by` from already-fetched API response
- `backend/app/services/stats.py` — new `get_stale_prs()` function, add `is_draft` filter to workload queries
- `backend/app/api/stats.py` — new `GET /api/stats/stale-prs` route

---

### #5: Review Quality Algorithm Is Unfair

**The Problem:** Review quality is classified purely by character count (`classify_review_quality()` at `github_sync.py:242`). A reviewer who catches a critical security bug in 15 characters scores "rubber stamp." A verbose reviewer who writes 600 characters of praise scores "thorough." The `CHANGES_REQUESTED` state — the strongest quality signal — is completely ignored in classification.

**Current algorithm:**
```
thorough:     body > 500 chars, or 3+ inline review comments
standard:     body 100-500 chars
rubber_stamp: state=APPROVED with body < 20 chars
minimal:      everything else
```

**The Fix:** Multi-signal classification:
- `CHANGES_REQUESTED` = minimum "standard" regardless of length
- Keep inline comment count (3+ = thorough)
- Add code block detection (backticks = technical substance)
- Rename "rubber_stamp" to "quick approval" in developer-facing UI (less stigmatizing)

**Files to change:**
- `backend/app/services/github_sync.py` lines 242-261 — rework `classify_review_quality()`

---

### #6: No Issue-to-PR Linkage

**The Problem:** DevPulse tracks issues and PRs completely independently. There is no way to see which issues led to which PRs, which issues required multiple PRs (scope too large), or which issues were never implemented. This is the **single most important gap for understanding management-created friction**.

**The Fix:**
- Parse closing keywords from `PullRequest.body` (`closes #NNN`, `fixes #NNN`) — the body is already stored
- Store results in a `closes_issue_numbers` JSONB column on `pull_requests`
- This enables: "issues that needed 3+ PRs" (bad scoping), "issues never linked to a PR" (orphaned work), "average PRs per issue" (scope accuracy)

**Files to change:**
- `backend/app/models/models.py` — add `closes_issue_numbers` JSONB to `pull_requests`
- `backend/app/services/github_sync.py` — parse closing keywords in `upsert_pull_request()`
- `backend/app/services/stats.py` — new `get_issue_quality_stats()` function

---

### #7: No Review Round-Trip Tracking

**The Problem:** The system cannot distinguish a PR merged on the first review pass from one that went through 5 rounds of changes-requested/re-review cycles. Review round-trip count is arguably the **best single indicator of process health** — it reflects PR description quality, requirements clarity, and team alignment.

**The Fix:** Count distinct `CHANGES_REQUESTED` reviews per PR from existing `pr_reviews` data. Store as `review_round_count` on `PullRequest`. Surface as a per-developer and per-team metric. No new API calls needed.

**Files to change:**
- `backend/app/models/models.py` — add `review_round_count` to `pull_requests`
- `backend/app/services/github_sync.py` — compute after review sync per PR
- `backend/app/services/stats.py` — add to developer and team stats
- `backend/app/schemas/schemas.py` — add to `DeveloperStatsResponse`

---

### #8: AI Results Displayed as Raw JSON

**The Problem:** The 1:1 prep brief and team health check — potentially the most valuable features — render as `JSON.stringify(result, null, 2)` in a `<pre>` tag. A manager cannot use raw JSON for a 1:1 meeting.

**The Fix:** Build structured rendering components for each AI analysis type:
- `period_summary` as a paragraph
- `metrics_highlights` as a color-coded table by concern level
- `suggested_talking_points` as accordion cards
- Add Markdown export (`GET /api/reports/.../markdown`) for copy-pasting into Notion/Confluence

**Files to change:**
- `frontend/src/pages/AIAnalysis.tsx` — structured result rendering per analysis type
- `frontend/src/pages/DeveloperDetail.tsx` — structured AI section
- `backend/app/api/ai_analysis.py` — add Markdown export endpoint

---

### #9: No Slack/Notification Integration

**The Problem:** Every insight is pull-only. A team lead never sees alerts unless they open the dashboard. Stale PRs, workload spikes, and goal deadlines go unnoticed.

**The Fix:** Add a webhook dispatch system: after each sync, compute alert state and POST to a configurable `ALERT_WEBHOOK_URL`. This enables Slack integration with zero Slack-specific code. Example: "PR #432 has been waiting for review for 24 hours — reviewer: @alice"

**Competitive context:** Swarmia's Slack nudges are their #1 differentiating feature. This is the highest-ROI integration to add.

**Files to change:**
- `backend/app/config.py` — add `ALERT_WEBHOOK_URL` env var
- `backend/app/services/notifications.py` — new service for webhook dispatch
- `backend/app/main.py` — attach alert dispatch job to APScheduler after sync

---

### #10: No Sprint/Iteration Model

**The Problem:** No concept of a named sprint with defined dates. "Sprint 42: Mar 17-28" doesn't exist as data. No planned-vs-actual tracking, no sprint-over-sprint comparison, no carry-over detection.

**The Fix:** Add a `Sprint` model with `name`, `team`, `start_date`, `end_date`. Sprint stats compute: PRs opened/merged in sprint, issues closed, carry-over count from previous sprint.

**Files to change:**
- `backend/app/models/models.py` — new `Sprint` model
- `backend/app/services/sprints.py` — new service
- `backend/app/api/sprints.py` — new router
- `backend/app/schemas/schemas.py` — sprint request/response schemas

---

## 3. Management Friction Detection (Novel Feature)

This is a **unique differentiator** no competitor offers well. DevPulse should help management see when **their own process is causing friction**:

| Friction Signal | Data Available? | Currently Tracked? |
|----------------|----------------|-------------------|
| Issues reopened (unclear requirements) | Need `state_reason` from GitHub API | No |
| Issues with high comment count before any PR | `IssueComment` exists, no PR linkage | No |
| Issues bouncing between assignees | Only current assignee stored | No |
| Issues closed as "won't fix" (wasted work) | `state_reason` available in API | No |
| Issues without acceptance criteria | `Issue.body` stored | No analysis |
| PRs requiring 3+ review rounds (unclear spec) | `pr_reviews` data exists | No computation |

### Proposed Implementation

**Priority 1 — No new API calls needed:**
1. Add `comment_count` to `Issue` model (from `comments` key in GitHub API response, already fetched)
2. Parse `Issue.body` for checklist markers (`- [ ]`) — store `has_checklist` boolean
3. Store `state_reason` from GitHub issue close event (`completed` / `not_planned` / `reopened`)
4. Parse closing keywords from `PullRequest.body` for issue-PR linkage
5. Add label distribution endpoint: `GET /api/stats/issues/labels`

**Priority 2 — Small schema additions:**
6. Capture `milestone` from issues list API response (already in payload, never read)
7. Store plural `assignees` as JSONB (GitHub returns this, only singular `assignee` is captured)
8. Add `reopen_count` via state-transition detection during incremental sync

**Priority 3 — New API endpoints:**
9. `GET /api/stats/issues/quality` — per-issue quality signals
10. `GET /api/stats/issues/creator/{github_username}` — aggregates quality metrics for all issues created by a specific person

**Priority 4 — AI feedback loop:**
11. Extend 1:1 prep to include issue quality context for team leads
12. New `POST /api/ai/issue-quality` endpoint for AI-generated recommendations on how to write better issues

---

## 4. Competitive Positioning

### DevPulse Strengths (Already Ahead)

- **AI-powered 1:1 prep briefs** — Only mature enterprise tools offer this
- **Review quality classification** — Most competitors only track review count/speed, not depth
- **Collaboration silo/bus-factor detection** — Genuinely novel signal

### Critical Gaps vs Industry

| Feature | LinearB | Swarmia | Sleuth | Jellyfish | DevPulse |
|---------|---------|---------|--------|-----------|----------|
| DORA metrics | Yes | Yes | Yes | Yes | **No** |
| Slack nudges | Yes | Yes | No | No | **No** |
| Work categorization (feature/bug/debt) | Yes | Yes | No | Yes | **No** |
| CI/CD integration | Yes | Yes | Yes | No | **No** |
| Sprint analytics | Partial | Yes | No | No | **No** |
| Developer self-service | Yes | Yes | No | No | **No** |
| Industry benchmarks | Yes | No | No | No | **No** |
| Code churn analysis | Partial | No | No | No | **No** |
| PR risk scoring | No | No | No | No | **No** |
| Management friction feedback | No | No | No | No | **No** |

### Biggest Differentiation Opportunity

**"Management quality feedback loop"** — No competitor helps management see when THEIR process creates friction. DevPulse could be the first tool that tells a team lead: "Issues you create without checklists take 2.3x longer to close" or "Your team's PRs average 3.2 review rounds vs industry norm of 1.8."

### Feature Priorities by Competitive Impact

| Priority | Feature | Impact | Difficulty | Differentiation |
|----------|---------|--------|------------|-----------------|
| 1 | Slack notifications and PR nudges | Very High | Low-Medium | Medium |
| 2 | Work categorization (feature/bug/debt) | Very High | Medium | High |
| 3 | Code churn / rework analysis | High | Medium | High |
| 4 | DORA metrics (deploy frequency + lead time) | Very High | High | Medium |
| 5 | Sprint/delivery predictability analytics | High | Medium-High | Medium |
| 6 | PR risk scoring and review routing | High | Medium | High |
| 7 | External/industry benchmarks | Medium | Low | High |
| 8 | Automated standup/async status summaries | Medium-High | Low-Medium | Medium |
| 9 | Developer experience surveys | Medium | Medium | High |
| 10 | Focus time / meeting load analysis | Medium | High | Medium |

---

## 5. Implementation Roadmap

### Phase 1: "Make It Usable" (2-3 weeks)

*No new API calls, mostly frontend + using existing data*

1. Add developer self-access tokens (backend auth change)
2. Add Recharts + trend sparklines on Developer Detail
3. Render workload alerts on Dashboard
4. Add team status grid to Dashboard (one row per dev)
5. Fix draft PR filtering in all workload queries
6. Show percentiles on Developer Detail (`include_percentiles=true`)
7. Add token entry UI (login page)
8. Add toast notifications for all mutations
9. Structured AI result rendering (replace JSON.stringify)
10. Add error states and skeleton loading

### Phase 2: "Make It Smart" (3-4 weeks)

*New computations from existing data + small schema additions*

1. Stale PR list endpoint with per-PR age and blocking reviewer
2. Review round-trip count (`changes_requested_count` per PR)
3. `approved_at` derived field + "time waiting to merge after approval"
4. Merged-without-review detection
5. Issue-to-PR linkage via closing keyword parsing
6. PR labels + `merged_by` + `base_ref` + `head_ref` capture
7. Revert detection from PR title patterns
8. Collaboration heatmap + workload page + benchmarks page
9. Goals UI page with progress bars
10. 1:1 Prep + Team Health as proper UI features

### Phase 3: "Make It Proactive" (4-6 weeks)

*New integrations + novel features*

1. Slack webhook integration for alerts and PR nudges
2. Sprint model with planned-vs-actual tracking
3. Issue quality scoring (`comment_count`, `has_checklist`, `state_reason`, `reopen_count`)
4. Issue creator analytics (management friction feedback)
5. PR risk scoring (size + author experience + review depth)
6. Code churn analysis (`pr_files` table)
7. CI/CD check-run integration (GitHub Actions)
8. Quarterly performance report export (Markdown)
9. Configurable alert thresholds per team
10. Developer "invisible work" notes for non-code periods

### Phase 4: "Make It Best-in-Class" (6-8 weeks)

*Competitive differentiators*

1. DORA metrics (deploy frequency + change lead time via GitHub Actions)
2. Work categorization (feature/bug/debt) via label + AI classification
3. Review comment categorization (nit/blocker/architectural/praise)
4. Cross-repo dependency detection
5. Developer experience survey integration
6. Executive reporting dashboard (director/VP view)
7. Bulk 1:1 prep generation sorted by concern level
8. Industry benchmark comparison (from published data)

---

## 6. Detailed Findings by Perspective

### 6A. Team Lead / Engineering Manager Perspective

#### What Works
- Core metrics pipeline: developer-level stats, team aggregates, benchmarks with percentiles
- Collaboration graph with silo/bus-factor detection
- Workload heuristic with alert generation
- Goal tracking with 8-week history and auto-achievement
- AI 1:1 prep brief with previous-brief continuity

#### Critical Gaps

**The Dashboard tells you nothing actionable.** Seven aggregate numbers with no trends, no alerts, no links, no drill-down. A team lead opens this Monday morning and cannot determine what needs their attention.

**No stale PR list.** The system counts `prs_waiting_for_review` but returns no list of which PRs are waiting, how long each has been open, or who is blocking them. A team lead needs: `[{pr_title, pr_url, author, age_hours, reviewer_count, repo}]` sorted by staleness.

**No sprint model.** The trends endpoint supports `period_type="sprint"` with configurable length, but there is no named sprint entity, no sprint-vs-sprint comparison, no planned-vs-actual, and no carry-over tracking.

**Alerts are pull-only, not push.** `WorkloadAlert` objects are computed on demand but never persisted or pushed. No email, Slack, or webhook notification when a PR has been waiting 48 hours.

**Alert thresholds are hardcoded.** Workload score buckets, bus factor threshold (>70%), stale PR threshold (48h) — all hardcoded with no configuration surface.

**No review bottleneck ranking.** Can detect bus factors but cannot show "reviewer X has 8 pending reviews and their average response time is 31 hours."

**Goals have no UI.** The full CRUD API exists at `/api/goals` but no frontend page renders or manages goals. No progress bars, no creation form, no expiry alerts.

**AI results are raw JSON.** The 1:1 prep brief — potentially the most valuable feature — renders as `JSON.stringify(result, null, 2)` in a `<pre>` tag.

**No exportable reports.** No PDF, Markdown, or HTML export for performance reviews, 1:1 prep, or quarterly summaries.

**The workload score formula is wrong.** It adds `reviews_given` (a flow metric of completed work) to open PR/issue counts (point-in-time snapshots). High review output is a sign of productivity, not overload, but it pushes developers toward "overloaded" status.

---

### 6B. Individual Contributor Developer Perspective

#### The Core Problem: Surveillance vs Self-Service

DevPulse is currently built primarily as a management observation tool. The data model, metric selection, and UI are all oriented toward answering "what is this developer doing?" rather than "what does this developer need to know about their own work?"

#### Metric Fairness Issues

**PR count as productivity proxy is deeply unfair.** It systematically disadvantages:
- Infrastructure engineers shipping one foundational migration PR per sprint
- Senior developers doing heavy architectural review (more time reviewing = fewer PRs authored)
- Developers on long-running features (zero `prs_merged` in any 30-day window)
- No PR complexity signal exists anywhere in the data model

**Review quality scoring penalizes concise, precise reviewers.** A reviewer who catches a critical security vulnerability in two sentences gets classified as "rubber_stamp" or "minimal." Character count measures verbosity, not insight.

**The "underutilized" alert is harmful without context.** A developer on vacation, doing architecture work, mentoring juniors, or on incident response rotation will trigger this alert. There is no mechanism to add context for non-code work.

#### What Developers Actually Want

1. **"How long are my PRs sitting before someone looks at them?"** — `avg_time_to_first_review_hours` is computed but **never rendered** on the Developer Detail page
2. **"Who is blocking me?"** — No per-developer view of pending reviews on their PRs
3. **"Am I improving?"** — Trends are computed (`GET /api/stats/developer/{id}/trends`) but **never rendered**
4. **"Where do I stand vs the team?"** — Percentiles are computed (`?include_percentiles=true`) but **never requested** by the frontend
5. **Self-set goals** — Goals require admin token; developers cannot set their own

#### Recommendations for Developer Trust

1. **Flip the primary metric** from "PRs Opened" to "Avg Wait for First Review" — respect their time rather than measuring it
2. **Developer self-access tokens** — let developers see their own data without the admin token
3. **Let developers create their own goals** via `POST /api/goals/self`
4. **Add "invisible work" notes** — let developers annotate non-code periods (on-call, mentoring, architecture)
5. **Add methodology tooltips** — explain how every metric is computed so developers can trust and challenge them
6. **Surface "Your PRs Currently Blocking Others"** — create social accountability developers welcome, not surveillance they resent
7. **Remove or gate the "underutilized" alert** — require 3 consecutive zero-activity weeks before firing

---

### 6C. Code Review & PR Workflow

#### What's Tracked
- PR state (open/closed), is_draft (stored but never queried), is_merged, merged_at
- First review timestamp + time_to_first_review_s, time_to_merge_s
- PR size: additions, deletions, changed_files
- Review state (APPROVED/CHANGES_REQUESTED/COMMENTED/DISMISSED), quality tier
- Review comments with body, path, line

#### Critical Gaps

**No review round-trips.** Cannot distinguish a PR merged on first pass from one with 5 rounds of changes-requested/re-review cycles. The data exists in `pr_reviews` but is never sequenced or counted.

**No `approved_at` timestamp.** Cannot compute "time from approval to merge" — a critical phase where many PRs sit idle because the author doesn't realize they can merge.

**No merged-without-review detection.** PRs where `is_merged = True` and no review has `state = 'APPROVED'` are invisible. Detectable today from existing data with a simple join.

**No self-merge detection.** `merged_by` is not captured from the GitHub API (available in the PR detail response already fetched).

**Draft PRs are invisible.** `is_draft` is written to the DB but never filtered, counted, or surfaced. Every stat treats drafts as regular open PRs.

**Stale PR detection is too narrow.** Only catches PRs with no first review after 48h. Misses: PRs stale after `CHANGES_REQUESTED`, draft PRs open for 14+ days, PRs approved but not merged.

**No branch/release tracking.** `base_ref` and `head_ref` are not stored. Cannot distinguish hotfix PRs (targeting release branches) from feature PRs.

**No PR labels.** `PullRequest.labels` is never populated even though `Issue.labels` is. Cannot categorize PRs by type (feature/bug/refactor).

**No review comment categorization.** Comments stored verbatim but never analyzed for patterns (nit, blocker, architectural concern, praise).

#### Latency Breakdown Gap

| Phase | Definition | Computable? |
|---|---|---|
| Time to first review | `first_review_at - created_at` | Yes (exists) |
| Time in review rounds | Between review submissions | No |
| Time waiting for author response | After `CHANGES_REQUESTED` to next activity | No |
| Time from approval to merge | `merged_at - last APPROVED review` | No (easy to add) |
| Total cycle time | `time_to_merge_s` | Yes (exists) |

Only the first and last phases are captured. Phases 2-4 are where most process friction hides.

---

### 6D. Issue/Task Management & Management Friction

#### Current State

The `Issue` model stores: title, body, state, labels (JSONB), single assignee_id, created_at, updated_at, closed_at, time_to_close_s. `IssueComment` stores: author, body, created_at.

#### What's Missing for Issue Quality Analysis

| Signal | Data Needed | Currently Available? |
|--------|-------------|---------------------|
| Issues reopened | `state_reason` from API or timeline events | Not stored |
| Back-and-forth before work starts | Comment count + first linked PR timestamp | No PR linkage |
| Issues split into multiple PRs | Issue-to-PR linkage | Not implemented |
| Issues without acceptance criteria | `Issue.body` analysis | Body stored but never analyzed |
| Bouncing between assignees | Assignee history | Only current assignee stored |
| Issues closed as "won't fix" | `state_reason: "not_planned"` | Not stored |
| Issue creator quality patterns | `creator_github_username` | Not stored |

#### Issue Lifecycle Coverage

| Stage | Captured? |
|---|---|
| Creation | Yes (`Issue.created_at`) |
| Assignment | Partially (current only, history lost) |
| First comment | Derivable (`MIN(IssueComment.created_at)`) |
| First linked PR | No (no issue-PR linkage) |
| First review on linked PR | No |
| Merge | No |
| Close | Yes (`Issue.closed_at`, `time_to_close_s`) |

The only metric surfaced is `avg_time_to_close_issue_hours` — purely `closed_at - created_at`. No intermediate lifecycle stages are measured.

#### Priority Schema Additions for Issues

1. `comment_count` (Integer) — from `comments` key in GitHub API, already returned
2. `body_length` (Integer) + `has_checklist` (Boolean) — parse at sync time
3. `state_reason` (String) — from GitHub API response, already available
4. `creator_github_username` (String) — from `issue_data.get("user", {}).get("login")`
5. `milestone_title` (String) + `milestone_due_on` (Date) — from issues list API, already in payload
6. `assignees` (JSONB) — plural assignees from API response
7. `reopen_count` (Integer) — detect state transitions during sync

---

### 6E. QA / Release Quality Perspective

#### Gap Summary Table

| Gap | Data Available | Missing Data | Missing Computation | Effort |
|---|---|---|---|---|
| Bug Rate Tracking | `Issue.labels` stored | `PullRequest.labels` not stored; no PR-issue link table | No label-filtered queries | Medium |
| Revert Detection | `PullRequest.title/body` stored | `is_revert` flag; `reverted_pr_id` FK | No title-pattern matching at sync | Low |
| Hotfix Patterns | `time_to_merge_s` stored | PR labels; `merged_by`; `head_branch` | No fast-track detection logic | Medium |
| Post-merge Bug Linkage | `Issue.body` stored | `pr_issue_links` table | No closing-keyword parser | Medium |
| CI/CD Signals | Nothing | `pr_check_runs` table; `head_sha` on PR | No check-runs API calls | High |
| Release Quality | Nothing | `milestone` on PR + Issue | No release-scoped queries | Medium |
| Code Churn | PR totals only | `pr_files` table | No file-frequency queries | High |
| Review Effectiveness | Quality tier exists | Needs reverts + bug links | No outcome-based scoring | Medium |
| Risk Assessment | Size + draft + role available | `pr_files` for file context | No `RiskAssessment` service | Medium |
| Technical Debt | Additions/deletions stored | PR labels; `pr_files` | No deletion-ratio trend | Low-Medium |

#### Revert Detection (Lowest Effort, Highest Signal)

Revert PRs have a predictable signature: titles follow `Revert "<original PR title>"` and bodies contain `This reverts commit <sha>`. Add `is_revert` boolean to `PullRequest`, set at sync time via title pattern matching. Expose `prs_reverted_by_others` per developer — one of the strongest quality signals in software engineering. ~30 lines of code.

#### PR Risk Scoring (Computable from Existing Data)

Risk factors with no new tables needed:
- PR size > 500 additions: +0.2
- Author has < 5 merged PRs in this repo: +0.15
- Zero or only rubber-stamp reviews: +0.25
- Merged < 2 hours after opening: +0.3

New `GET /api/stats/pr/{id}/risk` endpoint returning `{risk_score: 0.0-1.0, risk_factors: [...]}`.

#### Code Churn (High Effort, Transformative)

Requires new `pr_files` table populated from `GET /repos/{owner}/{repo}/pulls/{number}/files` API. Enables:
- `change_frequency`: how many distinct PRs touched a file
- `contributor_count`: bus factor at the file level
- `churn_ratio`: files with high change frequency are where bugs cluster

---

### 6F. Frontend UX & Data Visualization

#### Current State Summary

The frontend surfaces roughly 20% of the backend's data. Every page uses the same two-pattern vocabulary: a grid of `StatCard` components (bold number on white card), or a flat `Table`. There are no charts, no trend visualizations, no real-time feedback, no alerts, and no UI exposure of eight fully-implemented backend features.

#### Missing Infrastructure

- **No charting library** — zero visualizations exist
- **No authentication flow** — no login page, no token entry UI; first-time users see 401 errors
- **No empty-state design** — each page has ad-hoc text strings
- **No error boundary** — uncaught render errors crash the entire app
- **No skeleton loading** — plain "Loading..." text causes layout shift
- **No toast notifications** — mutations have no success/error feedback

#### Missing Pages

| Page | Backend API | Status |
|------|------------|--------|
| Workload Overview | `GET /api/stats/workload` | Not built |
| Collaboration Matrix | `GET /api/stats/collaboration` | Not built |
| Benchmarks | `GET /api/stats/benchmarks` | Not built |
| Goals | `GET/POST /api/goals` | Not built |
| 1:1 Prep | `POST /api/ai/one-on-one-prep` | Not built |
| Team Health | `POST /api/ai/team-health` | Not built |

#### Missing Sections in Existing Pages

- **DeveloperDetail**: Trends charts, review quality breakdown, percentile placement, goals section, proper AI rendering
- **Dashboard**: Alert strip, team status grid, trend deltas, drill-down links
- **AIAnalysis**: 1:1 Prep and Team Health triggers, structured result rendering

#### Navigation Restructure Recommendation

```
Primary nav:   Dashboard | Team | Repos | Insights
Secondary nav: Sync (admin) | Settings
Within Insights: Benchmarks, Workload, Collaboration, Goals
Within Team/[id]: Stats, Trends, Goals, Review Quality, 1:1 Prep
```

#### Other UX Gaps

- **No comparison views** — cannot compare developers, periods, teams, or repos side by side
- **No export** — no CSV, PDF, or shareable URLs with date range in query params
- **No mobile responsiveness** — header nav doesn't collapse, tables overflow, no touch targets
- **No real-time updates** — only sync events poll (10s); all other queries use 30s stale time with no feedback
- **Date picker** — raw `<input type="date">` fields with no quick-select presets (Last 7d, Last 30d, Last quarter)

---

## The Single Most Impactful Change

If you could only do **one thing**, it would be: **Add the "Needs Attention" section to the Dashboard.**

The data already exists. The backend already computes workload alerts, stale PR counts, and goal deadlines. The frontend just needs to fetch `GET /api/stats/workload` and render the alerts prominently at the top of the Dashboard.

This one change transforms DevPulse from "a wall of numbers I check occasionally" into "the first thing I open every morning because it tells me what to act on."
