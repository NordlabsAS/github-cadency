"""Unit tests for sync error handling improvements — pure functions, no DB needed."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.config import validate_github_config
from app.services.github_sync import (
    GitHubAuth,
    GitHubAuthError,
    _extract_github_message,
    make_sync_error,
)


# --- GitHubAuthError classification in make_sync_error ---


class TestMakeSyncError:
    def test_github_auth_error_produces_config_type(self):
        exc = GitHubAuthError("missing key", "download the .pem file")
        result = make_sync_error(step="run_sync", exception=exc)
        assert result["error_type"] == "config"
        assert result["retryable"] is False
        assert result["hint"] == "download the .pem file"
        assert "missing key" in result["message"]

    def test_file_not_found_produces_config_type(self):
        exc = FileNotFoundError("[Errno 2] No such file: './github-app.pem'")
        result = make_sync_error(step="run_sync", exception=exc)
        assert result["error_type"] == "config"
        assert result["retryable"] is False
        assert "hint" not in result  # no hint for generic FileNotFoundError

    def test_permission_error_produces_config_type(self):
        exc = PermissionError("[Errno 13] Permission denied: './github-app.pem'")
        result = make_sync_error(step="run_sync", exception=exc)
        assert result["error_type"] == "config"

    def test_http_error_includes_github_message(self):
        response = MagicMock()
        response.status_code = 401
        response.json.return_value = {
            "message": "Bad credentials",
            "documentation_url": "https://docs.github.com/rest",
        }
        exc = httpx.HTTPStatusError(
            "Client error '401 Unauthorized'",
            request=MagicMock(),
            response=response,
        )
        result = make_sync_error(step="run_sync", exception=exc)
        assert result["error_type"] == "auth"
        assert "Bad credentials" in result["message"]
        assert "docs.github.com" in result["message"]

    def test_http_error_without_json_body(self):
        response = MagicMock()
        response.status_code = 502
        response.json.side_effect = json.JSONDecodeError("", "", 0)
        exc = httpx.HTTPStatusError(
            "Server error '502 Bad Gateway'",
            request=MagicMock(),
            response=response,
        )
        result = make_sync_error(step="run_sync", exception=exc)
        assert result["error_type"] == "github_api"
        assert result["retryable"] is True
        assert "502" in result["message"]

    def test_timeout_error(self):
        exc = httpx.ReadTimeout("timed out")
        result = make_sync_error(step="sync_repo", exception=exc)
        assert result["error_type"] == "timeout"
        assert result["retryable"] is True

    def test_unknown_exception_type(self):
        exc = RuntimeError("something unexpected")
        result = make_sync_error(step="run_sync", exception=exc)
        assert result["error_type"] == "unknown"
        assert result["retryable"] is False

    def test_message_truncated_to_500(self):
        exc = RuntimeError("x" * 1000)
        result = make_sync_error(step="run_sync", exception=exc)
        assert len(result["message"]) <= 500


# --- _extract_github_message ---


class TestExtractGithubMessage:
    def test_extracts_message_and_doc_url(self):
        response = MagicMock()
        response.json.return_value = {
            "message": "Not Found",
            "documentation_url": "https://docs.github.com/rest",
        }
        exc = httpx.HTTPStatusError("", request=MagicMock(), response=response)
        assert "Not Found" in _extract_github_message(exc)
        assert "docs.github.com" in _extract_github_message(exc)

    def test_extracts_message_without_doc_url(self):
        response = MagicMock()
        response.json.return_value = {"message": "Bad credentials"}
        exc = httpx.HTTPStatusError("", request=MagicMock(), response=response)
        assert _extract_github_message(exc) == "Bad credentials"

    def test_returns_empty_on_non_json(self):
        response = MagicMock()
        response.json.side_effect = Exception("not json")
        exc = httpx.HTTPStatusError("", request=MagicMock(), response=response)
        assert _extract_github_message(exc) == ""


# --- GitHubAuth._generate_jwt error handling ---


class TestGitHubAuthJWT:
    def test_missing_pem_file(self, tmp_path):
        auth = GitHubAuth()
        with patch("app.services.github_sync.settings") as mock_settings:
            mock_settings.github_app_id = 12345
            mock_settings.github_app_private_key_path = str(tmp_path / "nonexistent.pem")
            with pytest.raises(GitHubAuthError, match="not found"):
                auth._generate_jwt()

    def test_empty_pem_file(self, tmp_path):
        pem = tmp_path / "empty.pem"
        pem.write_text("")
        auth = GitHubAuth()
        with patch("app.services.github_sync.settings") as mock_settings:
            mock_settings.github_app_id = 12345
            mock_settings.github_app_private_key_path = str(pem)
            with pytest.raises(GitHubAuthError, match="empty"):
                auth._generate_jwt()

    def test_invalid_pem_content(self, tmp_path):
        pem = tmp_path / "bad.pem"
        pem.write_text("this is not a valid key")
        auth = GitHubAuth()
        with patch("app.services.github_sync.settings") as mock_settings:
            mock_settings.github_app_id = 12345
            mock_settings.github_app_private_key_path = str(pem)
            with pytest.raises(GitHubAuthError, match="Invalid private key"):
                auth._generate_jwt()

    def test_zero_app_id(self, tmp_path):
        auth = GitHubAuth()
        with patch("app.services.github_sync.settings") as mock_settings:
            mock_settings.github_app_id = 0
            with pytest.raises(GitHubAuthError, match="GITHUB_APP_ID"):
                auth._generate_jwt()


# --- validate_github_config ---


class TestValidateGithubConfig:
    def test_all_errors_when_defaults(self, tmp_path):
        with patch("app.config.settings") as mock_settings:
            mock_settings.github_org = ""
            mock_settings.github_app_id = 0
            mock_settings.github_app_installation_id = 0
            mock_settings.github_app_private_key_path = str(tmp_path / "missing.pem")
            mock_settings.github_client_id = ""
            mock_settings.github_client_secret = ""

            checks = validate_github_config()
            errors = [c for c in checks if c["status"] == "error"]
            assert len(errors) >= 4  # org, app_id, installation_id, pem

    def test_empty_pem_detected(self, tmp_path):
        pem = tmp_path / "empty.pem"
        pem.write_text("")
        with patch("app.config.settings") as mock_settings:
            mock_settings.github_org = "myorg"
            mock_settings.github_app_id = 123
            mock_settings.github_app_installation_id = 456
            mock_settings.github_app_private_key_path = str(pem)
            mock_settings.github_client_id = "cid"
            mock_settings.github_client_secret = "csec"

            checks = validate_github_config()
            pem_check = next(c for c in checks if "PRIVATE_KEY" in c["field"])
            assert pem_check["status"] == "error"
            assert "empty" in pem_check["message"].lower()

    def test_corrupt_pem_detected(self, tmp_path):
        pem = tmp_path / "bad.pem"
        pem.write_text("not a pem key")
        with patch("app.config.settings") as mock_settings:
            mock_settings.github_org = "myorg"
            mock_settings.github_app_id = 123
            mock_settings.github_app_installation_id = 456
            mock_settings.github_app_private_key_path = str(pem)
            mock_settings.github_client_id = "cid"
            mock_settings.github_client_secret = "csec"

            checks = validate_github_config()
            pem_check = next(c for c in checks if "PRIVATE_KEY" in c["field"])
            assert pem_check["status"] == "error"
            assert "does not look like a PEM" in pem_check["message"]

    def test_valid_config_all_ok(self, tmp_path):
        pem = tmp_path / "good.pem"
        pem.write_text("-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----")
        with patch("app.config.settings") as mock_settings:
            mock_settings.github_org = "myorg"
            mock_settings.github_app_id = 123
            mock_settings.github_app_installation_id = 456
            mock_settings.github_app_private_key_path = str(pem)
            mock_settings.github_client_id = "cid"
            mock_settings.github_client_secret = "csec"

            checks = validate_github_config()
            assert all(c["status"] == "ok" for c in checks)

    def test_oauth_warning(self, tmp_path):
        pem = tmp_path / "good.pem"
        pem.write_text("-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----")
        with patch("app.config.settings") as mock_settings:
            mock_settings.github_org = "myorg"
            mock_settings.github_app_id = 123
            mock_settings.github_app_installation_id = 456
            mock_settings.github_app_private_key_path = str(pem)
            mock_settings.github_client_id = ""
            mock_settings.github_client_secret = ""

            checks = validate_github_config()
            warns = [c for c in checks if c["status"] == "warn"]
            assert len(warns) == 1
            assert "OAuth" in warns[0]["message"]
