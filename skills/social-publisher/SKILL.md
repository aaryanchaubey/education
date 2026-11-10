---
name: social-publisher
description: Publish a finished MP4 to YouTube and/or Instagram (Reels) through the Zapier MCP, hosting it on Google Drive first. Use when the user asks to upload, post or publish a video (for example one made with faceless-shorts or ai-video-editor) to YouTube, Instagram, or both.
---

# Social Publisher (Google Drive → YouTube + Instagram via Zapier MCP)

`SKILL` means this skill's folder (usually `~/.claude/skills/social-publisher`). Scripts print plain text; read
their output before the next step. This skill writes to the user's real accounts: **never post without an explicit
confirmation of the exact title, caption, visibility and platforms in this conversation.**

## 0. Preconditions (check once per session)
1. Zapier MCP is connected: Zapier tools are listed (e.g. `discover_zapier_actions`, `execute_zapier_write_action`,
   or per-action tools such as `youtube_upload_video`). If not, tell the user to run
   `claude mcp add --transport http zapier https://mcp.zapier.com/api/v1/connect`, restart Claude Code and sign in.
2. `bash SKILL/scripts/drive_upload.sh --check` prints `drive ok`. If not, the user must run `rclone config` once and
   create a Google Drive remote named `gdrive` (see the repo's SETUP.md). Never try to complete OAuth yourself.

## 1. Check the file
`bash SKILL/scripts/check_video.sh <file.mp4>` reports duration, size, resolution, codecs and what each platform
accepts. If it says `NEEDS TRANSCODE`, run the `ffmpeg` command it prints and use the new file. `NOT POSTABLE TO INSTAGRAM`
means YouTube only (or trim it, with the user's OK).
- YouTube: a vertical (9:16) video of 3 min or less becomes a Short automatically; 16:9 is a normal video.
- Instagram Reels: H.264 + AAC MP4, 3 s to 15 min, under 300 MB; 9:16 looks best (16:9 is letterboxed).

## 2. Ask, then confirm (one message)
Propose, then wait for the user's OK or edits:
- Platforms: YouTube, Instagram, or both.
- YouTube: title (≤ 100 chars), description (shorts: end with `#shorts`), 5-8 tags, category
  (Education 27, Comedy 23, Science & Tech 28, People & Blogs 22), privacy (`private` / `unlisted` / `public`,
  default `private`), made for kids (default no).
- Instagram: caption (≤ 2,200 chars, 5-8 hashtags at the end). Instagram has no private option: it posts publicly.
- Drive: the file is shared as "anyone with the link can view" (needed so Zapier can fetch it).

## 3. Host on Google Drive
`bash SKILL/scripts/drive_upload.sh <file.mp4>` uploads to `gdrive:Social Uploads/<date>/`, shares it and prints
`DIRECT_URL=<url>`. It verifies that the URL serves video bytes; if it fails, the output says so. Drive direct links
work for files under ~100 MB (bigger files hit Google's virus-scan page).
**Fallback** (only with the user's OK, since it's a public temp host that expires):
`curl -F "reqtype=fileupload" -F "time=24h" -F "fileToUpload=@<file.mp4>" https://litterbox.catbox.moe/resources/internals/api.php`
then `curl -sSI <url>` must show 200 and a `video/` content type.

## 4. Publish through Zapier MCP
Zapier exposes either per-action tools or meta-tools; use what is present. With meta-tools (they may be Code Mode
tools called as `tools.zapier.*` inside `execute`; follow the client's convention):
1. If `list_zapier_skills` shows a saved skill for these uploads, use it.
2. Discover and enable: `discover_zapier_actions({ app: "YouTube" })` and `({ app: "Instagram for Business" })`,
   then `enable_zapier_action` for **YouTube → Upload Video** and **Instagram for Business → Publish Video**.
   Use the `selected_api`, action and tool names that discovery returns; don't guess them.
   YouTube was validated as `selected_api: "YouTubeV4CLIAPI"`, `action: "upload_video"`, `tool_name: "youtube_upload_video"`.
3. No connection yet? `manage_zapier_connections({ selected_api })` returns a connect URL: give it to the user and wait.
4. Resolve dropdown values with `inspect_zapier_actions` (e.g. `enum_property: "category_id"`, Instagram account).
5. Execute:
   - YouTube `upload_video` params: `video: DIRECT_URL, title, description, tags, category_id, privacy_status,
     made_for_kids: false, embeddable: true, notify_subscribers: true, default_language, license: "youtube"`.
   - Instagram `publish_video` params: `video: DIRECT_URL, caption` (+ the account field if discovery lists one).
   Run them one at a time, and stop on the first error.

## 5. Report
- YouTube: the result's `id` → `https://www.youtube.com/watch?v=<id>` (Shorts also open at `/shorts/<id>`).
- Instagram: the result's `permalink` (or `id`). Reels can take a minute or two to process after the call returns.
- Tell the user the Drive file stays shared by link. Once both platforms have processed it, they can set it to
  "Restricted" in Drive, or you can delete it with `rclone deletefile "<DRIVE_PATH>"` if they ask.

## Errors
- Instagram "media type" / "processing failed": re-encode with the command `check_video.sh` prints (H.264 High,
  yuv420p, AAC 48 kHz, `+faststart`) and re-upload; make sure the account is **Business** and linked to a Facebook Page.
- YouTube `uploadLimitExceeded` / quota errors: the channel hit its daily limit; try again tomorrow.
- A Zapier error that mentions fetching the file: the URL isn't a raw file. Re-run `drive_upload.sh` or use the fallback host.

## Never
Post without confirmation; make a YouTube video public when the user said private/unlisted; retry a failed
Instagram publish more than once without telling the user (it may have posted anyway: check the profile first);
share any file other than the one being published.
