# P3-02: GitLab Support (Multi-SCM)

> Priority: 3 (Enterprise Readiness) | Effort: Very Large | Impact: High
> Competitive gap: LinearB, Jellyfish, Swarmia, Sleuth all support GitHub + GitLab + Bitbucket. DevPulse is GitHub-only.

## Context

Teams on GitLab (self-managed or cloud) are entirely excluded from DevPulse. GitLab has significant market share, especially in enterprises that prefer self-hosted SCM. Supporting GitLab would roughly double the addressable market.

This is architecturally the largest change — it requires abstracting the GitHub-specific sync, webhook, and auth layers into SCM-agnostic interfaces.

## What to Build

### Architecture: SCM Provider Abstraction

Create a provider interface that both GitHub and GitLab implement:

```python
class SCMProvider(Protocol):
    async def list_repos(self) -> list[RepoData]
    async def list_pull_requests(self, repo, state, since) -> list[PRData]
    async def get_pr_reviews(self, repo, pr_number) -> list[ReviewData]
    async def get_pr_files(self, repo, pr_number) -> list[FileData]
    async def get_pr_comments(self, repo, pr_number) -> list[CommentData]
    async def get_pr_check_runs(self, repo, pr_number) -> list[CheckRunData]
    async def list_issues(self, repo, state, since) -> list[IssueData]
    async def get_issue_comments(self, repo, issue_number) -> list[CommentData]
    async def get_repo_tree(self, repo, branch) -> list[TreeFile]
    async def list_deployments(self, repo, env) -> list[DeploymentData]
    async def list_org_members(self) -> list[MemberData]
    async def verify_webhook(self, request) -> bool
```

### GitLab API Mapping

| GitHub Concept | GitLab Equivalent | API |
|---------------|-------------------|-----|
| Pull Request | Merge Request | `GET /projects/:id/merge_requests` |
| PR Review | MR Approval + Notes | `GET /projects/:id/merge_requests/:iid/approvals` + notes |
| Check Runs | Pipeline Jobs | `GET /projects/:id/pipelines/:id/jobs` |
| GitHub Actions | GitLab CI/CD | `GET /projects/:id/pipelines` |
| Organization | Group | `GET /groups/:id` |
| Webhook events | System hooks + project hooks | Similar event types |

### Key Differences to Handle

- **Review model:** GitLab doesn't have formal "reviews" like GitHub. Approvals + discussion notes are the equivalent. Review quality classification needs adaptation.
- **Merge method:** GitLab supports merge commits, squash, rebase, fast-forward. Affects cycle time calculation.
- **CI/CD:** GitLab CI is pipeline-based (stages + jobs) vs. GitHub's workflow-based model.
- **Auth:** GitLab uses personal access tokens or OAuth 2.0 (no GitHub App equivalent for self-managed).
- **Issue tracking:** GitLab issues are built-in (no separate issue tracker). May overlap with Jira integration.

## Backend Changes

### SCM Provider Interface (`backend/app/services/scm/`)
```
backend/app/services/scm/
├── __init__.py       # Provider protocol + factory
├── base.py           # SCMProvider protocol, data classes
├── github.py         # GitHub implementation (refactored from github_sync.py)
├── gitlab.py         # GitLab implementation
└── mapping.py        # Provider-agnostic data normalization
```

### Model Changes (`backend/app/models/models.py`)
- `repositories` table: add `scm_provider: str = "github"`, `scm_project_id: str`
- `developers` table: add `gitlab_username: str | None` (alongside existing github_username)
- Add unique constraints scoped by provider

### Refactor Sync Service (`backend/app/services/github_sync.py`)
- Extract GitHub-specific code into `scm/github.py`
- `SyncContext` becomes provider-agnostic, accepts `SCMProvider` instance
- `run_sync()` dispatches to appropriate provider based on repo's `scm_provider`
- Upsert helpers work with normalized data classes (not raw GitHub API responses)

### GitLab Sync (`backend/app/services/scm/gitlab.py`)
- GitLab REST API v4 client
- Auth: personal access token or OAuth 2.0
- Pagination: keyset-based (GitLab's preferred) or offset
- Rate limit handling (GitLab uses `Retry-After` header)
- MR → PR normalization (map GitLab fields to DevPulse schema)
- Review quality: classify based on approval + note content (adapted algorithm)

### Webhook Handler (`backend/app/api/webhooks.py`)
- Add GitLab webhook verification (token-based, not HMAC)
- Parse GitLab webhook events (merge_request, note, pipeline, etc.)
- Normalize to same internal event format as GitHub webhooks

### New Router / Config
- `POST /api/scm/providers` — configure GitLab instance (admin)
- `GET /api/scm/providers` — list configured SCM providers
- Config: `GITLAB_URL`, `GITLAB_TOKEN`, `GITLAB_GROUP_ID`

## Frontend Changes

### Provider Indicator
- Show SCM provider icon (GitHub/GitLab) next to repo names throughout UI
- PR links route to correct SCM provider URL

### SCM Configuration Page (`/admin/settings/scm`)
- Add GitLab instance configuration
- Connection test
- Group/project discovery

### Minimal UI Changes
- Existing pages should work with normalized data — minimal changes needed
- "Pull Request" terminology may need "Merge Request" variant for GitLab context

## Migration Strategy

1. **Phase 1:** Create SCM provider abstraction, refactor GitHub code into it (no behavior change)
2. **Phase 2:** Implement GitLab provider
3. **Phase 3:** Multi-provider sync (repos from different providers in same instance)
4. **Future:** Bitbucket provider (same abstraction)

## Dependencies
- `python-gitlab` or raw httpx for GitLab API
- No additional frontend dependencies

## Testing
- Unit test GitLab API response → normalized data mapping
- Unit test review quality classification for GitLab (approval-based)
- Unit test webhook parsing for GitLab events
- Integration test with mock GitLab API
- Regression test: ensure GitHub sync is unchanged after refactor

## Acceptance Criteria
- [ ] SCM provider abstraction layer created
- [ ] Existing GitHub sync refactored to use abstraction (no regressions)
- [ ] GitLab MR sync (fetch, normalize, store as pull_requests)
- [ ] GitLab review/approval sync with quality classification
- [ ] GitLab CI pipeline sync (mapped to check_runs)
- [ ] GitLab webhook handler
- [ ] GitLab deployment sync
- [ ] Multi-provider instance support (GitHub + GitLab repos coexist)
- [ ] Provider icon shown in UI next to repos/PRs
- [ ] Admin configuration page for GitLab
