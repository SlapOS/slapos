#!/bin/bash
# Reprocess SlapOS instances.
# Usage: reprocess.sh [env-local-json] [partition]
#
# Environment setup:
# - Default: sources ~/bin/slapos-standalone-activate
# - For testing: pass env.local.json path to source slapos-sr-testing-environment

set -e

ENV_JSON="$1"
PARTITION="$2"

# --- Environment setup ---
if [ -n "$ENV_JSON" ] && [ -f "$ENV_JSON" ]; then
  # Testing mode: use env.local.json
  SR_ENV=$(grep '"slapos-sr-testing-environment"' "$ENV_JSON" | sed 's/.*: *"\(.*\)".*/\1/')
  if [ ! -f "$SR_ENV" ]; then
    echo "ERROR: slapos environment script not found: $SR_ENV"
    exit 1
  fi
  source "$SR_ENV" 2>/dev/null
  SLAPOS_BASE=$(dirname $(dirname "$SR_ENV"))
else
  # Default mode: source slapos-standalone-activate
  ACTIVATE="$HOME/bin/slapos-standalone-activate"
  if [ ! -f "$ACTIVATE" ]; then
    echo "ERROR: $ACTIVATE not found and no env.local.json provided."
    exit 1
  fi
  source "$ACTIVATE" 2>/dev/null
  SLAPOS_BASE="$HOME/srv/runner"
  # When no env.local.json, first arg is the partition
  PARTITION="$1"
fi

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
  slapos node instance --force --only="$PARTITION" 2>&1 | tail -30
else
  echo "=== Reprocessing all instances ==="
  slapos node instance --force 2>&1 | tail -30
fi

echo ""
echo "=== Instance processing complete ==="
