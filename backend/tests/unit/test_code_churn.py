"""Unit tests for code churn analysis (P3-06)."""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Developer, PRFile, PullRequest, RepoTreeFile, Repository
from app.services.stats import get_code_churn


NOW = datetime.now(timezone.utc)
ONE_WEEK_AGO = NOW - timedelta(days=7)
TWO_WEEKS_AGO = NOW - timedelta(days=14)
THREE_MONTHS_AGO = NOW - timedelta(days=90)


@pytest_asyncio.fixture
async def churn_repo(db_session: AsyncSession) -> Repository:
    repo = Repository(
        github_id=99999,
        name="churn-repo",
        full_name="org/churn-repo",
        default_branch="main",
        is_tracked=True,
        created_at=NOW,
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)
    return repo


@pytest_asyncio.fixture
async def churn_dev_a(db_session: AsyncSession) -> Developer:
    dev = Developer(
        github_username="churn_dev_a",
        display_name="Dev A",
        app_role="developer",
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )
    db_session.add(dev)
    await db_session.commit()
    await db_session.refresh(dev)
    return dev


@pytest_asyncio.fixture
async def churn_dev_b(db_session: AsyncSession) -> Developer:
    dev = Developer(
        github_username="churn_dev_b",
        display_name="Dev B",
        app_role="developer",
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )
    db_session.add(dev)
    await db_session.commit()
    await db_session.refresh(dev)
    return dev


@pytest_asyncio.fixture
async def churn_prs(
    db_session: AsyncSession,
    churn_repo: Repository,
    churn_dev_a: Developer,
    churn_dev_b: Developer,
) -> list[PullRequest]:
    """Create 3 PRs: 2 recent (within last 30 days) and 1 old (3 months ago)."""
    pr1 = PullRequest(
        github_id=10001,
        repo_id=churn_repo.id,
        author_id=churn_dev_a.id,
        number=1,
        title="PR 1",
        state="closed",
        is_merged=True,
        created_at=ONE_WEEK_AGO,
    )
    pr2 = PullRequest(
        github_id=10002,
        repo_id=churn_repo.id,
        author_id=churn_dev_b.id,
        number=2,
        title="PR 2",
        state="closed",
        is_merged=True,
        created_at=TWO_WEEKS_AGO,
    )
    pr3 = PullRequest(
        github_id=10003,
        repo_id=churn_repo.id,
        author_id=churn_dev_a.id,
        number=3,
        title="Old PR",
        state="closed",
        is_merged=True,
        created_at=THREE_MONTHS_AGO,
    )
    db_session.add_all([pr1, pr2, pr3])
    await db_session.commit()
    for pr in (pr1, pr2, pr3):
        await db_session.refresh(pr)
    return [pr1, pr2, pr3]


@pytest_asyncio.fixture
async def churn_pr_files(
    db_session: AsyncSession, churn_prs: list[PullRequest]
) -> list[PRFile]:
    """Create PR files:
    - PR1 touches src/main.py (hot) and src/utils.py
    - PR2 touches src/main.py (hot) and tests/test_main.py
    - PR3 (old) touches docs/README.md
    """
    pr1, pr2, pr3 = churn_prs
    files = [
        PRFile(pr_id=pr1.id, filename="src/main.py", additions=30, deletions=10, status="modified"),
        PRFile(pr_id=pr1.id, filename="src/utils.py", additions=5, deletions=2, status="modified"),
        PRFile(pr_id=pr2.id, filename="src/main.py", additions=20, deletions=5, status="modified"),
        PRFile(pr_id=pr2.id, filename="tests/test_main.py", additions=15, deletions=0, status="added"),
        PRFile(pr_id=pr3.id, filename="docs/README.md", additions=10, deletions=0, status="modified"),
    ]
    db_session.add_all(files)
    await db_session.commit()
    return files


@pytest_asyncio.fixture
async def churn_repo_tree(
    db_session: AsyncSession, churn_repo: Repository
) -> list[RepoTreeFile]:
    """Create a repo tree with directories: src, tests, docs, legacy (stale)."""
    entries = [
        # Directories
        RepoTreeFile(repo_id=churn_repo.id, path="src", type="tree", last_synced_at=NOW),
        RepoTreeFile(repo_id=churn_repo.id, path="tests", type="tree", last_synced_at=NOW),
        RepoTreeFile(repo_id=churn_repo.id, path="docs", type="tree", last_synced_at=NOW),
        RepoTreeFile(repo_id=churn_repo.id, path="legacy", type="tree", last_synced_at=NOW),
        # Sub-directories
        RepoTreeFile(repo_id=churn_repo.id, path="src/core", type="tree", last_synced_at=NOW),
        # Files
        RepoTreeFile(repo_id=churn_repo.id, path="src/main.py", type="blob", last_synced_at=NOW),
        RepoTreeFile(repo_id=churn_repo.id, path="src/utils.py", type="blob", last_synced_at=NOW),
        RepoTreeFile(repo_id=churn_repo.id, path="src/core/engine.py", type="blob", last_synced_at=NOW),
        RepoTreeFile(repo_id=churn_repo.id, path="tests/test_main.py", type="blob", last_synced_at=NOW),
        RepoTreeFile(repo_id=churn_repo.id, path="docs/README.md", type="blob", last_synced_at=NOW),
        RepoTreeFile(repo_id=churn_repo.id, path="legacy/old_code.py", type="blob", last_synced_at=NOW),
        RepoTreeFile(repo_id=churn_repo.id, path="legacy/deprecated.py", type="blob", last_synced_at=NOW),
    ]
    db_session.add_all(entries)
    await db_session.commit()
    return entries


@pytest.mark.asyncio
async def test_hotspot_files_ranked_by_frequency(
    db_session: AsyncSession,
    churn_repo: Repository,
    churn_pr_files: list[PRFile],
    churn_repo_tree: list[RepoTreeFile],
):
    """src/main.py is touched by 2 PRs and should be the top hotspot."""
    result = await get_code_churn(db_session, churn_repo.id)

    assert len(result.hotspot_files) > 0
    top = result.hotspot_files[0]
    assert top.path == "src/main.py"
    assert top.change_frequency == 2
    assert top.total_additions == 50  # 30 + 20
    assert top.total_deletions == 15  # 10 + 5
    assert top.total_churn == 65
    assert top.contributor_count == 2  # dev_a and dev_b


@pytest.mark.asyncio
async def test_hotspot_respects_date_range(
    db_session: AsyncSession,
    churn_repo: Repository,
    churn_pr_files: list[PRFile],
    churn_repo_tree: list[RepoTreeFile],
):
    """Old PR (3 months ago) should not appear in default 30-day range."""
    result = await get_code_churn(db_session, churn_repo.id)

    hotspot_paths = [f.path for f in result.hotspot_files]
    assert "docs/README.md" not in hotspot_paths  # Only in the old PR


@pytest.mark.asyncio
async def test_stale_directories_detected(
    db_session: AsyncSession,
    churn_repo: Repository,
    churn_pr_files: list[PRFile],
    churn_repo_tree: list[RepoTreeFile],
):
    """legacy/ and docs/ should be stale in default 30-day range.
    legacy/ has no PR activity ever. docs/ only has old activity."""
    result = await get_code_churn(db_session, churn_repo.id)

    stale_paths = [d.path for d in result.stale_directories]
    assert "legacy" in stale_paths
    assert "docs" in stale_paths
    # src and tests have recent activity
    assert "src" not in stale_paths
    assert "tests" not in stale_paths


@pytest.mark.asyncio
async def test_stale_directory_file_count(
    db_session: AsyncSession,
    churn_repo: Repository,
    churn_pr_files: list[PRFile],
    churn_repo_tree: list[RepoTreeFile],
):
    """legacy/ directory should report 2 files."""
    result = await get_code_churn(db_session, churn_repo.id)

    legacy = next(d for d in result.stale_directories if d.path == "legacy")
    assert legacy.file_count == 2
    assert legacy.last_pr_activity is None  # No PRs ever touched legacy/


@pytest.mark.asyncio
async def test_stale_directory_last_activity(
    db_session: AsyncSession,
    churn_repo: Repository,
    churn_pr_files: list[PRFile],
    churn_repo_tree: list[RepoTreeFile],
):
    """docs/ was touched 3 months ago — should report that as last activity."""
    result = await get_code_churn(db_session, churn_repo.id)

    docs = next(d for d in result.stale_directories if d.path == "docs")
    assert docs.last_pr_activity is not None


@pytest.mark.asyncio
async def test_totals(
    db_session: AsyncSession,
    churn_repo: Repository,
    churn_pr_files: list[PRFile],
    churn_repo_tree: list[RepoTreeFile],
):
    """Verify total file counts."""
    result = await get_code_churn(db_session, churn_repo.id)

    # 7 blob entries in tree
    assert result.total_files_in_repo == 7
    # 3 distinct files changed in recent PRs (src/main.py, src/utils.py, tests/test_main.py)
    assert result.total_files_changed == 3


@pytest.mark.asyncio
async def test_empty_repo_returns_empty(
    db_session: AsyncSession,
    churn_repo: Repository,
):
    """Repo with no PR files or tree returns empty results."""
    result = await get_code_churn(db_session, churn_repo.id)

    assert result.hotspot_files == []
    assert result.stale_directories == []
    assert result.total_files_in_repo == 0
    assert result.total_files_changed == 0


@pytest.mark.asyncio
async def test_limit_parameter(
    db_session: AsyncSession,
    churn_repo: Repository,
    churn_pr_files: list[PRFile],
    churn_repo_tree: list[RepoTreeFile],
):
    """Limit should cap the number of hotspot files returned."""
    result = await get_code_churn(db_session, churn_repo.id, limit=1)
    assert len(result.hotspot_files) == 1
    assert result.hotspot_files[0].path == "src/main.py"
