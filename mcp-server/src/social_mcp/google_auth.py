"""Google OAuth (one login covers YouTube and Drive)."""
from __future__ import annotations

import json
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


def login(client_secret: str | None = None) -> Path:
    from google_auth_oauthlib.flow import InstalledAppFlow

    src = Path(client_secret).expanduser() if client_secret else config.path(CLIENT)
    if not src.is_file():
        raise config.NotConfigured(f"OAuth client file not found: {src} (see SETUP.md, Google Cloud step)")
    if src.resolve() != config.path(CLIENT).resolve():
        config.save_json(CLIENT, json.loads(src.read_text()))
    flow = InstalledAppFlow.from_client_secrets_file(str(config.path(CLIENT)), SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    return config.save_json(TOKEN, json.loads(creds.to_json()))


def credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not config.path(TOKEN).exists():
        raise config.NotConfigured("Google is not connected. Run: social-mcp auth google")
    creds = Credentials.from_authorized_user_file(str(config.path(TOKEN)), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            config.save_json(TOKEN, json.loads(creds.to_json()))
        else:
            raise config.NotConfigured("Google login expired. Run: social-mcp auth google")
    return creds


def service(name: str, version: str):
    from googleapiclient.discovery import build

    return build(name, version, credentials=credentials(), cache_discovery=False)
