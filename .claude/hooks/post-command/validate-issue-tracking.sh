#!/usr/bin/env bash
# Post-command hook: Validate GH issue tracking label comments.
#
# Fires after every Bash tool use. If the command was a `gh issue edit --add-label "has-*"`
# call, checks that the most recent comment on that issue contains the matching 🏷️ header.
# Advisory only — always exits 0.

set -euo pipefail

# Read the hook payload from stdin (JSON with tool_name, tool_input, etc.)
INPUT=$(cat)

# Extract the bash command that was executed
BASH_CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null) || BASH_CMD=""

# Only act on `gh issue edit ... --add-label "has-` commands
if ! printf '%s' "$BASH_CMD" | grep -qE 'gh issue edit.*--add-label.*"has-'; then
    exit 0
fi

# Extract the issue number (first numeric argument after `gh issue edit`)
ISSUE_NUMBER=$(printf '%s' "$BASH_CMD" \
    | grep -oE 'gh issue edit [0-9]+' \
    | grep -oE '[0-9]+$') || ISSUE_NUMBER=""

if [ -z "$ISSUE_NUMBER" ]; then
    exit 0
fi

# Extract the label name from --add-label "has-..."
LABEL_NAME=$(printf '%s' "$BASH_CMD" \
    | grep -oE '"has-[^"]*"' \
    | head -1 \
    | tr -d '"') || LABEL_NAME=""

if [ -z "$LABEL_NAME" ]; then
    exit 0
fi

# Fetch the latest comment body on the issue
LATEST_COMMENT=$(gh issue view "$ISSUE_NUMBER" --json comments \
    --jq '.comments[-1].body // ""' 2>/dev/null) || LATEST_COMMENT=""

# Check whether it contains the expected 🏷️ header
if ! printf '%s' "$LATEST_COMMENT" | grep -qF "🏷️ ${LABEL_NAME}"; then
    echo "⚠️  [validate-issue-tracking] Warning: label '${LABEL_NAME}' was added to issue #${ISSUE_NUMBER}" >&2
    echo "   but the most recent comment does not contain a '🏷️ ${LABEL_NAME}' header." >&2
    echo "   Consider adding a tracking comment to document why this label was applied." >&2
fi

exit 0
