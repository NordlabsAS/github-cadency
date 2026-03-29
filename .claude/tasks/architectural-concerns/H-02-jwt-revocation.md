# Task H-02: Add JWT Revocation for Deactivated Users

## Severity
High

## Status
todo

## Blocked By
None

## Blocks
None

## Description
JWTs have a 7-day expiry with no revocation mechanism. When a developer is deactivated (`is_active=False`), their previously-issued token continues to work until it expires. `get_current_user()` only decodes the JWT — it does not check the database.

### Problem
A deactivated developer retains full API access for up to 7 days after deactivation. The OAuth callback correctly rejects inactive users on new login, but existing tokens are not invalidated.

### Options
1. **DB check on every request** — `get_current_user()` queries `developers.is_active` on each call. Simple but adds a DB round-trip per request.
2. **Short-lived tokens + refresh** — Reduce JWT expiry to ~15 minutes, add a refresh token endpoint that checks `is_active`. More complex but better performance.
3. **Token version column** — Add `token_version` to `developers`. Increment on deactivation. Include version in JWT; reject if mismatched. One DB query per request but can be cached.

Option 1 is the simplest and most appropriate given the current single-server architecture.

### Files
- `backend/app/api/auth.py` — `get_current_user()`: add `is_active` check
- `backend/app/models/database.py` — may need session access pattern for auth

### Architecture Docs
- `docs/architecture/DATA-FLOWS.md` — Auth flow section
- `docs/architecture/API-DESIGN.md` — Authentication Model section
