# P3-07: Outbound Webhooks / Public API

> Priority: 3 (Nice-to-Have) | Effort: Medium | Impact: Medium
> Competitive gap: No outbound webhooks for triggering actions in other systems. No public API for external consumers.

## Context

DevPulse currently only receives inbound webhooks from GitHub. There's no way for external systems to consume DevPulse data or react to DevPulse events. This limits integration with existing toolchains (Datadog, PagerDuty, custom automations, BI tools).

## What to Build

### Outbound Webhooks

**Events that can trigger webhooks:**

| Event | Payload |
|-------|---------|
| `sync.completed` | Sync summary (repos synced, PR/issue counts, errors) |
| `sync.failed` | Sync event with error details |
| `pr.risk.high` | PR details + risk score + risk factors |
| `pr.stale` | PR details + days open |
| `workload.overloaded` | Developer details + workload score |
| `agreement.violated` | Agreement details + violation context |
| `dora.band_change` | DORA metric that changed bands (e.g., "lead time moved from High to Medium") |
| `survey.completed` | Survey aggregate results (no individual responses) |
| `snapshot.captured` | Daily/weekly metric snapshot |

**Webhook delivery:**
- HTTP POST with JSON payload + HMAC signature
- Retry with exponential backoff (3 attempts)
- Delivery log with status codes

### Public API (Read-Only)

Expose DevPulse metrics via authenticated API for external consumption:

- `GET /api/v1/metrics/team` — team-level metrics
- `GET /api/v1/metrics/developer/{id}` — developer metrics
- `GET /api/v1/metrics/dora` — DORA metrics
- `GET /api/v1/metrics/workload` — workload summary
- `GET /api/v1/metrics/benchmarks` — benchmark data
- `GET /api/v1/metrics/snapshots` — historical snapshots

**Auth:** API key-based (separate from JWT, long-lived, scoped).

## Backend Changes

### New Models

**`webhook_configs` table:**
```
id, name, url, secret (encrypted), events (JSONB array of event types),
headers (JSONB — custom headers), enabled (bool),
created_by (FK), created_at, updated_at
```

**`webhook_deliveries` table:**
```
id, config_id (FK), event_type, payload (JSONB),
status_code (int, nullable), response_body (text, nullable),
attempt (int), delivered_at, next_retry_at (nullable),
status ("pending" | "delivered" | "failed")
```

**`api_keys` table:**
```
id, name, key_hash (str, indexed), key_prefix (str — first 8 chars for identification),
scopes (JSONB — list of allowed endpoint patterns),
developer_id (FK — creator), expires_at (nullable),
last_used_at, created_at, revoked_at (nullable)
```

### New Service: `backend/app/services/webhooks_outbound.py`
- `emit_event(event_type, payload)` — fan-out to matching webhook configs
- `deliver_webhook(config, event_type, payload)` — HTTP POST with HMAC
- `retry_failed_deliveries()` — scheduled job for retries
- HMAC: `SHA-256(secret, json_payload)` in `X-DevPulse-Signature` header

### New Service: `backend/app/services/api_keys.py`
- `create_api_key(name, scopes)` — generate key, store hash
- `validate_api_key(key)` — verify key, check scopes, update last_used
- `revoke_api_key(id)` — soft-delete

### Integration Points
- After sync: `emit_event("sync.completed", sync_summary)`
- After risk scoring: `emit_event("pr.risk.high", pr_details)` if score > threshold
- After agreement check: `emit_event("agreement.violated", details)`
- After snapshot: `emit_event("snapshot.captured", snapshot_summary)`

### New Routers

**Webhook admin (`backend/app/api/webhook_config.py`):**
- `POST /api/webhooks/configs` — create webhook config
- `GET /api/webhooks/configs` — list configs
- `PATCH /api/webhooks/configs/{id}` — update config
- `DELETE /api/webhooks/configs/{id}` — delete config
- `POST /api/webhooks/configs/{id}/test` — send test event
- `GET /api/webhooks/deliveries` — delivery log

**Public API (`backend/app/api/v1/`):**
- Versioned API routes under `/api/v1/`
- API key auth middleware (separate from JWT)
- Rate limiting (configurable per key)

## Frontend Changes

### Webhook Admin Page (`/admin/settings/webhooks`)
- Webhook config list with enable/disable toggles
- Create/edit webhook: URL, events (checkbox list), secret (auto-generated)
- Test webhook button
- Delivery log with status indicators (green/red)
- Retry failed deliveries button

### API Key Management (`/admin/settings/api-keys`)
- Key list with prefix, scopes, last used, expiry
- Create key dialog (shows full key once, never again)
- Scope selection (which endpoints the key can access)
- Revoke key button

## Security
- Webhook secrets encrypted at rest
- HMAC signatures on all deliveries (prevent spoofing)
- API keys hashed (never stored in plaintext)
- Scoped API keys (principle of least privilege)
- Rate limiting on public API
- Delivery log doesn't store response bodies > 1KB (prevent data leaks)

## Testing
- Unit test HMAC signature generation and verification
- Unit test webhook fan-out (event → matching configs)
- Unit test retry logic with exponential backoff
- Unit test API key generation, validation, revocation
- Unit test scope checking
- Integration test webhook delivery with mock server

## Acceptance Criteria
- [ ] Outbound webhooks configurable per event type
- [ ] HMAC-signed webhook payloads
- [ ] Retry with exponential backoff (3 attempts)
- [ ] Webhook delivery log with status
- [ ] Test webhook button
- [ ] API key creation with scopes
- [ ] Public API endpoints for metrics (read-only)
- [ ] API key auth middleware with rate limiting
- [ ] Admin UI for webhook and API key management
