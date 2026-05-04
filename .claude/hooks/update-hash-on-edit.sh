#!/bin/bash
# PostToolUse hook: run update-hash when a file under software/*/ is modified,
# unless the file is under software/*/test*.
set -e

# Read tool input from stdin
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

PROJECT_DIR=$(echo "$INPUT" | jq -r '.cwd // empty')
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi

# Make path relative to project dir
REL_PATH="${FILE_PATH#"$PROJECT_DIR"/}"

# Check if file is under software/*/
if ! echo "$REL_PATH" | grep -qE '^software/[^/]+/'; then
  exit 0
fi

# Skip test files (software/*/test*)
if echo "$REL_PATH" | grep -qE '^software/[^/]+/test'; then
  exit 0
fi

# Extract the software directory (e.g. software/rapid-cdn)
SOFTWARE_DIR=$(echo "$REL_PATH" | sed 's|^\(software/[^/]*\)/.*|\1|')

cd "$PROJECT_DIR/$SOFTWARE_DIR"
../../update-hash >&2

exit 0
