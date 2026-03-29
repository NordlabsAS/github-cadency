"""Tests for extract_mentions() function."""

from app.services.github_sync import extract_mentions


def test_no_mentions():
    assert extract_mentions("This is a comment without mentions.") is None


def test_empty_body():
    assert extract_mentions("") is None
    assert extract_mentions(None) is None


def test_single_mention():
    result = extract_mentions("Hey @alice can you review this?")
    assert result == ["alice"]


def test_multiple_mentions():
    result = extract_mentions("cc @alice @bob @charlie")
    assert sorted(result) == ["alice", "bob", "charlie"]


def test_duplicate_mentions():
    result = extract_mentions("@alice please check @alice")
    assert result == ["alice"]


def test_mention_with_hyphens():
    result = extract_mentions("Thanks @some-user-name for the review")
    assert result == ["some-user-name"]


def test_email_not_matched():
    # Emails like user@example.com should not be matched as @mentions
    # because the @ has a word char before it
    result = extract_mentions("Send to user@example.com")
    assert result is None


def test_mention_at_start():
    result = extract_mentions("@firstuser check this")
    assert result == ["firstuser"]


def test_mention_in_code_block():
    # We don't parse code blocks — mentions inside code are still extracted
    # This is acceptable for v1
    result = extract_mentions("```\n@codeuser\n```")
    assert result == ["codeuser"]


def test_mention_max_length():
    # GitHub usernames max 39 chars
    long_name = "a" * 39
    result = extract_mentions(f"@{long_name} hey")
    assert result == [long_name]


def test_mention_too_long():
    # 40+ chars should be truncated to 39
    long_name = "a" * 40
    result = extract_mentions(f"@{long_name}")
    # Regex captures up to 39 chars
    assert result == ["a" * 39]


def test_mention_with_numbers():
    result = extract_mentions("@user123 @123user")
    assert sorted(result) == ["123user", "user123"]
