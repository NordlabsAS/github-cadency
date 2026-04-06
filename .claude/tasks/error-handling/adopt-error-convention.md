# Task: Adopt Shared Error Classification Convention

## Status: Not Started

## Problem

GitHub Cadency has minimal error handling — only a rate limit handler via slowapi and
scattered try/except in lifespan. No error classification, no Sentinel reporting. Per the
Nordlabs error handling convention, all projects must implement the three-component pattern.

## What Needs to Be Done

Since GitHub Cadency is a separate repo, it needs its own implementation (~200 lines).
Copy and adapt from the Claros reference implementation.

### 1. Implement ErrorCategory + ErrorClassifier (~100 lines)

Create `backend/app/libs/error_classifier.py`:
- ErrorCategory enum (identical to Claros)
- ClassifiedError dataclass
- ErrorClassifier base class
- CadencyErrorClassifier with app-specific rules:
  - GitHub API rate limits (403 with X-RateLimit-Remaining: 0) → rate_limited
  - GitHub API errors (5xx) → provider
  - GitHub App auth errors → user_config

### 2. Implement ErrorReporter (~150 lines)

Create `backend/app/libs/error_reporter.py`:
- Auth: Explicit API key (SENTINEL_API_KEY)
- source_id: org_id or installation_id

### 3. Register global exception handlers in main.py

### 4. Wire periodic flush in lifespan

### 5. Add env vars: SENTINEL_URL, SENTINEL_API_KEY

### 6. Register in Sentinel as project "github-cadency"

## Reference

**Step-by-step onboarding guide with copy-paste code**:
`C:\Projects\claros\docs\sentinel-onboarding.md`

**Canonical implementation** (Claros monorepo):
- `C:\Projects\claros\packages\observability\claros_observability\errors.py`
- `C:\Projects\claros\packages\observability\claros_observability\reporter.py`
- `C:\Projects\claros\packages\observability\claros_observability\exception_handlers.py`

**Compliance validation**: `bash C:\Projects\claros\scripts\check-error-convention.sh C:\Projects\github-cadency`

## Definition of Done

- [ ] ErrorCategory enum matches canonical
- [ ] CadencyErrorClassifier with GitHub API rules
- [ ] ErrorReporter wired with periodic flush
- [ ] Global exception handlers in main.py
- [ ] Tests for classification rules
- [ ] Registered in Sentinel
