#!/bin/bash
# Mode a: set up dsh-superagent as the prototype's SETUP.md / docs/006-deployment.md describe (inside the sandbox).
. "$(dirname "$0")/env.sh"; cd "$HOME"; set -e
rm -rf ~/dsh-superagent; mkdir ~/dsh-superagent; cd ~/dsh-superagent
# Read-only prototype build lives in /opt/dsh-superagent; link it, but copy scripts/ so A4 can edit it.
for f in /opt/dsh-superagent/* /opt/dsh-superagent/.gitignore; do b=$(basename "$f"); [ "$b" = scripts ] && cp -a "$f" . || ln -s "$f" "$b"; done
bash "$KIT_IN/A4-status-mainthread.sh" scripts/dsh-superagent
dsh superagent --from-default-profile web --dump-config > /tmp/dump-config.txt 2>&1 || { tail -20 /tmp/dump-config.txt; exit 1; }
dsh plugin --profile superagent add "link:$PWD" 2>&1 | tail -5
cat > "$DSH_HOME/profiles/superagent/cordis.patch.yml" <<Y
- id: webserver
  config:
    host: 127.0.0.1
    port: 3082
- id: dsh-superagent
  config:
    stateDir: $HOME/.dsh/state/superagent
$(cat "$KIT_IN/model.patch.yml")
Y
echo MODE_A_READY
