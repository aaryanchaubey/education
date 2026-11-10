# Windows setup (step by step)

Use **PowerShell** for installs and logins, and **Git Bash** for `./install.sh` and the video skills' scripts.
Open a **new** terminal window after the installs in step 1 so the new commands are found.

## 1. Install the tools (PowerShell)
```powershell
winget install Git.Git
winget install OpenJS.NodeJS.LTS
winget install Python.Python.3.12
winget install astral-sh.uv
winget install Gyan.FFmpeg
winget install Google.Chrome
npm install -g @anthropic-ai/claude-code
```
Close PowerShell, open a new one, and check:
```powershell
git --version; node -v; python --version; uv --version; ffmpeg -version; claude --version
```
Every command should print a version (Node must be 22 or newer). Then run `claude` once and log in with your Claude account.

## 2. Clone the repo and add your files (PowerShell)
```powershell
cd $HOME
git clone https://github.com/aaryanchaubey/education.git
cd education
Copy-Item "$HOME\Downloads\faceless-shorts-skill.zip", "$HOME\Downloads\ai-video-editor.zip" private\
Copy-Item "$HOME\Downloads\*Prompt.txt" private\
dir private
```
(If your files are somewhere other than Downloads, change the paths.)

## 3. Run the installer (Git Bash)
Open **Git Bash** from the Start menu, then run:
```bash
cd ~/education
./install.sh
```
Expected output: `skill social-publisher`, `skill ai-video-editor`, `skill faceless-shorts`, seven `command /...` lines,
`mcp social registered with Claude Code` and `tool ffmpeg ok`.

Still in Git Bash, set up the video skills. This downloads free models (about 1–2 GB) and takes a while:
```bash
bash ~/.claude/skills/faceless-shorts/scripts/setup.sh       # ends with "All set"
bash ~/.claude/skills/faceless-shorts/scripts/selftest.sh    # ends with "SELFTEST PASSED"
python ~/.claude/skills/ai-video-editor/scripts/setup.py
```

## 4. Connect Google and Instagram (PowerShell)
First create the Google Cloud and Meta apps described in [SETUP.md](SETUP.md) steps 3 and 4. Then, in PowerShell:
```powershell
social-mcp auth google --client-secret "$HOME\Downloads\client_secret_XXXX.json"
social-mcp auth instagram --api instagram      # or: --api facebook (see SETUP.md step 4)
social-mcp status
```
Run these in PowerShell, not Git Bash: Git Bash can't hide the pasted token correctly.
`social-mcp status` should show your channel name and Instagram username.

## 5. Use it
```powershell
cd $HOME\education
claude
```
Then type, for example:
```
> Make a Stick Story short: what if the power went out for 3 days?
> Upload it to YouTube as private
```
Claude Code asks before running commands or posting. Answer "yes" for each, or allow the tool permanently.

## Problems
- **`social-mcp` not found:** run `uv tool update-shell`, then open a new terminal.
- **`claude mcp list` doesn't show `social`:** re-run `./install.sh` in Git Bash, then restart Claude Code.
- **Login page doesn't open:** copy the URL that `social-mcp auth google` prints into your browser.
- **3D styles render slowly:** this is normal without a strong GPU; the faceless-shorts skill tells Claude to use its software-render settings.
