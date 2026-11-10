"""ffprobe checks against YouTube / Instagram Reels limits, and an ffmpeg re-encode that satisfies both."""
from __future__ import annotations

import json
import shutil
import subprocess

from . import config


def probe(path: str) -> dict:
    f = config.local_file(path)
    if not shutil.which("ffprobe"):
        raise RuntimeError("ffprobe not found: install ffmpeg")
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_type,codec_name,pix_fmt,width,height",
         "-of", "json", str(f)], capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in data["streams"] if s["codec_type"] == "audio"), {})
    return {
        "path": str(f), "duration_s": round(float(data["format"]["duration"]), 2), "size_mb": round(int(data["format"]["size"]) / 2**20, 1),
        "video_codec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"), "width": v.get("width"), "height": v.get("height"),
        "audio_codec": a.get("codec_name"),
    }


def check(path: str) -> dict:
    p = probe(path)
    w, h, d = p["width"] or 0, p["height"] or 0, p["duration_s"]
    orient = "vertical" if h > w else "horizontal" if w > h else "square"
    yt = "Short (vertical, 3 min or less)" if orient == "vertical" and d <= 180 else f"regular video ({orient})"
    ig_problems = []
    if not 3 <= d <= 900:
        ig_problems.append("Reels must be 3 s to 15 min")
    if p["size_mb"] >= 300:
        ig_problems.append("Reels must be under 300 MB")
    warnings = [] if orient == "vertical" else [f"{orient} video is letterboxed on Instagram (9:16 looks best)"]
    needs_transcode = p["video_codec"] != "h264" or p["pix_fmt"] != "yuv420p" or (p["audio_codec"] not in (None, "aac"))
    return {**p, "youtube": yt, "instagram_ok": not ig_problems, "instagram_problems": ig_problems,
            "warnings": warnings, "needs_transcode": needs_transcode}


def transcode(path: str) -> dict:
    f = config.local_file(path)
    dst = f.with_name(f"{f.stem}-social.mp4")
    has_audio = probe(path)["audio_codec"] is not None
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(f)]
    if not has_audio:  # Instagram rejects some silent files; add a silent track
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest"]
    cmd += ["-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "21", "-preset", "slow", "-r", "30",
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True, capture_output=True)
    return check(str(dst))
