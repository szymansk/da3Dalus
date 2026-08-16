# artifact-serving — Technical Design

> Use-case design, nested under the module [`cad-generation`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> This use case has **no REST surface of its own** — the artefact routes belong
> to [`construction-plans`](../../construction-plans/contracts.md); see
> [`requirements.md`](requirements.md) §Overview for the boundary rationale.
> Sibling slices: [`../wing-tessellation/`](../wing-tessellation/design.md),
> [`../wing-export-task/`](../wing-export-task/design.md).

## Interface

### `app/services/artifact_service.py` (294 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_ensure_within_base` | `(path)` | `Path` | `resolve()` then `relative_to(base)`; `ValidationError` on escape (l.25-36) |
| `_last_execution_id` / `_last_execution_id_suffix` | module globals | — | same-second collision counter (l.39-58) |
| `TEMPLATE_RUNS_PREFIX` | `"_template_runs"` | — | l.78 |
| `create_execution_dir` | `(aeroplane_id, plan_id)` | `(Path, str)` | `<base>/<aeroplane_id>/<plan_id>/<execution_id>/` |
| `create_template_execution_dir` | `(template_id)` | `(Path, str)` | **`rmtree`s the previous run first** (l.81-110) |
| `list_executions` | `(plan_id)` | `list[ArtifactDirectory]` | 🔴 does **not** skip `_template_runs` (l.123-142) |
| `list_files` | `(plan_id, execution_id, subpath, recursive)` | `list[ArtifactFile]` | guarded |
| `get_file_path` | `(plan_id, execution_id, filename)` | `Path` | guards **and rejects symlinks** (l.202-203) |
| `zip_execution` | `(plan_id, execution_id)` | `Path` | `tempfile.mkstemp`, `ZIP_DEFLATED`, relative arcnames; empty → valid empty zip (l.233-265) |
| `delete_file` | `(plan_id, execution_id, filename)` | `None` | `unlink`, guarded |
| `delete_execution` | `(plan_id, execution_id)` | `None` | `rmtree`, guarded |
| `_resolve_execution_dir` | `(plan_id, execution_id)` | `Path` | scans per-aeroplane dirs **skipping** `_template_runs` (l.282-283), then falls back to it |

### Schemas — `app/schemas/construction_plan.py` 🟢

| Schema | Fields |
|---|---|
| `ArtifactFile` (l.144) | `name: str`, `is_dir: bool = False`, `size_bytes: int = 0`, `modified: str` (ISO) |
| `ArtifactDirectory` (l.153) | `execution_id: str`, `plan_id: int`, `aeroplane_id: str`, `created: str` (ISO), `file_count: int = 0` |

### Configuration 🟢

`ARTIFACTS_BASE_DIR` — default `/tmp/da3dalus_artifacts`, `.resolve()`d by a
pydantic validator at configuration time (`app/core/config.py:24-32`). The
resolution is load-bearing: `_ensure_within_base` compares two **fully
resolved** paths, and a relative or symlinked base would make the comparison
meaningless.

### State

No database table. **The directory layout is the data model** — an execution
exists because its directory does, and every attribute in `ArtifactDirectory`
is derived from the path and the filesystem metadata.

## Main Flow

### F1 — Directory layout 🟢

```
<ARTIFACTS_BASE_DIR>/                      # resolved once at config time
├── <aeroplane_id>/<plan_id>/<execution_id>/     plan runs      — accumulate
├── _template_runs/<template_id>/<execution_id>/ template runs  — rmtree'd
└── openvsp_imports/<aeroplane_uuid>/             ← owned by openvsp-import

NOT under the base (deliberately or otherwise):
    ./tmp/exports, ./tmp/{aeroplane}.zip          ← ../wing-export-task/
    tmp/construction_parts/{aeroplane}/           ← construction-plans
```

`TEMPLATE_RUNS_PREFIX = "_template_runs"` (l.78) is a **sibling of the aeroplane
directories**, not a separate root — which is the structural reason a scan must
explicitly exclude it (F5).

### F2 — Execution id 🟢

```
execution_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

if execution_id == _last_execution_id:            # module globals, l.39-58
    _last_execution_id_suffix += 1
    execution_id = f"{execution_id}-{_last_execution_id_suffix}"
else:
    _last_execution_id        = execution_id
    _last_execution_id_suffix = 0
```

Second resolution plus a counter is enough for one process. 🟡 The counter is
**per-process**, so two workers or two replicas creating an execution in the same
second still produce the same id — and because the id is also the directory
name, the second run would write into the first run's directory rather than
failing.

### F3 — Creating a directory 🟢

```
create_execution_dir(aeroplane_id, plan_id):
    execution_id = next_execution_id()
    path = base / str(aeroplane_id) / str(plan_id) / execution_id
    _ensure_within_base(path)
    path.mkdir(parents=True, exist_ok=True)
    return path, execution_id

create_template_execution_dir(template_id):                       # l.81-110
    template_root = base / TEMPLATE_RUNS_PREFIX / str(template_id)
    _ensure_within_base(template_root)
    if template_root.exists():
        shutil.rmtree(template_root)          # ← at most ONE execution survives
    execution_id = next_execution_id()
    path = template_root / execution_id
    path.mkdir(parents=True, exist_ok=True)
    return path, execution_id
```

The `rmtree` is the whole of BR-CG17: a template is a scratch pad, so its
previous output is disposable, whereas a plan run is a record and accumulates.
`state-machines.md` §6 states the same rule from the plan's side: execution is
**not idempotent** for plans and **destructive** for templates.

🔴 Nothing prunes accumulated plan executions. There is no retention policy, no
size cap and no TTL — growth is bounded only by the disk.

### F4 — The path guard (BR-68) 🟢

```
_ensure_within_base(path):                                        # l.25-36
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(base)          # base is already .resolve()d
    except ValueError:
        raise ValidationError(...)
    return resolved

get_file_path(...):                                               # l.202-203
    p = _ensure_within_base(execution_dir / filename)
    if p.is_symlink():                      # ← closes the resolve-then-follow gap
        raise ValidationError(...)
    return p
```

Two properties make this correct rather than merely plausible:

1. **Resolve before compare.** `resolve()` collapses `..` and follows symlinks,
   so `relative_to` sees the real target. A guard that compared the *unresolved*
   path would be defeated by `execution/../../../etc/passwd`.
2. **Symlink rejection on the read path.** Resolution alone would happily accept
   a symlink *inside* the base pointing at a target *also* inside the base;
   rejecting symlinks outright removes the whole class, including
   time-of-check/time-of-use swaps. 🟢

The base's own `.resolve()` at configuration time (`app/core/config.py:24-32`)
is the third leg: without it, `relative_to` could compare a resolved candidate
against an unresolved base and raise on legitimate paths (or, on a symlinked
base, accept illegitimate ones).

### F5 — Resolving and listing executions 🟢/🔴

```
_resolve_execution_dir(plan_id, execution_id):                    # l.282-283
    for aeroplane_dir in base.iterdir():
        if aeroplane_dir.name == TEMPLATE_RUNS_PREFIX:   # ← SKIPPED
            continue
        candidate = aeroplane_dir / str(plan_id) / execution_id
        if candidate.is_dir(): return candidate
    fallback = base / TEMPLATE_RUNS_PREFIX / str(plan_id) / execution_id
    if fallback.is_dir(): return fallback
    raise NotFoundError(...)

list_executions(plan_id):                                          # l.123-142
    for aeroplane_dir in base.iterdir():
        # ← NO skip of TEMPLATE_RUNS_PREFIX
        plan_dir = aeroplane_dir / str(plan_id)
        for exec_dir in plan_dir.iterdir():
            yield ArtifactDirectory(execution_id = exec_dir.name,
                                    plan_id      = plan_id,
                                    aeroplane_id = aeroplane_dir.name,   # ← "_template_runs"
                                    created      = ..., file_count = ...)
```

🔴 The two scans disagree. `_resolve_execution_dir` treats `_template_runs` as a
special case and handles it explicitly; `list_executions` treats it as just
another aeroplane directory. Consequence: when a *template* with id `7` and a
*plan* with id `7` both have runs, listing plan 7 returns the template's
executions with a fabricated `aeroplane_id` of `"_template_runs"`. Since plan and
template ids come from the same `construction_plans` sequence, the collision is
possible but not guaranteed. 🟡 (likelihood) / 🟢 (the mechanism).

The fix is one predicate — "is this an aeroplane directory?" — used by both.

### F6 — Listing files 🟢

```
list_files(plan_id, execution_id, subpath="", recursive=False):
    root = _resolve_execution_dir(plan_id, execution_id)
    target = _ensure_within_base(root / subpath)
    walker = target.rglob("*") if recursive else target.iterdir()
    return [ArtifactFile(name        = <relative to target>,
                         is_dir      = e.is_dir(),
                         size_bytes  = e.stat().st_size,
                         modified    = isoformat(e.stat().st_mtime))
            for e in walker]
```

`subpath` passes through the guard, so a caller cannot walk out of the
execution via the listing route either. 🟢

### F7 — Zipping 🟢

```
zip_execution(plan_id, execution_id):                             # l.233-265
    root = _resolve_execution_dir(plan_id, execution_id)
    fd, tmp_path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    with ZipFile(tmp_path, "w", ZIP_DEFLATED) as zf:
        for f in root.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=f.relative_to(root))   # ← relative arcnames
    return Path(tmp_path)
```

Three deliberate properties:

- **The archive is built outside the tree it archives** (`tempfile.mkstemp`), so
  a second zip of the same execution cannot include the first. 🟢 Contrast
  [`../wing-export-task/`](../wing-export-task/design.md) §F5, where the archive
  and the working directory share a parent and the worker deletes everything.
- **Arcnames are relative to the execution root**, so extraction reproduces the
  run's layout rather than an absolute path prefix. 🟢 Again the contrast with
  the export path, which keeps a `tmp/exports/` prefix.
- **An empty execution yields a valid empty zip**, not a 404 — a plan that
  produced no output is a legitimate outcome, not an error. 🟢

🔴 The temp file is returned, never deleted here. Ownership passes to the caller
(the `construction-plans` download route). Whether anyone deletes it is not
determined by this layer — and the sibling STL-regeneration path in
`construction-plans` is a confirmed leak of the same shape.

### F8 — Deletion 🟢

```
delete_file(plan_id, execution_id, filename):
    p = get_file_path(plan_id, execution_id, filename)   # guards + symlink check
    p.unlink()

delete_execution(plan_id, execution_id):
    root = _resolve_execution_dir(plan_id, execution_id)
    _ensure_within_base(root)
    shutil.rmtree(root)
```

Both go through the guard before touching the filesystem; `delete_file` inherits
the symlink rejection from `get_file_path`, so a symlink cannot be used to make
the service unlink something outside the base. 🟢

## Alternative Flows

- **Path escapes the base:** `ValidationError` before any filesystem read or
  write; the caller maps it to 422. 🟢
- **Requested file is a symlink:** `ValidationError`, even when its target is
  inside the base. 🟢
- **Execution id not found under any aeroplane:** `_resolve_execution_dir` falls
  back to `_template_runs`, then raises `NotFoundError` → 404. 🟢
- **Template id collides with a plan id:** listing that plan returns the
  template's runs with `aeroplane_id == "_template_runs"`. 🔴
- **Empty execution:** listing returns `[]`; zipping returns a valid empty
  archive. 🟢
- **Second template run:** the previous tree is `rmtree`d, so a client holding an
  older `execution_id` gets a 404 on the next read. 🟢
- **Same-second executions in two processes:** identical ids; the second run
  writes into the first run's directory rather than failing. 🟡
- **Base directory missing at startup:** created on first `mkdir(parents=True)`;
  the default `/tmp/...` may vanish across a reboot, silently emptying every
  execution history. 🟡
- **Concurrent zip of one execution while a file is deleted:** `rglob` may yield
  a path that no longer exists when `zf.write` runs. No guard was found. 🟡

## Dependencies

- **`app/core/config.py`** — `ARTIFACTS_BASE_DIR` and its `.resolve()` validator;
  without the resolution the guard is unsound.
- **`app/core/exceptions.py`** — `ValidationError` (guard violations) and
  `NotFoundError` (unknown execution), mapped to HTTP by the calling module.
- **`app/schemas/construction_plan.py`** — `ArtifactFile` and
  `ArtifactDirectory`, which are shaped for the artefact browser rather than for
  this layer.
- **`construction-plans`** — the only caller: it decides *when* an execution
  directory is created (plan vs template) and owns the REST routes, the download
  response and the lifetime of the temp zip.
- **`openvsp-import`** — writes `openvsp_imports/<aeroplane_uuid>/` under the
  same base without going through this service. 🟡 The guard therefore does not
  cover it.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The directory layout **is** the data model — no table, no manifest | `artifact_service.py` (whole module) | 🟢 |
| The base is resolved once at configuration time so the guard compares resolved paths | `app/core/config.py:24-32` | 🟢 |
| Guard = resolve + `relative_to`, raising a **domain** error rather than returning a bool | `artifact_service.py:25-36` | 🟢 |
| Symlinks are rejected outright on the read path rather than validated | `artifact_service.py:202-203` | 🟢 |
| A template keeps one execution; a plan accumulates | `artifact_service.py:81-110`; `state-machines.md` §6 | 🟢 |
| `_template_runs` is a sibling of the aeroplane directories, not a separate root | `TEMPLATE_RUNS_PREFIX` (l.78) | 🟢 — and the direct cause of BR-CG20 |
| Execution identity is a UTC second stamp, not a UUID or a sequence | `artifact_service.py:39-58` | 🟢 |
| Collision handling is a per-process counter rather than a filesystem probe | `artifact_service.py:39-58` | 🟢 (adequacy 🟡) |
| The zip is built in a temp file outside the archived tree | `artifact_service.py:233-265` | 🟢 |
| Arcnames are relative to the execution root | `artifact_service.py:233-265` | 🟢 |
| An empty execution is a valid state, not a 404 | `artifact_service.py:233-265` | 🟢 |
| Temp-zip lifetime is the caller's problem | `zip_execution` returns a path | 🟢 (intent 🔴) |
| No retention policy for plan executions | absence of pruning logic | 🟡 (`Q-VS-2` owns the growth policy) |

## Internal State

- **Module globals:** `_last_execution_id`, `_last_execution_id_suffix` — the
  same-second collision counter, per process, lost on restart (after which the
  next id in the same second would not be suffixed).
- **Filesystem:** everything else. Execution directories, their files, and the
  transient `tempfile.mkstemp` archives handed to callers.
- **Nothing persistent in the database.** An execution's metadata is derived from
  its path and `stat()` on every read.

## Observability

- The service raises typed domain errors (`ValidationError`, `NotFoundError`)
  that the calling module maps to 422 / 404 — the guard failures are therefore
  visible to the client, not swallowed. 🟢
- 🔴 **No audit log.** A rejected traversal or symlink attempt raises but is not
  logged distinctly, so a probing client is indistinguishable from a broken one.
  On a path-serving surface this is the one place logging would matter most.
- 🔴 **No storage metrics** — no total artefact size, no execution count, no
  oldest-execution age. Combined with the absent retention policy, disk growth
  is invisible until it is fatal.
- 🟡 Deletion is silent: `delete_execution` removes a tree with no record that it
  existed.

## Risks and Gaps

- 🔴 **`list_executions` does not skip `_template_runs`** while
  `_resolve_execution_dir` does, so a template run can surface in a plan listing
  with a fabricated `aeroplane_id`. One predicate should serve both scans.
- 🔴 **No retention policy.** Plan executions accumulate without bound; nothing
  prunes by age, count or size.
- 🔴 **Temp-zip ownership is undefined at this boundary.** `zip_execution`
  returns a `mkstemp` path and never deletes it; the sibling STL-regeneration
  path in `construction-plans` is a confirmed leak of exactly this shape.
- 🔴 **Guard failures are not logged distinctly**, so traversal or symlink probes
  leave no signal.
- 🟡 **The execution-id collision counter is per-process.** Two processes in the
  same second produce the same id, and because the id is the directory name the
  second run writes into the first run's directory instead of failing.
- 🟡 **The default base is `/tmp/da3dalus_artifacts`**, which many systems clear
  on reboot — silently discarding every execution history.
- 🟡 **`openvsp_imports/` lives under the same base without using this service**,
  so those paths are outside the guard.
- 🟡 **No concurrency control.** Zipping an execution while a file is deleted can
  race between `rglob` and `write`; deleting an execution while it is being
  listed is likewise unguarded.
- 🟡 **Execution metadata is re-derived from the filesystem on every listing**,
  which is fine at current scale but has no index behind it.
