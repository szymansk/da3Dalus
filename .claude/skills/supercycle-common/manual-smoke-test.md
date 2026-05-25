# Manual Smoke Test on Worktree

Reusable procedure invoked between implementation completion and
finishing a development branch. Lets the user manually verify the
PR scope on a live backend + frontend pair running inside the
worktree, before review/merge.

The worktree gives DB isolation for free: each worktree has its own
`db/test.db`, so parallel PR stacks don't collide. AVL runs via the
`avl-binary` Python wheel installed by `poetry install`.

---

## Step 1 — Build a PR-specific smoke-test checklist

Generate the checklist from the PR's actual scope, not a generic
template. Sources to read:

- Linked GH Issue body — acceptance criteria, user stories
- PR diff — files changed, public surfaces touched
- `has-spec` / `has-plan` step comments — what was promised

Produce a numbered checklist with **three sections**:

1. **Golden path** — the main feature flow the PR enables, as a
   user action with expected UI/API outcome.
2. **Direct edge cases** — empty inputs, max values, error paths,
   unit boundaries (mm vs m, dimensionless vectors), missing
   referenced entities.
3. **Regression risk** — list features that share files or schemas
   with the change (e.g. wing editor changes → wing CRUD, wing
   analysis, wing 3D viewer), each with a one-line check.

Frame each item as **action → expected outcome**, concrete enough
to be unambiguous. Example:

```
[ ] 1. Open Aeroplane "Cessna 172" → Workbench tree shows wings,
       fuselage, tail; 3D viewer renders without errors in console
[ ] 2. Click "Import OpenVSP" → select cessna172.vsp3 → quick-scale
       dialog appears with wingspan 11.0 m pre-filled
[ ] 3. Cancel quick-scale → no aeroplane created, no orphan files
       under components/airfoils/
```

---

## Step 2 — Ask the user

Post the checklist in conversation and ask whether to start the
stack. Example wording:

> Implementation fertig. Soll ich Backend + Frontend im Worktree
> starten zum manuellen Test?
>
> **Smoke-Test-Checkliste für PR #N:**
> [ ] 1. …
> [ ] 2. …
> …

If the user declines: skip to `/finishing-a-development-branch`.

---

## Step 3 — Pre-flight in the worktree

Run from the worktree root:

```bash
# Ensure backend deps installed
poetry env info -p >/dev/null 2>&1 || poetry install

# Ensure frontend deps installed
[ -d frontend/node_modules ] || (cd frontend && npm ci)

# Apply schema migrations if any
poetry run alembic upgrade head

# Ensure tmp/ exists (mounted as static-files dir)
mkdir -p tmp/exports
```

---

## Step 4 — Allocate free ports

Backend starts looking from 18001, frontend from 19001. Increment
on collision.

```bash
find_free_port() {
  local p=$1
  while lsof -ti :$p >/dev/null 2>&1; do p=$((p+1)); done
  echo $p
}
BACKEND_PORT=$(find_free_port 18001)
FRONTEND_PORT=$(find_free_port 19001)
```

---

## Step 5 — Start backend in background

```bash
poetry run uvicorn app.main:app \
  --host 127.0.0.1 \
  --port $BACKEND_PORT \
  --reload
```

Use `Bash(run_in_background: true)`. Then `Monitor` the stdout
stream until the line `Uvicorn running on http://127.0.0.1:<port>`
appears. If a startup error appears (Alembic error, import error)
report it and stop.

---

## Step 6 — Start frontend in background

```bash
cd frontend && \
PORT=$FRONTEND_PORT \
NEXT_PUBLIC_API_URL=http://localhost:$BACKEND_PORT \
npm run dev
```

Use `Bash(run_in_background: true)`. `Monitor` until `Ready in` or
`Local:   http://localhost:<port>` appears.

---

## Step 7 — Report and wait

```
Stage running on this worktree:

  Frontend  →  http://localhost:<FRONTEND_PORT>
  Backend   →  http://localhost:<BACKEND_PORT>/docs
  MCP       →  http://localhost:<BACKEND_PORT>/mcp
  DB        →  <worktree>/db/test.db  (isolated)

Smoke-Test-Checkliste für PR #N:
[ ] 1. …
[ ] 2. …
…

Sag Bescheid wenn fertig (oder bei einem Bug — Hot-Reload ist an,
ich kann sofort nachbessern).
```

Wait for user feedback. Track each item's pass/fail as the user
reports.

---

## Step 8 — Iterate on findings

If the user reports a bug:

1. Reproduce mentally from the symptom + relevant file from the PR
2. Fix it (TDD if applicable per the iron laws)
3. Hot-reload picks up the change; ask the user to retry the
   failed checklist item
4. Update the checklist with the result

If all items pass: continue to Step 9.

---

## Step 9 — Stop the stack

```bash
# Kill processes by port (more reliable than PID across worktrees)
lsof -ti :$BACKEND_PORT  | xargs -r kill
lsof -ti :$FRONTEND_PORT | xargs -r kill
```

Then continue with `/finishing-a-development-branch` (in
`supercycle-implement`) or the `track` step (in `supercycle-fix`).

---

## Notes & failure modes

- **Schema migrations:** if `alembic upgrade head` fails, the stack
  cannot start — report and stop, do not skip the migration.
- **Port range exhaustion:** if `find_free_port` walks past +20,
  something is wrong (orphaned dev servers). Use
  `kill-orphaned-workers` from `tracking.md` before retrying.
- **Multiple parallel stages:** OK. Track each active stack's
  worktree + port pair + PR number in conversation; the user may
  want to stop one without stopping the others.
- **Frontend env var caveat:** `NEXT_PUBLIC_API_URL` is bound at
  build time for prod builds, but in `npm run dev` it's read at
  request time. This procedure only uses `dev`, so it's fine.
