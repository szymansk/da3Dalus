# artifact-serving

> Use-case specification, nested under the module [`cad-generation`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: cad-generation
> (Artifacts), `_reversa_sdd/data-dictionary.md` §Artifact schemas,
> `_reversa_sdd/domain.md` §2.10 (BR-68), `_reversa_sdd/flowcharts/cad-generation.md` §7.

## Overview

`artifact-serving` is the filesystem layer under every CAD execution: it mints
execution directories, guarantees that no path escapes the artefact base, and
lists, zips, downloads and deletes the files an execution produced. It stores
nothing in the database — an execution's existence *is* its directory.

**Boundary note.** The artefact **REST routes**
(`/construction-plans/{plan_id}/artifacts/…`) belong to
[`construction-plans`](../../construction-plans/contracts.md); this use case
owns the **storage semantics** those routes call into. The split follows
`code-analysis.md`, which documents `artifact_service.py` under
*Module: cad-generation* while listing its routes under
*Module: construction-plans*. 🟢

## Responsibilities

- Resolve and pin the artefact base directory once, at configuration time. 🟢
- Mint an execution directory per plan run, and a separate one per template
  run. 🟢
- Generate a collision-resistant `execution_id`. 🟢
- Keep at most one execution per template, deleting the previous run. 🟢
- Reject every path that escapes the base directory, and every symlink. 🟢
- List executions for a plan, and list files within an execution. 🟢
- Zip an execution for download, including the empty case. 🟢
- Delete a single file or a whole execution. 🟢

**Explicitly NOT this use case's responsibility:** the artefact REST routes and
their status codes (→ [`construction-plans`](../../construction-plans/contracts.md));
plan execution itself, which decides *when* a directory is created
(→ `construction-plans`); the export archive path `./tmp/exports` and
`./tmp/{aeroplane}.zip`, which deliberately live **outside** this layer
(→ [`../wing-export-task/`](../wing-export-task/requirements.md)); the
tessellation cache, which is database state
(→ [`../wing-tessellation/`](../wing-tessellation/requirements.md));
construction-part file storage under `tmp/construction_parts/`
(→ `construction-plans`); the OpenVSP STEP artefacts under
`openvsp_imports/` (→ `openvsp-import`).

## Business Rules

> IDs are inherited verbatim from [`../requirements.md`](../requirements.md).

- **BR-68 — Every artefact path is traversal-guarded.** 🟢 *(this use case is its
  owner.)* `_ensure_within_base` resolves the candidate and then calls
  `relative_to(base)`, raising `ValidationError` on escape
  (`app/services/artifact_service.py:25-36`). `get_file_path` additionally
  **rejects symlinks** (l.202-203). The base itself is `.resolve()`d by a
  pydantic validator at configuration time (`app/core/config.py:24-32`), so the
  comparison is between two fully resolved paths.
- **BR-CG17 — A template keeps exactly one execution.** 🟢
  `create_template_execution_dir` **`shutil.rmtree`s** the previous run before
  creating the new one (`artifact_service.py:81-110`). Plan runs accumulate
  instead — execution is **not idempotent** for plans and **destructive** for
  templates (`state-machines.md` §6).
- **BR-CG18 — `execution_id` is a UTC second stamp with a per-process collision
  suffix.** 🟢 `datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")`, with a `-N`
  suffix when the previous id in the same process had the same second, tracked
  in the module globals `_last_execution_id` / `_last_execution_id_suffix`
  (l.39-58). 🟡 The counter is per-process, so two processes in the same second
  still collide.
- **BR-CG19 — An empty execution zips to a valid empty archive.** 🟢
  `zip_execution` writes to a `tempfile.mkstemp` archive with `ZIP_DEFLATED` and
  arcnames relative to the execution directory; an execution with no files
  yields a valid empty zip rather than a 404 (l.233-265).
- **BR-CG20 — 🟢 `list_executions` applies the same reserved-prefix skip; the prefix becomes one module constant (`Q-CG-6`). Previously skipped in one scan and not the other:
  `_resolve_execution_dir` deliberately skips the `_template_runs` prefix when
  scanning per-aeroplane directories (l.282-283), but `list_executions` does not
  (l.123-142) — a template run can therefore surface in a plan listing with
  `aeroplane_id == "_template_runs"`.
- **BR-CG21 — The directory layout is the data model.** 🟢
  `<ARTIFACTS_BASE_DIR>/<aeroplane_id>/<plan_id>/<execution_id>/` for plan runs,
  `<ARTIFACTS_BASE_DIR>/_template_runs/<template_id>/<execution_id>/` for
  template runs (`TEMPLATE_RUNS_PREFIX = "_template_runs"`, l.78). There is no
  table, no index and no metadata file — listing an execution means reading the
  filesystem, and the "aeroplane id" in a listing is a **directory name**, which
  is why BR-CG20 can produce a fake one.
- **BR-CG22 — The zip is built in a temp file, not in the execution
  directory.** 🟢 `tempfile.mkstemp` keeps the archive out of the very tree it
  is archiving, so a second zip of the same execution cannot include the first.
  🔴 Nothing in this layer deletes that temp file afterwards; ownership passes to
  the caller.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-AS-01 | Resolve the artefact base once at configuration time | Must | `ARTIFACTS_BASE_DIR` (default `/tmp/da3dalus_artifacts`) is `.resolve()`d by a validator; every later comparison uses the resolved value |
| RF-AS-02 | Create a plan execution directory | Must | `<base>/<aeroplane_id>/<plan_id>/<execution_id>/` exists and is returned with its `execution_id` |
| RF-AS-03 | Create a template execution directory | Must | `<base>/_template_runs/<template_id>/<execution_id>/` exists |
| RF-AS-04 | Delete the previous template run first | Must | After two template runs exactly one execution directory remains, and it is the newer one |
| RF-AS-05 | Accumulate plan runs | Must | After two plan runs both execution directories exist |
| RF-AS-06 | Generate a UTC execution id | Must | The id matches `%Y%m%dT%H%M%SZ` |
| RF-AS-07 | Disambiguate same-second ids | Must | Two executions created in the same second within one process differ by a `-N` suffix |
| RF-AS-08 | Reject a path escaping the base | Must | `../` traversal and an absolute outside path both raise `ValidationError` |
| RF-AS-09 | Reject a symlinked artefact | Must | A symlink inside an execution directory raises when requested as a file |
| RF-AS-10 | List the executions of a plan | Must | Each entry carries `execution_id`, `plan_id`, `aeroplane_id`, `created` (ISO) and `file_count` |
| RF-AS-11 | Exclude template runs from plan listings | Must | A template run never appears with `aeroplane_id == "_template_runs"` (🔴 legacy includes it) |
| RF-AS-12 | List the files of an execution | Must | Each entry carries `name`, `is_dir`, `size_bytes` and `modified` (ISO); recursion is supported |
| RF-AS-13 | Resolve an execution by plan and execution id | Must | Per-aeroplane directories are scanned first, then `_template_runs` |
| RF-AS-14 | Zip an execution | Must | `ZIP_DEFLATED`, arcnames relative to the execution directory, written to a temp file |
| RF-AS-15 | Zip an empty execution successfully | Must | A valid, readable, empty archive is returned rather than a 404 |
| RF-AS-16 | Return the path of a single artefact file | Must | Guards applied; the returned path is inside the execution directory |
| RF-AS-17 | Delete a single file | Must | The file is removed; the execution directory survives |
| RF-AS-18 | Delete a whole execution | Must | The directory tree is removed |
| RF-AS-19 | Clean up the temporary zip file | Should | No temp archive is left behind after a download completes (🔴 ownership is currently undefined here) |
| RF-AS-20 | Record execution metadata explicitly | Could | Today the directory name is the only metadata; there is no manifest and no database row |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Security | Every path is resolved and constrained to the base before any I/O | `artifact_service.py:25-36` (BR-68) | 🟢 |
| Security | Symlinks are rejected on the file-read path, closing the resolve-then-follow gap | `artifact_service.py:202-203` | 🟢 |
| Security | The base is resolved once at configuration time, so the guard cannot be defeated by a relative base | `app/core/config.py:24-32` | 🟢 |
| Correctness | The archive is built outside the tree it archives | `artifact_service.py:233-265` (`tempfile.mkstemp`) | 🟢 |
| Correctness | Arcnames are relative to the execution directory, so extraction reproduces the run's layout | `artifact_service.py:233-265` | 🟢 |
| Robustness | An empty execution is a valid state, not an error | `artifact_service.py:233-265` | 🟢 |
| Storage | Template runs are bounded to one execution; plan runs are unbounded | `artifact_service.py:81-110` | 🟢 |
| Storage | Nothing prunes old plan executions — growth is unbounded | no retention logic found | 🟡 |
| Scalability | The execution-id collision counter is per-process only | `artifact_service.py:39-58` | 🟡 |
| Scalability | Listing scans the filesystem; there is no index | `artifact_service.py:123-142` | 🟡 |
| Portability | The base defaults to `/tmp/da3dalus_artifacts`, which many systems clear on reboot | `app/core/config.py:24-32` | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Execution directories

  Scenario: A plan execution directory is created
    Given ARTIFACTS_BASE_DIR is a resolved absolute path
    When an execution starts for plan 7 of aeroplane "A"
    Then the directory <base>/A/7/<execution_id>/ exists
    And execution_id matches the pattern %Y%m%dT%H%M%SZ

  Scenario: Plan runs accumulate
    Given plan 7 already has one execution directory
    When a second plan execution starts
    Then both execution directories exist

  Scenario: A template run replaces its predecessor
    Given template 3 already has one execution directory
    When a new template execution starts
    Then the previous directory tree is removed first
    And exactly one execution remains under _template_runs/3/

  Scenario: Two executions in the same second are distinguishable
    Given two executions created within the same UTC second in one process
    When both ids are generated
    Then the second carries a "-1" suffix
    And the two directories are distinct

Feature: Path safety

  Scenario: A traversal attempt is rejected
    Given an artefact filename of "../../etc/passwd"
    When the file path is resolved
    Then a ValidationError is raised
    And no filesystem read occurs

  Scenario: An absolute path outside the base is rejected
    Given an artefact filename of "/etc/passwd"
    When the file path is resolved
    Then a ValidationError is raised

  Scenario: A symlink is rejected
    Given a symlink inside an execution directory pointing outside the base
    When the file is requested
    Then a ValidationError is raised

  Scenario: A legitimate nested file resolves
    Given a file at "sub/dir/part.step" inside the execution directory
    When the file path is resolved
    Then the returned path is inside that execution directory

Feature: Listing

  Scenario: Executions of a plan are listed
    Given plan 7 has two executions for aeroplane "A"
    When the executions are listed
    Then two entries are returned
    And each carries execution_id, plan_id, aeroplane_id, created and file_count

  Scenario: A template run does not masquerade as a plan run
    Given template 7 has one execution under _template_runs/7/
    When the executions of plan 7 are listed
    Then no entry has aeroplane_id "_template_runs"
    # BR-CG20: list_executions does not skip the prefix that _resolve_execution_dir skips

  Scenario: Files of an execution are listed recursively
    Given an execution containing "a.step" and "sub/b.stl"
    When the files are listed recursively
    Then both entries appear
    And each carries name, is_dir, size_bytes and an ISO modified timestamp

Feature: Zipping and deletion

  Scenario: An execution is zipped
    Given an execution containing two files
    When the execution is zipped
    Then the archive is ZIP_DEFLATED
    And the arcnames are relative to the execution directory
    And the archive is written outside that directory

  Scenario: An empty execution zips successfully
    Given an execution directory with no files
    When the zip is requested
    Then a valid, readable, empty archive is returned
    And no error is raised

  Scenario: A single file is deleted
    Given an execution containing "a.step" and "b.stl"
    When "a.step" is deleted
    Then only "b.stl" remains
    And the execution directory still exists

  Scenario: A whole execution is deleted
    Given an execution with files
    When the execution is deleted
    Then its directory tree no longer exists
    And sibling executions of the same plan are untouched
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Path traversal and symlink guards (RF-AS-08/RF-AS-09) | Must | This layer serves arbitrary filenames from a URL path; the guards are the entire security boundary (BR-68) |
| Base resolved at configuration time (RF-AS-01) | Must | A relative or unresolved base would defeat `relative_to` |
| Execution directory creation (RF-AS-02/RF-AS-03) | Must | `construction-plans` cannot execute anything without it |
| Template single-execution rule (RF-AS-04) | Must | Deliberate storage bound; changing it silently fills the disk |
| Execution id + collision suffix (RF-AS-06/RF-AS-07) | Must | The id is the only identity an execution has |
| Listing and file resolution (RF-AS-10/RF-AS-12/RF-AS-13/RF-AS-16) | Must | The artefact browser has no other data source |
| Zip incl. the empty case (RF-AS-14/RF-AS-15) | Must | The primary download path; the empty case is a real state after a no-output run |
| Deletion (RF-AS-17/RF-AS-18) | Must | The only way to reclaim space for plan runs |
| Template runs excluded from plan listings (RF-AS-11) | Must | A listing entry with a fabricated aeroplane id misleads every consumer |
| Plan-run accumulation (RF-AS-05) | Should | Deliberate, but unbounded — see the retention gap |
| Temp-zip cleanup (RF-AS-19) | Should | A slow leak; ownership currently sits with the caller and is undefined |
| Explicit execution metadata (RF-AS-20) | Could | Today the directory name is the whole model; a manifest would remove the filesystem scan |
| Retention/pruning of old plan executions | Won't (today) | No retention logic exists; growth is unbounded |
| Reproducing the `_template_runs` scan asymmetry | Won't | A confirmed defect; one predicate must serve both scans |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/artifact_service.py` (294 l.) | `_ensure_within_base` (l.25-36), `_last_execution_id` / `_last_execution_id_suffix` (l.39-58), `TEMPLATE_RUNS_PREFIX` (l.78), `create_execution_dir`, `create_template_execution_dir` (l.81-110), `list_executions` (l.123-142), `list_files`, `get_file_path` (l.202-203), `zip_execution` (l.233-265), `delete_file`, `delete_execution`, `_resolve_execution_dir` (l.282-283) | 🟢 |
| `app/core/config.py` | `ARTIFACTS_BASE_DIR` default `/tmp/da3dalus_artifacts` + the `.resolve()` validator (l.24-32) | 🟢 |
| `app/schemas/construction_plan.py` | `ArtifactFile` (l.144: `name`, `is_dir`, `size_bytes`, `modified`), `ArtifactDirectory` (l.153: `execution_id`, `plan_id`, `aeroplane_id`, `created`, `file_count`) | 🟢 |
| `app/services/construction_plan_service.py` | the caller — `execute_plan` / `execute_plan_streaming` choose plan vs template directories | 🟢 see `construction-plans` |
| `app/api/v2/endpoints/construction_plans.py` | the artefact **routes** that call into this layer | 🟢 owned by `construction-plans` |
| `_reversa_sdd/flowcharts/cad-generation.md` §7 | the directory-layout diagram | 🟢 |
