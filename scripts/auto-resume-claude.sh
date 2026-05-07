#!/usr/bin/env bash
set -euo pipefail

# Auto-resume Claude CLI after usage quota expiry.
#
# Runs /supercycle-work for GitHub issues autonomously. Detects epics
# and loops through all open sub-issues until the epic is complete.
# When the 5h usage quota expires, waits and resumes automatically.
#
# Usage:
#   ./scripts/auto-resume-claude.sh 424              # single issue
#   ./scripts/auto-resume-claude.sh 417              # epic — loops all sub-issues
#   ./scripts/auto-resume-claude.sh 424 --max-retries 10
#   ./scripts/auto-resume-claude.sh --resume

RETRY_INTERVAL_MIN=10
MAX_RETRIES=50
LOG_FILE="claude-auto-resume.log"
OUTPUT_DIR="claude-auto-resume-output"
VERBOSITY="quiet"  # quiet | normal | verbose

ISSUE_NUMBER=""
RESUME_MODE=false
SUPERCYCLE_CMD="supercycle-work"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-retries)  MAX_RETRIES="$2"; shift 2 ;;
    --interval)     RETRY_INTERVAL_MIN="$2"; shift 2 ;;
    --log)          LOG_FILE="$2"; shift 2 ;;
    --resume)       RESUME_MODE=true; shift ;;
    --verbose)      VERBOSITY="verbose"; shift ;;
    --normal)       VERBOSITY="normal"; shift ;;
    --quiet)        VERBOSITY="quiet"; shift ;;
    --implement)    SUPERCYCLE_CMD="supercycle-implement"; shift ;;
    -*)             echo "Unknown option: $1" >&2; exit 1 ;;
    *)              ISSUE_NUMBER="$1"; shift ;;
  esac
done

if [[ "$RESUME_MODE" == false && -z "$ISSUE_NUMBER" ]]; then
  cat >&2 <<'USAGE'
Usage: auto-resume-claude.sh <issue-number> [options]
       auto-resume-claude.sh --resume [options]

Output modes:
  --quiet (default)  Only log messages, no Claude output on terminal
  --normal           Status lines on terminal, full Claude output in files
  --verbose          Full Claude output streamed to terminal (+ files)

Options:
  --resume           Resume last conversation instead of starting new
  --implement        Use /supercycle-implement instead of /supercycle-work
  --max-retries N    Max retry attempts per issue (default: 50)
  --interval N       Minutes to wait between retries (default: 10)
  --log FILE         Log file path (default: claude-auto-resume.log)

Examples:
  ./scripts/auto-resume-claude.sh 424
  ./scripts/auto-resume-claude.sh 417                # epic — auto-loops sub-issues
  ./scripts/auto-resume-claude.sh 417 --implement    # skip brainstorming per issue
  ./scripts/auto-resume-claude.sh --resume --quiet
USAGE
  exit 1
fi

read -r -d '' AUTONOMOUS_RULES <<'RULES' || true
AUTONOMOUS EXECUTION RULES — follow these for the entire session:

1. FOCUS ON THIS SINGLE ISSUE ONLY. Complete all supercycle phases for
   the issue number given in the prompt. Do NOT pick up other issues,
   sub-issues, or related work. When this issue is done, stop.

2. RUN ALL SUPERCYCLE PHASES without stopping to ask. Do not pause
   between phases. Do not ask "shall I continue?" — just continue.

3. DECISIONS: When you encounter a question or choice, pick the
   recommended option (the one you would suggest). If no option is
   marked as recommended, pick the most pragmatic one. Never ask
   the user to choose.

4. SUBAGENTS: Always use worktree subagents for implementation work.
   Dispatch parallel subagents whenever tasks are independent.
   Do not implement in the main conversation — delegate to subagents.

5. TESTS FIRST: Write failing tests before production code (TDD).
   Never skip tests. Never weaken assertions to make tests pass.

6. CODE REVIEW: After implementation, run /supercycle-review and fix
   any findings automatically via /supercycle-fix. Do not ask whether
   to fix — just fix.

7. MERGE: After review passes, run /supercycle-merge. Push the result.
   Do not ask "ready to push?" — just push.

8. If ANY phase fails with a non-quota error, investigate the root cause,
   fix it, and retry. Do not give up or ask for help unless the error
   is truly unrecoverable (e.g. missing credentials, broken CI that
   needs human intervention).
RULES

log() {
  local ts
  ts="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "[$ts] $*" | tee -a "$LOG_FILE"
}

is_epic() {
  local issue="$1"
  gh issue view "$issue" --json labels --jq '.labels[].name' 2>/dev/null \
    | grep -qx 'epic'
}

get_open_sub_issues() {
  local epic="$1"
  local epic_node_id
  epic_node_id="$(gh api graphql -f query='{ repository(owner:"szymansk", name:"da3Dalus") { issue(number: '"$epic"') { id } } }' --jq '.data.repository.issue.id')"

  gh api graphql -f query='
    query {
      node(id: "'"$epic_node_id"'") {
        ... on Issue {
          subIssues(first: 50) {
            nodes { number title state }
          }
        }
      }
    }' --jq '.data.node.subIssues.nodes[] | select(.state == "OPEN") | .number'
}

is_quota_error() {
  local output="$1"
  local exit_code="$2"

  [[ "$exit_code" -ne 0 ]] || return 1

  grep -qiE \
    'rate.?limit|quota|usage.?limit|too.?many.?requests|capacity|throttl|429|overloaded' \
    <<< "$output"
}

is_success() {
  local exit_code="$1"
  [[ "$exit_code" -eq 0 ]]
}

build_initial_prompt() {
  local issue="${1:-$ISSUE_NUMBER}"
  cat <<EOF
/${SUPERCYCLE_CMD} #${issue}

${AUTONOMOUS_RULES}
EOF
}

build_resume_prompt() {
  cat <<EOF
The session was interrupted by a usage quota timeout.
Pick up exactly where you left off and continue the work.

${AUTONOMOUS_RULES}
EOF
}

extract_status_lines() {
  grep -iE \
    'phase|step|task|issue|#[0-9]+|implement|review|merge|test|branch|commit|push|complete|fail|error|warn|start|finish|running|creating|trim|dirty|subagent|worktree|supercycle' \
    || true
}

run_claude() {
  local attempt="$1"
  local issue="${2:-$ISSUE_NUMBER}"
  local attempt_output="${OUTPUT_DIR}/issue-${issue}-attempt-${attempt}.log"
  local exit_code=0
  local prompt

  if [[ "$attempt" -eq 1 ]]; then
    log "Starting: /${SUPERCYCLE_CMD} #${issue}"
    prompt="$(build_initial_prompt "$issue")"
  else
    log "Resuming #${issue} (attempt $attempt)"
    prompt="$(build_resume_prompt)"
  fi

  local claude_args=(--dangerously-skip-permissions)
  if [[ "$attempt" -gt 1 ]]; then
    claude_args+=(--resume)
  fi
  claude_args+=(-p "$prompt")

  case "$VERBOSITY" in
    verbose)
      claude "${claude_args[@]}" 2>&1 | tee "$attempt_output" || exit_code=$?
      ;;
    quiet)
      claude "${claude_args[@]}" > "$attempt_output" 2>&1 || exit_code=$?
      ;;
    normal)
      claude "${claude_args[@]}" 2>&1 | tee "$attempt_output" | extract_status_lines || exit_code=$?
      if [[ "${PIPESTATUS[0]}" -ne 0 ]]; then
        exit_code="${PIPESTATUS[0]}"
      fi
      ;;
  esac

  LAST_OUTPUT="$(tail -100 "$attempt_output")"
  LAST_EXIT_CODE="$exit_code"
  log "Full output saved to: $attempt_output"
}

run_single_issue() {
  local issue="$1"
  local attempt=1

  LAST_OUTPUT=""
  LAST_EXIT_CODE=0

  while [[ "$attempt" -le "$MAX_RETRIES" ]]; do
    log "--- Issue #${issue} — attempt $attempt of $MAX_RETRIES ---"

    run_claude "$attempt" "$issue"

    if is_success "$LAST_EXIT_CODE"; then
      log "Issue #${issue} completed successfully."
      return 0
    fi

    if is_quota_error "$LAST_OUTPUT" "$LAST_EXIT_CODE"; then
      log "Quota/rate-limit detected. Waiting ${RETRY_INTERVAL_MIN} minutes..."
      log "Next attempt at: $(date -v+${RETRY_INTERVAL_MIN}M '+%H:%M:%S' 2>/dev/null || date -d "+${RETRY_INTERVAL_MIN} minutes" '+%H:%M:%S' 2>/dev/null || echo "~${RETRY_INTERVAL_MIN}m from now")"
      sleep "$((RETRY_INTERVAL_MIN * 60))"
      attempt=$((attempt + 1))
    else
      log "Issue #${issue} failed with non-quota error (exit code $LAST_EXIT_CODE)."
      log "Last output tail:"
      tail -5 <<< "$LAST_OUTPUT" | while read -r line; do log "  $line"; done
      return "$LAST_EXIT_CODE"
    fi
  done

  log "Max retries ($MAX_RETRIES) exhausted for issue #${issue}."
  return 1
}

main() {
  log "=== Auto-resume session started ==="
  log "Issue: ${ISSUE_NUMBER:-'(resume mode)'}"
  log "Mode: $VERBOSITY | Max retries: $MAX_RETRIES | Retry interval: ${RETRY_INTERVAL_MIN}m"
  log "Output dir: $OUTPUT_DIR/"

  mkdir -p "$OUTPUT_DIR"

  if [[ "$RESUME_MODE" == true ]]; then
    log "Resuming last conversation..."
    LAST_OUTPUT=""
    LAST_EXIT_CODE=0
    local attempt=1
    while [[ "$attempt" -le "$MAX_RETRIES" ]]; do
      log "--- Resume attempt $attempt of $MAX_RETRIES ---"
      run_claude "$attempt"
      if is_success "$LAST_EXIT_CODE"; then
        log "Resume completed successfully."
        exit 0
      fi
      if is_quota_error "$LAST_OUTPUT" "$LAST_EXIT_CODE"; then
        log "Quota detected. Waiting ${RETRY_INTERVAL_MIN} minutes..."
        sleep "$((RETRY_INTERVAL_MIN * 60))"
        attempt=$((attempt + 1))
      else
        log "Resume failed (exit code $LAST_EXIT_CODE)."
        exit "$LAST_EXIT_CODE"
      fi
    done
    exit 1
  fi

  if is_epic "$ISSUE_NUMBER"; then
    log "Issue #${ISSUE_NUMBER} is an EPIC — entering sub-issue loop."
    local failed_issues=()
    local completed=0

    while true; do
      local sub_issues
      sub_issues="$(get_open_sub_issues "$ISSUE_NUMBER")"

      if [[ -z "$sub_issues" ]]; then
        log "All sub-issues of epic #${ISSUE_NUMBER} are closed."
        break
      fi

      local remaining
      remaining="$(echo "$sub_issues" | wc -l | tr -d ' ')"
      log "Epic #${ISSUE_NUMBER}: $remaining open sub-issue(s) remaining."

      local next_issue
      next_issue="$(echo "$sub_issues" | head -1)"

      if [[ ${#failed_issues[@]} -gt 0 ]] && printf '%s\n' "${failed_issues[@]}" | grep -qx "$next_issue"; then
        log "Issue #${next_issue} already failed — skipping."
        sub_issues="$(echo "$sub_issues" | tail -n +2)"
        if [[ -z "$sub_issues" ]]; then
          log "No more sub-issues to try."
          break
        fi
        next_issue="$(echo "$sub_issues" | head -1)"
      fi

      log "=== Starting sub-issue #${next_issue} ==="

      if run_single_issue "$next_issue"; then
        completed=$((completed + 1))
        log "Sub-issue #${next_issue} done. ($completed completed so far)"
      else
        log "Sub-issue #${next_issue} failed. Continuing with next."
        failed_issues+=("$next_issue")
      fi
    done

    log "=== Epic #${ISSUE_NUMBER} loop finished ==="
    log "Completed: $completed | Failed: ${#failed_issues[@]}"
    if [[ ${#failed_issues[@]} -gt 0 ]]; then
      log "Failed issues: ${failed_issues[*]}"
      exit 1
    fi
    exit 0
  else
    run_single_issue "$ISSUE_NUMBER"
    exit $?
  fi
}

main
