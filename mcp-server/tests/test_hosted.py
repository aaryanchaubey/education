import json
from urllib.parse import parse_qs, urlparse

import pytest

from social_mcp import cli, config, google_auth, instagram

CLIENT = {"installed": {"client_id": "cid.apps.googleusercontent.com", "client_secret": "s", "project_id": "p",
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["http://localhost"]}}


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIAL_MCP_HOME", str(tmp_path / "cfg"))
    for k in ["SOCIAL_MCP_INSTAGRAM_TOKEN", "SOCIAL_MCP_INSTAGRAM_USER_ID", "SOCIAL_MCP_INSTAGRAM_API",
              "SOCIAL_MCP_GOOGLE_TOKEN", "SOCIAL_MCP_GOOGLE_CLIENT"]:
        monkeypatch.delenv(k, raising=False)


def test_instagram_settings_from_env(monkeypatch):
    monkeypatch.setenv("SOCIAL_MCP_INSTAGRAM_TOKEN", "tok")
    monkeypatch.setenv("SOCIAL_MCP_INSTAGRAM_USER_ID", "999")
    s = instagram.settings()
    assert s["access_token"] == "tok" and s["user_id"] == "999" and s["api"] == "instagram"


def test_google_token_from_env(monkeypatch):
    tok = {"token": "at", "refresh_token": "rt", "client_id": "c", "client_secret": "s",
           "token_uri": "https://oauth2.googleapis.com/token", "scopes": google_auth.SCOPES, "expiry": "2999-01-01T00:00:00Z"}
    monkeypatch.setenv("SOCIAL_MCP_GOOGLE_TOKEN", json.dumps(tok))
    assert google_auth.credentials().token == "at"


def test_google_manual_login_url_from_env_client(monkeypatch):
    monkeypatch.setenv("SOCIAL_MCP_GOOGLE_CLIENT", json.dumps(CLIENT))
    q = parse_qs(urlparse(google_auth.manual_start()).query)
    assert q["redirect_uri"] == [google_auth.MANUAL_REDIRECT] and q["access_type"] == ["offline"]
    assert q["code_challenge_method"] == ["S256"] and set(q["scope"][0].split()) == set(google_auth.SCOPES)
    pending = config.load_json(google_auth.PENDING)
    assert pending["state"] == q["state"][0] and pending["code_verifier"]


def test_manual_finish_without_start():
    with pytest.raises(config.NotConfigured, match="No login in progress"):
        google_auth.manual_finish("http://localhost:8765/?code=x&state=y")


def test_cli_reports_missing_config(capsys):
    with pytest.raises(SystemExit, match="Google is not connected"):
        cli.main(["youtube-upload", __file__, "--title", "t"])
