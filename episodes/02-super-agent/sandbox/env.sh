# Sourced by every in-sandbox script. Every value can be overridden from the environment.
export HOME=/home/agent
export DSH_HOME=$HOME/.dsh
export KIT_IN=${KIT_IN:-/tmp/kit}                     # where the host uploaded this kit's sandbox/ files + per-run inputs
export SANDBOX_HOST_ALIAS=${SANDBOX_HOST_ALIAS:-host.openshell.internal}   # OpenShell's generic name for the sandbox host
export MODEL_HOST_PORT=${MODEL_HOST_PORT:-8000}       # OpenAI-compatible server (e.g. vLLM) on the host
export FORGE_HOST_PORT=${FORGE_HOST_PORT:-13300}      # forge relay on the host
export MODEL_ID=${MODEL_ID:-your-local-model}         # set this to the model id your endpoint serves
export MODEL_CONTEXT=${MODEL_CONTEXT:-131072} MODEL_MAX_TOKENS=${MODEL_MAX_TOKENS:-32768}
export FORGE_URL=http://127.0.0.1:3000                # the forge as the agent sees it (fixed: A1 patch and A5 use it)
export FORGE_REPO=${FORGE_REPO:-maint/widgets} FORGE_LOGIN=${FORGE_LOGIN:-agentbot}
export LOCAL_VLLM_API_KEY=unused                      # the local endpoint needs no key; dsh wants the variable to exist
# Canary placed in the agent processes' environment (injection check). Value comes from the per-run canaries file.
[ -f "$KIT_IN/canaries.env" ] && . "$KIT_IN/canaries.env"
export DSHSA_CANARY=${CANARY_ENV:-CANARY-ENV-unset}
export PATH=$HOME/.local/bin:$PATH
