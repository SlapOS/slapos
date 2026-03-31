#!/bin/bash
# Rebuild a SlapOS software release.
# Usage: rebuild.sh <env-local-json> [software-path-or-name]
#
# Reads env.local.json to find the slapos environment, identifies the
# software release hash, removes .completed, and runs slapos node software.

set -e

ENV_JSON="$1"
SR_FILTER="$2"

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

# Source the environment (suppress verbose output)
source "$SR_ENV" 2>/dev/null

# Get the slapos base directory
SLAPOS_BASE=$(dirname $(dirname "$SR_ENV"))

# Find software releases from proxy
echo "=== Software releases in proxy ==="
PROXY_OUTPUT=$(slapos proxy show 2>&1)

# Extract software table lines (URL + hash)
echo "$PROXY_OUTPUT" | grep -E '^\s+/' | while read -r line; do
  url=$(echo "$line" | awk '{print $1}')
  state=$(echo "$line" | awk '{print $(NF-1)}')
  hash=$(echo "$line" | awk '{print $NF}')
  name=$(basename $(dirname "$url"))
  echo "  $name ($state) hash=$hash path=$url"
done

echo ""

if [ -n "$SR_FILTER" ]; then
  # Find matching software release
  SR_LINE=$(echo "$PROXY_OUTPUT" | grep -E '^\s+/' | grep -i "$SR_FILTER" | grep 'available' | head -1)
else
  # Try to detect from current directory
  CWD=$(pwd)
  SR_LINE=$(echo "$PROXY_OUTPUT" | grep -E '^\s+/' | grep 'available' | while read -r line; do
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

# Find software directory
SOFT_DIR="$SLAPOS_BASE/tmp/soft/$SR_HASH"
if [ ! -d "$SOFT_DIR" ]; then
  echo "ERROR: Software directory not found: $SOFT_DIR"
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

# Remove .completed
if [ -f "$SOFT_DIR/.completed" ]; then
  rm "$SOFT_DIR/.completed"
  echo "Removed $SOFT_DIR/.completed"
else
  echo ".completed already absent"
fi

# Rebuild
echo ""
echo "=== Running slapos node software --only=$SR_HASH ==="
slapos node software --only="$SR_HASH" 2>&1 | tail -20

echo ""
if [ -f "$SOFT_DIR/.completed" ]; then
  echo "=== SUCCESS: Software rebuild completed ==="
else
  echo "=== FAILED: Software rebuild did not complete ==="
  exit 1
fi
