#!/bin/bash
# Show SlapOS proxy status and instance state.
# Usage: status.sh [env-local-json] [filter]
#
# Environment setup:
# - Default: sources ~/bin/slapos-standalone-activate
# - For testing: pass env.local.json path to source slapos-sr-testing-environment

set -e

ENV_JSON="$1"
FILTER="$2"

# --- Environment setup ---
if [ -n "$ENV_JSON" ] && [ -f "$ENV_JSON" ]; then
  # Testing mode: use env.local.json
  SR_ENV=$(grep '"slapos-sr-testing-environment"' "$ENV_JSON" | sed 's/.*: *"\(.*\)".*/\1/')
  if [ ! -f "$SR_ENV" ]; then
    echo "ERROR: slapos environment script not found: $SR_ENV"
    exit 1
  fi
  source "$SR_ENV" 2>/dev/null
else
  # Default mode: source slapos-standalone-activate
  ACTIVATE="$HOME/bin/slapos-standalone-activate"
  if [ ! -f "$ACTIVATE" ]; then
    echo "ERROR: $ACTIVATE not found and no env.local.json provided."
    exit 1
  fi
  source "$ACTIVATE" 2>/dev/null
  # When no env.local.json, first arg is the filter
  FILTER="$1"
fi

echo "=== SlapOS Proxy Status ==="
echo ""

if [ -n "$FILTER" ]; then
  slapos proxy show 2>&1 | grep -i -A2 "$FILTER"
else
  slapos proxy show 2>&1
fi
