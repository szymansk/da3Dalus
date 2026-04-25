# Agent Instructions

<!-- BEGIN:nextjs-agent-rules -->

## Next.js: ALWAYS read docs before coding

Before any Next.js work, find and read the relevant doc in
`frontend/node_modules/next/dist/docs/`. Your training data is outdated —
the docs are the source of truth.

<!-- END:nextjs-agent-rules -->

## Project structure

- `app/` — Python FastAPI Backend (port 8000)
- `frontend/` — Next.js Frontend (port 3000)
- Backend REST API: http://localhost:8001
- Swagger UI: http://localhost:8001/docs
- Frontend dev server: http://localhost:3000

This project uses **gh** (GitHub) for issue tracking.

## Serena — Prefer Semantic Code Operations

This project has **Serena** configured as an MCP server for IDE-level
code intelligence. **Always prefer Serena tools over text-based
operations** for the following tasks:

- **Finding symbols:** Use Serena's symbol search instead of Grep
- **Finding references:** Use Serena's reference lookup for cross-file
  analysis instead of grepping for function names
- **Renaming:** Use Serena's semantic rename (handles all references
  across files) instead of find-and-replace
- **Replacing function/method bodies:** Use Serena's symbol body
  replacement instead of Edit with line numbers
- **Understanding code structure:** Use Serena's file outline and
  type hierarchy instead of reading entire files

**Standard tools remain appropriate for:** simple edits, new file
creation, config changes, reading files where symbol context isn't
needed, and when Serena tools are unavailable.

## Non-Interactive Shell Commands

**ALWAYS use non-interactive flags** with file operations to avoid hanging on confirmation prompts.

Shell commands like `cp`, `mv`, and `rm` may be aliased to include `-i` (interactive) mode on some systems, causing the agent to hang indefinitely waiting for y/n input.

**Use these forms instead:**
```bash
# Force overwrite without prompting
cp -f source dest           # NOT: cp source dest
mv -f source dest           # NOT: mv source dest
rm -f file                  # NOT: rm file

# For recursive operations
rm -rf directory            # NOT: rm -r directory
cp -rf source dest          # NOT: cp -r source dest
```

**Other commands that may prompt:**
- `scp` - use `-o BatchMode=yes` for non-interactive
- `ssh` - use `-o BatchMode=yes` to fail instead of prompting
- `apt-get` - use `-y` flag
- `brew` - use `HOMEBREW_NO_AUTO_UPDATE=1` env var


## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
