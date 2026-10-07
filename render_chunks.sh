#!/usr/bin/env sh
# Render a project in N parallel chunks and concat: ./render_chunks.sh projects/NAME [N] [mac.py args...]
set -e
PY=${PY:-uv run python}   # interpreter; e.g. PY=python3
P=$1; N=${2:-6}; shift 2 || shift $#
NAME=$(basename "$P"); OUT="$P/out"; mkdir -p "$OUT"
TOTAL=$($PY -c "import sys;sys.argv=['x'];import mac;print(sum(s.duration for s in mac.load('$P/animation.toml')[0]))")
STEP=$(python3 -c "print($TOTAL/$N)")
for k in $(seq 0 $((N-1))); do
  S=$(python3 -c "print($k*$STEP)")
  OMP_NUM_THREADS=1 $PY mac.py "$P" --start "$S" --seconds "$STEP" --out "$OUT/part$k.mp4" "$@" 2>/dev/null &
done
wait
for k in $(seq 0 $((N-1))); do echo "file part$k.mp4"; done > "$OUT/parts.txt"
ffmpeg -v error -y -f concat -i "$OUT/parts.txt" -c copy -movflags +faststart "$OUT/$NAME.mp4"
rm "$OUT"/part*.mp4 "$OUT/parts.txt"
ffprobe -v error -show_entries stream=width,height,r_frame_rate:format=duration -of compact "$OUT/$NAME.mp4"
