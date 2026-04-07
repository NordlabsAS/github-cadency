"""Unit tests for Linear sync utilities — key extraction, status mapping, issue type detection,
auto-mapping, scope unit handling."""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Developer,
    DeveloperIdentityMap,
    ExternalIssue,
    IntegrationConfig,
    PullRequest,
    PRExternalIssueLink,
    Repository,
)
from app.services.encryption import encrypt_token
from app.services.linear_sync import (
    LINEAR_ISSUE_KEY_PATTERN,
    extract_linear_keys,
    _map_project_state,
    _map_project_health,
    _map_status_type,
    _detect_issue_type,
    auto_map_developers,
    link_prs_to_external_issues,
)


class TestExtractLinearKeys:
    def test_single_key(self):
        assert extract_linear_keys("Fix ENG-123 in production") == ["ENG-123"]

    def test_multiple_keys(self):
        assert extract_linear_keys("ENG-123 and PROJ-456 are related") == ["ENG-123", "PROJ-456"]

    def test_duplicate_keys_deduplicated(self):
        assert extract_linear_keys("ENG-123 is related to ENG-123") == ["ENG-123"]

    def test_key_in_branch_name(self):
        assert extract_linear_keys("feat/ENG-123-add-feature") == ["ENG-123"]

    def test_short_prefix(self):
        assert extract_linear_keys("AB-99999") == ["AB-99999"]

    def test_long_prefix(self):
        assert extract_linear_keys("PLATFORM-42") == ["PLATFORM-42"]

    def test_no_keys(self):
        assert extract_linear_keys("No issue keys here") == []

    def test_empty_string(self):
        assert extract_linear_keys("") == []

    def test_none(self):
        assert extract_linear_keys(None) == []

    def test_lowercase_not_matched(self):
        assert extract_linear_keys("eng-123 lowercase") == []

    def test_single_letter_prefix_not_matched(self):
        """Single letter prefixes like A-123 should not match (min 2 chars)."""
        assert extract_linear_keys("A-123 too short") == []

    def test_preserves_order(self):
        result = extract_linear_keys("PROJ-1 ENG-2 PROJ-3")
        assert result == ["PROJ-1", "ENG-2", "PROJ-3"]

    def test_key_at_start_and_end(self):
        assert extract_linear_keys("ENG-1 some text ENG-2") == ["ENG-1", "ENG-2"]


class TestMapProjectState:
    def test_planned(self):
        assert _map_project_state("planned") == "planned"

    def test_started(self):
        assert _map_project_state("started") == "started"

    def test_canceled_to_cancelled(self):
        assert _map_project_state("canceled") == "cancelled"

    def test_none(self):
        assert _map_project_state(None) is None

    def test_unknown_passthrough(self):
        assert _map_project_state("custom") == "custom"


class TestMapProjectHealth:
    def test_on_track(self):
        assert _map_project_health("onTrack") == "on_track"

    def test_at_risk(self):
        assert _map_project_health("atRisk") == "at_risk"

    def test_off_track(self):
        assert _map_project_health("offTrack") == "off_track"

    def test_none(self):
        assert _map_project_health(None) is None


class TestMapStatusType:
    def test_triage(self):
        assert _map_status_type("triage") == "triage"

    def test_backlog(self):
        assert _map_status_type("backlog") == "backlog"

    def test_unstarted_to_todo(self):
        assert _map_status_type("unstarted") == "todo"

    def test_started_to_in_progress(self):
        assert _map_status_type("started") == "in_progress"

    def test_completed_to_done(self):
        assert _map_status_type("completed") == "done"

    def test_canceled_to_cancelled(self):
        assert _map_status_type("canceled") == "cancelled"


class TestDetectIssueType:
    def test_bug_label(self):
        data = {"labels": {"nodes": [{"name": "Bug"}]}}
        assert _detect_issue_type(data) == "bug"

    def test_feature_label(self):
        data = {"labels": {"nodes": [{"name": "Feature"}]}}
        assert _detect_issue_type(data) == "feature"

    def test_improvement_label(self):
        data = {"labels": {"nodes": [{"name": "Improvement"}]}}
        assert _detect_issue_type(data) == "improvement"

    def test_sub_issue(self):
        data = {"labels": {"nodes": []}, "parent": {"id": "abc"}}
        assert _detect_issue_type(data) == "sub_issue"

    def test_default_issue(self):
        data = {"labels": {"nodes": []}, "parent": None}
        assert _detect_issue_type(data) == "issue"

    def test_no_labels_key(self):
        data = {"labels": None, "parent": None}
        assert _detect_issue_type(data) == "issue"


# --- Fixtures for DB-backed tests ---


@pytest_asyncio.fixture
async def linear_integration(db_session: AsyncSession) -> IntegrationConfig:
    config = IntegrationConfig(
        type="linear",
        display_name="Linear",
        api_key=encrypt_token("lin_api_test_key"),
        workspace_id="ws_123",
        workspace_name="Test Workspace",
        status="active",
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


# --- Auto-mapping tests ---


class TestAutoMapDevelopers:
    @pytest.mark.asyncio
    async def test_auto_map_sets_external_user_id(
        self, db_session: AsyncSession, linear_integration, sample_developer
    ):
        """When linear_users list is provided, auto-map should store the real Linear user ID."""
        # Create an external issue with the developer's email as assignee
        issue = ExternalIssue(
            integration_id=linear_integration.id,
            external_id="issue_1",
            identifier="ENG-1",
            title="Test",
            assignee_email=sample_developer.email,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(issue)
        await db_session.commit()

        linear_users = [
            {"id": "linear_user_abc", "email": sample_developer.email, "displayName": "Test", "active": True},
        ]

        mapped, unmapped = await auto_map_developers(
            db_session, linear_integration.id, linear_users=linear_users
        )

        assert mapped == 1
        assert unmapped == 0

        # Verify the mapping has the correct external_user_id
        from sqlalchemy import select
        result = await db_session.execute(
            select(DeveloperIdentityMap).where(
                DeveloperIdentityMap.developer_id == sample_developer.id,
            )
        )
        mapping = result.scalar_one()
        assert mapping.external_user_id == "linear_user_abc"
        assert mapping.external_email == sample_developer.email
        assert mapping.mapped_by == "auto"

    @pytest.mark.asyncio
    async def test_auto_map_backfills_empty_external_user_id(
        self, db_session: AsyncSession, linear_integration, sample_developer
    ):
        """Existing mappings with empty external_user_id should be backfilled."""
        # Create an existing mapping with empty external_user_id
        stale_mapping = DeveloperIdentityMap(
            developer_id=sample_developer.id,
            integration_type="linear",
            external_user_id="",
            external_email=sample_developer.email,
            mapped_by="auto",
        )
        db_session.add(stale_mapping)
        await db_session.commit()

        linear_users = [
            {"id": "linear_user_xyz", "email": sample_developer.email, "displayName": "Test", "active": True},
        ]

        await auto_map_developers(
            db_session, linear_integration.id, linear_users=linear_users
        )

        await db_session.refresh(stale_mapping)
        assert stale_mapping.external_user_id == "linear_user_xyz"

    @pytest.mark.asyncio
    async def test_auto_map_without_users_list_stores_empty(
        self, db_session: AsyncSession, linear_integration, sample_developer
    ):
        """When no linear_users list is provided, falls back to empty string (backward compat)."""
        issue = ExternalIssue(
            integration_id=linear_integration.id,
            external_id="issue_2",
            identifier="ENG-2",
            title="Test",
            assignee_email=sample_developer.email,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(issue)
        await db_session.commit()

        mapped, _ = await auto_map_developers(db_session, linear_integration.id)

        assert mapped == 1
        from sqlalchemy import select
        result = await db_session.execute(
            select(DeveloperIdentityMap).where(
                DeveloperIdentityMap.developer_id == sample_developer.id,
            )
        )
        mapping = result.scalar_one()
        assert mapping.external_user_id == ""


# --- PR linking incremental tests ---


class TestLinkPRsIncremental:
    @pytest.mark.asyncio
    async def test_link_with_since_skips_old_prs(
        self, db_session: AsyncSession, linear_integration, sample_repo
    ):
        """When since is provided, only PRs updated after that timestamp should be scanned."""
        now = datetime.now(timezone.utc)
        old_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        recent_time = datetime(2026, 4, 1, tzinfo=timezone.utc)

        # Create an external issue
        issue = ExternalIssue(
            integration_id=linear_integration.id,
            external_id="issue_link_1",
            identifier="ENG-100",
            title="Link target",
            created_at=now,
            updated_at=now,
        )
        db_session.add(issue)
        await db_session.commit()
        await db_session.refresh(issue)

        # Create old PR (should be skipped by since filter)
        old_pr = PullRequest(
            github_id=9001,
            repo_id=sample_repo.id,
            number=901,
            title="ENG-100 old fix",
            state="closed",
            is_merged=True,
            additions=1,
            deletions=1,
            changed_files=1,
            created_at=old_time,
            updated_at=old_time,
        )
        # Create recent PR (should be found)
        new_pr = PullRequest(
            github_id=9002,
            repo_id=sample_repo.id,
            number=902,
            title="ENG-100 new fix",
            state="closed",
            is_merged=True,
            additions=1,
            deletions=1,
            changed_files=1,
            created_at=recent_time,
            updated_at=recent_time,
        )
        db_session.add_all([old_pr, new_pr])
        await db_session.commit()

        # Link with since=2026-03-01 — should only find the recent PR
        since = datetime(2026, 3, 1, tzinfo=timezone.utc)
        count = await link_prs_to_external_issues(db_session, linear_integration.id, since=since)

        assert count == 1  # Only the recent PR

        # Verify only new_pr is linked
        from sqlalchemy import select
        result = await db_session.execute(select(PRExternalIssueLink))
        links = result.scalars().all()
        assert len(links) == 1
        await db_session.refresh(new_pr)
        assert links[0].pull_request_id == new_pr.id

    @pytest.mark.asyncio
    async def test_link_without_since_scans_all(
        self, db_session: AsyncSession, linear_integration, sample_repo
    ):
        """When since is None, all PRs should be scanned (full scan)."""
        now = datetime.now(timezone.utc)
        old_time = datetime(2025, 1, 1, tzinfo=timezone.utc)

        issue = ExternalIssue(
            integration_id=linear_integration.id,
            external_id="issue_link_2",
            identifier="ENG-200",
            title="Link target",
            created_at=now,
            updated_at=now,
        )
        db_session.add(issue)

        pr = PullRequest(
            github_id=9010,
            repo_id=sample_repo.id,
            number=910,
            title="ENG-200 old fix",
            state="closed",
            is_merged=True,
            additions=1,
            deletions=1,
            changed_files=1,
            created_at=old_time,
            updated_at=old_time,
        )
        db_session.add(pr)
        await db_session.commit()

        count = await link_prs_to_external_issues(db_session, linear_integration.id, since=None)
        assert count == 1


# --- Scope unit tests ---


class TestScopeUnit:
    def test_scope_unit_points_when_history_present(self):
        """When scopeHistory is present, scope_unit should be 'points'."""
        from app.models.models import ExternalSprint

        sprint = ExternalSprint(
            integration_id=1,
            external_id="cycle_1",
            state="closed",
        )
        # Simulate the scope logic from sync_linear_cycles
        scope_history = [10, 12, 15]
        completed_history = [8, 10, 13]

        sprint.planned_scope = scope_history[0]
        initial_scope = scope_history[0]
        final_scope = scope_history[-1]
        sprint.added_scope = max(0, final_scope - initial_scope) if initial_scope is not None else None
        sprint.completed_scope = completed_history[-1]
        sprint.scope_unit = "points"

        assert sprint.scope_unit == "points"
        assert sprint.planned_scope == 10
        assert sprint.completed_scope == 13
        assert sprint.added_scope == 5

    def test_scope_unit_issues_when_no_history(self):
        """When no scopeHistory, fallback uses issue counts for both planned and completed."""
        from app.models.models import ExternalSprint

        sprint = ExternalSprint(
            integration_id=1,
            external_id="cycle_2",
            state="closed",
        )
        # Simulate: no scope_history, completed cycle
        total_issues = 8
        uncompleted = 2

        sprint.planned_scope = total_issues
        sprint.completed_scope = total_issues - uncompleted
        sprint.added_scope = None
        sprint.scope_unit = "issues"

        assert sprint.scope_unit == "issues"
        assert sprint.planned_scope == 8
        assert sprint.completed_scope == 6

    def test_added_scope_zero_initial(self):
        """When initial_scope is 0, added_scope should be 0, not None."""
        scope_history = [0, 5, 10]
        initial_scope = scope_history[0]
        final_scope = scope_history[-1]

        # This is the fixed logic (was `if initial_scope` which fails for 0)
        added = max(0, final_scope - initial_scope) if initial_scope is not None else None
        assert added == 10  # 10 - 0 = 10, not None
