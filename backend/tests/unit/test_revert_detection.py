"""Unit tests for detect_revert()."""
from app.services.github_sync import detect_revert


class TestDetectRevert:
    def test_standard_github_revert_with_body_pr_ref(self):
        is_revert, pr_num = detect_revert(
            'Revert "Add auth middleware"',
            "Reverts org/repo#123\n\nThis reverts commit abc123.",
        )
        assert is_revert is True
        assert pr_num == 123

    def test_revert_body_simple_hash_ref(self):
        is_revert, pr_num = detect_revert(
            'Revert "Fix login bug"',
            "Reverts #42",
        )
        assert is_revert is True
        assert pr_num == 42

    def test_revert_title_only_no_body_ref(self):
        is_revert, pr_num = detect_revert(
            'Revert "Add auth middleware"',
            "This reverts commit abc123.",
        )
        assert is_revert is True
        assert pr_num is None

    def test_not_a_revert(self):
        is_revert, pr_num = detect_revert("Fix login bug", "")
        assert is_revert is False
        assert pr_num is None

    def test_not_a_revert_with_body(self):
        is_revert, pr_num = detect_revert(
            "Add new feature",
            "This PR adds authentication.",
        )
        assert is_revert is False
        assert pr_num is None

    def test_none_title(self):
        is_revert, pr_num = detect_revert(None, "some body")
        assert is_revert is False
        assert pr_num is None

    def test_none_body(self):
        is_revert, pr_num = detect_revert('Revert "Something"', None)
        assert is_revert is True
        assert pr_num is None

    def test_case_insensitive_title(self):
        is_revert, pr_num = detect_revert(
            'revert "Add feature"',
            "Reverts #10",
        )
        assert is_revert is True
        assert pr_num == 10

    def test_body_revert_keyword_without_title_pattern(self):
        # Body mentions "revert" but title doesn't match pattern — not a revert
        is_revert, pr_num = detect_revert(
            "Fix the revert issue",
            "This fixes the revert that happened earlier",
        )
        assert is_revert is False
        assert pr_num is None

    def test_empty_strings(self):
        is_revert, pr_num = detect_revert("", "")
        assert is_revert is False
        assert pr_num is None
