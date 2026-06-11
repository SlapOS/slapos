#!/bin/bash
# PostToolUse hook: verify buildout.hash.cfg md5sums are up-to-date after edits.
# This runs after update-hash-on-edit.sh and checks if the hash file has unstaged changes,
# which would indicate the update-hash script could not run or a new file was added
# without a corresponding hash entry.
set -e

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

PROJECT_DIR=$(echo "$INPUT" | jq -r '.cwd // empty')
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi

REL_PATH="${FILE_PATH#"$PROJECT_DIR"/}"

# Check if file is under software/*/
if ! echo "$REL_PATH" | grep -qE '^software/[^/]+/'; then
  exit 0
fi

# Skip test files and buildout.hash.cfg itself
if echo "$REL_PATH" | grep -qE '^software/[^/]+/test'; then
  exit 0
fi
if echo "$REL_PATH" | grep -qE 'buildout\.hash\.cfg$'; then
  exit 0
fi

# Extract the software directory
SOFTWARE_DIR=$(echo "$REL_PATH" | sed 's|^\(software/[^/]*\)/.*|\1|')
HASH_FILE="$PROJECT_DIR/$SOFTWARE_DIR/buildout.hash.cfg"

if [ ! -f "$HASH_FILE" ]; then
  exit 0
fi

# Check if the edited file is a .in template that should be tracked in buildout.hash.cfg
if echo "$REL_PATH" | grep -qE '\.in$'; then
  # Extract just the filename relative to the software dir
  FILE_IN_SW="${REL_PATH#"$SOFTWARE_DIR"/}"
  # Check if this file is referenced in buildout.hash.cfg
  if ! grep -q "$FILE_IN_SW" "$HASH_FILE" 2>/dev/null; then
    echo "Warning: $FILE_IN_SW is not tracked in $SOFTWARE_DIR/buildout.hash.cfg. Add a section with _update_hash_filename_ = $FILE_IN_SW" >&2
  fi
fi

exit 0
