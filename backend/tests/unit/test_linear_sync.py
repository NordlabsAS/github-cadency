"""Unit tests for Linear sync utilities — key extraction, status mapping, issue type detection."""

import pytest

from app.services.linear_sync import (
    LINEAR_ISSUE_KEY_PATTERN,
    extract_linear_keys,
    _map_project_state,
    _map_project_health,
    _map_status_type,
    _detect_issue_type,
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
