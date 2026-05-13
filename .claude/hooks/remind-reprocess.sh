#!/bin/bash
# PostToolUse hook: remind to run /reprocess-instance when instance templates change.
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

# Skip test files
if echo "$REL_PATH" | grep -qE '^software/[^/]+/test'; then
  exit 0
fi

# Match instance templates: instance*.cfg.in, templates/*.in
if echo "$REL_PATH" | grep -qE '(instance.*\.cfg\.in|templates/.*\.in)$'; then
  BASENAME=$(basename "$REL_PATH")
  echo "Instance template changed: $BASENAME. Run /reprocess-instance to apply." >&2
fi

exit 0
