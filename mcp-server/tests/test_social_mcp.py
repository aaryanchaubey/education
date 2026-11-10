import json
import subprocess
import sys

import httpx
import pytest

from social_mcp import config, drive, instagram, video, youtube


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIAL_MCP_HOME", str(tmp_path / "cfg"))
    return tmp_path


@pytest.fixture
def mp4(tmp_path):
    def make(name="v.mp4", size="1080x1920", vcodec="libx264", audio=True, dur=4):
        out = tmp_path / name
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc=s={size}:d={dur}:r=30"]
        if audio:
            cmd += ["-f", "lavfi", "-i", f"sine=d={dur}", "-c:a", "aac", "-shortest"]
        cmd += ["-c:v", vcodec] + (["-pix_fmt", "yuv420p"] if vcodec == "libx264" else []) + [str(out)]
        subprocess.run(cmd, check=True)
        return out
    return make


# ---------- video ----------
def test_check_vertical_short(mp4):
    r = video.check(str(mp4()))
    assert r["youtube"].startswith("Short") and r["instagram_ok"] and not r["needs_transcode"] and r["warnings"] == []


def test_transcode_fixes_codec_and_adds_audio(mp4):
    src = mp4("h.mp4", size="1280x720", vcodec="mpeg4", audio=False)
    assert video.check(str(src))["needs_transcode"]
    r = video.transcode(str(src))
    assert r["path"].endswith("h-social.mp4") and not r["needs_transcode"] and r["audio_codec"] == "aac"
    assert "letterboxed" in r["warnings"][0]


def test_too_short_for_instagram(mp4):
    r = video.check(str(mp4(dur=2)))
    assert not r["instagram_ok"]


# ---------- instagram ----------
class Recorder:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, req: httpx.Request):
        body = req.content if req.method == "POST" else b""
        self.calls.append((req.method, req.url.host, req.url.path, dict(req.url.params), body, dict(req.headers)))
        for (method, frag), resp in self.routes.items():
            if req.method == method and frag in str(req.url):
                r = resp(req) if callable(resp) else resp
                return httpx.Response(200, json=r) if isinstance(r, dict) else r
        return httpx.Response(404, json={"error": {"message": f"unrouted {req.method} {req.url}"}})


def graph(api, rec):
    s = {"api": api, "access_token": "TOKEN", "user_id": "17841", "graph_version": "v24.0"}
    return instagram.Graph(s, http=httpx.Client(transport=httpx.MockTransport(rec)))


def test_reel_facebook_resumable_upload(mp4):
    f = mp4()
    statuses = iter([{"status_code": "IN_PROGRESS"}, {"status_code": "FINISHED"}])
    rec = Recorder({
        ("POST", "/17841/media_publish"): {"id": "MEDIA1"},
        ("POST", "/17841/media"): {"id": "C1", "uri": "https://rupload.facebook.com/ig-api-upload/v24.0/C1"},
        ("POST", "rupload.facebook.com"): {"success": True},
        ("GET", "/C1"): lambda r: next(statuses),
        ("GET", "/MEDIA1"): {"permalink": "https://www.instagram.com/reel/abc/"},
    })
    out = instagram.publish_reel(str(f), "hello #x", g=graph("facebook", rec), sleep=lambda s: None)
    assert out == {"media_id": "MEDIA1", "permalink": "https://www.instagram.com/reel/abc/", "container_id": "C1"}
    create = rec.calls[0]
    assert create[1] == "graph.facebook.com" and b"upload_type=resumable" in create[4] and b"media_type=REELS" in create[4]
    up = rec.calls[1]
    assert up[1] == "rupload.facebook.com" and up[5]["authorization"] == "OAuth TOKEN"
    assert up[5]["file_size"] == str(f.stat().st_size) and up[4] == f.read_bytes()


def test_reel_instagram_login_uses_drive_and_unshares(mp4):
    f = mp4()

    class FakeDrive:
        unshared = None

        def upload(self, path, folder, dated_subfolder, share_public):
            assert share_public
            return {"file_id": "D1", "permission_id": "P1", "direct_url": "https://drive.usercontent.google.com/download?id=D1"}

        def unshare(self, fid, pid):
            self.unshared = (fid, pid)

    fd = FakeDrive()
    rec = Recorder({
        ("POST", "/media_publish"): {"id": "M2"},
        ("POST", "/media"): {"id": "C2"},
        ("GET", "/C2"): {"status_code": "FINISHED"},
        ("GET", "/M2"): {"permalink": "https://www.instagram.com/reel/x/"},
    })
    out = instagram.publish_reel(str(f), "cap", g=graph("instagram", rec), drive_mod=fd, sleep=lambda s: None)
    assert out["media_id"] == "M2" and fd.unshared == ("D1", "P1")
    assert rec.calls[0][1] == "graph.instagram.com" and b"video_url=https" in rec.calls[0][4]


def test_reel_processing_error_raises_and_unshares(mp4):
    class FakeDrive:
        unshared = False

        def upload(self, *a, **k):
            return {"file_id": "D", "permission_id": "P", "direct_url": "u"}

        def unshare(self, *a):
            self.unshared = True

    fd = FakeDrive()
    rec = Recorder({("POST", "/media"): {"id": "C3"}, ("GET", "/C3"): {"status_code": "ERROR", "status": "bad codec"}})
    with pytest.raises(instagram.GraphError, match="bad codec"):
        instagram.publish_reel(str(mp4()), g=graph("instagram", rec), drive_mod=fd, sleep=lambda s: None)
    assert fd.unshared and not any("media_publish" in c[2] for c in rec.calls)


def test_graph_error_message():
    rec = Recorder({("GET", "/17841"): httpx.Response(400, json={"error": {"message": "Invalid OAuth access token"}})})
    with pytest.raises(instagram.GraphError, match="Invalid OAuth"):
        instagram.whoami(graph("facebook", rec))


def test_not_configured():
    with pytest.raises(config.NotConfigured):
        instagram.settings()


# ---------- youtube / drive with fake Google clients ----------
class Exec:
    def __init__(self, v):
        self.v = v

    def execute(self):
        return self.v


class FakeYT:
    def __init__(self):
        self.insert_kwargs = None

    def videos(self):
        yt = self

        class V:
            def insert(self, **kw):
                yt.insert_kwargs = kw

                class Req:
                    n = 0

                    def next_chunk(self, num_retries=0):
                        self.n += 1
                        return (None, None) if self.n < 2 else (None, {"id": "VID", "status": {"privacyStatus": kw["body"]["status"]["privacyStatus"], "uploadStatus": "uploaded"}})
                return Req()
        return V()


def test_youtube_upload_body(mp4):
    yt = FakeYT()
    out = youtube.upload(str(mp4()), "My short", "desc #shorts", ["a", "b"], "27", "unlisted", yt=yt)
    body = yt.insert_kwargs["body"]
    assert out["url"] == "https://www.youtube.com/watch?v=VID" and out["privacy_status"] == "unlisted"
    assert body["snippet"]["categoryId"] == "27" and body["status"]["selfDeclaredMadeForKids"] is False
    assert yt.insert_kwargs["media_body"].resumable()


@pytest.mark.parametrize("kw,msg", [({"privacy_status": "secret"}, "privacy"), ({"title": ""}, "title"),
                                    ({"publish_at": "2026-12-01T10:00:00Z", "privacy_status": "public"}, "publish_at")])
def test_youtube_validation(mp4, kw, msg):
    args = {"title": "t", **kw}
    with pytest.raises(ValueError, match=msg):
        youtube.upload(str(mp4()), yt=FakeYT(), **args)


def test_drive_upload_creates_folders_and_shares(mp4):
    created, perms = [], []

    class Files:
        def list(self, q, **k):
            return Exec({"files": []})

        def create(self, body, **k):
            created.append(body)
            return Exec({"id": f"id{len(created)}", "name": body["name"], "webViewLink": "w"})

    class Perms:
        def create(self, fileId, body, **k):
            perms.append((fileId, body))
            return Exec({"id": "perm"})

    class D:
        files = staticmethod(lambda: Files())
        permissions = staticmethod(lambda: Perms())

    out = drive.upload(str(mp4()), "Social Uploads", True, True, drive=D())
    assert [c["name"] for c in created][0] == "Social Uploads" and created[-1]["name"] == "v.mp4"
    assert perms == [("id3", {"type": "anyone", "role": "reader"})] and out["direct_url"].endswith("id=id3&export=download&confirm=t")


# ---------- MCP protocol over stdio ----------
def test_stdio_lists_tools(tmp_path):
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "instagram_publish_reel", "arguments": {"path": "/nope.mp4"}}},
    ]
    p = subprocess.Popen([sys.executable, "-m", "social_mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, env={"SOCIAL_MCP_HOME": str(tmp_path), "PATH": "/usr/bin:/bin"})
    replies = {}
    try:
        for m in msgs:
            p.stdin.write(json.dumps(m) + "\n")
            p.stdin.flush()
            if "id" in m:  # wait for each reply so the server never sees EOF mid-request
                while m["id"] not in replies:
                    line = p.stdout.readline()
                    assert line, p.stderr.read()
                    r = json.loads(line)
                    if "id" in r:
                        replies[r["id"]] = r
    finally:
        p.kill()
    names = {t["name"] for t in replies[2]["result"]["tools"]}
    assert names == {"status", "check_video", "transcode_video", "youtube_upload", "instagram_publish_reel",
                     "instagram_publishing_limit", "drive_upload"}
    assert replies[3]["result"]["isError"] and "No such file" in json.dumps(replies[3]["result"])
