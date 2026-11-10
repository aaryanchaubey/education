---
name: social-publisher
description: Publish a finished MP4 to YouTube and/or Instagram Reels (and optionally archive it on Google Drive) through the self-hosted `social` MCP server. Use when the user asks to upload, post or publish a video, for example one made with faceless-shorts or ai-video-editor.
---

# Social Publisher (own MCP server: YouTube + Instagram + Google Drive)

The `social` MCP server talks to the YouTube Data API, Meta's Instagram Graph API and the Google Drive API with the
user's own credentials (no Zapier or other middleman). Its tools post to the user's **real accounts**:
**never call `youtube_upload` or `instagram_publish_reel` without an explicit OK in this conversation for the exact
file, title/caption, tags and privacy.**

## 0. Check connections
Call `status`. If a service says "not connected", tell the user the command it prints (`social-mcp auth google` or
`social-mcp auth instagram --api ...`), to be run in their own terminal (it opens a browser or asks for a token). Never try
to complete a login yourself. If the `social` tools are missing entirely, the server isn't installed: point to SETUP.md.

## 1. Check the file
`check_video(path)`. If `needs_transcode` is true, call `transcode_video(path)` and use the returned `path`
(`<name>-social.mp4`). If `instagram_ok` is false, the video can go to YouTube only (or the user can trim it).
Vertical videos of 3 min or less become YouTube Shorts automatically. 16:9 videos are letterboxed on Instagram.

## 2. Propose, then wait for the OK (one message)
- Platforms: YouTube, Instagram, or both. Also save a copy to Drive? (default no)
- YouTube: title (≤ 100 chars), description (Shorts: end with `#shorts`), 5-8 tags, category (27 Education,
  28 Science & Tech, 23 Comedy, 24 Entertainment, 22 People & Blogs), privacy (`private` / `unlisted` / `public`,
  default `private`), optional schedule (`publish_at` RFC 3339, needs `private`), optional thumbnail (cover frame PNG/JPG).
- Instagram: caption (≤ 2,200 chars, hashtags at the end). Reels are always **public**: say so.

## 3. Publish (one platform at a time, stop at the first error)
- `youtube_upload(path, title, description, tags, category_id, privacy_status, ...)` → `url`, `shorts_url`.
- `instagram_publish_reel(path, caption)` → `permalink`. It waits for Instagram's processing (up to ~15 min).
  On Instagram Login accounts it briefly shares the file from Drive and removes the share afterwards.
  **Never retry automatically** after an error or timeout: the Reel may still appear. Ask the user to check the profile first.
- `drive_upload(path)` → archive copy in `Social Uploads/<date>/` (private unless `share_public=true`).

## 4. Report
Give each link. YouTube may show "processing" for a few minutes; Instagram Reels can take a minute to appear on the profile.

## Errors
- Google "quotaExceeded" / "uploadLimitExceeded": the daily upload limit was hit; try tomorrow.
- Google "invalid_grant" / "login expired": the user runs `social-mcp auth google` again (the Google Cloud app must be
  "In production", otherwise logins expire every 7 days; see SETUP.md).
- Instagram "Invalid OAuth access token" / expired: Instagram Login → `social-mcp refresh instagram` (or re-run auth);
  Facebook Login → re-run `social-mcp auth instagram --api facebook`.
- Instagram processing `ERROR`: re-encode with `transcode_video` and try once more, with the user's OK.
- `instagram_publishing_limit` shows the 24-hour posting quota.
