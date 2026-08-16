# artifact-serving — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Nested under the module [`cad-generation`](../tasks.md).
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Tasks marked **DO NOT REPRODUCE** describe a confirmed legacy defect that a
> re-implementation must fix rather than copy.
> This use case has no REST surface of its own — the artefact routes belong to
> [`construction-plans`](../../construction-plans/tasks.md).

## Prerequisites

- [ ] `app/core/config.py` exposes `ARTIFACTS_BASE_DIR` (default
      `/tmp/da3dalus_artifacts`) **and resolves it with a validator** — the guard
      is unsound against an unresolved or symlinked base.
- [ ] `app/core/exceptions.py` provides `ValidationError` and `NotFoundError`;
      the calling module maps them to 422 and 404.
- [ ] `app/schemas/construction_plan.py` provides `ArtifactFile` and
      `ArtifactDirectory`.
- [ ] A writable filesystem at the base path; the process may create it on first
      use.
- [ ] Agreement with `construction-plans` on who owns the lifetime of the
      temporary zip file (see T-AS-13).

## Tasks

### Base and layout

- [ ] **T-AS-01 — Resolve the base once, at configuration time.**
  `ARTIFACTS_BASE_DIR` is `.resolve()`d by a pydantic validator so every later
  comparison is between two fully resolved paths.
  - Legacy origin: `app/core/config.py:24-32`
  - Definition of done: a relative or symlinked configured value is stored
    resolved; a test asserts `Path(settings.ARTIFACTS_BASE_DIR).is_absolute()`
    and that it equals its own `.resolve()`.
  - Confidence: 🟢

- [ ] **T-AS-02 — The directory layout.**
  `<base>/<aeroplane_id>/<plan_id>/<execution_id>/` for plan runs;
  `<base>/_template_runs/<template_id>/<execution_id>/` for template runs, with
  `TEMPLATE_RUNS_PREFIX = "_template_runs"` as a **sibling** of the aeroplane
  directories.
  - Legacy origin: `app/services/artifact_service.py:78`;
    `_reversa_sdd/flowcharts/cad-generation.md` §7
  - Definition of done: both shapes are created by their respective factory and
    the prefix constant is used everywhere rather than a literal.
  - Confidence: 🟢

### Execution identity

- [ ] **T-AS-03 — `execution_id` generation.**
  `datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")`, with a `-N` suffix when the
  previous id generated in this process had the same second, tracked in
  `_last_execution_id` / `_last_execution_id_suffix`.
  - Legacy origin: `artifact_service.py:39-58`
  - Definition of done: two executions created within one UTC second in one
    process differ by the suffix; the pattern is asserted with a regex.
  - Confidence: 🟢

- [ ] **T-AS-04 — Make the id collision-safe across processes.**
  The counter is per-process, so two workers or replicas in the same second
  produce the **same** id — and because the id is the directory name, the second
  run silently writes into the first run's directory instead of failing.
  - Legacy origin: `artifact_service.py:39-58`
  - Definition of done: either the directory creation is exclusive
    (`mkdir(exist_ok=False)` with retry) or the id carries process-independent
    entropy; a test simulates two creators in the same second.
  - Confidence: 🟡 INFERRED — no incident is recorded, but the failure mode is
    silent data mixing.

### Directory creation

- [ ] **T-AS-05 — `create_execution_dir`.**
  Mint an id, build `<base>/<aeroplane_id>/<plan_id>/<execution_id>/`, pass it
  through the guard, `mkdir(parents=True)`, return the path and the id. Plan runs
  **accumulate**.
  - Legacy origin: `artifact_service.py` (`create_execution_dir`)
  - Definition of done: two runs of the same plan leave two directories; the
    returned id matches the directory name.
  - Confidence: 🟢

- [ ] **T-AS-06 — `create_template_execution_dir`.**
  `shutil.rmtree` the template's previous run **before** creating the new one, so
  at most one execution survives.
  - Legacy origin: `artifact_service.py:81-110`; `state-machines.md` §6
  - Definition of done: after two template runs exactly one execution directory
    remains and it is the newer one; the rmtree target passes the guard first.
  - Confidence: 🟢

- [ ] **T-AS-07 — Retention for plan executions.**
  Nothing prunes accumulated plan runs — no TTL, no count cap, no size cap.
  - Legacy origin: absence of pruning logic in `artifact_service.py`
  - Definition of done: a documented retention policy exists (even if "keep
    everything"), and if bounded, a prune routine with a test.
  - Confidence: 🟡 GAP — the policy is a product decision.

### Path safety (BR-68)

- [ ] **T-AS-08 — `_ensure_within_base`.**
  `Path(p).resolve()` then `relative_to(base)`, raising `ValidationError` on
  escape. Resolve **before** comparing, so `..` segments and symlinked
  components are collapsed first.
  - Legacy origin: `artifact_service.py:25-36`
  - Definition of done: `../../etc/passwd`, an absolute outside path, and a
    path with an embedded symlinked directory all raise; a legitimate nested
    path returns the resolved location.
  - Confidence: 🟢

- [ ] **T-AS-09 — Reject symlinks on the read path.**
  `get_file_path` raises when the resolved target `is_symlink()`, even if the
  target is inside the base — this closes the time-of-check/time-of-use gap that
  resolution alone leaves open.
  - Legacy origin: `artifact_service.py:202-203`
  - Definition of done: a symlink inside an execution directory raises whether
    it points inside or outside the base.
  - Confidence: 🟢

- [ ] **T-AS-10 — Guard every entry point.**
  Creation, listing, file resolution, zipping and both deletions all pass
  through the guard before any filesystem call — including the `subpath`
  parameter of `list_files`.
  - Legacy origin: `artifact_service.py` (all public functions)
  - Definition of done: a parametrised test drives a traversal payload through
    **every** public function and asserts `ValidationError` each time.
  - Confidence: 🟢

- [ ] **T-AS-11 — Log rejected path attempts.**
  A traversal or symlink rejection raises but leaves no distinct log record, so
  a probing client is indistinguishable from a broken one.
  - Legacy origin: `artifact_service.py:25-36, 202-203` (no logging)
  - Definition of done: guard violations emit a warning with the sanitised
    offending input and the operation attempted.
  - Confidence: 🟡 INFERRED — an observability improvement on a security
    boundary, not legacy behaviour.

### Listing and resolution

- [ ] **T-AS-12 — `_resolve_execution_dir`.**
  Scan the per-aeroplane directories **skipping** `TEMPLATE_RUNS_PREFIX`, then
  fall back to `<base>/_template_runs/<plan_id>/<execution_id>`; raise
  `NotFoundError` when neither matches.
  - Legacy origin: `artifact_service.py:282-283`
  - Definition of done: a plan execution and a template execution are both
    resolvable; an unknown id raises `NotFoundError`.
  - Confidence: 🟢

- [ ] **T-AS-13 — Make both scans agree on `_template_runs`.**
  **DO NOT REPRODUCE** the asymmetry: `_resolve_execution_dir` skips the prefix
  (l.282-283) while `list_executions` does not (l.123-142), so a template run can
  appear in a plan listing with `aeroplane_id == "_template_runs"`. Extract one
  predicate — "is this an aeroplane directory?" — and use it in both.
  - Legacy origin: `artifact_service.py:123-142, 282-283`
  - Definition of done: with a template id and a plan id that collide, listing
    the plan returns only real plan runs; a regression test pins it.
  - Confidence: 🟢

- [ ] **T-AS-14 — `list_executions`.**
  Return `ArtifactDirectory` entries carrying `execution_id`, `plan_id`,
  `aeroplane_id`, `created` (ISO) and `file_count`.
  - Legacy origin: `artifact_service.py:123-142`;
    `app/schemas/construction_plan.py:153`
  - Definition of done: a plan with two executions returns two fully populated
    entries; `file_count` matches the number of files on disk.
  - Confidence: 🟢

- [ ] **T-AS-15 — `list_files`.**
  Support an optional `subpath` (guarded) and a `recursive` flag; return
  `ArtifactFile` entries with `name`, `is_dir`, `size_bytes` and an ISO
  `modified`.
  - Legacy origin: `artifact_service.py` (`list_files`);
    `app/schemas/construction_plan.py:144`
  - Definition of done: a nested execution lists both `a.step` and `sub/b.stl`
    when recursive, and only the top level otherwise.
  - Confidence: 🟢

### Zip, download and deletion

- [ ] **T-AS-16 — `zip_execution`.**
  Write to a `tempfile.mkstemp` archive (**outside** the tree being archived),
  `ZIP_DEFLATED`, arcnames **relative to the execution directory**.
  - Legacy origin: `artifact_service.py:233-265`
  - Definition of done: extraction reproduces the execution's layout with no
    absolute or `tmp/` prefix; a second zip of the same execution does not
    contain the first.
  - Confidence: 🟢

- [ ] **T-AS-17 — An empty execution zips successfully.**
  A directory with no files yields a valid, readable, empty archive — not a 404.
  - Legacy origin: `artifact_service.py:233-265`
  - Definition of done: `ZipFile(result).namelist() == []` and the file opens
    without error.
  - Confidence: 🟢

- [ ] **T-AS-18 — Define the temp-zip lifetime.**
  `zip_execution` returns a `mkstemp` path and never deletes it; ownership
  passes implicitly to the caller. The sibling STL-regeneration path in
  `construction-plans` is a confirmed leak of exactly this shape.
  - Legacy origin: `artifact_service.py:233-265` (no cleanup)
  - Definition of done: either the archive is streamed and removed by a
    `BackgroundTask`/context manager owned here, or the contract explicitly
    documents caller ownership and `construction-plans` implements it.
  - Confidence: 🟡 GAP — the boundary must be agreed with `construction-plans`.

- [ ] **T-AS-19 — `delete_file`.**
  Resolve through `get_file_path` (guard **and** symlink rejection), then
  `unlink`. The execution directory survives.
  - Legacy origin: `artifact_service.py` (`delete_file`)
  - Definition of done: deleting one of two files leaves the other and the
    directory; a symlink cannot be used to unlink outside the base.
  - Confidence: 🟢

- [ ] **T-AS-20 — `delete_execution`.**
  Resolve the execution, guard it, `shutil.rmtree`. Sibling executions of the
  same plan are untouched.
  - Legacy origin: `artifact_service.py` (`delete_execution`)
  - Definition of done: the tree is gone, siblings remain, and an unknown
    execution raises `NotFoundError`.
  - Confidence: 🟢

- [ ] **T-AS-21 — Consider concurrency on zip and delete.**
  `rglob` may yield a path that a concurrent delete removes before `zf.write`
  runs; no guard was found.
  - Legacy origin: `artifact_service.py:233-265` (no locking, no `exists()`
    re-check)
  - Definition of done: a missing file mid-zip is skipped rather than raising,
    or the operation is serialised per execution.
  - Confidence: 🟡 INFERRED — no incident recorded; the race is structural.

## Test Tasks

- [ ] **TT-AS-01 — Happy path, plan execution:** create a directory, write two
      files, list them, zip, download, delete — end to end.
- [ ] **TT-AS-02 — Plan runs accumulate:** two runs leave two directories.
- [ ] **TT-AS-03 — Template runs replace:** after two runs exactly one
      execution remains and it is the newer one.
- [ ] **TT-AS-04 — Execution id pattern:** matches `%Y%m%dT%H%M%SZ`.
- [ ] **TT-AS-05 — Same-second suffix:** two ids in one second differ by `-1`.
- [ ] **TT-AS-06 — Cross-process collision:** two creators in the same second do
      not silently share a directory.
- [ ] **TT-AS-07 — Failure, traversal:** `"../../etc/passwd"` raises
      `ValidationError` from **every** public entry point.
- [ ] **TT-AS-08 — Failure, absolute outside path:** `/etc/passwd` raises.
- [ ] **TT-AS-09 — Failure, symlink:** a symlink inside an execution raises
      whether it points inside or outside the base.
- [ ] **TT-AS-10 — Guarded `subpath`:** a traversal in the `list_files` subpath
      raises.
- [ ] **TT-AS-11 — Legitimate nested path resolves** and stays inside the
      execution directory.
- [ ] **TT-AS-12 — Guard violations are logged** with sanitised input.
- [ ] **TT-AS-13 — Execution resolution:** a plan execution and a template
      execution both resolve; an unknown id raises `NotFoundError`.
- [ ] **TT-AS-14 — Template runs excluded from plan listings:** with colliding
      plan and template ids, no entry has `aeroplane_id == "_template_runs"`.
- [ ] **TT-AS-15 — Listing fields:** `ArtifactDirectory` and `ArtifactFile`
      entries are fully populated, with ISO timestamps.
- [ ] **TT-AS-16 — Recursive listing** finds nested files; non-recursive does
      not.
- [ ] **TT-AS-17 — Zip arcnames** are relative to the execution root; no
      absolute or `tmp/` prefix appears.
- [ ] **TT-AS-18 — Zip is built outside the archived tree:** a second zip of the
      same execution does not contain the first.
- [ ] **TT-AS-19 — Empty zip:** a valid, readable, empty archive.
- [ ] **TT-AS-20 — Temp file lifetime:** after a completed download no temp
      archive remains.
- [ ] **TT-AS-21 — Delete file:** one file removed, the other and the directory
      intact.
- [ ] **TT-AS-22 — Delete execution:** the tree is gone, siblings survive.
- [ ] **TT-AS-23 — Concurrent delete during zip** does not raise.

## Suggested Order

1. **T-AS-01 → T-AS-02** first — the resolved base and the layout constants are
   preconditions for the guard being sound at all. Nothing else can be tested
   correctly before them.
2. **T-AS-08 → T-AS-11** immediately after — the guard is the security boundary
   and every later function calls it. Writing T-AS-10's parametrised traversal
   test early means each new entry point is covered as it is added.
3. **T-AS-03 → T-AS-06** — identity and creation. T-AS-04 is a correctness
   decision that should be settled before directories are created in anger, since
   the failure mode (two runs sharing a directory) is silent.
4. **T-AS-12 → T-AS-15** — resolution and listing. T-AS-13 must land with
   T-AS-12 so that both scans are written against the same predicate from the
   start rather than diverging again.
5. **T-AS-16 → T-AS-20** — zip and deletion, which depend on T-AS-12 for
   resolution. T-AS-18 is a boundary agreement with `construction-plans` and
   should be settled before the download route is implemented there.
6. **T-AS-07** and **T-AS-21** last — retention and concurrency are both policy
   decisions that do not block the functional path.

## Pending Gaps

- **What is the retention policy for plan executions?** Nothing prunes them —
  no TTL, no count cap, no size cap — and there are no storage metrics, so
  growth is invisible until the disk fills.
- **Who deletes the temporary zip file?** `zip_execution` returns a `mkstemp`
  path and never removes it. `construction-plans` has a confirmed leak of the
  same shape in its STL-regeneration path, which suggests the answer today is
  "nobody".
- **Should the same-second execution id be made collision-safe across
  processes?** Today two processes produce the same id and the second run writes
  into the first run's directory without failing.
- **Should `ARTIFACTS_BASE_DIR` default to `/tmp`?** Many systems clear it on
  reboot, silently discarding every execution history.
- **Should `openvsp_imports/` go through this service?** It lives under the same
  base but is written directly by `openvsp-import`, so it is outside the guard.
- **Should guard violations be logged and alertable?** A traversal or symlink
  probe currently leaves no distinct signal on the one surface where it would
  matter most.
- **Is an execution's metadata meant to stay filesystem-derived?** There is no
  manifest and no database row, so every listing is a directory scan and the
  "aeroplane id" is a directory name — which is what made the `_template_runs`
  leak possible in the first place.
