"""Linear integration service — GraphQL client, sync orchestration, PR linking, developer mapping."""

import asyncio
import re
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models.models import (
    Developer,
    DeveloperIdentityMap,
    ExternalIssue,
    ExternalProject,
    ExternalSprint,
    IntegrationConfig,
    PRExternalIssueLink,
    PullRequest,
    SyncEvent,
)
from app.services.encryption import decrypt_token, encrypt_token

logger = get_logger(__name__)

LINEAR_API_URL = "https://api.linear.app/graphql"
LINEAR_ISSUE_KEY_PATTERN = re.compile(r"\b([A-Z]{2,10}-\d+)\b")


# --- Linear GraphQL Client ---


class LinearClient:
    """Read-only GraphQL client for the Linear API."""

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=LINEAR_API_URL,
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def query(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query against Linear. Returns the 'data' payload."""
        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = await self._client.post("", json=payload)

        # Handle 429 rate limit with single retry
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "60"))
            logger.warning(
                "Linear rate limited (429)",
                retry_after=retry_after,
                event_type="system.linear_api",
            )
            await asyncio.sleep(min(retry_after, 120))
            resp = await self._client.post("", json=payload)

        resp.raise_for_status()

        # Proactive slowdown when approaching rate limit
        remaining = int(resp.headers.get("X-RateLimit-Remaining", "100"))
        if remaining < 10:
            reset_at = int(resp.headers.get("X-RateLimit-Reset", "0"))
            wait_seconds = max(0, reset_at - int(time.time())) + 1
            logger.warning(
                "Linear rate limit approaching",
                remaining=remaining,
                wait_seconds=wait_seconds,
                event_type="system.linear_api",
            )
            await asyncio.sleep(min(wait_seconds, 60))

        body = resp.json()
        if "errors" in body:
            errors = body["errors"]
            msg = errors[0].get("message", str(errors)) if errors else "Unknown GraphQL error"
            raise LinearAPIError(msg, errors=errors)
        return body.get("data", {})

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


class LinearAPIError(Exception):
    def __init__(self, message: str, errors: list | None = None):
        super().__init__(message)
        self.errors = errors or []


# --- Key extraction ---


def extract_linear_keys(text: str) -> list[str]:
    """Extract Linear issue identifiers (e.g., ENG-123) from text. Returns unique keys."""
    if not text:
        return []
    return list(dict.fromkeys(LINEAR_ISSUE_KEY_PATTERN.findall(text)))


# --- Integration config helpers ---


async def get_integration(db: AsyncSession, integration_id: int) -> IntegrationConfig | None:
    return await db.get(IntegrationConfig, integration_id)


async def get_active_linear_integration(db: AsyncSession) -> IntegrationConfig | None:
    result = await db.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.type == "linear",
            IntegrationConfig.status == "active",
        )
    )
    return result.scalar_one_or_none()


async def create_integration(
    db: AsyncSession, type: str, display_name: str | None, api_key: str | None
) -> IntegrationConfig:
    config = IntegrationConfig(type=type, display_name=display_name or type.capitalize())
    if api_key:
        config.api_key = encrypt_token(api_key)
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


async def update_integration(
    db: AsyncSession, config: IntegrationConfig, updates: dict
) -> IntegrationConfig:
    for field, value in updates.items():
        if field == "api_key":
            if value:
                value = encrypt_token(value)
            else:
                value = None  # Clear the key rather than storing empty string
        setattr(config, field, value)
    config.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(config)
    return config


async def delete_integration(db: AsyncSession, config: IntegrationConfig) -> None:
    await db.delete(config)
    await db.commit()


async def test_linear_connection(db: AsyncSession, config: IntegrationConfig) -> dict:
    """Test Linear API connection. Returns {success, message, workspace_name}."""
    if not config.api_key:
        return {"success": False, "message": "No API key configured", "workspace_name": None}
    try:
        api_key = decrypt_token(config.api_key)
    except ValueError:
        return {"success": False, "message": "Failed to decrypt API key — encryption key may have changed", "workspace_name": None}

    try:
        async with LinearClient(api_key) as client:
            data = await client.query("{ viewer { id name email } organization { id name urlKey } }")
            org = data.get("organization", {})
            workspace_name = org.get("name")
            workspace_id = org.get("id")

            if workspace_id and workspace_id != config.workspace_id:
                config.workspace_id = workspace_id
                config.workspace_name = workspace_name
                await db.commit()

            return {
                "success": True,
                "message": f"Connected to workspace: {workspace_name}",
                "workspace_name": workspace_name,
            }
    except LinearAPIError as e:
        return {"success": False, "message": f"Linear API error: {e}", "workspace_name": None}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return {"success": False, "message": "Invalid API key — authentication failed", "workspace_name": None}
        return {"success": False, "message": f"HTTP error: {e.response.status_code}", "workspace_name": None}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {e}", "workspace_name": None}


async def get_primary_issue_source(db: AsyncSession) -> str:
    """Returns 'github' or 'linear'. Checks integration_config for is_primary_issue_source=True."""
    result = await db.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.is_primary_issue_source.is_(True),
            IntegrationConfig.status == "active",
        )
    )
    config = result.scalar_one_or_none()
    return config.type if config else "github"


async def set_primary_issue_source(db: AsyncSession, integration_id: int) -> IntegrationConfig:
    """Set the given integration as primary issue source, clearing any others."""
    await db.execute(
        IntegrationConfig.__table__.update().values(is_primary_issue_source=False)
    )
    config = await db.get(IntegrationConfig, integration_id)
    if not config:
        raise ValueError(f"Integration {integration_id} not found")
    config.is_primary_issue_source = True
    await db.commit()
    await db.refresh(config)
    return config


# --- Linear users (for mapping UI) ---


async def list_linear_users(db: AsyncSession, config: IntegrationConfig) -> dict:
    """Fetch Linear workspace users and annotate with existing developer mappings."""
    if not config.api_key:
        return {"users": [], "total": 0, "mapped_count": 0, "unmapped_count": 0}

    try:
        api_key = decrypt_token(config.api_key)
    except ValueError:
        logger.warning("Failed to decrypt Linear API key", error_category="user_config", event_type="system.sync")
        return {"users": [], "total": 0, "mapped_count": 0, "unmapped_count": 0}

    async with LinearClient(api_key) as client:
        data = await client.query("""
            {
                users {
                    nodes {
                        id
                        name
                        displayName
                        email
                        active
                    }
                }
            }
        """)

    users_data = data.get("users", {}).get("nodes", [])

    # Load existing mappings
    result = await db.execute(
        select(DeveloperIdentityMap).where(DeveloperIdentityMap.integration_type == "linear")
    )
    mappings = {m.external_user_id: m for m in result.scalars().all()}

    # Load developers for mapped names
    dev_ids = [m.developer_id for m in mappings.values()]
    devs_by_id = {}
    if dev_ids:
        result = await db.execute(select(Developer).where(Developer.id.in_(dev_ids)))
        devs_by_id = {d.id: d for d in result.scalars().all()}

    users = []
    mapped_count = 0
    for u in users_data:
        mapping = mappings.get(u["id"])
        dev = devs_by_id.get(mapping.developer_id) if mapping else None
        if mapping:
            mapped_count += 1
        users.append({
            "id": u["id"],
            "name": u.get("name", ""),
            "display_name": u.get("displayName"),
            "email": u.get("email"),
            "active": u.get("active", True),
            "mapped_developer_id": mapping.developer_id if mapping else None,
            "mapped_developer_name": dev.display_name if dev else None,
        })

    return {
        "users": users,
        "total": len(users),
        "mapped_count": mapped_count,
        "unmapped_count": len(users) - mapped_count,
    }


async def map_user(
    db: AsyncSession, config: IntegrationConfig, external_user_id: str, developer_id: int
) -> DeveloperIdentityMap:
    """Manually map a Linear user to a DevPulse developer."""
    result = await db.execute(
        select(DeveloperIdentityMap).where(
            DeveloperIdentityMap.developer_id == developer_id,
            DeveloperIdentityMap.integration_type == "linear",
        )
    )
    mapping = result.scalar_one_or_none()
    if mapping:
        mapping.external_user_id = external_user_id
        mapping.mapped_by = "admin"
    else:
        mapping = DeveloperIdentityMap(
            developer_id=developer_id,
            integration_type="linear",
            external_user_id=external_user_id,
            mapped_by="admin",
        )
        db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    return mapping


# --- Sync orchestration ---


MAX_LOG_ENTRIES = 500


class LinearSyncCancelled(Exception):
    """Raised when a Linear sync is cancelled by user request."""
    pass


def _add_log(sync_event: SyncEvent, level: str, msg: str) -> None:
    """Append a structured log entry to sync_event.log_summary."""
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "level": level.lower(),
        "msg": msg[:200],
    }
    logs = list(sync_event.log_summary or [])
    if len(logs) >= MAX_LOG_ENTRIES:
        # Drop oldest info entries first
        for i, e in enumerate(logs):
            if e.get("level") == "info":
                logs.pop(i)
                break
        else:
            logs.pop(0)
    logs.append(entry)
    sync_event.log_summary = logs


async def _check_linear_cancel(db: AsyncSession, sync_event: SyncEvent) -> None:
    """Check if cancellation was requested. Raises LinearSyncCancelled if so."""
    result = await db.execute(
        select(SyncEvent.cancel_requested).where(SyncEvent.id == sync_event.id)
    )
    if result.scalar_one_or_none():
        _add_log(sync_event, "warn", "Sync cancelled by user")
        sync_event.status = "cancelled"
        sync_event.completed_at = datetime.now(timezone.utc)
        await db.commit()
        raise LinearSyncCancelled("Linear sync cancelled by user")


async def run_linear_sync(
    db: AsyncSession,
    integration_id: int,
    sync_event_id: int | None = None,
    triggered_by: str = "manual",
) -> SyncEvent:
    """Full Linear sync orchestration. Creates a SyncEvent if sync_event_id not provided."""
    config = await db.get(IntegrationConfig, integration_id)
    if not config or config.status != "active" or not config.api_key:
        raise ValueError("Linear integration not active or missing API key")

    # Concurrency guard: skip if another Linear sync is already running
    active = (await db.execute(
        select(SyncEvent.id).where(
            SyncEvent.sync_type == "linear",
            SyncEvent.status == "started",
        ).limit(1)
    )).scalar_one_or_none()
    if active:
        logger.info(
            "Skipping Linear sync — another sync already in progress",
            active_sync_id=active,
            event_type="system.sync",
        )
        raise ValueError("Linear sync already in progress")

    api_key = decrypt_token(config.api_key)

    # Create or load sync event
    if sync_event_id:
        sync_event = await db.get(SyncEvent, sync_event_id)
    else:
        sync_event = SyncEvent(
            sync_type="linear",
            status="started",
            started_at=datetime.now(timezone.utc),
            triggered_by=triggered_by,
            sync_scope="Linear workspace sync",
        )
        db.add(sync_event)
        await db.commit()
        await db.refresh(sync_event)

    logger.info(
        "Starting Linear sync",
        sync_id=sync_event.id,
        integration_id=integration_id,
        event_type="system.sync",
    )
    _add_log(sync_event, "info", "Starting Linear workspace sync")

    counts = {"projects": 0, "sprints": 0, "issues": 0, "pr_links": 0, "mapped": 0}

    try:
        async with LinearClient(api_key) as client:
            # 1. Sync projects
            await _check_linear_cancel(db, sync_event)
            sync_event.current_step = "syncing_projects"
            _add_log(sync_event, "info", "Syncing Linear projects...")
            await db.commit()
            counts["projects"] = await sync_linear_projects(client, db, integration_id)
            _add_log(sync_event, "info", f"Synced {counts['projects']} projects")

            # 2. Sync cycles (sprints)
            await _check_linear_cancel(db, sync_event)
            sync_event.current_step = "syncing_cycles"
            _add_log(sync_event, "info", "Syncing Linear cycles (sprints)...")
            await db.commit()
            counts["sprints"] = await sync_linear_cycles(client, db, integration_id)
            _add_log(sync_event, "info", f"Synced {counts['sprints']} sprints")

            # 3. Sync issues (since last sync or all)
            await _check_linear_cancel(db, sync_event)
            since = config.last_synced_at
            sync_event.current_step = "syncing_issues"
            mode = f"incremental since {since.strftime('%Y-%m-%d %H:%M')}" if since else "full scan"
            _add_log(sync_event, "info", f"Syncing issues ({mode})...")
            await db.commit()
            counts["issues"] = await sync_linear_issues(
                client, db, integration_id, since=since, sync_event=sync_event
            )
            _add_log(sync_event, "info", f"Synced {counts['issues']} issues")

            # 4. Link PRs to external issues (incremental after first sync)
            await _check_linear_cancel(db, sync_event)
            sync_event.current_step = "linking_prs"
            _add_log(sync_event, "info", "Linking PRs to external issues...")
            await db.commit()
            counts["pr_links"] = await link_prs_to_external_issues(db, integration_id, since=since)
            _add_log(sync_event, "info", f"Created {counts['pr_links']} new PR-issue links")

            # 5. Fetch Linear users for accurate identity mapping, then auto-map
            await _check_linear_cancel(db, sync_event)
            sync_event.current_step = "mapping_developers"
            _add_log(sync_event, "info", "Auto-mapping developers...")
            await db.commit()
            linear_users = await _fetch_linear_users(client)
            mapped, unmapped = await auto_map_developers(db, integration_id, linear_users=linear_users)
            counts["mapped"] = mapped
            _add_log(sync_event, "info", f"Mapped {mapped} developers ({unmapped} unmapped)")

        # Update integration
        config.last_synced_at = datetime.now(timezone.utc)
        config.error_message = None

        # Update sync event
        sync_event.status = "completed"
        sync_event.completed_at = datetime.now(timezone.utc)
        sync_event.repos_synced = counts["issues"]  # reuse field for issue count
        sync_event.current_step = None
        started = sync_event.started_at
        if started:
            sync_event.duration_s = int((sync_event.completed_at - started).total_seconds())
        _add_log(sync_event, "info", f"Sync completed: {counts}")

        await db.commit()

        logger.info(
            "Linear sync completed",
            sync_id=sync_event.id,
            counts=counts,
            event_type="system.sync",
        )

        # Trigger planning notification evaluation after successful sync
        try:
            from app.services.notifications import evaluate_all_alerts
            await evaluate_all_alerts(db)
        except Exception as eval_err:
            logger.warning(
                "Post-sync notification evaluation failed",
                error=str(eval_err),
                event_type="system.notifications",
            )

    except LinearSyncCancelled:
        logger.info("Linear sync cancelled", sync_id=sync_event.id, event_type="system.sync")
        # Status already set by _check_linear_cancel

    except Exception as e:
        sync_event.status = "failed"
        sync_event.completed_at = datetime.now(timezone.utc)
        sync_event.current_step = None
        config.error_message = str(e)[:500]
        _add_log(sync_event, "error", f"Sync failed: {str(e)[:180]}")
        await db.commit()

        from app.main import _classifier

        classified = _classifier.classify(e)
        log_level = logger.error if classified.category.value == "app_bug" else logger.warning
        log_level(
            "Linear sync failed",
            sync_id=sync_event.id,
            error=str(e)[:200],
            exc_type=type(e).__name__,
            error_category=classified.category.value,
            event_type="system.sync",
        )
        raise

    return sync_event


# --- Individual sync functions ---


PROJECTS_QUERY = """
query($cursor: String) {
    projects(first: 50, after: $cursor, filter: { state: { nin: ["canceled"] } }) {
        pageInfo { hasNextPage endCursor }
        nodes {
            id
            name
            slugId
            state
            health
            startDate
            targetDate
            progress
            url
            lead { id email }
        }
    }
}
"""


async def sync_linear_projects(client: LinearClient, db: AsyncSession, integration_id: int) -> int:
    """Sync all non-cancelled projects from Linear. Returns count synced."""
    count = 0
    cursor = None

    while True:
        data = await client.query(PROJECTS_QUERY, {"cursor": cursor})
        projects = data.get("projects", {})
        nodes = projects.get("nodes", [])

        for p in nodes:
            result = await db.execute(
                select(ExternalProject).where(ExternalProject.external_id == p["id"])
            )
            project = result.scalar_one_or_none()
            if not project:
                project = ExternalProject(
                    integration_id=integration_id,
                    external_id=p["id"],
                    name=p.get("name", ""),
                )
                db.add(project)
            else:
                project.name = p.get("name", "")
            project.key = p.get("slugId")
            project.status = _map_project_state(p.get("state"))
            project.health = _map_project_health(p.get("health"))
            project.start_date = _parse_date(p.get("startDate"))
            project.target_date = _parse_date(p.get("targetDate"))
            project.progress_pct = p.get("progress")
            project.url = p.get("url")

            # Map lead if possible
            lead = p.get("lead")
            if lead and lead.get("email"):
                project.lead_id = await _resolve_developer_by_email(db, lead["email"])

            count += 1

        await db.commit()

        page_info = projects.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    logger.info("Synced Linear projects", count=count, event_type="system.sync")
    return count


CYCLES_QUERY = """
query($cursor: String) {
    cycles(first: 50, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
            id
            name
            number
            startsAt
            endsAt
            completedAt
            progress
            scopeHistory
            completedScopeHistory
            url
            team { id key name }
            issues { nodes { id } }
            uncompletedIssuesUponClose { nodes { id } }
        }
    }
}
"""


async def sync_linear_cycles(client: LinearClient, db: AsyncSession, integration_id: int) -> int:
    """Sync all cycles from Linear. Returns count synced."""
    count = 0
    cursor = None

    while True:
        data = await client.query(CYCLES_QUERY, {"cursor": cursor})
        cycles = data.get("cycles", {})
        nodes = cycles.get("nodes", [])

        for c in nodes:
            result = await db.execute(
                select(ExternalSprint).where(ExternalSprint.external_id == c["id"])
            )
            sprint = result.scalar_one_or_none()
            if not sprint:
                sprint = ExternalSprint(
                    integration_id=integration_id,
                    external_id=c["id"],
                    state="active",
                )
                db.add(sprint)

            sprint.name = c.get("name")
            sprint.number = c.get("number")

            team = c.get("team") or {}
            sprint.team_key = team.get("key")
            sprint.team_name = team.get("name")

            sprint.start_date = _parse_date(c.get("startsAt"))
            sprint.end_date = _parse_date(c.get("endsAt"))

            # Determine state
            if c.get("completedAt"):
                sprint.state = "closed"
            elif sprint.start_date and sprint.end_date:
                now = datetime.now(timezone.utc).date()
                if now < sprint.start_date:
                    sprint.state = "future"
                else:
                    sprint.state = "active"
            else:
                sprint.state = "active"

            sprint.url = c.get("url")

            # Scope metrics from history arrays
            scope_history = c.get("scopeHistory") or []
            completed_history = c.get("completedScopeHistory") or []

            total_issues = len((c.get("issues") or {}).get("nodes", []))
            uncompleted = len((c.get("uncompletedIssuesUponClose") or {}).get("nodes", []))

            if scope_history:
                # Points-based scope from Linear history arrays
                sprint.planned_scope = scope_history[0]
                initial_scope = scope_history[0]
                final_scope = scope_history[-1]
                sprint.added_scope = max(0, final_scope - initial_scope) if initial_scope is not None else None
                sprint.completed_scope = completed_history[-1] if completed_history else None
                sprint.scope_unit = "points"
            elif c.get("completedAt"):
                # Fallback to issue counts for closed cycles without scope history
                sprint.planned_scope = total_issues
                sprint.completed_scope = total_issues - uncompleted
                sprint.added_scope = None
                sprint.scope_unit = "issues"
            else:
                sprint.planned_scope = None
                sprint.completed_scope = None
                sprint.added_scope = None
                sprint.scope_unit = None
            sprint.cancelled_scope = uncompleted if c.get("completedAt") else None

            count += 1

        await db.commit()

        page_info = cycles.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    logger.info("Synced Linear cycles", count=count, event_type="system.sync")
    return count


_ISSUES_FIELDS = """
        pageInfo { hasNextPage endCursor }
        nodes {
            id
            identifier
            title
            description
            state { name type }
            priority
            priorityLabel
            estimate
            labels { nodes { name } }
            assignee { id email displayName }
            creator { id email displayName }
            project { id }
            cycle { id }
            parent { id }
            createdAt
            startedAt
            completedAt
            canceledAt
            updatedAt
            url
        }
"""

ISSUES_QUERY = """
query($cursor: String, $updatedAfter: DateTime) {
    issues(
        first: 50,
        after: $cursor,
        filter: { updatedAt: { gte: $updatedAfter } }
    ) {""" + _ISSUES_FIELDS + """    }
}
"""

ISSUES_QUERY_ALL = """
query($cursor: String) {
    issues(first: 50, after: $cursor) {""" + _ISSUES_FIELDS + """    }
}
"""


def _classify_external_issue(issue: ExternalIssue, rules: list) -> tuple[str, str]:
    """Classify an external issue using the same work category rules as GitHub issues."""
    from app.services.work_categories import classify_work_item_with_rules

    labels = issue.labels if isinstance(issue.labels, list) else []
    return classify_work_item_with_rules(labels, issue.title, rules, issue_type=issue.issue_type)


async def sync_linear_issues(
    client: LinearClient,
    db: AsyncSession,
    integration_id: int,
    since: datetime | None = None,
    sync_event: SyncEvent | None = None,
) -> int:
    """Sync issues from Linear updated since the given timestamp. Returns count synced."""
    # Load classification rules once for the entire sync
    from app.services.work_categories import get_all_rules
    classification_rules = await get_all_rules(db)

    count = 0
    cursor = None
    updated_after = since.isoformat() if since else None

    while True:
        variables: dict = {"cursor": cursor}
        if updated_after:
            variables["updatedAfter"] = updated_after
            query = ISSUES_QUERY
        else:
            query = ISSUES_QUERY_ALL

        data = await client.query(query, variables)
        issues = data.get("issues", {})
        nodes = issues.get("nodes", [])

        for i in nodes:
            result = await db.execute(
                select(ExternalIssue).where(ExternalIssue.external_id == i["id"])
            )
            issue = result.scalar_one_or_none()
            if not issue:
                issue = ExternalIssue(
                    integration_id=integration_id,
                    external_id=i["id"],
                    identifier=i.get("identifier", ""),
                    title=i.get("title", "")[:500],
                )
                db.add(issue)
            else:
                issue.identifier = i.get("identifier", "")
                issue.title = i.get("title", "")[:500]
            desc = i.get("description") or ""
            issue.description_length = len(desc)

            # State mapping
            state = i.get("state") or {}
            issue.status = state.get("name")
            issue.status_category = _map_status_type(state.get("type"))

            # Issue type from labels
            issue.issue_type = _detect_issue_type(i)

            issue.priority = i.get("priority", 0)
            issue.priority_label = i.get("priorityLabel")
            issue.estimate = i.get("estimate")
            issue.labels = [l["name"] for l in (i.get("labels") or {}).get("nodes", [])]

            # Assignee
            assignee = i.get("assignee")
            if assignee:
                issue.assignee_email = assignee.get("email")
                issue.assignee_developer_id = await _resolve_developer_by_email(
                    db, assignee.get("email")
                )

            # Creator
            creator = i.get("creator")
            if creator:
                issue.creator_email = creator.get("email")
                issue.creator_developer_id = await _resolve_developer_by_email(
                    db, creator.get("email")
                )

            # Foreign keys to other synced entities
            project_data = i.get("project")
            if project_data:
                issue.project_id = await _resolve_external_project(db, project_data["id"])
            else:
                issue.project_id = None

            cycle_data = i.get("cycle")
            if cycle_data:
                issue.sprint_id = await _resolve_external_sprint(db, cycle_data["id"])
            else:
                issue.sprint_id = None

            parent_data = i.get("parent")
            if parent_data:
                issue.parent_issue_id = await _resolve_external_issue(db, parent_data["id"])

            # Timestamps
            issue.created_at = _parse_datetime(i.get("createdAt")) or datetime.now(timezone.utc)
            issue.started_at = _parse_datetime(i.get("startedAt"))
            issue.completed_at = _parse_datetime(i.get("completedAt"))
            issue.cancelled_at = _parse_datetime(i.get("canceledAt"))
            issue.updated_at = _parse_datetime(i.get("updatedAt")) or datetime.now(timezone.utc)
            issue.url = i.get("url")

            # Compute durations
            if issue.status_category != "triage" and issue.created_at and issue.started_at:
                issue.triage_duration_s = int(
                    (issue.started_at - issue.created_at).total_seconds()
                )
            if issue.started_at and issue.completed_at:
                issue.cycle_time_s = int(
                    (issue.completed_at - issue.started_at).total_seconds()
                )

            # Work categorization (same pipeline as GitHub issues)
            if issue.work_category_source != "manual":
                cat, source = _classify_external_issue(issue, classification_rules)
                issue.work_category = cat
                issue.work_category_source = source

            count += 1

            if count % 50 == 0:
                if sync_event:
                    sync_event.current_repo_issues_done = count
                    await _check_linear_cancel(db, sync_event)
                await db.commit()

        if sync_event:
            sync_event.current_repo_issues_done = count
        await db.commit()

        page_info = issues.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    logger.info("Synced Linear issues", count=count, event_type="system.sync")
    return count


# --- PR ↔ External Issue linking ---


async def link_prs_to_external_issues(
    db: AsyncSession, integration_id: int, since: datetime | None = None
) -> int:
    """Scan PR titles and branches for Linear issue keys, create links. Returns count created.

    When ``since`` is provided, only PRs updated after that timestamp are scanned
    (incremental linking). Pass ``None`` for a full scan on first sync.
    """
    # Load all known identifiers
    result = await db.execute(
        select(ExternalIssue.id, ExternalIssue.identifier).where(
            ExternalIssue.integration_id == integration_id
        )
    )
    issue_map = {row.identifier: row.id for row in result.all()}
    if not issue_map:
        return 0

    # Load existing links to avoid duplicates
    result = await db.execute(
        select(PRExternalIssueLink.pull_request_id, PRExternalIssueLink.external_issue_id)
    )
    existing_links = {(row[0], row[1]) for row in result.all()}

    # Process PRs in batches
    count = 0
    batch_size = 500
    offset = 0

    while True:
        pr_query = (
            select(PullRequest.id, PullRequest.title, PullRequest.head_branch, PullRequest.body)
            .order_by(PullRequest.id)
            .limit(batch_size)
            .offset(offset)
        )
        if since is not None:
            pr_query = pr_query.where(PullRequest.updated_at >= since)
        result = await db.execute(pr_query)
        rows = result.all()
        if not rows:
            break

        for pr_id, title, branch, body in rows:
            sources = [
                ("title", title or ""),
                ("branch", branch or ""),
                ("body", body or ""),
            ]
            for source_name, text in sources:
                keys = extract_linear_keys(text)
                for key in keys:
                    issue_id = issue_map.get(key)
                    if issue_id and (pr_id, issue_id) not in existing_links:
                        existing_links.add((pr_id, issue_id))
                        link = PRExternalIssueLink(
                            pull_request_id=pr_id,
                            external_issue_id=issue_id,
                            link_source=source_name,
                        )
                        db.add(link)
                        count += 1

        offset += batch_size

    if count:
        await db.commit()

    logger.info("Linked PRs to external issues", count=count, event_type="system.sync")
    return count


# --- Developer auto-mapping ---


async def _fetch_linear_users(client: LinearClient) -> list[dict]:
    """Fetch all workspace users from Linear. Returns list of {id, email, displayName}."""
    data = await client.query("""
        {
            users {
                nodes {
                    id
                    name
                    displayName
                    email
                    active
                }
            }
        }
    """)
    return data.get("users", {}).get("nodes", [])


async def auto_map_developers(
    db: AsyncSession,
    integration_id: int,
    linear_users: list[dict] | None = None,
) -> tuple[int, int]:
    """Auto-map Linear users to DevPulse developers by email match.

    When ``linear_users`` is provided, uses the list to resolve the correct
    ``external_user_id`` for each mapping (fixing the empty-string bug).

    Returns (mapped_count, unmapped_count).
    """
    # Build email → Linear user ID lookup from the users list
    email_to_linear_id: dict[str, str] = {}
    if linear_users:
        for u in linear_users:
            u_email = u.get("email")
            if u_email:
                email_to_linear_id[u_email.lower()] = u["id"]

    # Forward-fix: backfill existing mappings with empty external_user_id
    if email_to_linear_id:
        result = await db.execute(
            select(DeveloperIdentityMap).where(
                DeveloperIdentityMap.integration_type == "linear",
                DeveloperIdentityMap.external_user_id == "",
                DeveloperIdentityMap.external_email.isnot(None),
            )
        )
        for stale_mapping in result.scalars().all():
            linear_id = email_to_linear_id.get((stale_mapping.external_email or "").lower())
            if linear_id:
                stale_mapping.external_user_id = linear_id

    # Get unique assignee emails from external issues
    result = await db.execute(
        select(ExternalIssue.assignee_email)
        .where(
            ExternalIssue.integration_id == integration_id,
            ExternalIssue.assignee_email.isnot(None),
        )
        .distinct()
    )
    external_emails = {row[0] for row in result.all()}

    # Get already mapped developer IDs for linear
    result = await db.execute(
        select(DeveloperIdentityMap.external_email).where(
            DeveloperIdentityMap.integration_type == "linear",
            DeveloperIdentityMap.external_email.isnot(None),
        )
    )
    already_mapped_emails = {row[0] for row in result.all()}

    unmapped_emails = external_emails - already_mapped_emails
    mapped = 0
    unmapped = 0

    for email in unmapped_emails:
        result = await db.execute(
            select(Developer).where(
                func.lower(Developer.email) == email.lower(),
                Developer.is_active.is_(True),
            )
        )
        dev = result.scalar_one_or_none()
        if dev:
            # Check if this developer already has a linear mapping
            result2 = await db.execute(
                select(DeveloperIdentityMap).where(
                    DeveloperIdentityMap.developer_id == dev.id,
                    DeveloperIdentityMap.integration_type == "linear",
                )
            )
            if not result2.scalar_one_or_none():
                linear_id = email_to_linear_id.get(email.lower(), "")
                mapping = DeveloperIdentityMap(
                    developer_id=dev.id,
                    integration_type="linear",
                    external_user_id=linear_id,
                    external_email=email,
                    mapped_by="auto",
                )
                db.add(mapping)
                mapped += 1
        else:
            unmapped += 1

    if mapped:
        await db.commit()

    logger.info(
        "Auto-mapped developers",
        mapped=mapped,
        unmapped=unmapped,
        event_type="system.sync",
    )
    return mapped, unmapped


# --- Helper functions ---


def _map_project_state(state: str | None) -> str | None:
    """Map Linear project state to normalized status."""
    mapping = {
        "planned": "planned",
        "started": "started",
        "paused": "paused",
        "completed": "completed",
        "canceled": "cancelled",
        "cancelled": "cancelled",
    }
    return mapping.get(state, state)


def _map_project_health(health: str | None) -> str | None:
    """Map Linear project health to normalized health."""
    mapping = {
        "onTrack": "on_track",
        "atRisk": "at_risk",
        "offTrack": "off_track",
    }
    return mapping.get(health, health)


def _map_status_type(status_type: str | None) -> str | None:
    """Map Linear workflow state type to normalized status category."""
    mapping = {
        "triage": "triage",
        "backlog": "backlog",
        "unstarted": "todo",
        "started": "in_progress",
        "completed": "done",
        "canceled": "cancelled",
        "cancelled": "cancelled",
    }
    return mapping.get(status_type, status_type)


def _detect_issue_type(issue_data: dict) -> str | None:
    """Detect issue type from Linear issue data (labels or other signals)."""
    labels = [l["name"].lower() for l in (issue_data.get("labels") or {}).get("nodes", [])]
    if "bug" in labels:
        return "bug"
    if "feature" in labels:
        return "feature"
    if "improvement" in labels:
        return "improvement"
    parent = issue_data.get("parent")
    if parent:
        return "sub_issue"
    return "issue"


def _parse_date(value: str | None):
    """Parse ISO date string to date object."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string to datetime object."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


async def _resolve_developer_by_email(db: AsyncSession, email: str | None) -> int | None:
    """Look up a developer by email, return their ID or None."""
    if not email:
        return None
    result = await db.execute(
        select(Developer.id).where(
            func.lower(Developer.email) == email.lower(),
            Developer.is_active.is_(True),
        )
    )
    row = result.first()
    return row[0] if row else None


async def _resolve_external_project(db: AsyncSession, external_id: str) -> int | None:
    """Look up an external project by its Linear ID, return internal ID or None."""
    result = await db.execute(
        select(ExternalProject.id).where(ExternalProject.external_id == external_id)
    )
    row = result.first()
    return row[0] if row else None


async def _resolve_external_sprint(db: AsyncSession, external_id: str) -> int | None:
    """Look up an external sprint by its Linear ID, return internal ID or None."""
    result = await db.execute(
        select(ExternalSprint.id).where(ExternalSprint.external_id == external_id)
    )
    row = result.first()
    return row[0] if row else None


async def _resolve_external_issue(db: AsyncSession, external_id: str) -> int | None:
    """Look up an external issue by its Linear ID, return internal ID or None."""
    result = await db.execute(
        select(ExternalIssue.id).where(ExternalIssue.external_id == external_id)
    )
    row = result.first()
    return row[0] if row else None
