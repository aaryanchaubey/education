"""Instagram Reels publishing through Meta's Graph API.

Two account setups are supported (stored in instagram.json by `social-mcp auth instagram`):
  api="facebook"   Facebook Login for Business (graph.facebook.com). Supports resumable upload of the local file.
  api="instagram"  Instagram API with Instagram Login (graph.instagram.com). Meta must fetch the video from a public
                   URL, so the file goes to Google Drive, is shared by link while Meta processes it, then unshared.
"""
from __future__ import annotations

import os
import time

import httpx

from . import config

CONFIG = "instagram.json"
DEFAULT_VERSION = "v24.0"
HOSTS = {"facebook": "https://graph.facebook.com", "instagram": "https://graph.instagram.com"}


class GraphError(RuntimeError):
    pass


def settings() -> dict:
    s = config.load_json(CONFIG)
    if not s and os.environ.get("SOCIAL_MCP_INSTAGRAM_TOKEN"):
        # Hosted use: token and account id come from secrets/project variables.
        s = {"api": os.environ.get("SOCIAL_MCP_INSTAGRAM_API", "instagram"),
             "access_token": os.environ["SOCIAL_MCP_INSTAGRAM_TOKEN"],
             "user_id": os.environ.get("SOCIAL_MCP_INSTAGRAM_USER_ID") or _lookup_user_id(os.environ["SOCIAL_MCP_INSTAGRAM_TOKEN"]),
             "graph_version": os.environ.get("SOCIAL_MCP_INSTAGRAM_GRAPH_VERSION", DEFAULT_VERSION)}
    if not s or not s.get("access_token") or not s.get("user_id"):
        raise config.NotConfigured("Instagram is not connected. Run: social-mcp auth instagram (or set SOCIAL_MCP_INSTAGRAM_TOKEN)")
    return s


def _lookup_user_id(token: str) -> str:
    if os.environ.get("SOCIAL_MCP_INSTAGRAM_API", "instagram") != "instagram":
        raise config.NotConfigured("Set SOCIAL_MCP_INSTAGRAM_USER_ID for Facebook Login tokens")
    g = Graph({"api": "instagram", "access_token": token, "user_id": ""})
    me = g.get("me", fields="user_id,username")
    return str(me.get("user_id") or me["id"])


class Graph:
    def __init__(self, s: dict, http: httpx.Client | None = None):
        self.s = s
        self.api = s.get("api", "facebook")
        self.base = f"{HOSTS[self.api]}/{s.get('graph_version', DEFAULT_VERSION)}"
        self.http = http or httpx.Client(timeout=httpx.Timeout(60, read=600))

    def _check(self, r: httpx.Response) -> dict:
        try:
            data = r.json()
        except ValueError:
            data = {"raw": r.text[:500]}
        if r.status_code >= 400 or (isinstance(data, dict) and "error" in data):
            err = data.get("error", data) if isinstance(data, dict) else data
            msg = err.get("error_user_msg") or err.get("message") if isinstance(err, dict) else str(err)
            raise GraphError(f"Instagram API error ({r.status_code}): {msg}")
        return data

    def get(self, path: str, **params) -> dict:
        return self._check(self.http.get(f"{self.base}/{path}", params={**params, "access_token": self.s["access_token"]}))

    def post(self, path: str, **data) -> dict:
        data = {k: v for k, v in data.items() if v is not None}
        return self._check(self.http.post(f"{self.base}/{path}", data={**data, "access_token": self.s["access_token"]}))

    def upload_bytes(self, uri: str, f) -> dict:
        size = f.stat().st_size
        headers = {"Authorization": f"OAuth {self.s['access_token']}", "offset": "0", "file_size": str(size)}
        with open(f, "rb") as fh:
            return self._check(self.http.post(uri, headers=headers, content=fh.read()))


def whoami(g: Graph | None = None) -> dict:
    g = g or Graph(settings())
    me = g.get(g.s["user_id"], fields="username")
    return {"user_id": g.s["user_id"], "username": me.get("username"), "api": g.api}


def publishing_limit(g: Graph | None = None) -> dict:
    g = g or Graph(settings())
    return g.get(f"{g.s['user_id']}/content_publishing_limit", fields="quota_usage,config")


def _wait_until_ready(g: Graph, container_id: str, timeout_s: int, sleep) -> None:
    deadline = time.monotonic() + timeout_s
    while True:
        st = g.get(container_id, fields="status_code,status")
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise GraphError(f"Instagram could not process the video ({code}): {st.get('status', '')}")
        if time.monotonic() > deadline:
            raise GraphError(f"Timed out waiting for Instagram to process the video (last status {code}); container {container_id}")
        sleep(5)


def publish_reel(
    path: str,
    caption: str = "",
    share_to_feed: bool = True,
    thumb_offset_ms: int | None = None,
    timeout_s: int = 900,
    g: Graph | None = None,
    drive_mod=None,
    sleep=time.sleep,
) -> dict:
    f = config.local_file(path)
    if len(caption) > 2200:
        raise ValueError("caption must be at most 2,200 characters")
    g = g or Graph(settings())
    uid = g.s["user_id"]
    common = {"media_type": "REELS", "caption": caption, "share_to_feed": str(share_to_feed).lower(), "thumb_offset": thumb_offset_ms}

    shared = None
    try:
        if g.api == "facebook":
            c = g.post(f"{uid}/media", upload_type="resumable", **common)
            cid = c["id"]
            uri = c.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{g.s.get('graph_version', DEFAULT_VERSION)}/{cid}"
            g.upload_bytes(uri, f)
        else:
            if drive_mod is None:
                from . import drive as drive_mod
            shared = drive_mod.upload(str(f), folder="Social Uploads/instagram-tmp", dated_subfolder=False, share_public=True)
            cid = g.post(f"{uid}/media", video_url=shared["direct_url"], **common)["id"]
        _wait_until_ready(g, cid, timeout_s, sleep)
    finally:
        # Meta has the bytes once processing ends (or failed), so the public link can go.
        if shared:
            try:
                drive_mod.unshare(shared["file_id"], shared["permission_id"])
            except Exception:
                pass

    media_id = g.post(f"{uid}/media_publish", creation_id=cid)["id"]
    try:
        permalink = g.get(media_id, fields="permalink").get("permalink")
    except GraphError:
        permalink = None
    out = {"media_id": media_id, "permalink": permalink, "container_id": cid}
    if shared:
        out["drive_file_id"] = shared["file_id"]
    return out


def refresh_token() -> dict:
    """Instagram Login tokens last 60 days; refreshing extends them (token must be at least 24 h old)."""
    s = settings()
    if s.get("api") != "instagram":
        raise ValueError("Only Instagram Login tokens can be refreshed this way; for Facebook Login, re-run: social-mcp auth instagram")
    r = httpx.get("https://graph.instagram.com/refresh_access_token", params={"grant_type": "ig_refresh_token", "access_token": s["access_token"]})
    data = Graph(s)._check(r)
    s["access_token"] = data["access_token"]
    s["expires_at"] = int(time.time()) + int(data.get("expires_in", 0))
    config.save_json(CONFIG, s)
    return {"refreshed": True, "expires_in_days": round(int(data.get("expires_in", 0)) / 86400)}
