#!/bin/bash
# Reprocess SlapOS instances.
# Usage: reprocess.sh <env-local-json> [partition]
#
# Reads env.local.json to find the slapos environment, kills any running
# slapos node instance process, and runs slapos node instance.

set -e

ENV_JSON="$1"
PARTITION="$2"

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

SLAPOS_BASE=$(dirname $(dirname "$SR_ENV"))

# Kill any running slapos node instance process
PID_FILE="$SLAPOS_BASE/var/run/slapos-node-instance.pid"
if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE" 2>/dev/null)
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "Killing existing slapos node instance (PID $PID)..."
    kill "$PID" 2>/dev/null || true
    sleep 1
  fi
fi

# Run slapos node instance
if [ -n "$PARTITION" ]; then
  echo "=== Reprocessing partition: $PARTITION ==="
  slapos node instance --only="$PARTITION" 2>&1 | tail -30
else
  echo "=== Reprocessing all instances ==="
  slapos node instance --all 2>&1 | tail -30
fi

echo ""
echo "=== Instance processing complete ==="
