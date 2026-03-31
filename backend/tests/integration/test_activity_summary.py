"""Integration tests for GET /api/developers/{id}/activity-summary."""
import pytest
from datetime import datetime, timedelta, timezone

from app.models.models import Developer, Issue, PRReview, PullRequest, Repository

pytestmark = pytest.mark.asyncio

NOW = datetime.now(timezone.utc)
ONE_WEEK_AGO = NOW - timedelta(days=7)
ONE_DAY_AGO = NOW - timedelta(days=1)


async def test_activity_summary_empty(client, sample_developer):
    """Developer with zero activity returns all zeros."""
    resp = await client.get(f"/api/developers/{sample_developer.id}/activity-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["prs_authored"] == 0
    assert data["prs_merged"] == 0
    assert data["prs_open"] == 0
    assert data["reviews_given"] == 0
    assert data["issues_created"] == 0
    assert data["issues_assigned"] == 0
    assert data["repos_touched"] == 0
    assert data["first_activity"] is None
    assert data["last_activity"] is None
    assert data["work_categories"] == {}


async def test_activity_summary_with_data(client, sample_developer, sample_pr, sample_review, sample_issue, db_session):
    """Developer with PRs, reviews, and issues returns correct counts."""
    # sample_pr: author=sample_developer, merged, labels=["bug"]
    # sample_review: reviewer=sample_developer_b (not sample_developer)
    # sample_issue: assignee=sample_developer

    # Add a review BY sample_developer (not sample_developer_b)
    review = PRReview(
        github_id=999,
        pr_id=sample_pr.id,
        reviewer_id=sample_developer.id,
        state="COMMENTED",
        body="Nice",
        body_length=4,
        quality_tier="minimal",
        submitted_at=ONE_DAY_AGO,
    )
    db_session.add(review)

    # Add an issue created by sample_developer
    sample_issue.creator_id = sample_developer.id
    await db_session.commit()

    resp = await client.get(f"/api/developers/{sample_developer.id}/activity-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["prs_authored"] == 1
    assert data["prs_merged"] == 1
    assert data["prs_open"] == 0
    assert data["reviews_given"] == 1
    assert data["issues_created"] == 1
    assert data["issues_assigned"] == 1
    assert data["repos_touched"] >= 1
    assert data["first_activity"] is not None
    assert data["last_activity"] is not None
    # sample_pr has labels=["bug"] which classifies as "bugfix"
    assert data["work_categories"].get("bugfix", 0) == 1


async def test_activity_summary_not_found(client):
    """Non-existent developer returns 404."""
    resp = await client.get("/api/developers/99999/activity-summary")
    assert resp.status_code == 404


async def test_activity_summary_access_control(developer_client, sample_developer, sample_admin):
    """Developer can see own summary but not others'."""
    # Own page — should work
    resp = await developer_client.get(f"/api/developers/{sample_developer.id}/activity-summary")
    assert resp.status_code == 200

    # Other developer — should be 403
    resp = await developer_client.get(f"/api/developers/{sample_admin.id}/activity-summary")
    assert resp.status_code == 403


async def test_activity_summary_work_categories_title_fallback(client, sample_developer, sample_repo, db_session):
    """PRs without labels fall back to title-based classification."""
    pr = PullRequest(
        github_id=5000,
        repo_id=sample_repo.id,
        author_id=sample_developer.id,
        number=50,
        title="feat: add new dashboard widget",
        state="closed",
        is_merged=True,
        additions=100,
        deletions=0,
        changed_files=5,
        created_at=ONE_WEEK_AGO,
        merged_at=ONE_DAY_AGO,
    )
    db_session.add(pr)
    await db_session.commit()

    resp = await client.get(f"/api/developers/{sample_developer.id}/activity-summary")
    data = resp.json()
    assert data["prs_merged"] == 1
    assert data["work_categories"].get("feature", 0) == 1
