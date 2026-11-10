"""YouTube Data API v3 uploads (resumable, straight from the local file)."""
from __future__ import annotations

from . import config, google_auth

PRIVACY = {"private", "unlisted", "public"}


def channel(yt=None) -> dict:
    yt = yt or google_auth.service("youtube", "v3")
    items = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    if not items:
        raise RuntimeError("This Google account has no YouTube channel.")
    return {"channel_id": items[0]["id"], "title": items[0]["snippet"]["title"]}


def upload(
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
    yt=None,
) -> dict:
    from googleapiclient.http import MediaFileUpload

    f = config.local_file(path)
    if privacy_status not in PRIVACY:
        raise ValueError(f"privacy_status must be one of {sorted(PRIVACY)}")
    if not title.strip() or len(title) > 100:
        raise ValueError("title must be 1-100 characters")
    if publish_at and privacy_status != "private":
        raise ValueError("publish_at (scheduled release) requires privacy_status='private'")

    status = {"privacyStatus": privacy_status, "selfDeclaredMadeForKids": made_for_kids, "embeddable": True}
    if publish_at:
        status["publishAt"] = publish_at
    snippet = {"title": title, "description": description, "tags": tags or [], "categoryId": str(category_id)}
    if default_language:
        snippet["defaultLanguage"] = snippet["defaultAudioLanguage"] = default_language

    yt = yt or google_auth.service("youtube", "v3")
    req = yt.videos().insert(
        part="snippet,status",
        body={"snippet": snippet, "status": status},
        media_body=MediaFileUpload(str(f), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True),
        notifySubscribers=notify_subscribers,
    )
    resp = None
    while resp is None:
        _, resp = req.next_chunk(num_retries=3)
    vid = resp["id"]
    out = {
        "video_id": vid,
        "url": f"https://www.youtube.com/watch?v={vid}",
        "shorts_url": f"https://www.youtube.com/shorts/{vid}",
        "privacy_status": resp.get("status", {}).get("privacyStatus", privacy_status),
        "upload_status": resp.get("status", {}).get("uploadStatus"),
    }
    if thumbnail_path:
        try:
            thumb = config.local_file(thumbnail_path)
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb))).execute()
            out["thumbnail"] = "set"
        except Exception as e:  # the video is already up; report rather than fail
            out["thumbnail"] = f"failed: {e}"
    return out
