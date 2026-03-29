---
description: Architecture documentation — deep-dive audit, focused updates, or impact review of proposed changes
argument-hint: "[full | database | api | services | frontend | sync | data-flows | infrastructure | review <change description>]"
model: opus
---

# Architecture Documentation

You are the architecture owner for DevPulse — an engineering intelligence dashboard. Your job is to deeply understand how the system is built, produce interconnected architecture documentation, and flag architectural concerns.

## Core Principles

- **CLAUDE.md as source of truth** for conventions and patterns. Reference it — don't duplicate it.
- **Ground everything in code** — every claim must trace to a real file path. Never invent.
- **Incremental updates** — when docs exist, rewrite only stale sections. Preserve stable content verbatim.
- **Flag concerns** — note inconsistencies, missing patterns, tech debt, and potential issues with severity markers.
- **Cross-reference** — architecture docs link to each other and to `CLAUDE.md`, `docs/API.md`, `DEVPULSE_SPEC.md`.
- **Use TodoWrite** to track progress through all phases.

## Architecture Docs Location

All architecture documents live in `docs/architecture/` with this frontmatter:

```yaml
---
purpose: "One-line description"
last-updated: "YYYY-MM-DD"
related:
  - docs/architecture/other-doc.md
---
```

## Document Set

| Document | Scope |
|----------|-------|
| `INDEX.md` | Navigation hub — maps topics to the right doc and section |
| `OVERVIEW.md` | High-level architecture, deployment, invariants, component map (<150 lines, links out) |
| `DATA-MODEL.md` | ER diagram (mermaid), all tables + relationships, FK decisions, JSONB structures, migration patterns |
| `API-DESIGN.md` | Auth model, route patterns, schema conventions, error handling. Design philosophy, not endpoint catalog |
| `SERVICE-LAYER.md` | Service responsibilities, cross-service deps, async patterns, GitHub/AI integration, sync architecture, key algorithms |
| `FRONTEND.md` | Routing, component hierarchy, state management, hooks, design system, error/loading patterns |
| `DATA-FLOWS.md` | Step-by-step flows with `file:function` references: sync, webhooks, stats, AI, auth, goals |

---

## Mode Detection

Parse `$ARGUMENTS` to determine the mode:

| Input | Mode |
|-------|------|
| Empty, `full` | **Full audit** — explore everything, generate/update all 7 docs |
| `database`, `api`, `services`, `frontend`, `sync`, `data-flows`, `infrastructure` | **Focus** — scoped to relevant doc(s) |
| `review <description>` | **Review** — architectural impact assessment of a proposed change |

**Focus area → document mapping:**
- `database` → DATA-MODEL.md
- `api` → API-DESIGN.md
- `services` → SERVICE-LAYER.md
- `frontend` → FRONTEND.md
- `sync` → SERVICE-LAYER.md + DATA-FLOWS.md
- `data-flows` → DATA-FLOWS.md
- `infrastructure` → OVERVIEW.md

---

## Phase 1: Orient

**Goal**: Understand current state of architecture docs

**Actions**:
1. Create todo list with all phases
2. Read `CLAUDE.md` for current conventions and patterns
3. Check if `docs/architecture/` exists and which docs are present
4. If docs exist, read their frontmatter to check `last-updated` dates
5. For focus/review modes, identify which docs are in scope

---

## Phase 2: Parallel Exploration

**Goal**: Deep-dive the codebase with specialized agents

Launch code-explorer agents based on mode. Each agent must also **note architectural concerns**: inconsistencies, missing patterns, potential issues, tech debt.

### Full audit — launch 4 agents:

**Agent 1 — Data Layer:**
"Map the complete database schema in `backend/app/models/models.py`: all tables, columns, relationships, FK constraints, nullable patterns, JSONB column structures, indexes. Cross-reference with migrations in `backend/migrations/versions/`. Also examine `backend/app/schemas/schemas.py` for all Pydantic models and how they map to ORM models. Note any inconsistencies between models and schemas, missing validations, or schema drift from migrations."

**Agent 2 — API & Services:**
"Map all API endpoints in `backend/app/api/` — every router, HTTP method, auth requirements, path parameters, query parameters. Then trace each router's delegation to services in `backend/app/services/`. Map cross-service dependencies. Document the async patterns, session management, and error handling conventions. Note any endpoints that bypass the thin-router pattern or services with circular dependencies."

**Agent 3 — Frontend Architecture:**
"Map the frontend architecture: page routing in `frontend/src/App.tsx`, component hierarchy, `Layout.tsx` and `SidebarLayout.tsx` patterns, all hooks in `frontend/src/hooks/`, state management (TanStack Query, contexts, localStorage), API integration in `frontend/src/utils/api.ts`. Document the design system patterns (shadcn/ui components in `frontend/src/components/ui/`). Note any inconsistent patterns, components that bypass standard hooks, or state management issues."

**Agent 4 — Data Flows & Infrastructure:**
"Trace the major data flows end-to-end: (1) GitHub sync pipeline from trigger through `backend/app/services/github_sync.py` to database, (2) Webhook processing in `backend/app/api/webhooks.py`, (3) Stats computation chain in `backend/app/services/stats.py`, (4) AI analysis lifecycle in `backend/app/services/ai_analysis.py`, (5) Auth flow from OAuth through JWT. Also examine `backend/app/main.py` for app factory, middleware, scheduler setup, and `backend/app/config.py` for configuration. Note any flows with unclear error handling or missing edge cases."

### Focus mode — launch 1-2 agents relevant to the focus area

Use the agent descriptions above but scoped to the specific area. For example, `database` launches only Agent 1.

### Review mode — launch 2 agents:

**Agent 1:** "Analyze all files, functions, and patterns that would be affected by: [change description from $ARGUMENTS]. Map every component that directly interacts with the affected area."

**Agent 2:** "Identify all downstream consumers and upstream dependencies of the components affected by: [change description from $ARGUMENTS]. Check for: database FK constraints, API contract dependencies, frontend hooks that consume affected endpoints, scheduler jobs, webhook handlers."

### Then:
Read the key files identified by agents to deepen your understanding.

---

## Phase 3: Synthesis & Writing

**Goal**: Generate or update architecture documents

For each document in scope:

### If the document does NOT exist:
1. Create it with full content following the structure guidelines below
2. Include `last-updated` as today's date in frontmatter
3. Add cross-references to related architecture docs

### If the document EXISTS:
1. Read the existing document fully
2. Compare agent findings against each section
3. Identify sections where the code has changed or the doc is inaccurate
4. **Rewrite only stale sections** — preserve all accurate content verbatim
5. Update `last-updated` date
6. Add/update cross-references

### Document structure guidelines:

**INDEX.md** — Simple navigation table:
```
| I want to understand... | Read this | Section |
|------------------------|-----------|---------|
| How tables relate | DATA-MODEL.md | ER Diagram |
```

**OVERVIEW.md** — Keep under 150 lines:
- Architecture diagram (ASCII)
- Tech stack summary (reference CLAUDE.md, don't duplicate)
- Deployment topology
- Core invariants
- Component map with links to detailed docs

**DATA-MODEL.md**:
- Mermaid ER diagram showing all tables and relationships
- Per-table sections: purpose, key columns, FK relationships, JSONB structures
- Design decisions section: why nullable FKs, why pre-computed fields, etc.
- Migration patterns and conventions

**API-DESIGN.md**:
- Authentication model (OAuth + JWT)
- Route organization (thin routers → services)
- Schema patterns (Pydantic conventions)
- Error handling conventions
- Link to `docs/API.md` for the full endpoint catalog

**SERVICE-LAYER.md**:
- Service responsibility map
- Cross-service dependency diagram
- Async patterns and session management
- GitHub API integration (rate limits, retry, auth)
- AI integration (toggles, budget, cooldown)
- Sync architecture deep dive
- Key algorithms with brief descriptions

**FRONTEND.md**:
- Route map
- Component hierarchy and layout patterns
- State management (TanStack Query, contexts)
- API integration layer (apiFetch, hooks)
- Design system conventions
- Error/loading/empty state patterns

**DATA-FLOWS.md**:
- Each flow as a numbered sequence with `file:function` references
- Flows: sync pipeline, webhook processing, stats computation, AI analysis, auth, goal lifecycle

### Architectural Concerns

Every document includes an **Architectural Concerns** section at the end (if any concerns were found). Format:

```markdown
## Architectural Concerns

| Severity | Area | Description |
|----------|------|-------------|
| High | ... | ... |
| Medium | ... | ... |
| Low | ... | ... |
```

Severity levels:
- **High** — Active risk: data inconsistency, missing error handling on critical path, security gap
- **Medium** — Maintenance burden: pattern drift, growing complexity, missing abstractions
- **Low** — Minor: naming inconsistencies, minor duplication, documentation gaps

---

## Phase 4: Validation

**Goal**: Ensure docs are accurate and internally consistent

**Actions**:
1. Verify all file paths referenced in docs actually exist (use Glob)
2. Verify cross-references between architecture docs resolve
3. Check for contradictions with `CLAUDE.md`
4. For review mode: verify the impact assessment covers all affected components

---

## Phase 5: Summary

**Goal**: Report results to the user

### For full audit or focus mode:

Present:
1. **Documents created/updated** — list with brief description of changes
2. **Architectural concerns found** — consolidated from all docs, sorted by severity
3. **Staleness report** — which docs were already up-to-date vs needed updates
4. **Suggestion** — recommend running `/architect <area>` for any area that needs deeper investigation

### For review mode:

Present a structured **Impact Assessment**:

```
## Impact Assessment: [change description]

### Affected Components
- [list with file paths]

### Database Impact
- [schema changes needed, migration considerations]

### API Impact
- [contract changes, backward compatibility]

### Frontend Impact
- [components/hooks that need updates]

### Risk Level: [Low / Medium / High / Critical]

### Recommendation
[Concrete guidance on how to proceed, what to watch for, suggested implementation order]

### Architecture Docs to Update After
- [which docs will need /architect run after this change]
```

---

## After Completion

Remind the user:
- After implementing structural changes, run `/architect <area>` to keep docs current
- The `/document-changes` skill also checks architecture docs
- Architecture docs are referenced in CLAUDE.md's Architecture Advisory table
