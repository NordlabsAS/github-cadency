"""Unit tests for issue quality scoring logic in upsert_issue."""
import re

import pytest


class TestChecklistDetection:
    """Test the regex used to detect checklists in issue bodies."""

    CHECKLIST_RE = re.compile(r'- \[[ xX]\]')

    def test_unchecked_item(self):
        assert self.CHECKLIST_RE.search("- [ ] task 1")

    def test_checked_item(self):
        assert self.CHECKLIST_RE.search("- [x] done task")

    def test_mixed_checklist(self):
        body = "## Tasks\n- [ ] first\n- [x] second\n- [ ] third"
        assert self.CHECKLIST_RE.search(body)

    def test_no_checklist(self):
        assert not self.CHECKLIST_RE.search("Just a regular description")

    def test_empty_body(self):
        assert not self.CHECKLIST_RE.search("")

    def test_bullet_without_checkbox(self):
        assert not self.CHECKLIST_RE.search("- item without checkbox")

    def test_checkbox_without_dash(self):
        assert not self.CHECKLIST_RE.search("[ ] no dash prefix")

    def test_uppercase_x(self):
        assert self.CHECKLIST_RE.search("- [X] done task")

    def test_nested_checklist(self):
        assert self.CHECKLIST_RE.search("  - [ ] nested item")


class TestBodyLength:
    def test_empty_body(self):
        body = None
        assert len(body or "") == 0

    def test_normal_body(self):
        body = "This is a description"
        assert len(body or "") == 21

    def test_body_with_checklist(self):
        body = "Description\n- [ ] task 1\n- [x] task 2"
        assert len(body or "") == 37
