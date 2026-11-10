"""Credential storage. Everything lives in ~/.config/social-mcp (override with SOCIAL_MCP_HOME), files are mode 600."""
from __future__ import annotations

import json
import os
from pathlib import Path


class NotConfigured(RuntimeError):
    pass


def home() -> Path:
    p = Path(os.environ.get("SOCIAL_MCP_HOME") or Path.home() / ".config" / "social-mcp")
    p.mkdir(parents=True, exist_ok=True)
    try:
        p.chmod(0o700)
    except OSError:
        pass
    return p


def path(name: str) -> Path:
    return home() / name


def load_json(name: str) -> dict | None:
    p = path(name)
    return json.loads(p.read_text()) if p.exists() else None


def save_json(name: str, data: dict) -> Path:
    p = path(name)
    p.touch(mode=0o600, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))
    p.chmod(0o600)
    return p


def local_file(p: str) -> Path:
    f = Path(p).expanduser().resolve()
    if not f.is_file():
        raise FileNotFoundError(f"No such file: {f}")
    return f
