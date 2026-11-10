# Setup (once, on your own computer)

Run every step on the computer where you'll use Claude Code: videos render there, and the sign-ins open your browser.

## 1. Tools
| Tool | macOS | Windows (use Git Bash) | Linux |
|---|---|---|---|
| Claude Code | `npm i -g @anthropic-ai/claude-code` | same | same |
| Node.js 22+ | `brew install node` | `winget install OpenJS.NodeJS` | nodejs.org |
| Python 3.10+ | `brew install python` | `winget install Python.Python.3.12` | `sudo apt install python3 python3-venv` |
| ffmpeg | `brew install ffmpeg` | `winget install Gyan.FFmpeg` | `sudo apt install ffmpeg` |
| Google Chrome | google.com/chrome | google.com/chrome | google.com/chrome |
| rclone | `brew install rclone` | `winget install Rclone.Rclone` | `sudo apt install rclone` |

## 2. Install the skills, prompts and Zapier MCP
```bash
git clone https://github.com/aaryanchaubey/education.git && cd education
# copy faceless-shorts-skill.zip, ai-video-editor.zip and the 7 *Prompt.txt files into ./private/
./install.sh
```
This installs:
- `~/.claude/skills/faceless-shorts`, `~/.claude/skills/ai-video-editor` and `~/.claude/skills/social-publisher`
- the slash commands `/chalk-video`, `/clean-tech`, `/data-story`, `/kinetic-video`, `/pop-info`, `/software-walkthrough` and `/warm-canvas`
- the Zapier MCP server (`claude mcp add --scope user --transport http zapier https://mcp.zapier.com/api/v1/connect`)

Then finish the video skills' own setup. These scripts download free local models, about 1–2 GB in total:
```bash
bash ~/.claude/skills/faceless-shorts/scripts/setup.sh      # prints "All set"
bash ~/.claude/skills/faceless-shorts/scripts/selftest.sh   # prints "SELFTEST PASSED"
python3 ~/.claude/skills/ai-video-editor/scripts/setup.py
```

## 3. Zapier: sign in and connect YouTube + Instagram
1. Create a free account at zapier.com. Each MCP tool call uses Zapier tasks, roughly 2 per call.
2. Start `claude`, run `/mcp`, choose **zapier → Authenticate**, then click **Allow** in the browser.
3. Ask Claude: *"Using Zapier, enable YouTube Upload Video and Instagram for Business Publish Video, and connect my accounts."*
   Claude returns connect links. Open each one and sign in:
   - **YouTube**: the Google account that owns your channel.
   - **Instagram for Business**: your Instagram account must be a **Business** account linked to a **Facebook Page**. Switch it in Instagram under Settings → Account type and tools, then link the Page in Meta Business Suite. Zapier doesn't support Personal accounts.
4. Alternatively, open mcp.zapier.com → your server → **Add tool**, and add *YouTube → Upload Video* and *Instagram for Business → Publish Video*.

## 4. Google Drive (rclone)
```bash
rclone config
#  n) New remote → name: gdrive → storage: drive → leave client_id/secret empty → scope: 1 (full access)
#  → defaults for the rest → "Use web browser to automatically authenticate?" y → sign in → Shared Drive? n → q
bash ~/.claude/skills/social-publisher/scripts/drive_upload.sh --check   # prints "drive ok"
```
Uploads go to `My Drive/Social Uploads/<date>/` and are shared as "anyone with the link". To use a different remote or folder, set `GDRIVE_REMOTE` or `GDRIVE_FOLDER`.

## 5. Test it end to end
```bash
claude
> Make a Stick Story short: what if the power went out for 3 days?
> Post it to YouTube as private, skip Instagram
```
Check that the video appears in YouTube Studio as **Private**. Then test Instagram with a video you're happy to post publicly, because Instagram has no private option.

## Notes and limits
- Claude always asks before posting. Nothing is published without your OK in the chat.
- Drive direct links work for files under ~100 MB, which covers shorts. Bigger files fall back to a temporary public host, and only if you agree.
- YouTube limits uploads per day for each channel. Instagram allows about 50 API posts per 24 hours.
- **Hands-free option (no Claude in the loop):** in the Zapier editor, build a Zap: *Google Drive – New File in Folder* (`Social Uploads`) → *YouTube – Upload Video* → *Instagram for Business – Publish Video*, and use the file name as the title. Then any MP4 you drop into that folder gets posted.
- Using claude.ai or Claude Desktop instead of Claude Code: add Zapier under Settings → Connectors. The skills need a computer to render on, so Claude Code is the recommended setup.
