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

from . import config, drive, google_auth, instagram, video, youtube


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
    g.add_argument("--manual", action="store_true", help="no local browser: print a URL to open on any device")
    g.add_argument("--response-url", help="finish a --manual login with the localhost URL the browser ended on")
    i = a.add_parser("instagram")
    i.add_argument("--api", choices=["facebook", "instagram"], required=True,
                   help="facebook = Facebook Login for Business (direct upload); instagram = Instagram Login (uses Drive for a temporary link)")
    i.add_argument("--user-id")
    i.add_argument("--graph-version", default=instagram.DEFAULT_VERSION)
    r = sub.add_parser("refresh").add_subparsers(dest="service", required=True)
    r.add_parser("instagram")
    sub.add_parser("status")
    sub.add_parser("serve")
    c = sub.add_parser("check", help="check a video against YouTube / Instagram limits")
    c.add_argument("path")
    t = sub.add_parser("transcode", help="re-encode to a file both platforms accept")
    t.add_argument("path")
    y = sub.add_parser("youtube-upload", help="upload a video to YouTube (prints JSON)")
    y.add_argument("path")
    y.add_argument("--title", required=True)
    y.add_argument("--description", default="")
    y.add_argument("--tags", default="", help="comma-separated")
    y.add_argument("--category", default="22")
    y.add_argument("--privacy", default="private", choices=sorted(youtube.PRIVACY))
    y.add_argument("--publish-at")
    y.add_argument("--thumbnail")
    y.add_argument("--language")
    ig = sub.add_parser("instagram-publish", help="publish a video as a public Instagram Reel (prints JSON)")
    ig.add_argument("path")
    ig.add_argument("--caption", default="")
    ig.add_argument("--no-feed", action="store_true", help="Reels tab only, not the main feed")
    d = sub.add_parser("drive-upload", help="copy a file to Google Drive (prints JSON)")
    d.add_argument("path")
    d.add_argument("--folder", default="Social Uploads")
    args = ap.parse_args(argv)

    if args.cmd in (None, "serve"):
        from .server import run
        return run()
    out = lambda r: print(json.dumps(r, indent=2))  # noqa: E731
    try:
        if args.cmd == "auth" and args.service == "google":
            if args.response_url:
                print(f"Saved Google login to {google_auth.manual_finish(args.response_url)}")
            elif args.manual:
                print("Open this URL, sign in and allow access. The browser then fails to load a localhost page:")
                print("copy that page's full address and run: social-mcp auth google --response-url '<address>'\n")
                print(google_auth.manual_start(args.client_secret))
            else:
                print(f"Saved Google login to {google_auth.login(args.client_secret)}")
        elif args.cmd == "auth":
            print(f"Connected Instagram: {_auth_instagram(args.api, args.user_id, args.graph_version)}")
        elif args.cmd == "refresh":
            print(instagram.refresh_token())
        elif args.cmd == "status":
            from .server import status
            out(status())
        elif args.cmd == "check":
            out(video.check(args.path))
        elif args.cmd == "transcode":
            out(video.transcode(args.path))
        elif args.cmd == "youtube-upload":
            tags = [x.strip() for x in args.tags.split(",") if x.strip()]
            out(youtube.upload(args.path, args.title, args.description, tags, args.category, args.privacy,
                               publish_at=args.publish_at, thumbnail_path=args.thumbnail, default_language=args.language))
        elif args.cmd == "instagram-publish":
            out(instagram.publish_reel(args.path, args.caption, share_to_feed=not args.no_feed))
        elif args.cmd == "drive-upload":
            out(drive.upload(args.path, args.folder))
    except (config.NotConfigured, instagram.GraphError, ValueError, FileNotFoundError) as e:
        raise SystemExit(f"error: {e}")
