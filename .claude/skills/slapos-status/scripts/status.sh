#!/bin/bash
# Show SlapOS proxy status and instance state.
# Usage: status.sh <env-local-json> [filter]
#
# Reads env.local.json to find the slapos environment, runs slapos proxy show,
# and optionally filters the output.

set -e

ENV_JSON="$1"
FILTER="$2"

if [ -z "$ENV_JSON" ] || [ ! -f "$ENV_JSON" ]; then
  echo "ERROR: env.local.json not found at: $ENV_JSON"
  exit 1
fi

# Extract slapos-sr-testing-environment path from JSON
SR_ENV=$(python3 -c "import json; print(json.load(open('$ENV_JSON'))['slapos-sr-testing-environment'])")
if [ ! -f "$SR_ENV" ]; then
  echo "ERROR: slapos environment script not found: $SR_ENV"
  exit 1
fi

# Source the environment
source "$SR_ENV" 2>/dev/null

echo "=== SlapOS Proxy Status ==="
echo ""

if [ -n "$FILTER" ]; then
  slapos proxy show 2>&1 | grep -i -A2 "$FILTER"
else
  slapos proxy show 2>&1
fi
