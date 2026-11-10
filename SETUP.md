# Setup (once, on your own computer)

**On Windows? Follow [WINDOWS.md](WINDOWS.md)**, which gives exact commands for each step and links back here for the Google and Meta app setup.

## 1. Tools
| Tool | macOS | Windows (use Git Bash) | Linux |
|---|---|---|---|
| Claude Code | `npm i -g @anthropic-ai/claude-code` | same | same |
| uv (runs the MCP server) | `brew install uv` | `winget install astral-sh.uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js 22+ | `brew install node` | `winget install OpenJS.NodeJS` | nodejs.org |
| Python 3.10+ | `brew install python` | `winget install Python.Python.3.12` | `sudo apt install python3 python3-venv` |
| ffmpeg | `brew install ffmpeg` | `winget install Gyan.FFmpeg` | `sudo apt install ffmpeg` |
| Google Chrome | google.com/chrome | google.com/chrome | google.com/chrome |

## 2. Install
```bash
git clone https://github.com/aaryanchaubey/education.git && cd education
# copy faceless-shorts-skill.zip, ai-video-editor.zip and the 7 *Prompt.txt files into ./private/
./install.sh
```
This installs the `social-mcp` command and registers it with Claude Code (`claude mcp list` should show
`social … ✔ Connected`). It also installs the 3 skills and the slash commands `/chalk-video`, `/clean-tech`, `/data-story`,
`/kinetic-video`, `/pop-info`, `/software-walkthrough` and `/warm-canvas`.

Then run the video skills' own setup. It downloads free local models, about 1–2 GB:
```bash
bash ~/.claude/skills/faceless-shorts/scripts/setup.sh      # prints "All set"
bash ~/.claude/skills/faceless-shorts/scripts/selftest.sh   # prints "SELFTEST PASSED"
python3 ~/.claude/skills/ai-video-editor/scripts/setup.py
```

## 3. Google: YouTube + Drive (free)
1. Go to console.cloud.google.com and create a project (any name, e.g. "social-mcp").
2. Open **APIs & Services → Library** and enable **YouTube Data API v3** and **Google Drive API**.
3. Open **Google Auth Platform** (OAuth consent screen) and choose **External**. Fill in the app name and your email.
   Then, under **Audience**, click **Publish app** so the status is **In production**. In "Testing" status, Google
   logs you out every 7 days. You don't need verification for your own use: on the sign-in screen, click
   *Advanced → Go to social-mcp (unsafe)*.
4. Open **Clients → Create client**, choose **Desktop app**, then download the JSON file.
5. Run:
   ```bash
   social-mcp auth google --client-secret ~/Downloads/client_secret_XXXX.json
   ```
   A browser opens. Pick the Google account that owns your channel; for a brand channel, pick the channel. Allow access.
   Drive access is limited to files this app creates (`drive.file`), so it can't read the rest of your Drive.

Limits: each project gets about 100 uploads per day (YouTube's `videos.insert` quota) and 10,000 units for everything else.
Since Nov 2026, uploads from unverified projects can be public; earlier, they were forced to private.

## 4. Instagram (free, choose one option)
Your Instagram account must be a **professional account** (Business or Creator). To switch: Instagram → Settings →
Account type and tools.

**Option A: Instagram Login (simplest, no Facebook Page needed)**
1. At developers.facebook.com, open **My Apps → Create app**. Choose the use case **"Manage messaging & content on Instagram"**.
2. Under **API setup with Instagram login**, click **Generate access tokens → Add account**, log in to Instagram, then copy the token.
   The token needs `instagram_business_basic` and `instagram_business_content_publish`, which this use case includes.
3. Run `social-mcp auth instagram --api instagram` and paste the token (input is hidden).
   - With this option, Meta must download the video from a link. The server uploads the video to your Drive, shares it
     while Instagram processes it, then removes the share automatically. Google (step 3) must be connected.
   - The token lasts 60 days. Run `social-mcp refresh instagram` at least once a month, for example with a monthly
     calendar reminder or a cron job.

**Option B: Facebook Login for Business (direct upload, most reliable)**
1. Link your Instagram professional account to a **Facebook Page**: Meta Business Suite → Settings → Instagram accounts.
2. Create an app at developers.facebook.com (type **Business**) and add **Facebook Login for Business**.
3. Open **Graph API Explorer**, select your app, and add these permissions: `instagram_basic`,
   `instagram_content_publish`, `pages_show_list`, `pages_read_engagement` and `business_management`.
   Click **Generate Access Token** and approve.
4. Open the **Access Token Debugger**, paste the token, then click **Extend Access Token**. You get a 60-day token.
5. Run `social-mcp auth instagram --api facebook` and paste it. The server finds the linked Instagram account itself.
   If you have several accounts, pass `--user-id`.

In development mode, both options only work for accounts that have a role on your app. As the app's admin, you already
do, so you don't need Meta App Review to post to your own account.

## 5. Test it
```bash
social-mcp status          # shows your channel name and Instagram username
claude
> Make a Stick Story short: what if the power went out for 3 days?
> Upload it to YouTube as private
```
Check that the video appears in YouTube Studio as **Private**. Instagram has no private option, so test it with a video
you're happy to post publicly.

## Troubleshooting
- **The `social` tools don't show in Claude:** run `claude mcp list`, then re-run `./install.sh`, then restart Claude Code.
- **"Google login expired":** check that the app is *In production* (step 3.3), then run `social-mcp auth google` again.
- **Instagram "processing failed":** ask Claude to run `transcode_video` first. Reels need H.264/AAC, 3 s–15 min, and under 300 MB.
- **Updating:** `git pull && ./install.sh`.
