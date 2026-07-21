"""Tests for the `adloop init` wizard helpers in `adloop.cli`."""

from __future__ import annotations

import yaml

from adloop import _mcp_run_options
from adloop.cli import _generate_config_yaml


def test_mcp_run_options_defaults_to_stdio(monkeypatch):
    """Keeps local IDE launches on FastMCP's default stdio transport.

    Args:
        monkeypatch: Pytest environment fixture used to clear hosted deployment variables.

    Returns:
        None. Asserts that no FastMCP transport options are supplied locally.
    """
    monkeypatch.delenv("ADLOOP_TRANSPORT", raising=False)

    assert _mcp_run_options() == {}


def test_mcp_run_options_uses_cloud_run_http_configuration(monkeypatch):
    """Builds the externally reachable HTTP settings required by Cloud Run.

    Args:
        monkeypatch: Pytest environment fixture used to provide deployment variables.

    Returns:
        None. Asserts FastMCP receives the configured host and Cloud Run port.
    """
    monkeypatch.setenv("ADLOOP_TRANSPORT", "http")
    monkeypatch.setenv("ADLOOP_HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "8080")

    assert _mcp_run_options() == {
        "transport": "http",
        "host": "0.0.0.0",
        "port": 8080,
    }


class TestGenerateConfigYaml:
    """YAML generation in the init wizard must produce parseable output."""

    def _generate(self, **overrides):
        defaults = {
            "project_id": "",
            "credentials_path": "",
            "property_id": "123456789",
            "developer_token": "abc123",
            "customer_id": "123-456-7890",
            "login_customer_id": "987-654-3210",
            "max_daily_budget": 50.0,
            "require_dry_run": True,
        }
        defaults.update(overrides)
        return _generate_config_yaml(**defaults)

    def test_windows_credentials_path_parses(self):
        """Regression for Windows backslash paths breaking YAML parsing.

        Previously the wizard wrote `credentials_path: "c:\\Users\\..."` which
        YAML interpreted as a `\\U` Unicode escape sequence and raised
        ScannerError. Single quotes treat backslashes literally.
        """
        win_path = r"c:\Users\user\.adloop\credentials.json"
        text = self._generate(credentials_path=win_path)
        parsed = yaml.safe_load(text)
        assert parsed["google"]["credentials_path"] == win_path

    def test_posix_credentials_path_parses(self):
        posix_path = "/home/user/.adloop/credentials.json"
        text = self._generate(credentials_path=posix_path)
        parsed = yaml.safe_load(text)
        assert parsed["google"]["credentials_path"] == posix_path

    def test_path_with_embedded_apostrophe_parses(self):
        """YAML single-quoted strings escape `'` by doubling — make sure we do."""
        weird_path = r"c:\Users\o'brien\.adloop\credentials.json"
        text = self._generate(credentials_path=weird_path)
        parsed = yaml.safe_load(text)
        assert parsed["google"]["credentials_path"] == weird_path

    def test_no_credentials_path_comment(self):
        text = self._generate(credentials_path="")
        assert "credentials_path resolved from" in text
        parsed = yaml.safe_load(text)
        assert "credentials_path" not in parsed.get("google", {})
