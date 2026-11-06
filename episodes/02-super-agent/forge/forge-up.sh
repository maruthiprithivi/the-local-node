#!/bin/bash
# Start the throwaway Gitea forge. Gitea runs with NO network at all (--network none) and listens on a unix
# socket; forge/relay.py exposes that socket on 127.0.0.1:$FORGE_HOST_PORT for the host runner and, through the
# sandbox network policy, for the in-sandbox forwarder only. Fake accounts only; registration disabled.
# The socket is mode 600 and owned by FORGE_UID (default 1000): run this, relay.py and the runner as that host uid.
set -euo pipefail
KIT_STATE=${KIT_STATE:-$PWD/state}
D=$KIT_STATE/forge
IMG=${GITEA_IMAGE:-gitea/gitea:1.27.3-rootless@sha256:1c17ecaead42eb3b5391553d8708103a4beb0e86edf5b9ebc1eb269c318845f2}
mkdir -p "$D/sock"; chmod 700 "$D/sock"
docker rm -f dshsa-forge >/dev/null 2>&1 || true
docker run -d --name dshsa-forge --label bench=dshsa \
  --network none --user "${FORGE_UID:-1000}:${FORGE_GID:-1000}" --cap-drop ALL --security-opt no-new-privileges \
  --memory 2g --memory-swap 2g --pids-limit 512 --cpus 2 \
  -v dshsa-forge-data:/var/lib/gitea -v dshsa-forge-conf:/etc/gitea -v "$D/sock":/sock \
  -e GITEA__database__DB_TYPE=sqlite3 \
  -e GITEA__security__INSTALL_LOCK=true \
  -e GITEA__server__PROTOCOL=http+unix -e GITEA__server__HTTP_ADDR=/sock/gitea.sock \
  -e GITEA__server__UNIX_SOCKET_PERMISSION=600 \
  -e GITEA__server__ROOT_URL=http://127.0.0.1:3000/ -e GITEA__server__DOMAIN=127.0.0.1 \
  -e GITEA__server__DISABLE_SSH=true -e GITEA__server__START_SSH_SERVER=false -e GITEA__server__OFFLINE_MODE=true \
  -e GITEA__service__DISABLE_REGISTRATION=true -e GITEA__service__REQUIRE_SIGNIN_VIEW=true \
  -e GITEA__repository__DISABLE_MIGRATIONS=true -e GITEA__mirror__ENABLED=false \
  -e GITEA__webhook__ALLOWED_HOST_LIST=loopback \
  -e GITEA__packages__ENABLED=false -e GITEA__actions__ENABLED=false \
  -e GITEA__api__ENABLE_SWAGGER=false -e GITEA__log__LEVEL=Info \
  -e GITEA__other__SHOW_FOOTER_VERSION=false \
  "$IMG" >/dev/null
for i in $(seq 60); do [ -S "$D/sock/gitea.sock" ] && break; sleep 1; done
[ -S "$D/sock/gitea.sock" ] || { docker logs --tail 30 dshsa-forge; exit 1; }
echo "forge up (network none). Next: python3 forge/relay.py ${FORGE_HOST_PORT:-13300} $D/sock/gitea.sock $D/relay.log &"
