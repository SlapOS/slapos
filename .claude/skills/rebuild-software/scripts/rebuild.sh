#!/bin/bash
# Rebuild a SlapOS software release.
# Usage: rebuild.sh [env-local-json] [software-path-or-name]
#
# Environment setup:
# - Default: sources ~/bin/slapos-standalone-activate
# - For testing: pass env.local.json path to source slapos-sr-testing-environment
#
# Runs `slapos node software --force` (which ignores the extends-cache;
# removing .completed alone is not equivalent).

set -e

ENV_JSON="$1"
SR_FILTER="$2"

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
  # When no env.local.json, first arg is the SR filter
  SR_FILTER="$1"
fi

# Find software releases from proxy
echo "=== Software releases in proxy ==="
PROXY_OUTPUT=$(slapos proxy show 2>&1)

# Extract software table lines (URL + hash)
echo "$PROXY_OUTPUT" | grep -E '^\s+(https?://|/)' | while read -r line; do
  url=$(echo "$line" | awk '{print $1}')
  state=$(echo "$line" | awk '{print $(NF-1)}')
  hash=$(echo "$line" | awk '{print $NF}')
  name=$(basename $(dirname "$url"))
  echo "  $name ($state) hash=$hash path=$url"
done

echo ""

if [ -n "$SR_FILTER" ]; then
  # Find matching software release
  SR_LINE=$(echo "$PROXY_OUTPUT" | grep -E '^\s+(https?://|/)' | grep -i "$SR_FILTER" | grep 'available' | head -1)
else
  # Try to detect from current directory
  CWD=$(pwd)
  SR_LINE=$(echo "$PROXY_OUTPUT" | grep -E '^\s+(https?://|/)' | grep 'available' | while read -r line; do
    url=$(echo "$line" | awk '{print $1}')
    if echo "$CWD" | grep -q "$(dirname "$url")" 2>/dev/null; then
      echo "$line"
      break
    fi
  done)
fi

if [ -z "$SR_LINE" ]; then
  echo "ERROR: No matching software release found."
  echo "Specify a software name or path as argument."
  exit 1
fi

SR_HASH=$(echo "$SR_LINE" | awk '{print $NF}')
SR_URL=$(echo "$SR_LINE" | awk '{print $1}')
SR_NAME=$(basename $(dirname "$SR_URL"))
echo "=== Rebuilding: $SR_NAME (hash: $SR_HASH) ==="

# Find software directory from slapos config
# SLAPOS_CONFIGURATION is set by the sourced environment
SOFT_ROOT=$(grep 'software_root' "${SLAPOS_CONFIGURATION:-$SLAPOS_BASE/etc/slapos.cfg}" 2>/dev/null | head -1 | sed 's/.*= *//')
SOFT_DIR=""
if [ -n "$SOFT_ROOT" ] && [ -d "$SOFT_ROOT/$SR_HASH" ]; then
  SOFT_DIR="$SOFT_ROOT/$SR_HASH"
else
  # Fallback: search common locations
  for d in "$SLAPOS_BASE/tmp/soft/$SR_HASH" "$(dirname "$SLAPOS_BASE")/software/$SR_HASH" "$(dirname $(dirname "$SLAPOS_BASE"))/software/$SR_HASH"; do
    if [ -d "$d" ]; then
      SOFT_DIR="$d"
      break
    fi
  done
fi
if [ -z "$SOFT_DIR" ] || [ ! -d "$SOFT_DIR" ]; then
  echo "ERROR: Software directory not found for hash: $SR_HASH"
  exit 1
fi

# Kill any running slapos node software process
PID_FILE="$SLAPOS_BASE/var/run/slapos-node-software.pid"
if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE" 2>/dev/null)
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "Killing existing slapos node software (PID $PID)..."
    kill "$PID" 2>/dev/null || true
    sleep 1
  fi
fi

# Rebuild
echo ""
echo "=== Running slapos node software --force --only=$SR_HASH ==="
slapos node software --force --only="$SR_HASH" 2>&1 | tail -20

echo ""
if [ -f "$SOFT_DIR/.completed" ]; then
  echo "=== SUCCESS: Software rebuild completed ==="
else
  echo "=== FAILED: Software rebuild did not complete ==="
  exit 1
fi
