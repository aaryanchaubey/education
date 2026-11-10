# Claude → YouTube + Instagram, with your own MCP server

Make a video with Claude Code, then say **"post it to YouTube and Instagram"**. No Zapier and no paid middleman:
`social-mcp` is a small MCP server in this repo that runs on your computer and calls the official APIs
(YouTube Data API v3, Meta Instagram Graph API, Google Drive API) with **your own** credentials.

```
Claude Code ──skills──▶ MP4 on your computer
     │
     └── social MCP server (runs locally, stdio)
           ├─ youtube_upload ─────────▶ YouTube Data API (resumable upload of the local file)
           ├─ instagram_publish_reel ─▶ Instagram Graph API (direct upload, or a temporary Drive link)
           ├─ drive_upload ───────────▶ Google Drive API (archive copies)
           └─ check_video / transcode_video / status / instagram_publishing_limit
```

**Start here: [SETUP.md](SETUP.md)** (about 30–40 minutes, done once).

## What's in this repo
| Path | What it is |
|---|---|
| `mcp-server/` | The `social-mcp` server and CLI (Python, official `mcp` SDK). Tests: `cd mcp-server && uv run pytest` |
| `skills/social-publisher/` | Skill that tells Claude how to publish safely: check → propose → wait for OK → post |
| `install.sh` | Installs the server, skills, prompt slash commands and the Claude Code MCP registration |
| `private/` | Put your skill zips and prompt `.txt` files here. Git ignores this folder because the repo is public. |

## Daily use
```
claude
> Make a Deep Dive 3D short: what happens if you crack your knuckles?
> Post it to YouTube (unlisted) and Instagram
```
Claude shows the title, caption, tags and privacy, and posts only after you say yes. Claude Code also asks permission
before each tool call, unless you've allowed that tool.

## Where your keys live
`~/.config/social-mcp/` (file mode 600): Google OAuth client and token, Instagram token. Nothing is sent anywhere
except Google and Meta. Run `social-mcp status` at any time to see what's connected.
