#!/bin/bash
# Adaptation A4 (mode a): under Node 24 the dsh main thread's comm name is 'MainThread', which the prototype's
# service script process finder (comm in node/dsh) does not recognise. Accept it too (process detection only).
# usage: A4-status-mainthread.sh <path to the copied scripts/dsh-superagent>
set -e
f=${1:?path to scripts/dsh-superagent}
sed -i "s/name in ('node', 'dsh')/name in ('node', 'dsh', 'MainThread')/g" "$f"
n=$(grep -c MainThread "$f"); echo "A4 applied: $n line(s)"; [ "$n" -ge 1 ]
