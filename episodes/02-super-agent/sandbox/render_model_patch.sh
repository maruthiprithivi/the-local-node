#!/bin/bash
# Renders model.patch.yml.tmpl with MODEL_ID / MODEL_CONTEXT / MODEL_MAX_TOKENS into $KIT_IN/model.patch.yml.
. "$(dirname "$0")/env.sh"
python3 -c 'import os,sys; print(os.path.expandvars(open(sys.argv[1]).read()), end="")' "$KIT_IN/model.patch.yml.tmpl" > "$KIT_IN/model.patch.yml"
