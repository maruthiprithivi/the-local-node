#!/bin/sh
# Run only on a parent-approved Linux worker; no provider/model calls.
set -eu
cd "$(dirname "$0")/.."
python -m pytest -q
for lesson in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32; do
  for scenario in coding sre automation; do
    python -m course_harness checkpoint "$lesson" --scenario "$scenario"
  done
done
