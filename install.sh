#!/bin/bash
# Installs everything for Claude Code:
#   - this repo's social-publisher skill          -> ~/.claude/skills/social-publisher
#   - any skill zips in the given folder           -> ~/.claude/skills/<name>   (faceless-shorts, ai-video-editor)
#   - any *Prompt.txt files in the given folder     -> ~/.claude/commands/<name>.md  (slash commands, e.g. /kinetic-video)
#   - the self-hosted `social` MCP server (YouTube, Instagram, Google Drive): `social-mcp` via uv, registered with Claude Code
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

# Point faceless-shorts' Zapier upload step at the self-hosted publisher.
FS="$SKILLS/faceless-shorts/SKILL.md"
if [ -f "$FS" ] && ! grep -q "social-publisher" "$FS"; then
  awk '{print} /^## 5b\. Publish to YouTube/ && !done {print "If the `social-publisher` skill is installed, follow it instead of this section: it posts to YouTube and/or Instagram through the self-hosted social MCP server.\n"; done=1}' \
    "$FS" >"$FS.tmp" && mv "$FS.tmp" "$FS" && echo "patched  faceless-shorts -> social-publisher"
fi

if ! command -v uv >/dev/null; then
  echo "uv MISSING: install it (macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh · Windows: winget install astral-sh.uv), then re-run"
  exit 1
fi
uv tool install --force --quiet "$REPO/mcp-server"
BIN="$(uv tool dir --bin)/social-mcp"
[ -x "$BIN" ] || BIN="$BIN.exe"
echo "server   $BIN"

if command -v claude >/dev/null; then
  # Re-register so the command path stays current. Run from $HOME so project-scoped configs don't interfere.
  (cd "$HOME" && claude mcp remove --scope user social >/dev/null 2>&1 || true)
  (cd "$HOME" && claude mcp add --scope user social -- "$BIN") >/dev/null && echo "mcp      social registered with Claude Code"
else
  echo "mcp      'claude' CLI not found: install Claude Code, then run: claude mcp add --scope user social -- \"$BIN\""
fi

for t in ffmpeg node python3; do command -v "$t" >/dev/null && echo "tool     $t ok" || echo "tool     $t MISSING (see SETUP.md)"; done
echo "Done. Next: SETUP.md steps 3-5 (Google + Meta credentials, then: social-mcp auth google / social-mcp auth instagram)."
