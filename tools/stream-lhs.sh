#!/bin/bash
set -euo pipefail

HOST="aura67@100.97.205.28"

WIDTH=640
HEIGHT=480
FRAMERATE=15
BITRATE=2000000

SEG=0.5                 # 0.5–1.0 is a sweet spot for HLS-TS
LIST=6
OUTDIR="./hls_out"

INTRA=$(printf "%.0f" "$(echo "$FRAMERATE * $SEG" | bc -l)")

mkdir -p "$OUTDIR"

# Start a simple HTTP server to serve the output folder in the background
python3 -m http.server --directory "$OUTDIR" 8000 &
HTTP_PID=$!
trap "kill $HTTP_PID 2>/dev/null" EXIT

ssh "$HOST" \
  "libcamera-vid -t 0 --codec h264 --inline \
   --framerate $FRAMERATE --intra $INTRA \
   --width $WIDTH --height $HEIGHT \
   --bitrate $BITRATE --nopreview -o -" \
| ffmpeg -hide_banner -loglevel warning \
    -fflags +genpts+nobuffer \
    -flags low_delay \
    -probesize 32 -analyzeduration 0 \
    -f h264 -r $FRAMERATE -i pipe:0 \
    -c:v copy \
    -flush_packets 1 \
    -muxdelay 0 -muxpreload 0 \
    -f hls \
    -hls_time $SEG \
    -hls_list_size $LIST \
    -hls_flags delete_segments+append_list+independent_segments+omit_endlist+discont_start \
    -hls_segment_type mpegts \
    -hls_segment_filename "$OUTDIR/stream_%03d.ts" \
    "$OUTDIR/stream.m3u8"

