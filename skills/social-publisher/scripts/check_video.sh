#!/bin/bash
# Report whether an MP4 is ready for YouTube and Instagram Reels; print a fix-up ffmpeg command if not.
set -euo pipefail
F="${1:?usage: check_video.sh <file.mp4>}"
[ -f "$F" ] || { echo "no such file: $F"; exit 1; }
command -v ffprobe >/dev/null || { echo "ffprobe MISSING: install ffmpeg"; exit 1; }

q() { ffprobe -v error -select_streams "$1" -show_entries "$2" -of default=nw=1:nk=1 "$F" | head -n1; }
VC=$(q v:0 stream=codec_name); PF=$(q v:0 stream=pix_fmt)
W=$(q v:0 stream=width); H=$(q v:0 stream=height)
AC=$(q a:0 stream=codec_name || true)
DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$F")
SIZE=$(wc -c <"$F" | tr -d ' ')
MB=$(awk -v s="$SIZE" 'BEGIN{printf "%.1f", s/1048576}')
SECS=$(awk -v d="$DUR" 'BEGIN{printf "%.1f", d}')

echo "file:     $F"
echo "video:    ${VC} ${PF} ${W}x${H}   audio: ${AC:-none}"
echo "duration: ${SECS}s   size: ${MB} MB"

ORIENT=$(awk -v w="$W" -v h="$H" 'BEGIN{ if (h>w) print "vertical"; else if (w>h) print "horizontal"; else print "square" }')
if [ "$ORIENT" = vertical ] && awk -v d="$DUR" 'BEGIN{exit !(d<=180)}'; then
  echo "youtube:  ok (vertical, <=3 min: becomes a Short)"
else
  echo "youtube:  ok (${ORIENT}: regular video)"
fi

ok=1
awk -v d="$DUR" 'BEGIN{exit !(d>=3 && d<=900)}' || { echo "instagram: duration must be 3 s to 15 min"; ok=0; }
awk -v s="$SIZE" 'BEGIN{exit !(s<300*1048576)}' || { echo "instagram: file must be under 300 MB"; ok=0; }
awk -v s="$SIZE" 'BEGIN{exit !(s<100*1048576)}' || echo "drive:    over 100 MB, so the Drive direct link may fail; use the fallback host"
[ "$ORIENT" = vertical ] || echo "instagram: ${ORIENT} video will be letterboxed in Reels (9:16 looks best)"

[ $ok = 1 ] || { echo "NOT POSTABLE TO INSTAGRAM (fix the length/size above); YouTube only"; exit 4; }
if [ "$VC" != h264 ] || [ "$PF" != yuv420p ] || { [ -n "$AC" ] && [ "$AC" != aac ]; }; then
  echo "NEEDS TRANSCODE:"
  echo "  ffmpeg -i \"$F\" -c:v libx264 -profile:v high -pix_fmt yuv420p -crf 21 -preset slow -r 30 -c:a aac -b:a 160k -ar 48000 -movflags +faststart \"${F%.*}-social.mp4\""
  exit 3
fi
echo "READY"
