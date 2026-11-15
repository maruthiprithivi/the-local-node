# Sandcastle 0.14.0 OpenCode image, versions pinned (the upstream init template uses opencode-ai@latest).
# Base digest recorded in versions.txt.
FROM node:22-bookworm@sha256:e13726ca604184d7a91fcacab1fc09eefd642dc28e79ac34e85540dd93b78cfb

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    jq \
    iputils-ping \
    libcap2-bin \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ARG AGENT_UID=1000
ARG AGENT_GID=1000

RUN groupmod -o -g $AGENT_GID node && usermod -o -u $AGENT_UID -g $AGENT_GID -d /home/agent -m -l agent node

# Pin OpenCode to the npm latest current as of 2026-11-15 (1.19.5), not @latest.
# 1.19.5 still accepts `opencode export` / `opencode import` and `opencode run --format json`.
# --help lists --auto for permissions; --dangerously-skip-permissions (what Sandcastle 0.14.0 passes) is accepted and does not abort the CLI.
RUN npm install -g opencode-ai@1.19.5

USER ${AGENT_UID}:${AGENT_GID}
WORKDIR /home/agent
ENTRYPOINT ["sleep", "infinity"]
