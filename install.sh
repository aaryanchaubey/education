#!/bin/bash
# Installs everything for Claude Code:
#   - this repo's social-publisher skill          -> ~/.claude/skills/social-publisher
#   - any skill zips in the given folder           -> ~/.claude/skills/<name>   (faceless-shorts, ai-video-editor)
#   - any *Prompt.txt files in the given folder     -> ~/.claude/commands/<name>.md  (slash commands, e.g. /kinetic-video)
#   - the Zapier MCP server (user scope), if the `claude` CLI is installed
# Usage: ./install.sh [folder with your zips and prompt .txt files]   (default: ./private)
# Safe to re-run: existing skills are replaced, nothing else in ~/.claude is touched.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
SRC="${1:-$REPO/private}"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
SKILLS="$CLAUDE_HOME/skills"; CMDS="$CLAUDE_HOME/commands"
mkdir -p "$SKILLS" "$CMDS"

install_dir() { rm -rf "$SKILLS/$2"; cp -R "$1" "$SKILLS/$2"; echo "skill    $2"; }

install_dir "$REPO/skills/social-publisher" social-publisher
chmod +x "$SKILLS/social-publisher/scripts/"*.sh

if [ -d "$SRC" ]; then
  shopt -s nullglob
  for z in "$SRC"/*.zip; do
    tmp=$(mktemp -d)
    unzip -q "$z" -d "$tmp"
    for d in "$tmp"/*/; do
      [ -f "$d/SKILL.md" ] && install_dir "${d%/}" "$(basename "$d")"
    done
    rm -rf "$tmp"
  done
  for p in "$SRC"/*Prompt.txt; do
    # kineticVideoPrompt.txt -> kinetic-video
    name=$(basename "$p" Prompt.txt | sed -E 's/([a-z0-9])([A-Z])/\1-\2/g' | tr '[:upper:]' '[:lower:]')
    { cat "$p"; printf '\n\nMY TOPIC OR SCRIPT (if empty, ask me): $ARGUMENTS\n'; } >"$CMDS/$name.md"
    echo "command  /$name"
  done
else
  echo "note     no folder $SRC: put your skill zips and prompt .txt files there and re-run to install them"
fi

# Point faceless-shorts' own YouTube-only upload step at the Drive + YouTube + Instagram publisher.
FS="$SKILLS/faceless-shorts/SKILL.md"
if [ -f "$FS" ] && ! grep -q "social-publisher" "$FS"; then
  awk '{print} /^## 5b\. Publish to YouTube/ && !done {print "If the `social-publisher` skill is installed, follow it instead of this section: it hosts the file on Google Drive and posts to YouTube and/or Instagram.\n"; done=1}' \
    "$FS" >"$FS.tmp" && mv "$FS.tmp" "$FS" && echo "patched  faceless-shorts -> social-publisher"
fi

if command -v claude >/dev/null; then
  # Check from $HOME so this repo's project-scoped .mcp.json doesn't count as a user-level install.
  if (cd "$HOME" && claude mcp get zapier >/dev/null 2>&1); then echo "mcp      zapier already configured"
  else claude mcp add --scope user --transport http zapier https://mcp.zapier.com/api/v1/connect && echo "mcp      zapier added (sign in on first use)"; fi
else
  echo "mcp      'claude' CLI not found: install Claude Code, then run: claude mcp add --scope user --transport http zapier https://mcp.zapier.com/api/v1/connect"
fi

for t in ffmpeg rclone node python3; do command -v "$t" >/dev/null && echo "tool     $t ok" || echo "tool     $t MISSING (see SETUP.md)"; done
echo "Done. Next: SETUP.md steps 3-5 (Zapier apps, rclone Drive remote, skill setup scripts)."
