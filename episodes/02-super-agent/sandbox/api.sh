#!/bin/bash
# usage: api.sh METHOD path [json]   (dsh-superagent Management API inside the sandbox)
m=$1; p=$2; d=$3; U=http://127.0.0.1:3082/orchestrator/api
if [ -n "$d" ]; then curl -s -X "$m" -H 'x-orchestrator-request: 1' -H 'content-type: application/json' --data "$d" "$U/$p"
else curl -s -X "$m" -H 'x-orchestrator-request: 1' "$U/$p"; fi
