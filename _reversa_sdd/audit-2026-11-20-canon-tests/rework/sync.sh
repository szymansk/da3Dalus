#!/bin/zsh
# usage: sync.sh "<history line>" — refresh the ledger, commit, push
W=/Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/canon-test-audit
python3 $W/_reversa_sdd/audit-2026-11-20-canon-tests/rework/ledger.py "$1" | tail -12
git -C $W add _reversa_sdd/audit-2026-11-20-canon-tests/rework
git -C $W commit -qm "docs: canon test review rework — $1

Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0174GvfMXUUorM2zeowWp5WK" && git -C $W push -q github docs/canon-test-review-step6 && git -C $W log --oneline -1
