# Task P3-06: Code Churn Analysis (File-Level Change Tracking)

## Phase
Phase 3 — Make It Proactive

## Status
pending

## Blocked By
- 04-github-sync-service

## Blocks
- P4-01-dora-metrics

## Description
Track which files are changed by each PR to enable code churn analysis — identifying hotspots where bugs cluster, files with concentrated ownership (bus factor at file level), and areas of the codebase that may need refactoring. Requires a new API call per PR during sync.

## Deliverables

### Database migration
New table: `pr_files`
- `id` (Integer, PK)
- `pr_id` (Integer, FK to pull_requests)
- `path` (Text, not null) — file path relative to repo root
- `additions` (Integer, default 0)
- `deletions` (Integer, default 0)
- `status` (String(20)) — "added", "modified", "removed", "renamed"

Index on `(pr_id)` and `(path)`.

### backend/app/services/github_sync.py (extend)
After upserting a PR, fetch file data:
```python
files_url = f"/repos/{repo.full_name}/pulls/{pr.number}/files"
files_data = await self._paginated_get(files_url)
for file_data in files_data:
    upsert_pr_file(session, pr.id, file_data)
```

Rate limit consideration: this adds 1 API call per PR. For incremental sync (only changed PRs), this is manageable. For full sync, paginate carefully and respect rate limits.

### backend/app/services/stats.py (extend)
New function: `async def get_code_churn(session, repo_id, date_from, date_to, limit=50)`

Returns files ranked by:
- `change_frequency` — number of distinct PRs that modified this file
- `total_additions` + `total_deletions` — cumulative churn volume
- `contributor_count` — number of distinct PR authors who modified this file
- `last_modified_at` — date of most recent PR touching this file

### backend/app/schemas/schemas.py (extend)
```python
class FileChurnEntry(BaseModel):
    path: str
    change_frequency: int
    total_additions: int
    total_deletions: int
    contributor_count: int
    last_modified_at: datetime

class CodeChurnResponse(BaseModel):
    repo_id: int
    repo_name: str
    hotspot_files: list[FileChurnEntry]
    directories_with_no_changes: list[str]  # potential abandoned areas
```

### backend/app/api/stats.py (extend)
New route: `GET /api/stats/repo/{id}/churn`
- Query params: `date_from`, `date_to`, `limit` (default 50)
- Returns `CodeChurnResponse`

## Performance Note
The `pr_files` table will grow large (avg ~10 files per PR). Add appropriate indexes and consider only syncing files for PRs modified in the last N days during incremental sync.
