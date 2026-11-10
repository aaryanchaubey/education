#!/bin/bash
# Upload an MP4 to Google Drive with rclone, share it by link, print a direct-download URL Zapier can fetch.
#   drive_upload.sh --check          verify the rclone remote works
#   drive_upload.sh <file.mp4>       upload + share; prints DRIVE_PATH=, FILE_ID=, DIRECT_URL=
# Env: GDRIVE_REMOTE (default gdrive), GDRIVE_FOLDER (default "Social Uploads")
set -euo pipefail
REMOTE="${GDRIVE_REMOTE:-gdrive}"
FOLDER="${GDRIVE_FOLDER:-Social Uploads}"

if ! command -v rclone >/dev/null; then
  echo "rclone MISSING: install it (macOS: brew install rclone · Windows: winget install Rclone.Rclone · Linux: sudo apt install rclone)"
  exit 1
fi
if ! rclone listremotes 2>/dev/null | grep -qx "${REMOTE}:"; then
  echo "drive NOT CONFIGURED: run 'rclone config', add a remote named '${REMOTE}' of type 'drive' (scope 1, full access)"
  exit 1
fi

if [ "${1:-}" = "--check" ]; then
  rclone about "${REMOTE}:" >/dev/null 2>&1 && echo "drive ok (${REMOTE}:)" || { echo "drive FAILED: run 'rclone config reconnect ${REMOTE}:'"; exit 1; }
  exit 0
fi

SRC="${1:?usage: drive_upload.sh <file.mp4> | --check}"
[ -f "$SRC" ] || { echo "no such file: $SRC"; exit 1; }

DEST="${REMOTE}:${FOLDER}/$(date +%Y-%m-%d)/$(basename "$SRC")"
rclone copyto "$SRC" "$DEST"
# `rclone link` on Drive adds an "anyone with the link can view" permission.
LINK=$(rclone link "$DEST")
ID=$(printf '%s' "$LINK" | sed -nE 's#.*[?&]id=([A-Za-z0-9_-]+).*#\1#p; s#.*/d/([A-Za-z0-9_-]+).*#\1#p' | head -n1)
[ -n "$ID" ] || { echo "could not parse a file id from: $LINK"; exit 1; }
URL="https://drive.usercontent.google.com/download?id=${ID}&export=download&confirm=t"

echo "DRIVE_PATH=$DEST"
echo "FILE_ID=$ID"
echo "SHARE_URL=$LINK"
# Sharing can take a few seconds to propagate.
for _ in 1 2 3 4 5 6; do
  CT=$(curl -sSIL "$URL" | tr -d '\r' | awk -F': ' 'tolower($1)=="content-type"{v=$2} END{print v}')
  case "$CT" in
    video/*|application/octet-stream*) echo "DIRECT_URL=$URL"; echo "verified ($CT)"; exit 0 ;;
  esac
  sleep 5
done
echo "DIRECT_URL NOT VERIFIED (content-type: ${CT:-none}). Drive may be serving a warning page; use the fallback host."
exit 2
