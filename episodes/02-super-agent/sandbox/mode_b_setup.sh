#!/bin/bash
# Mode b: one plain headless dsh session (with the subagent tool available) in the same sandbox layout.
. "$(dirname "$0")/env.sh"; cd "$HOME"; set -e
mkdir -p "$DSH_HOME/profiles/headless"
cp "$KIT_IN/model.patch.yml" "$DSH_HOME/profiles/headless/cordis.patch.yml"
ln -sf /opt/ghcompat/gh ~/.local/bin/gh
# Same credential arrangement as mode a: only the agent's gh answers for the forge URL.
cat > ~/.gitconfig <<G
[user]
	useConfigOnly = true
[credential]
	helper =
[credential "$FORGE_URL"]
	helper = !/opt/ghcompat/gh auth git-credential
G
echo MODE_B_READY
