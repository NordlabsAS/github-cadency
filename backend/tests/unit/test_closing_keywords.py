"""Unit tests for extract_closing_issue_numbers()."""
from app.services.github_sync import extract_closing_issue_numbers


class TestExtractClosingIssueNumbers:
    def test_basic_closes(self):
        assert extract_closing_issue_numbers("Closes #42") == [42]

    def test_multiple_keywords(self):
        assert extract_closing_issue_numbers("Fixes #42 and closes #108") == [42, 108]

    def test_case_insensitive(self):
        assert extract_closing_issue_numbers("CLOSES #5") == [5]
        assert extract_closing_issue_numbers("Fixes #10") == [10]
        assert extract_closing_issue_numbers("RESOLVED #7") == [7]

    def test_all_keyword_variants(self):
        assert extract_closing_issue_numbers("close #1") == [1]
        assert extract_closing_issue_numbers("closes #2") == [2]
        assert extract_closing_issue_numbers("closed #3") == [3]
        assert extract_closing_issue_numbers("fix #4") == [4]
        assert extract_closing_issue_numbers("fixes #5") == [5]
        assert extract_closing_issue_numbers("fixed #6") == [6]
        assert extract_closing_issue_numbers("resolve #7") == [7]
        assert extract_closing_issue_numbers("resolves #8") == [8]
        assert extract_closing_issue_numbers("resolved #9") == [9]

    def test_deduplication(self):
        assert extract_closing_issue_numbers("Fixes #42, also closes #42") == [42]

    def test_sorted_output(self):
        assert extract_closing_issue_numbers("Closes #108, fixes #42") == [42, 108]

    def test_no_closing_keywords(self):
        assert extract_closing_issue_numbers("This PR adds a new feature") == []
        assert extract_closing_issue_numbers("See #42 for context") == []
        assert extract_closing_issue_numbers("References #10") == []

    def test_none_body(self):
        assert extract_closing_issue_numbers(None) == []

    def test_empty_body(self):
        assert extract_closing_issue_numbers("") == []

    def test_no_false_positive_urls(self):
        assert extract_closing_issue_numbers(
            "See https://github.com/org/repo/issues/42"
        ) == []

    def test_embedded_in_paragraph(self):
        body = "This PR implements the feature.\n\nFixes #15\nCloses #20"
        assert extract_closing_issue_numbers(body) == [15, 20]
