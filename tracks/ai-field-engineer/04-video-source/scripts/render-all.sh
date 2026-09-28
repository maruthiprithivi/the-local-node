#!/usr/bin/env bash
# Render every explainer to out/<id>.mp4 (1440x810, subtitles burned in)
set -uo pipefail
cd "$(dirname "$0")/.."
IDS=${IDS:-$(node -e "console.log(Object.keys(require('./src/narration.json')).join(' '))")}
mkdir -p out
BROWSER=${BROWSER_BIN:-}
[ -n "$BROWSER" ] && BFLAG="--browser-executable=$BROWSER" || BFLAG=""
[ -z "$BROWSER" ] && npx remotion browser ensure
for id in $IDS; do
  [ -s "out/$id.mp4" ] && { echo "skip $id (exists)"; continue; }
  echo "── rendering $id  $(date +%H:%M:%S)"
  npx remotion render "$id" "out/$id.mp4" $BFLAG \
    --concurrency=2 --scale=0.65 --jpeg-quality=78 --log=error || echo "FAILED $id"
done
echo "done $(date +%H:%M:%S)"
ls -lh out/*.mp4
