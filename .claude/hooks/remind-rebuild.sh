#!/bin/bash
# PostToolUse hook: remind to run /rebuild-software when build-affecting files change.
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

# Check if file is a build-affecting file under software/*/
if ! echo "$REL_PATH" | grep -qE '^software/[^/]+/'; then
  exit 0
fi

# Skip test files
if echo "$REL_PATH" | grep -qE '^software/[^/]+/test'; then
  exit 0
fi

# Match build-affecting files: software.cfg, setup.py, software.py, component changes
BASENAME=$(basename "$REL_PATH")
case "$BASENAME" in
  software.cfg|setup.py|software.py)
    echo "Build-affecting file changed: $BASENAME. Run /rebuild-software to apply." >&2
    ;;
esac

exit 0
