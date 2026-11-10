# Claude → YouTube + Instagram video automation

Make a video with Claude Code, then say **"post it to YouTube and Instagram"**. Claude:

1. Makes the video with your skills: **faceless-shorts** (narrated 9:16 shorts) or **ai-video-editor** (edits your talking-head recordings, 16:9). The 7 style prompts also work as slash commands (for example `/kinetic-video my topic`).
2. Checks the MP4 meets YouTube and Instagram Reels requirements, and re-encodes it if needed (`check_video.sh`).
3. Uploads it to **Google Drive** (`Social Uploads/<date>/`) and makes a direct link (`drive_upload.sh`, using rclone).
4. Shows you the title, caption, tags and privacy, and **waits for your OK**.
5. Posts through the **Zapier MCP**: YouTube "Upload Video" and Instagram for Business "Publish Video" (Reel). Then it gives you both links.

```
Claude Code ──skills──▶ MP4 ──rclone──▶ Google Drive (public link)
     │                                           │
     └──Zapier MCP──▶ YouTube Upload Video ◀─────┤
                  └─▶ Instagram Publish Video ◀──┘
```

Zapier's servers can't read files on your computer, so Drive provides the URL they download from.

**Start here: [SETUP.md](SETUP.md)** (about 20 minutes, done once).

## What's in this repo
| Path | What it is |
|---|---|
| `skills/social-publisher/` | The publishing skill: `SKILL.md`, `scripts/check_video.sh`, `scripts/drive_upload.sh` |
| `install.sh` | Installs the skills, slash commands and Zapier MCP into `~/.claude` |
| `.mcp.json` | Adds the Zapier MCP to Claude Code when you run Claude Code inside this folder |
| `private/` | Put your skill zips and prompt `.txt` files here. Git ignores this folder because the repo is public. |

## Daily use
```
claude
> Make a Deep Dive 3D short: what happens if you crack your knuckles?
> (approve the script, review the render)
> Post it to YouTube (unlisted) and Instagram
```
For a recording: `> Edit my video ~/Videos/raw.mp4`, then `> publish it to YouTube`.
