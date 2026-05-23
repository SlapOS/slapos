#!/bin/bash
# Destroy a SlapOS instance (IRREVERSIBLE).
# Usage: destroy.sh [env-local-json] <partition-reference>
#
# Environment setup:
# - Default: sources ~/bin/slapos-standalone-activate
# - For testing: pass env.local.json path to source slapos-sr-testing-environment
#
# Flow:
# 1. Look up the software URL for <partition-reference> from the proxy DB.
# 2. Require an interactive 'yes' confirmation.
# 3. slapos request <ref> <url> --state destroyed.
# 4. Loop slapos node report (up to 5 times), then one final slapos node instance
#    pass, polling the proxy DB after each step until the row is no longer busy.

set -e

echo "############################################################"
echo "# DESTROY-INSTANCE — IRREVERSIBLE DESTRUCTION"
echo "# Partition filesystem, databases and logs will be removed."
echo "############################################################"
echo ""

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
  # When no env.local.json, first arg is the partition reference.
  PARTITION="$1"
fi

# --- Validate partition reference ---
if [ -z "$PARTITION" ]; then
  echo "ERROR: partition reference is required."
  echo "Usage: destroy.sh [env-local-json] <partition-reference>"
  exit 1
fi
case "$PARTITION" in
  "*"|all|ALL|any|ANY)
    echo "ERROR: refusing wildcard/bulk destruction. Name one partition reference."
    exit 1
    ;;
esac
case "$PARTITION" in
  *"*"*|*"?"*|*"["*|*" "*)
    echo "ERROR: partition reference must be a plain name, got: $PARTITION"
    exit 1
    ;;
esac

PROXY_DB="$SLAPOS_BASE/var/proxy.db"
if [ ! -f "$PROXY_DB" ]; then
  echo "ERROR: proxy DB not found at $PROXY_DB"
  exit 1
fi

# --- Look up software URL for this partition reference ---
# Only match busy partitions (slap_state = 'busy'); a 'free' row means it is
# already destroyed or never allocated.
ROW=$(sqlite3 -separator $'\t' "$PROXY_DB" \
  "SELECT reference, partition_reference, software_release, slap_state
   FROM partition17
   WHERE partition_reference = '$PARTITION' AND slap_state = 'busy'")

ROW_COUNT=$(printf '%s\n' "$ROW" | grep -c . || true)
if [ "$ROW_COUNT" -eq 0 ]; then
  echo "ERROR: no busy partition with reference '$PARTITION' in $PROXY_DB"
  echo "       (run '/slapos-status' to list current partitions)"
  exit 1
fi
if [ "$ROW_COUNT" -gt 1 ]; then
  echo "ERROR: more than one busy partition matches '$PARTITION':"
  printf '%s\n' "$ROW"
  echo "       refusing to guess. Destroy each one by its unique reference."
  exit 1
fi

SLOT=$(printf '%s' "$ROW" | cut -f1)
SOFTWARE_URL=$(printf '%s' "$ROW" | cut -f3)

echo "Target partition:"
echo "  slot              : $SLOT"
echo "  reference         : $PARTITION"
echo "  software_release  : $SOFTWARE_URL"
echo ""

# --- Explicit interactive confirmation ---
if [ ! -t 0 ]; then
  echo "ERROR: destroy.sh requires an interactive terminal for confirmation."
  echo "       Re-run it from a shell, not from a pipe or non-interactive wrapper."
  exit 1
fi
printf "Type 'yes' to permanently destroy this partition: "
read CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Aborted — no changes made."
  exit 1
fi

# --- Kill any running slapos node processes (we need exclusive access) ---
for phase in software instance report; do
  PID_FILE="$SLAPOS_BASE/var/run/slapos-node-$phase.pid"
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
      echo "Killing existing slapos node $phase (PID $PID)..."
      kill "$PID" 2>/dev/null || true
      sleep 1
    fi
  fi
done

# --- Mark for destruction ---
echo ""
echo "=== slapos request $PARTITION ... --state destroyed ==="
slapos request "$PARTITION" "$SOFTWARE_URL" --state destroyed 2>&1 | tail -20

# Helper: is this partition still busy in the proxy DB?
is_still_busy() {
  local count
  count=$(sqlite3 "$PROXY_DB" \
    "SELECT COUNT(*) FROM partition17
     WHERE partition_reference = '$PARTITION' AND slap_state = 'busy'")
  [ "$count" != "0" ]
}

# --- Loop slapos node report up to 5 passes ---
MAX_PASSES=5
for i in $(seq 1 "$MAX_PASSES"); do
  echo ""
  echo "=== slapos node report (pass $i/$MAX_PASSES) ==="
  slapos node report 2>&1 | tail -20 || true
  if ! is_still_busy; then
    echo ""
    echo "=== Partition $PARTITION no longer busy in proxy DB (after report pass $i) ==="
    break
  fi
  sleep 1
done

# --- Final cleanup pass: slapos node instance on the freed slot ---
# After destruction, the partition directory still contains .slapgrid/.timestamp
# leftovers; slapgrid.py:1420 removes them on the next instance pass.
if [ -n "$SLOT" ]; then
  echo ""
  echo "=== slapos node instance --force --only=$SLOT (cleanup) ==="
  slapos node instance --force --only="$SLOT" 2>&1 | tail -20 || true
fi

echo ""
if is_still_busy; then
  echo "WARN: $PARTITION is still marked busy after $MAX_PASSES report passes."
  echo "      Likely a process refused to stop. Investigate with:"
  echo "        slapos node supervisorctl status | grep $SLOT"
  echo "      Then re-run /destroy-instance $PARTITION."
  exit 1
fi

echo "=== Destruction complete for $PARTITION ==="
echo "Run /slapos-status to confirm, and remove any leftover"
echo "~/srv/project/${PARTITION}-request.py request script manually."
