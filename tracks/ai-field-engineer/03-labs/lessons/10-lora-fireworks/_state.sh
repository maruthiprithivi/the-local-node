# Shared by the numbered scripts: remembers ids between steps in .state (git-ignored).
# shellcheck disable=SC2034
STATE="$(dirname "$0")/.state"
[[ -f "$STATE" ]] && source "$STATE"
save() { echo "$1=\"$2\"" >> "$STATE"; eval "$1=\"$2\""; }
ACCOUNT=${FIREWORKS_ACCOUNT_ID:-$(firectl whoami 2>/dev/null | grep -oE 'accounts/[a-z0-9-]+' | head -1 | cut -d/ -f2)}
BASE_MODEL=${BASE_MODEL:-accounts/fireworks/models/qwen2p5-7b-instruct}   # must be tunable — check the docs list
DEPLOY_RATE=${DEPLOY_RATE:-8}   # $/hour for the deployment shape you get — check the pricing page
