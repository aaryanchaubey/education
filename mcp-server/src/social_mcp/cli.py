"""social-mcp            run the MCP server (stdio)
social-mcp auth google [--client-secret FILE]
social-mcp auth instagram --api facebook|instagram [--user-id ID] [--graph-version v24.0]   (token is prompted, never an argument)
social-mcp refresh instagram
social-mcp status"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys

import httpx

from . import config, google_auth, instagram


def _auth_instagram(api: str, user_id: str | None, version: str) -> dict:
    token = os.environ.get("IG_ACCESS_TOKEN") or getpass.getpass("Paste the Instagram access token (input hidden): ").strip()
    if not token:
        raise SystemExit("No token given.")
    base = f"{instagram.HOSTS[api]}/{version}"
    if api == "instagram":
        r = httpx.get(f"{base}/me", params={"fields": "user_id,username", "access_token": token})
        me = instagram.Graph({"api": api, "access_token": token, "user_id": ""})._check(r)
        user_id = user_id or me.get("user_id") or me.get("id")
    elif not user_id:
        # Facebook Login: find the Instagram Business account linked to one of the user's Pages.
        r = httpx.get(f"{base}/me/accounts", params={"fields": "name,instagram_business_account{id,username}", "access_token": token})
        pages = instagram.Graph({"api": api, "access_token": token, "user_id": ""})._check(r).get("data", [])
        linked = [p["instagram_business_account"] for p in pages if p.get("instagram_business_account")]
        if not linked:
            raise SystemExit("No Instagram Business account is linked to this token's Facebook Pages. Pass --user-id.")
        if len(linked) > 1:
            print("Several accounts found, using the first. Pass --user-id to choose:", file=sys.stderr)
            for a in linked:
                print(f"  {a['id']}  @{a.get('username')}", file=sys.stderr)
        user_id = linked[0]["id"]
    s = {"api": api, "access_token": token, "user_id": user_id, "graph_version": version}
    who = instagram.whoami(instagram.Graph(s))
    config.save_json(instagram.CONFIG, s)
    return who


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="social-mcp", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("auth").add_subparsers(dest="service", required=True)
    g = a.add_parser("google")
    g.add_argument("--client-secret", help="OAuth client JSON downloaded from Google Cloud (Desktop app)")
    i = a.add_parser("instagram")
    i.add_argument("--api", choices=["facebook", "instagram"], required=True,
                   help="facebook = Facebook Login for Business (direct upload); instagram = Instagram Login (uses Drive for a temporary link)")
    i.add_argument("--user-id")
    i.add_argument("--graph-version", default=instagram.DEFAULT_VERSION)
    r = sub.add_parser("refresh").add_subparsers(dest="service", required=True)
    r.add_parser("instagram")
    sub.add_parser("status")
    sub.add_parser("serve")
    args = ap.parse_args(argv)

    if args.cmd in (None, "serve"):
        from .server import run
        return run()
    try:
        if args.cmd == "auth" and args.service == "google":
            print(f"Saved Google login to {google_auth.login(args.client_secret)}")
        elif args.cmd == "auth":
            print(f"Connected Instagram: {_auth_instagram(args.api, args.user_id, args.graph_version)}")
        elif args.cmd == "refresh":
            print(instagram.refresh_token())
        elif args.cmd == "status":
            from .server import status
            print(json.dumps(status(), indent=2))
    except (config.NotConfigured, instagram.GraphError) as e:
        raise SystemExit(str(e))
