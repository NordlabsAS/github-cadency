"""Regression tests for the planning alert evaluators.

These guard against a class of bug where the evaluator reads a different
dict key than the underlying stats function emits — the alert silently
never fires regardless of real data.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ExternalIssue,
    ExternalSprint,
    IntegrationConfig,
    Notification,
)
from app.services.encryption import encrypt_token
from app.services.notifications import (
    _evaluate_planning_alerts,
    get_notification_config,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def linear_integration(db_session: AsyncSession) -> IntegrationConfig:
    config = IntegrationConfig(
        type="linear",
        display_name="Linear",
        api_key=encrypt_token("lin_api_test"),
        status="active",
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


async def _notification_keys(db: AsyncSession, alert_type: str) -> set[str]:
    result = await db.execute(
        select(Notification.alert_key).where(
            Notification.alert_type == alert_type,
            Notification.resolved_at.is_(None),
        )
    )
    return set(result.scalars().all())


async def test_velocity_declining_fires_when_trend_declines(
    db_session: AsyncSession, linear_integration: IntegrationConfig
):
    # 4 closed sprints; completed_scope drops sharply in the newer half.
    # Evaluator loads newest-first via get_sprint_velocity (which reverses,
    # so velocity["data"] is oldest-first), but then re-orders by taking
    # the first half as "older" and second half as "newer" — so we set up
    # a clear decline in raw chronological order.
    for i, completed in enumerate([40, 38, 10, 8]):
        db_session.add(ExternalSprint(
            integration_id=linear_integration.id,
            external_id=f"cycle_{i}",
            name=f"Sprint {i+1}",
            number=i + 1,
            team_key="ENG",
            state="closed",
            start_date=date(2026, 1 + i, 1),
            end_date=date(2026, 1 + i, 14),
            planned_scope=40,
            completed_scope=completed,
        ))
    await db_session.commit()

    config = await get_notification_config(db_session)
    await _evaluate_planning_alerts(db_session, config)

    keys = await _notification_keys(db_session, "velocity_declining")
    assert "velocity_declining:system:trend" in keys


async def test_scope_creep_high_fires_when_creep_exceeds_threshold(
    db_session: AsyncSession, linear_integration: IntegrationConfig
):
    # Latest closed sprint has 40% scope creep (added_scope=4 / planned_scope=10).
    db_session.add(ExternalSprint(
        integration_id=linear_integration.id,
        external_id="cycle_creep",
        name="Scope Creep Sprint",
        number=9,
        team_key="ENG",
        state="closed",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 14),
        planned_scope=10,
        completed_scope=8,
        added_scope=4,
    ))
    await db_session.commit()

    config = await get_notification_config(db_session)
    await _evaluate_planning_alerts(db_session, config)

    keys = await _notification_keys(db_session, "scope_creep_high")
    assert any(k.startswith("scope_creep_high:sprint:") for k in keys)

    # Title should carry the actual sprint name (regression: used to read
    # latest["name"] instead of latest["sprint_name"] and always show "Sprint").
    result = await db_session.execute(
        select(Notification.title).where(Notification.alert_type == "scope_creep_high")
    )
    titles = list(result.scalars().all())
    assert any("Scope Creep Sprint" in t for t in titles)


async def test_triage_queue_growing_fires_when_queue_depth_exceeds_max(
    db_session: AsyncSession, linear_integration: IntegrationConfig
):
    # 15 issues currently in triage — exceeds default threshold of 10.
    for i in range(15):
        db_session.add(ExternalIssue(
            integration_id=linear_integration.id,
            external_id=f"issue_triage_{i}",
            identifier=f"ENG-{100+i}",
            title=f"Triage issue {i}",
            status_category="triage",
        ))
    await db_session.commit()

    config = await get_notification_config(db_session)
    await _evaluate_planning_alerts(db_session, config)

    keys = await _notification_keys(db_session, "triage_queue_growing")
    assert "triage_queue_growing:system:triage" in keys


async def test_triage_queue_growing_fires_on_long_triage_duration(
    db_session: AsyncSession, linear_integration: IntegrationConfig
):
    # Small queue but avg triage > 48h. Default threshold is 48 hours.
    # Regression: used to read avg_triage_hours from a dict that emits
    # avg_triage_duration_s (seconds), so this condition never tripped.
    for i in range(3):
        db_session.add(ExternalIssue(
            integration_id=linear_integration.id,
            external_id=f"issue_slow_{i}",
            identifier=f"ENG-{200+i}",
            title=f"Slow-triage issue {i}",
            status_category="done",
            triage_duration_s=72 * 3600,  # 72 hours
        ))
    await db_session.commit()

    config = await get_notification_config(db_session)
    await _evaluate_planning_alerts(db_session, config)

    keys = await _notification_keys(db_session, "triage_queue_growing")
    assert "triage_queue_growing:system:triage" in keys


async def test_estimation_accuracy_low_fires_when_avg_below_threshold(
    db_session: AsyncSession, linear_integration: IntegrationConfig
):
    # 3 closed sprints; each has estimated=10, completed (done) issues total 3 — 30% accuracy.
    for i in range(3):
        sprint = ExternalSprint(
            integration_id=linear_integration.id,
            external_id=f"cycle_est_{i}",
            name=f"Est Sprint {i+1}",
            number=i + 1,
            team_key="ENG",
            state="closed",
            start_date=date(2026, 1 + i, 1),
            end_date=date(2026, 1 + i, 14),
        )
        db_session.add(sprint)
        await db_session.flush()

        # Two issues — one done (estimate 3), one in_progress (estimate 7).
        # total estimate = 10, completed = 3, accuracy = 30%.
        db_session.add(ExternalIssue(
            integration_id=linear_integration.id,
            external_id=f"issue_est_done_{i}",
            identifier=f"ENG-{300+i*2}",
            title=f"Done {i}",
            status_category="done",
            estimate=3.0,
            sprint_id=sprint.id,
        ))
        db_session.add(ExternalIssue(
            integration_id=linear_integration.id,
            external_id=f"issue_est_wip_{i}",
            identifier=f"ENG-{301+i*2}",
            title=f"WIP {i}",
            status_category="in_progress",
            estimate=7.0,
            sprint_id=sprint.id,
        ))
    await db_session.commit()

    config = await get_notification_config(db_session)
    await _evaluate_planning_alerts(db_session, config)

    keys = await _notification_keys(db_session, "estimation_accuracy_low")
    assert "estimation_accuracy_low:system:trend" in keys


async def test_planning_alerts_noop_without_linear_integration(db_session: AsyncSession):
    # No IntegrationConfig row — evaluator must short-circuit, no notifications.
    config = await get_notification_config(db_session)
    await _evaluate_planning_alerts(db_session, config)

    result = await db_session.execute(select(Notification))
    assert result.scalars().first() is None
