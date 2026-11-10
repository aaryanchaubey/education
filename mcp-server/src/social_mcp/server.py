"""MCP server (stdio). Tools return JSON; errors come back as tool errors with a readable message."""
from __future__ import annotations

import functools

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import config, drive, instagram, video, youtube

mcp = MCPServer(
    "social",
    instructions=(
        "Publishes local video files to YouTube, Instagram Reels and Google Drive using the user's own API credentials. "
        "These tools post to the user's real accounts: before youtube_upload or instagram_publish_reel, show the user the "
        "exact file, title/caption, tags and privacy, and get an explicit OK in the conversation. Instagram posts are always public."
    ),
)

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)


def _readable_errors(fn):
    # The SDK hides messages of unexpected exceptions; Claude needs them (e.g. "Run: social-mcp auth google").
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"{type(e).__name__}: {e}") from e
    return wrapper


@mcp.tool(annotations=READ)
@_readable_errors
def status() -> dict:
    """Which accounts are connected (YouTube channel, Instagram username, Drive) and what to run if one isn't."""
    out: dict = {"config_dir": str(config.home())}
    try:
        out["youtube"] = youtube.channel()
        out["drive"] = "connected"
    except Exception as e:
        out["youtube"] = out["drive"] = f"not connected: {e}"
    try:
        out["instagram"] = instagram.whoami()
    except Exception as e:
        out["instagram"] = f"not connected: {e}"
    return out


@mcp.tool(annotations=READ)
@_readable_errors
def check_video(path: str) -> dict:
    """Inspect a local MP4 (codec, size, duration, orientation) against YouTube and Instagram Reels limits."""
    return video.check(path)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
@_readable_errors
def transcode_video(path: str) -> dict:
    """Re-encode to H.264/AAC MP4 (faststart) that both platforms accept; writes <name>-social.mp4 next to it."""
    return video.transcode(path)


@mcp.tool(annotations=WRITE)
@_readable_errors
def youtube_upload(
    path: str,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    category_id: str = "22",
    privacy_status: str = "private",
    made_for_kids: bool = False,
    publish_at: str | None = None,
    thumbnail_path: str | None = None,
    notify_subscribers: bool = True,
    default_language: str | None = None,
) -> dict:
    """Upload a local video to the user's YouTube channel. Only call after the user confirmed the details.

    category_id: 22 People & Blogs, 27 Education, 28 Science & Technology, 23 Comedy, 24 Entertainment.
    privacy_status: private | unlisted | public. publish_at: RFC 3339 time to go public (needs privacy_status=private).
    Vertical videos of 3 min or less become Shorts automatically; put #shorts in the description.
    """
    return youtube.upload(path, title, description, tags, category_id, privacy_status, made_for_kids,
                          publish_at, thumbnail_path, notify_subscribers, default_language)


@mcp.tool(annotations=WRITE)
@_readable_errors
def instagram_publish_reel(path: str, caption: str = "", share_to_feed: bool = True, thumb_offset_ms: int | None = None) -> dict:
    """Publish a local video as a public Instagram Reel. Only call after the user confirmed the caption.

    Waits until Instagram finishes processing (usually under a few minutes). Never retry blindly after an error:
    check the profile first, the post may exist.
    """
    return instagram.publish_reel(path, caption, share_to_feed, thumb_offset_ms)


@mcp.tool(annotations=READ)
@_readable_errors
def instagram_publishing_limit() -> dict:
    """How many API posts the Instagram account has used in the last 24 hours."""
    return instagram.publishing_limit()


@mcp.tool(annotations=WRITE)
@_readable_errors
def drive_upload(path: str, folder: str = "Social Uploads", share_public: bool = False) -> dict:
    """Copy a local file to Google Drive (<folder>/<today>/). share_public=True also makes an anyone-with-link URL."""
    return drive.upload(path, folder, True, share_public)


def run() -> None:
    mcp.run("stdio")
