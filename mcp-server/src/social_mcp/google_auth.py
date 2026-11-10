"""Google OAuth (one login covers YouTube and Drive)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import config

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    # drive.file only sees files this app created: it can't read the rest of your Drive.
    "https://www.googleapis.com/auth/drive.file",
]
TOKEN = "google_token.json"
CLIENT = "google_client_secret.json"
PENDING = "google_pending_login.json"
TOKEN_ENV = "SOCIAL_MCP_GOOGLE_TOKEN"
CLIENT_ENV = "SOCIAL_MCP_GOOGLE_CLIENT"
MANUAL_REDIRECT = "http://localhost:8765/"


def login(client_secret: str | None = None) -> Path:
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(_client_file(client_secret)), SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    return config.save_json(TOKEN, json.loads(creds.to_json()))


def credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if config.path(TOKEN).exists():
        creds = Credentials.from_authorized_user_file(str(config.path(TOKEN)), SCOPES)
    elif os.environ.get(TOKEN_ENV):
        # Hosted use: the token JSON is stored as a secret/project variable instead of a file.
        creds = Credentials.from_authorized_user_info(json.loads(os.environ[TOKEN_ENV]), SCOPES)
    else:
        raise config.NotConfigured(f"Google is not connected. Run: social-mcp auth google (or set {TOKEN_ENV})")
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            config.save_json(TOKEN, json.loads(creds.to_json()))
        else:
            raise config.NotConfigured("Google login expired. Run: social-mcp auth google")
    return creds


def _client_file(client_secret: str | None) -> Path:
    if client_secret:
        src = Path(client_secret).expanduser()
        if not src.is_file():
            raise config.NotConfigured(f"OAuth client file not found: {src}")
        if src.resolve() != config.path(CLIENT).resolve():
            config.save_json(CLIENT, json.loads(src.read_text()))
    elif not config.path(CLIENT).exists() and os.environ.get(CLIENT_ENV):
        config.save_json(CLIENT, json.loads(os.environ[CLIENT_ENV]))
    if not config.path(CLIENT).exists():
        raise config.NotConfigured(f"No OAuth client: pass --client-secret FILE or set {CLIENT_ENV} (see SETUP.md, Google step)")
    return config.path(CLIENT)


def manual_start(client_secret: str | None = None) -> str:
    """Step 1 of a login without a local browser: returns the URL to open on any device."""
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_secrets_file(str(_client_file(client_secret)), SCOPES, redirect_uri=MANUAL_REDIRECT,
                                         autogenerate_code_verifier=True)
    url, state = flow.authorization_url(access_type="offline", prompt="consent")
    config.save_json(PENDING, {"state": state, "code_verifier": flow.code_verifier})
    return url


def manual_finish(response_url: str) -> Path:
    """Step 2: the URL the browser was redirected to (it fails to load; that's expected) carries the one-time code."""
    from google_auth_oauthlib.flow import Flow

    pending = config.load_json(PENDING)
    if not pending:
        raise config.NotConfigured("No login in progress. Run: social-mcp auth google --manual")
    flow = Flow.from_client_secrets_file(str(_client_file(None)), SCOPES, redirect_uri=MANUAL_REDIRECT, state=pending["state"])
    flow.code_verifier = pending["code_verifier"]
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")  # the redirect is plain http://localhost by design
    flow.fetch_token(authorization_response=response_url.strip())
    config.path(PENDING).unlink(missing_ok=True)
    return config.save_json(TOKEN, json.loads(flow.credentials.to_json()))


def service(name: str, version: str):
    from googleapiclient.discovery import build

    return build(name, version, credentials=credentials(), cache_discovery=False)
