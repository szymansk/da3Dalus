# Wave-3 lookup answers (18 factual questions)

Every claim below was read out of the working tree on `main`, or produced by a
read-only command run against it. Citations are `path:line`. Nothing here is
inferred from documentation or naming — where a fact could not be established
from the code, that is stated explicitly.

The security question (`Q-PT-13`) is first and its verdict is stated in full.

Contents:
[Q-PT-13](#a--q-pt-13-security-does-the-cots-model-upload-path-do-the-containment-check) ·
[Q-CC-17](#b--q-cc-17-does-the-circular-dependency-exist) ·
[Q-AF-4](#c--q-af-4-route-declaration-order) ·
[Q-AF-5](#d--q-af-5-polar-and-scoring-edge-cases-six-sub-facts) ·
[Q-AF-1](#e--q-af-1-are-all-bundled-dat-files-selig) ·
[Q-CT-4](#f--q-ct-4-is-euler_xyz-read-by-any-geometry-path) ·
[Q-FD-6](#g--q-fd-6-fuselage-slicing-details) ·
[Q-VI-9](#h--q-vi-9-the-openvsp-custom-handler) ·
[Q-WD-9](#i--q-wd-9-exception-types-and-http-mapping) ·
[Q-WD-10](#j--q-wd-10-turbulator-xtr_opt-persistence-and-symmetry_factor) ·
[Q-AA-5](#k--q-aa-5-does-any-ordering-guarantee-depend-on-mark_ops_dirty-preceding-publish) ·
[Q-AA-6](#l--q-aa-6-are-orphaned-operating-points-cleaned-up) ·
[Q-CG-4](#m--q-cg-4-what-would-supply-the-wing-schema-pickle-at-hook-time) ·
[Q-MC-6](#n--q-mc-6-does-any-requestnone-path-dereference-request) ·
[Q-MB-11](#o--q-mb-11-print_resolution_mm-node-field-or-material-spec) ·
[Q-FW-8](#p--q-fw-8-is-metricsmockts-still-referenced) ·
[Q-CP-5](#q--q-cp-5-does-stock-snapping-run-whenever-a-db-session-is-present) ·
[Q-AV-1](#r--q-av-1-does-avl-emit-a-genuine-convergence-indicator)

---

## A — `Q-PT-13` (SECURITY): does the COTS model-upload path do the containment check?

### Verdict, unambiguously

**Two separate answers, and they differ.**

1. **The upload (write) path — `POST /components/{id}/model` — is CONFIRMED SAFE,
   but not for the reason the rule asks about.** It performs **no**
   `Path.resolve()` containment check. It does not need one, because it never
   uses the client-supplied filename to build the destination: only the
   whitelisted *extension* is taken from it, and the basename is generated from
   an integer path parameter and a `uuid4`. There is no traversal primitive on
   the write path.

2. **The download (read) path — `GET /components/{id}/model` — is a CONFIRMED
   DEFECT: an unauthenticated arbitrary-file-read.** `model_ref` is a
   client-writable free-form string on the ordinary `PUT /components/{id}`
   contract, it is persisted verbatim, and the download endpoint hands it
   straight to `FileResponse` with no containment check at all.

So the answer to "does the COTS model-upload path perform the `Path.resolve()`
containment check that `.claude/rules/security.md` requires, or is it
path-traversal-exposed?" is: **the check is absent everywhere in
`app/api/v2/endpoints/components.py`, the write half is nevertheless not
exploitable, and the read half is.**

### 1. The write path

`app/api/v2/endpoints/components.py:186-199`

```python
comp = _call(svc.get_component, db, component_id)

suffix = FilePath(file.filename or "model.step").suffix.lower()
if suffix not in (".step", ".stp", ".stl"):
    raise HTTPException(status_code=422, detail=f"Unsupported file type: {suffix}. ...")

MODELS_DIR.mkdir(parents=True, exist_ok=True)
dest = MODELS_DIR / f"{component_id}_{uuid4().hex[:8]}{suffix}"
with dest.open("wb") as out:
    shutil.copyfileobj(file.file, out)
```

with `MODELS_DIR = FilePath("tmp") / "component_models"`
(`app/api/v2/endpoints/components.py:167`).

Why it is not traversable, component by component:

- `component_id` is `Annotated[int, Path(...)]`
  (`app/api/v2/endpoints/components.py:182`) — FastAPI coerces or 422s, so it can
  only ever contribute digits (or a leading `-`) to the filename.
- `uuid4().hex[:8]` is server-generated.
- `suffix` comes from `Path(...).suffix`, which by definition is the extension of
  the **last** path component and can never contain a `/` or `..`; it is then
  whitelisted against three literals. `Path("../../etc/passwd").suffix` is
  `""` → 422.
- The client filename is used for nothing else. It is not stored, not echoed.

There is no `Path.resolve()` / `commonpath` check, so the code does not follow
the pattern `.claude/rules/security.md` prescribes ("Path Safety"), but the
property that pattern exists to guarantee holds by construction.

**For contrast, the codebase does implement the prescribed check in five other
places** — which is what makes the omission here look like an oversight rather
than a considered decision:

| Where | Line |
|---|---|
| `app/api/v2/endpoints/cad.py` | `62-74` (`tmp_root = (FilePath.cwd() / "tmp").resolve()`) |
| `app/api/v2/endpoints/airfoils.py` | `207-209` |
| `app/api/v2/endpoints/aeroplane/fuselages.py` | `180-181` |
| `app/services/artifact_service.py` | `31` |
| `app/services/fuselage_slice_service.py` | `62` (`if not tmp_file.resolve().is_relative_to(tmp_dir.resolve())`) |

### 2. The read path — the actual defect

`model_ref` is a **client-writable field on the public write schema**:

`app/schemas/component.py:9,22`

```python
class ComponentWrite(BaseModel):
    ...
    model_ref: Optional[str] = Field(None, description="Reference to STEP/STL 3D model file")
```

`ComponentWrite` is the body of both `POST /components`
(`app/api/v2/endpoints/components.py:100`) and `PUT /components/{id}`
(`app/api/v2/endpoints/components.py:139`). The service stores every field
verbatim, with no validation of `model_ref` at all:

`app/services/component_service.py:113-114`

```python
for key, value in data.model_dump().items():
    setattr(comp, key, value)
```

The download endpoint then does:

`app/api/v2/endpoints/components.py:236-249`

```python
comp = _call(svc.get_component, db, component_id)
if not comp.model_ref:
    raise HTTPException(status_code=404, detail=...)
path = FilePath(comp.model_ref)
if not path.is_file():
    raise HTTPException(status_code=404, detail=f"Model file not found on disk: {path.name}")
media_type = "application/sla" if path.suffix.lower() == ".stl" else "application/step"
return FileResponse(path, media_type=media_type, filename=path.name)
```

`FilePath(comp.model_ref)` accepts an absolute path. `path.is_file()` is the
**only** gate — there is no base directory, no `resolve()`, no `relative_to`, and
no extension check on read (the `.stl`/`.step` test only picks a MIME type; any
other suffix falls through to `application/step` and is still served).

The two-request exploit is entirely within the documented API:

```
PUT  /components/1   {"name":"x","component_type":"material","model_ref":"/etc/passwd","specs":{}}
GET  /components/1/model      → 200, body = contents of /etc/passwd
```

There is no authentication in front of it: `app/main.py` registers only
`CORSMiddleware` (`app/main.py:233-234`); a grep for auth dependencies across the
app returns nothing.

Scope of the read: anything the API process can open — `.env`, `db/test.db`,
SSH keys, the whole filesystem.

### 3. Related — not security, but found on the same path

`ComponentEditDialog.tsx` hard-codes `model_ref: null` in the PUT body it sends:

`frontend/components/workbench/ComponentEditDialog.tsx:173-183`

```ts
const data = {
  name: name.trim(),
  ...
  model_ref: null,
  specs: buildOutSpecs(),
};
```

Combined with the blind `setattr` loop above, **editing any component in the UI
erases its uploaded 3D-model reference** and orphans the file under
`tmp/component_models/`. `ComponentWrite` has no partial-update semantics, so
every client must round-trip the field or lose it.

### 4. The other upload path, checked for completeness

`app/services/construction_part_service.py:134-141`

```python
def _store_file(aeroplane_id: str, part_id: int, content: bytes, suffix: str) -> Path:
    target_dir = STORAGE_ROOT / aeroplane_id
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / f"{part_id}_{uuid4().hex[:8]}{suffix}"
```

Here the *directory* segment is a raw string path parameter (`aeroplane_id`,
`app/api/v2/endpoints/aeroplane/construction_parts.py:138`), used with no
containment check, and `create_part`
(`app/services/construction_part_service.py:201-233`) never verifies the
aeroplane exists. The basename is still server-generated and the suffix
whitelisted (`_validate_upload`, `:125-129`), and Starlette's default path
convertor is `[^/]+`, so no `/` can reach it — the reachable worst case is a
single `..` segment writing one directory up into `tmp/`. Low severity, but the
`resolve()` check is missing here too. `part.file_path` is server-set and is not
in `ConstructionPartUpdate` (`:301` "File and geometry are NOT touched"), so the
read side of *this* pair is not exposed.

**Verdict:** **confirmed defect (high severity)** — the containment check is
absent from `components.py`; the write half is safe by construction, the read
half (`GET /components/{id}/model` + client-writable `model_ref`) is an
unauthenticated arbitrary-file-read. This is the security answer the corpus was
missing, and it is a real finding, not a theoretical one.

---

## B — `Q-CC-17`: does the circular dependency exist?

**Yes.** Run just now, read-only:

```
$ cd frontend && npm run deps:check
> depcruise --config .dependency-cruiser.cjs components/ hooks/ lib/ app/
...
  error no-circular: components/workbench/ImportOpenVspButton.tsx →
      components/workbench/ImportProgressBar.tsx →
      components/workbench/ImportOpenVspButton.tsx

x 22 dependency violations (1 errors, 16 warnings). 212 modules, 501 dependencies cruised.
```

Exit code **1** (verified separately, not through a pipe).

Current counts:

| Severity | Count | What |
|---|---|---|
| error | **1** | `no-circular`: `ImportOpenVspButton.tsx ↔ ImportProgressBar.tsx` |
| warn | **16** | `no-lib-import-components` — `lib/*` importing `hooks/*` or `components/*` |
| info | **5** | `no-orphans` |
| **total** | **22** | |

The 16 warnings are all one rule, on 8 `lib/` modules:
`treeDnd.ts`, `sparSizingHelpers.ts` (×2), `sparPlanHelpers.ts` (×2),
`planValidation.ts` (×2), `planTreeUtils.ts` (×2), `missionScale.ts` (×2),
`metricsAdapters.ts` (×4), `geometryDiff.ts`.

The 5 orphans: `SplitHandle.tsx`, `RadarChart.tsx`, `MarkerDetailBox.tsx`,
`AlertBanner.tsx`, `AirfoilPreview.tsx`.

**`deps:check` is not wired into CI** — a grep for `deps:check` across
`.github/workflows/` returns nothing. So the error has been sitting at exit
code 1 with no gate to catch it.

**Verdict:** **confirmed defect** — the cycle is real and reproducible; 1 error /
16 warnings / 5 info. Residual decision: whether to add `deps:check` to the
frontend CI job (today nothing enforces it).

---

## C — `Q-AF-4`: route declaration order

**`/airfoils/db/suitability` is declared first. The route is not shadowed.**

| Route | Declared at |
|---|---|
| `GET /airfoils/db/suitability` | `app/api/v2/endpoints/airfoils.py:492-493` |
| `GET /airfoils/db` | `app/api/v2/endpoints/airfoils.py:682-683` |
| `GET /airfoils/db/{name}` | `app/api/v2/endpoints/airfoils.py:698-699` |

492 < 698, so FastAPI matches the literal first. Full declaration order in the
module (all 12 routes) confirms no other literal/parameterised collision:
`492 db/suitability`, `682 db`, `698 db/{name}`, `715 import`,
`746 {airfoil_name}/known`, `779 datfile`, `812 airfoils`,
`837 {airfoil_name}/datfile`, `872 {airfoil_name}/geometry-stats`,
`901 {airfoil_name}/coordinates`, `946 {airfoil_name}/neuralfoil/analysis`,
`993 …/diagrams`. `POST /airfoils/datfile` (779) precedes no conflicting
`POST /airfoils/{x}`.

**Should a test pin it?** It is already pinned *behaviourally*, though not by an
explicit ordering assertion: `app/tests/test_airfoils_suitability_endpoint.py`
calls `/airfoils/db/suitability` and asserts a **422** for a missing required
query param (`:114`, `:119`). If `db/{name}` shadowed it, the request would reach
`get_airfoil_db(name="suitability")` and produce a **404**, failing those tests.

**Verdict:** **confirmed safe.** Residual decision: whether to add an explicit
route-order assertion in addition to the incidental behavioural coverage.

---

## D — `Q-AF-5`: polar and scoring edge cases (six sub-facts)

### D.1 — Null-metric policy: **a row IS written, with every metric `NULL`**

When no α point clears the confidence gate, the trusted arrays are empty and
`_extract_metrics` returns its all-`None` template early:

`app/services/airfoil_low_re_service.py:486-501`

```python
trusted = conf_arr >= confidence_gate
cl_trusted = cl_arr[trusted] if trusted.any() else np.array([])
...
row = _extract_metrics(cl_trusted, cd_trusted, alpha_trusted, 0.0, re, ...)
```

`app/services/airfoil_low_re_service.py:582-603`

```python
result: dict = {
    "reynolds": reynolds, "ld_max": None, "cl_max": None,
    "alpha_attached_lo": None, "alpha_attached_hi": None,
    "drag_bucket_width": None, "cd_min": None, "stall_gentleness": None,
    "cd0": None, "k": None, "cl0": None,
    "cl_valid_lo": None, "cl_valid_hi": None,
    "min_analysis_confidence": min_confidence, ...
}
if len(cl) < 4 or len(cd) < 4:
    return result
```

`compute_airfoil_low_re` appends that row unconditionally (`:519`), and the
persistence layer upserts **every** returned row without inspecting it:

`app/core/background_jobs.py:396-410` (and the identical path in
`scripts/backfill_airfoil_low_re.py:153,177`)

```python
for row in polar_results:
    ...
    if polar_row is None:
        polar_row = AirfoilLowRePolarModel(airfoil_name=name, reynolds=re_val)
        session.add(polar_row)
    for field_name, value in row.items():
        if field_name != "reynolds" and hasattr(polar_row, field_name):
            setattr(polar_row, field_name, value)
```

One detail worth writing into the contract: **`min_analysis_confidence` is still
a real number on such a row**, never `None` — `_windowed_min_confidence` falls
back to the whole-sweep minimum, and to `0.0` only when no finite value exists
(`app/services/airfoil_low_re_service.py:552-553`). So a fully-gated-out row
reads as "we know the confidence, we have no metrics".

### D.2 — Airfoil with no polar rows: **returned, with a fabricated `0.0`, not `null`**

The scoring loop iterates over **geometry** rows, not polar rows:

`app/services/suitability_service.py:444-447`

```python
for name, geo in geo_by_name.items():
    rows = polars_by_name.get(name, [])
    polar = interpolate_polar_at_re(rows, re_clamped_root, re_grid)
```

`interpolate_polar_at_re` returns `None` for an empty list
(`app/services/airfoil_low_re_service.py:327-328`), `score_re_agnostic(None)`
returns `None` (`:845-846`) — and then the coercion at
`app/services/suitability_service.py:467-469`:

```python
re_agn = score_re_agnostic(polar)
if re_agn is None:
    re_agn = 0.0
```

The item is appended unconditionally at `:556-572`. Consequence: an airfoil with
a geometry row and **zero** polar rows appears in `results` with
`re_agnostic = 0.0`, `min_analysis_confidence = 0.0` (`:534-536`) → confidence
tier 1 → sorted last. The target-CL lenses stay `None` because their guards
require a non-`None` polar (`:486`, `:495`, `:504`).

Two asymmetries follow, both spec-relevant:

- An airfoil with a polar row but **no geometry row** is omitted entirely (it is
  never in `geo_by_name`).
- The `include=` extras path **refuses** to do what the main loop does. It
  explicitly declines to fabricate:
  `app/services/suitability_service.py:660-668`
  ```python
  candidate = all_items_by_name.get(name_lower)
  if candidate is None:
      continue  # no geometry row at all — not fabricated
  has_polars = any(n.lower() == name_lower for n in polars_by_name)
  if not has_polars:
      continue  # no polar data — not fabricated
  ```
  So the same airfoil is *excluded* when named in `include` but *included with a
  0.0* when it falls out of the main sweep. Under `P-WARN-0` the `include` path
  is the correct behaviour and the main loop is the defect.

### D.3 — Null propagation through Lens 2: **it does NOT propagate**

`score_mission` is written to propagate:

`app/services/airfoil_low_re_service.py:894-906`

```python
def score_mission(re_agnostic: float | None, family: str, ..., ) -> float | None:
    ...
    if re_agnostic is None or mission_type not in mission_weights:
        return None
    ...
    mission_score = re_agnostic * family_bonus * thickness_match * cl_bonus
```

but the only production caller has already replaced `None` with `0.0` two lines
earlier (`app/services/suitability_service.py:467-469`, quoted above) before
passing it in at `:474-481`. So the `None` branch is unreachable from
`search_suitability`, and a no-polar airfoil gets `mission = 0.0 × bonuses = 0.0`
— a number that looks like a scored result. `cl_max=None` is likewise absorbed
(`cl_bonus = 1.0`, `:938-941`).

### D.4 — `_level_flight_cl` call sites: **three, all in `suitability_service`**

Defined at `app/services/airfoil_low_re_service.py:686`, imported at
`app/services/suitability_service.py:61`, and called exactly three times — all
inside the `aeroplane_id` resolution block, all `None`-guarded and all
override-guarded:

| Call | Line | Produces | Inputs from |
|---|---|---|---|
| cruise | `app/services/suitability_service.py:336-338` | `effective_target_cl_cruise` | `ctx["mass_kg"]`, `ctx["v_cruise_mps"]`, `ctx["s_ref_m2"]` |
| best glide | `:346-348` | `effective_target_cl_best_glide` | `ctx["v_md_mps"]` |
| min sink | `:356-358` | `effective_target_cl_min_sink` | `ctx["v_min_sink_mps"]` |

`ctx` is `aeroplane.assumption_computation_context` (`:325`). Each call is
wrapped as:

```python
if effective_target_cl_cruise is None:                       # explicit param wins
    if all(v is not None for v in (mass_kg, v_cruise_mps, s_ref_m2)):
        try:
            effective_target_cl_cruise = _level_flight_cl(mass_kg, v_cruise_mps, s_ref_m2)
        except (ValueError, ZeroDivisionError):
            effective_target_cl_cruise = None
```

So: **all three `target_cl_*` values are derived from `_level_flight_cl` when and
only when an `aeroplane_id` resolves and the computation context carries mass,
the matching speed and `s_ref`; the query parameters
`target_cl_cruise` / `target_cl_best_glide` / `target_cl_min_sink`
(`app/api/v2/endpoints/airfoils.py:523-546`) override the derived value
entirely.** There are no other call sites in `app/` or `scripts/`.

### D.5 — Duplicate upload: **409 by default, 200 with `?overwrite=true`**

`app/api/v2/endpoints/airfoils.py:437-458`

```python
exists = target.exists()
if exists and not overwrite:
    raise ConflictError(message=f"Airfoil '{file_name}' existiert bereits.", ...)

target.write_bytes(dat_bytes)
return AirfoilUploadResponse(..., overwritten=exists)
```

`ConflictError` → **409** via `_raise_http_from_domain`
(`app/api/v2/endpoints/airfoils.py:478-479`). With `?overwrite=true` the file is
replaced and the status is downgraded from the declared 201 to **200**:

`app/api/v2/endpoints/airfoils.py:800-802`

```python
if result.overwritten:
    response.status_code = status.HTTP_200_OK
```

So: **not** the directory importer's silent case-insensitive skip
(`app/services/airfoil_service.py:127-129`). Two further contract differences
from the importer: the collision test here is `Path.exists()` on the filesystem —
**case-sensitive on Linux, case-insensitive on macOS** — and the upload writes
only the `.dat` file, it does **not** insert an `airfoils` DB row.

### D.6 — ASB-absent response shape: **there is no ASB-absent path at all**

`app/api/v2/endpoints/airfoils.py:7`

```python
import aerosandbox as asb
```

An unguarded module-level import. On a platform without AeroSandbox
(`linux/aarch64`, per the pyproject markers) the whole `airfoils` module fails to
import — all **12** airfoil routes disappear and app startup fails. The endpoint
can therefore return neither a 200-with-empty-body nor a 5xx: it does not exist.

The `[]` referenced in the question is a **different function**:

`app/services/airfoil_low_re_service.py:458-462`

```python
try:
    import aerosandbox as asb
except ImportError:
    logger.warning("AeroSandbox not available — skipping NeuralFoil compute for %s", name)
    return []
```

That is `compute_airfoil_low_re`, consumed by the backfill
(`app/core/background_jobs.py:384`), never by `/neuralfoil/analysis` — whose
compute helper `_run_neuralfoil_analysis` uses the module-level `asb` directly
(`app/api/v2/endpoints/airfoils.py:333`). So ADR 0012's graceful-degradation
pattern is implemented in the service and **absent** in the endpoint module.

**And `/geometry-stats` on an imported-but-unclassified airfoil: 404, not a
null-filled body.** The endpoint reads the **filesystem**, not the DB:

`app/api/v2/endpoints/airfoils.py:882-884` → `_resolve_airfoil_file`
(`:213-224`), which raises `NotFoundError` ("Airfoil '…' wurde nicht gefunden.")
when the `.dat` is not in `AIRFOILS_DIR` → **404** via
`_raise_http_from_domain` (`:472-473`). An airfoil present in the `airfoils`
table but with no bundled `.dat` file is therefore a 404 from `geometry-stats`,
`coordinates`, `datfile` and both `neuralfoil` routes, while `GET
/airfoils/db/{name}` serves it happily.

**Verdict:** six facts established. **Confirmed defects:** D.2 (no-polar airfoils
scored as `0.0` and ranked, contradicting the `include` path's explicit
"not fabricated" rule), D.3 (Lens-2 null propagation does not happen — the
`None` is coerced upstream), D.6 (the unguarded `import aerosandbox` at
`airfoils.py:7` breaks ADR 0012 for the entire airfoil router). **Confirmed
safe / as-specified:** D.1, D.4, D.5.

---

## E — `Q-AF-1`: are all bundled `.dat` files Selig?

**Yes — 0 Lednicer candidates in 1 665 files.**

Method: a throwaway script at
`/private/tmp/claude-501/-Users-szymanski-Projects-da3Dalus-cad-modelling-service/fd877672-d18a-4105-a9f5-076e060dddfd/scratchpad/sniff_dat_format.py`
(scratchpad, not the repo) that replicates `_parse_dat_file`
(`app/services/airfoil_service.py:57-87`) exactly — skip line 0 as a header, then
accept any line whose first two whitespace tokens parse as floats — and flags a
file as a Lednicer candidate when the **first** parsed pair has both values
`> 1.0` (the point-count row, e.g. `61. 61.`).

```
total .dat files:            1665
LEDNICER candidates:         0  []
any x > 1.0:                 65
any |y| > 1.0:               0
< 3 parsable coords:         0
line-0 parses as coord pair: 0
```

The 65 files with some `x > 1.0` were checked individually and are all benign —
sorted by maximum x:

```
e664ex.dat           max_x=1.2
vr8b.dat             max_x=1.01
s1221.dat            max_x=1.00182
s4096.dat            max_x=1.00113
s4095.dat            max_x=1.00071
ah88k136.dat         max_x=1.00058
hor12.dat            max_x=1.00047
… (58 more, all < 1.0004)
```

i.e. one extended-chord section (`e664ex`, 1.2) and 64 files with
rounding-level overshoot. None is a count row, and no file has `|y| > 1`.

Two additional facts the same pass establishes:

- **No file loses a coordinate to the header skip** — line 0 never parses as a
  coordinate pair in any of the 1 665 files, so the unconditional `lines[1:]`
  (`app/services/airfoil_service.py:73`) is safe for the bundled corpus.
- **Every file yields ≥ 3 coordinates**, so none of them would hit
  `_parse_dat_file`'s `"Too few valid coordinates"` guard (`:84-85`).

**Verdict:** **confirmed safe** for the bundled corpus — all 1 665 are Selig, and
format sniffing would change nothing today. Residual decision (unchanged, and a
real one): user uploads via `POST /airfoils/datfile` are **not** validated at all
— `_save_airfoil_dat` (`app/api/v2/endpoints/airfoils.py:437-458`) writes the
bytes without parsing them, so a Lednicer file uploaded by a user is accepted and
mis-parsed on first read. The question of whether to add sniffing is therefore
about the upload path only, and it remains open.

---

## F — `Q-CT-4`: is `euler_xyz` read by any geometry path?

**No. It is display/serialisation-only, and it is not even read back on
deserialisation.**

Computed once in the constructor:

`cad_designer/airplane/aircraft_topology/wing/CoordinateSystem.py:52-53`

```python
R = np.matrix([xDir, yDir, zDir]).T
self.euler_xyz: list[float] = CoordinateSystem._rotation_matrix_to_euler_angles(R, 'XYZ').tolist()
```

Emitted in `__getstate__`:

`cad_designer/airplane/aircraft_topology/wing/CoordinateSystem.py:55-63`

```python
def __getstate__(self):
    return {"xDir": ..., "yDir": ..., "zDir": ..., "origin": ..., "euler_xyz": self.euler_xyz}
```

**Discarded on the way back in** — `from_json_dict` reconstructs from the three
direction vectors and the origin and lets the constructor recompute the angles:

`cad_designer/airplane/aircraft_topology/wing/CoordinateSystem.py:112-117`

```python
return CoordinateSystem(
    xDir=data.get('xDir', [1, 0, 0]),
    yDir=data.get('yDir', [0, 1, 0]),
    zDir=data.get('zDir', [0, 0, 1]),
    origin=data.get('origin', [0, 0, 0])
)
```

A repo-wide grep for `euler_xyz` across `app/`, `cad_designer/` and `frontend/`
(excluding `node_modules`) returns exactly **three** production lines — the two
above (`:53`, `:62`) plus the `from_json_dict` omission — and **17 lines in
`cad_designer/tests/test_coordinate_system.py`**. No consumer in `app/`, none in
the frontend, none in any converter.

Geometry consumes the direction vectors, never the angles — the one place a
`CoordinateSystem` is built from real CAD geometry passes the CadQuery plane's
vectors straight through:

`cad_designer/airplane/aircraft_topology/wing/Airfoil.py:52`

```python
self.coordinate_system = CoordinateSystem(cs.xDir.toTuple(), cs.yDir.toTuple(), cs.zDir.toTuple(), cs.origin.toTuple())
```

**Verdict:** **confirmed safe** — the intrinsic/extrinsic convention is
unobservable: no geometry path reads `euler_xyz`, and a round-trip through JSON
does not preserve it, it recomputes it. The spec can state it as a derived,
informational field. (Note the class is frozen topology per `cad_designer/CLAUDE.md`,
so nothing is to be changed here regardless.)

---

## G — `Q-FD-6`: fuselage slicing details

### G.1 — `slice_axis="auto"` → longest bounding-box axis

`cad_designer/aerosandbox/slicing.py:892-904`

```python
if slice_axis == "auto":
    slice_axis = detect_longest_axis(model.val())
    logger.info(f"Auto-detected slice axis: {slice_axis}")

# Rotate model so slicing always happens along X
if slice_axis == "y":
    model = model.rotateAboutCenter((0, 0, 1), 90)
elif slice_axis == "z":
    model = model.rotateAboutCenter((0, 1, 0), -90)
elif slice_axis != "x":
    raise ValueError(f"Invalid slice_axis: {slice_axis}. Must be 'x', 'y', 'z', or 'auto'.")
```

`cad_designer/aerosandbox/slicing.py:470-473`

```python
def detect_longest_axis(shape: cq.Shape) -> str:
    """Detect the longest bounding box axis (x, y, or z)."""
    dims = get_bounding_box_dims(shape)
    return max(dims, key=dims.get)
```

Alternatives: `"x"` (no-op), `"y"` (rotate +90° about Z), `"z"` (rotate −90°
about Y); anything else raises. Slicing then always proceeds along X. The
endpoint pre-validates the four literals and 422s otherwise
(`app/api/v2/endpoints/fuselage_slice.py:44-48`), so the `ValueError` branch is
defence-in-depth. Note that `detect_longest_axis` is purely a bounding-box
comparison — a short, wide body (a flying-wing pod) will be sliced across its
span with no warning.

### G.2 — Minimum 2 usable slices: **NOT guaranteed**

Two clamps exist, and both apply to the **station count**, not to the number of
cross-sections that survive:

`cad_designer/aerosandbox/slicing.py:949-955` (shell / adaptive path)

```python
# Clamp the slice-station count so a caller-controlled
# ``number_of_slices`` can't drive an unbounded loop.
n_stations = max(2, min(int(number_of_slices), 4096))
x_stations = [bb.xmin + (bb.xmax - bb.xmin) * i / (n_stations - 1) for i in range(n_stations)]
```

`cad_designer/aerosandbox/slicing.py:498-500` and `:521-523` (solid path)

```python
number_of_slices = max(number_of_slices, 2)
spacing = (xmax - xmin) / (number_of_slices - 1)
```

But every station may be dropped downstream, at three separate `continue`/`if`
gates:

- `if polylines:` — the station is only appended when the section returned
  something (`cad_designer/aerosandbox/slicing.py:958-960`);
- `if not wire_set: continue` and `if not slice_points: continue` in the
  superellipse-fitting loop (`:987-993`);
- on the solid path, `except Exception … continue` swallows a failed slice
  (`:544-547`).

Nothing between the loop and the return asserts `len(xsec_dicts) >= 2`, and
`slice_step_file` does not check either
(`app/services/fuselage_slice_service.py:87-97`). So a degenerate body can return
a `FuselageSchema` with 0 or 1 xsecs and HTTP 200 — the failure only surfaces on
the caller's `PUT`, against `min_length=2`
(`app/schemas/aeroplaneschema.py:659,689,705,760`).

For contrast, the CUSTOM OpenVSP handler *does* enforce this exact invariant
(`app/converters/openvsp_custom_handler.py:98-106`), so the pattern exists in the
codebase — it is just missing here.

### G.3 — Upper bound on cross-section count: **yes, two of them**

| Bound | Value | Where |
|---|---|---|
| HTTP request | `2 ≤ number_of_slices ≤ 500` | `app/api/v2/endpoints/fuselage_slice.py:25-27` (`Form(ge=2, le=500)`) |
| internal (shell/adaptive path) | `min(…, 4096)` | `cad_designer/aerosandbox/slicing.py:951` |
| `points_per_slice` | `10 ≤ n ≤ 200` | `app/api/v2/endpoints/fuselage_slice.py:28-30` |

The **solid** path has no 4096 clamp; it is bounded only by the endpoint's 500
and by `max_iterations = int((xmax - xmin) / spacing) + 2`
(`cad_designer/aerosandbox/slicing.py:527`). And nothing bounds the *stored*
`x_secs` list on the `PUT` side — `min_length=2` is the only constraint
(`app/schemas/aeroplaneschema.py`).

**Verdict:** G.1 **confirmed** (longest bbox axis, alternatives x/y/z, invalid →
422 at the endpoint). G.2 **confirmed defect** — ≥ 2 stations are guaranteed,
≥ 2 *usable* cross-sections are not, and the 200-with-1-xsec response only fails
later at the caller's `PUT`. G.3 **confirmed** — 500 at the HTTP boundary, 4096
internally (shell path only).

---

## H — `Q-VI-9`: the OpenVSP CUSTOM handler

Read in full: `app/converters/openvsp_custom_handler.py` (156 lines) plus the two
helpers it borrows.

### H.1 — Exact parm coverage

The handler touches **five** things, and nothing else:

| # | API / parm | Where | Role |
|---|---|---|---|
| 1 | `GetNumMainSurfs(gid)` | `openvsp_custom_handler.py:59` | capability probe, `>= 1` |
| 2 | `GetNumXSecSurfs(gid)` | `:60` | capability probe, `>= 1` |
| 3 | `CompPnt01(gid, 0, u, w)` | `openvsp_fuselage_handler.py:350` | **the only geometry source** |
| 4 | `Sym_Planar_Flag` (group `Sym`) | `openvsp_fuselage_handler.py:287` via `_read_sym_planar_flag` | symmetry flag |
| 5 | `X/Y/Z_Location`, `X/Y/Z_Rotation` | `openvsp_wing_handler.py:190-199` via `_read_geom_xform` | **read and then deliberately discarded** |

**Not read at all** — and this is the re-implementation-relevant part:

- Every script-private `Design.*` parm. The module docstring names them and says
  why: *"the geometry is generated from script-private `Design.*` parms (Length,
  Diameter, NoseMult, AftMult, NoseCenter, AftCenter, …) that we can't enumerate
  ahead of time"* (`openvsp_custom_handler.py:6-9`).
- Any XSec shape / type / skinning parm — the standard `XLocPercent` family is
  explicitly stated to be zero on Custom Geoms (`:5-6`).
- The superellipse exponent: **hard-coded `n=2.0`** (`:93`), i.e. every station is
  a plain ellipse.
- Scale, colour/material, sub-surfaces, `NumMainSurfs > 1`.

The reconstruction is therefore: **12 u-stations × 32 w-points of
`CompPnt01`, reduced to a Y/Z bounding box per station.**

`app/converters/openvsp_custom_handler.py:45`
```python
_N_U_STATIONS = 12
```
`app/converters/openvsp_fuselage_handler.py:335-359`
```python
def sample_station_via_comp_pnt(vsp, gid, u, n_w: int = 32):
    for k in range(n_w):
        w = k / float(n_w)
        p = vsp.CompPnt01(gid, 0, u, w)
        ...
    cx = sum(xs_list) / len(xs_list)
    cy = (max(ys) + min(ys)) / 2.0
    cz = (max(zs) + min(zs)) / 2.0
    a = (max(ys) - min(ys)) / 2.0
    b = (max(zs) - min(zs)) / 2.0
    return cx, cy, cz, a, b
```

Fidelity consequences a re-implementation must reproduce (or consciously reject):

- `a` / `b` are **bounding-box half-widths**, so any non-elliptical section is
  rounded *up* to its bounding box — a square-ish fuselage gains area.
- The station centre is inconsistent: `cx` is the **arithmetic mean** of the
  sampled x, while `cy`/`cz` are **bbox midpoints** (`:354` vs `:355-356`).
- `CompPnt01(gid, **0**, u, w)` hard-codes main-surface index 0, while the probe
  only requires `GetNumMainSurfs >= 1` — a multi-surface Custom Geom silently
  loses every surface but the first.
- The sampling is uniform and fixed at 12; `xsec_us` is collected and then thrown
  away (`openvsp_custom_handler.py:96`, `_ = xsec_us  # reserved for a future
  curvature-aware sampler`), and `_apply_xform` is imported only to be silenced
  (`:132`, `_ = _apply_xform`).

### H.2 — Degradation behaviour: four distinct branches

| Trigger | Warning severity | `mark_lossy`? | Result |
|---|---|---|---|
| Any of `GetNumMainSurfs` / `GetNumXSecSurfs` / `CompPnt01` missing or `< 1` (`:59-73`) | `info` | **yes** (`:72`) | geom skipped entirely |
| `CompPnt01` raises at station *u* (`:79-91`) | `warning` | **no** | `break` — keeps the stations collected so far |
| `len(xsecs) < 2` (`:98-106`) | `warning` | **yes** (`:105`) | geom skipped entirely |
| Geom-level rotation non-zero (`:114-126`) | `info` | no | XForm **not** applied; note emitted |

The second row is the one to flag. The exception handler is:

```python
except Exception as exc:  # noqa: BLE001 — defensive against API drift
    ctx.add_warning(..., reason=f"Custom Geom {name!r}: CompPnt01 sampling failed at "
                    f"u={u:.3f} ({exc}); skipping rest of the body.", severity="warning")
    break
```

`break`, not `return` — so a body whose sampling fails at u=0.8 is imported as a
**truncated fuselage** with 9 of 12 stations, and the geom is **not** marked
lossy (the `mark_lossy` at `:105` only fires if the partial count then drops below
2). The import reports success with a `warning` in the stream and a silently
foreshortened body. That is a genuine, confirmed defect.

Two smaller provenance points:

- Symmetry is XZ-only: `Sym_Planar_Flag == 2` → symmetric, `0` → not, anything
  else → `info` warning + non-symmetric
  (`openvsp_fuselage_handler.py:287-304`, `_SYM_XZ = 2` at `:269`). Those
  warnings are emitted with `component_type="FUSELAGE"` (`:296`), **not**
  `"CUSTOM"` — so a CUSTOM geom's symmetry warning is mis-attributed in the
  warning stream.
- The XForm is read (`:113`) and then explicitly not applied, on the stated
  ground that `CompPnt01` returns world-frame points (`:108-132`). Translation is
  discarded without any warning at all (`:127`); only a non-zero **rotation**
  produces the `info` note.

Registration is real: `openvsp_importer.py:316-318` imports and calls
`openvsp_custom_handler.register()`, which binds `"CUSTOM"` → `_handle_custom`
(`openvsp_custom_handler.py:153-155`).

Output shape: a `FuselageSchema` with a de-duplicated name (`name (2)`, `name (3)`
…, `:142-149`), registered in `ctx.fuselage_geom_ids` (`:150`).

**Verdict:** **fully documented — the re-implementation blocker is cleared.**
Coverage is 5 API calls, geometry is 12×32 `CompPnt01` samples reduced to Y/Z
bbox half-axes with `n=2.0`, and degradation is the four-branch table above.
**One confirmed defect found in the process:** the mid-body `CompPnt01` failure
path truncates the fuselage without marking it lossy
(`app/converters/openvsp_custom_handler.py:79-91`).

---

## I — `Q-WD-9`: exception types and HTTP mapping

Both functions raise **bare `ValueError`**, which is **not** in the
`ServiceException` hierarchy (`app/core/exceptions.py:11`), so neither is
translated by the global handler (`app/main.py:274-306`). The two nevertheless
end up in different places.

### I.1 — `assert_unique_control_names` → **500**, confirmed defect

`app/services/control_surface_mixing.py:149-164`

```python
def assert_unique_control_names(names: list[str]) -> None:
    ...
    if dupes:
        raise ValueError(
            f"Duplicate control-variable names would collapse into one AVL DOF: {sorted(dupes)}"
        )
```

Called from `build_avl_geometry_file`:

`app/services/avl_geometry_service.py:202-208`

```python
from app.services.control_surface_mixing import assert_unique_control_names
cross_surface_names: list[str] = []
for surface in surfaces:
    names_in_surface = {c.name for section in surface.sections for c in section.controls}
    cross_surface_names.extend(names_in_surface)
assert_unique_control_names(cross_surface_names)
```

Two reachable outcomes, both 500:

1. **Via the AVL-geometry routes.** `GET /aeroplanes/{id}/avl-geometry` and
   `POST …/avl-geometry/regenerate` catch **only** `ServiceException`
   (`app/api/v2/endpoints/aeroplane/avl_geometry.py:31-32`, `:64-65`). A bare
   `ValueError` escapes to FastAPI's default handler → **500 Internal Server
   Error**, and the message — the one that names the duplicated control — is
   **not** in the response body.
2. **Via the analysis routes.** `build_avl_geometry_file` is called at
   `app/services/analysis_service.py:312` (and `:359`, `:1821`, `:1956`), in most
   cases *outside* the surrounding `try` (the try opens at `:316`), so the same
   raw 500. Where it is inside a try, the `except Exception → raise
   InternalError(...)` (`analysis_service.py:327-329`) maps to **500** as well
   (`app/main.py:291-293`).

There is no path on which a duplicate control name produces a 422. The user
cannot tell "rename your control surface" from "the server is broken".

### I.2 — `required_section_modulus` → **422 in practice**, confirmed safe

`app/services/spar_sizing.py:78-88`

```python
def required_section_modulus(m_design_Nm: float, sigma_allow_mpa: float) -> float:
    ...
    if sigma_allow_mpa <= 0:
        raise ValueError(f"sigma_allow must be positive, got {sigma_allow_mpa}")
    return m_design_Nm * 1000.0 / sigma_allow_mpa
```

The `ValueError` is unreachable through the only production route, because the
caller validates first with a real domain exception:

`app/services/analysis_service.py:2136-2150`

```python
# The material schema permits allowable_bending_stress_mpa=0 (min=0), which would
# make required_section_modulus divide by zero → 500. Surface a clear 422
# instead (gh-1008 review).
sigma_allow = spar_params.sigma_allow_mpa_override
if sigma_allow is None:
    sigma_allow = material_specs.get("allowable_bending_stress_mpa")
if sigma_allow is None or sigma_allow <= 0:
    raise ValidationError(message=(f"Material '{material.name}' has no positive ..."), ...)
```

`ValidationError` → **422** (`app/main.py:283-286`). `compute_spar_sizing`
(`app/services/spar_sizing.py:260`) has exactly one caller,
`_compute_spar_sizing_for_surfaces` (`app/services/analysis_service.py:2104`,
imported at `:2116`, called at `:2184`), so there is no bypass. The bare
`ValueError` is defence-in-depth behind a correct 422 guard.

**Verdict:** `assert_unique_control_names` — **confirmed defect**: bare
`ValueError` surfaces as an opaque **500**, on a user-fixable input error, with
the diagnostic message dropped. `required_section_modulus` — **confirmed safe**:
the real answer to the client is **422**, produced one layer up; the bare
`ValueError` never fires today. Residual decision: whether the second one should
still be converted to a domain exception so a future second caller cannot
reintroduce the 500.

---

## J — `Q-WD-10`: turbulator `xtr_opt` persistence and `symmetry_factor`

### J.1 — `xtr_opt` is **never** persisted

The endpoint says so twice, and the code matches:

`app/api/v2/endpoints/aeroplane/turbulator_optimizer.py:6-7`

```
This is a compute-only endpoint (Slice 2): results are returned but not
persisted. Persisting the optimal position to the turbulator is Slice 3.
```

`app/api/v2/endpoints/aeroplane/turbulator_optimizer.py:196-198` (docstring of
`optimize_turbulator`)

```
This endpoint is COMPUTE-ONLY (Slice 2). The results are not persisted
back to the turbulator position — that is Slice 3.
```

Verified independently: `optimize_turbulator` (`:184-199`) calls `_call_optimizer`
then `_result_to_response` and returns; there is no DB write between them, and
`_result_to_response` (`:141-167`) only re-shapes the dataclass.

A repo-wide grep for writers of `position_root` / `position_tip` /
`WingXSecTurbulatorModel(` in `app/` returns exactly three, none of which is the
optimiser:

| Writer | Line | What |
|---|---|---|
| `app/services/wing_service.py:1541` | `turb = WingXSecTurbulatorModel(wing_xsec_detail_id=detail.id)` | ordinary wing CRUD |
| `app/models/aeroplanemodel.py:401` | *"Build a WingXSecTurbulatorModel from a turbulator payload dict or None"* | ordinary wing CRUD |
| `app/services/aeroplane_clone_service.py:279-284` | `position_root=turbulator.position_root, position_tip=turbulator.position_tip` | version clone (copies, never computes) |

So the propose/adopt boundary of ADR 0007 is **not** crossed: adoption is manual
and the UI needs an explicit apply step. The optimiser's `xtr_opt` reaches only
the response (`TurbulatorSectionResult.xtr_opt`, `:150`).

The *stored* positions are read in the other direction — the assumption pipeline
consumes them to adjust `cd0`
(`app/services/assumption_compute_service.py:2236-2237`,
`compute_delta_cd0_from_turbulator_position` at
`app/services/turbulator_optimizer_service.py:641`) — which is read-only with
respect to `wing_xsec_turbulators`.

### J.2 — `symmetry_factor` comes from the **ASB wing's `symmetric` flag**, which is `wings.symmetric`

The factor itself:

`app/services/turbulator_optimizer_service.py:330-331`

```python
symmetry_factor = 2.0 if wing_symmetric else 1.0
return symmetry_factor * half_span_sum
```

`wing_symmetric` is read — not inferred from the section list — at both call
sites, and in both cases from the **main wing selected by largest planform
area**:

`app/api/v2/endpoints/aeroplane/turbulator_optimizer.py:99-102`

```python
main_wing = max(asb_airplane.wings, key=lambda w: float(w.area()))
wing_name = getattr(main_wing, "name", None) or "main_wing"
s_ref = float(main_wing.area())
wing_symmetric = getattr(main_wing, "symmetric", False)
```

`app/services/assumption_compute_service.py:144-148`

```python
_main_wing_asb = max(asb_airplane.wings, key=lambda w: float(w.area()))
_wing_name_turb = getattr(_main_wing_asb, "name", None) or "main_wing"
# MAJOR 1 fix: detect symmetry so ΔCD0 aggregation applies the
# factor-of-2 when the turbulator covers both half-spans.
_wing_symmetric_flag = getattr(_main_wing_asb, "symmetric", False)
```

and the ASB `Wing.symmetric` attribute is set directly from the DB column by the
converter:

`app/converters/model_schema_converters.py:796-806`

```python
asb_wings = [
    Wing(
        name=wing_name,
        symmetric=wing.symmetric,
        xsecs=...,
    )
    for wing_name, wing in plane_schema.wings.items()
]
```

**The vertical-stabiliser failure mode the question anticipated does not occur**,
for two independent reasons: (a) the flag is read, not inferred, so a VTP with
`symmetric=False` yields factor 1.0; and (b) the optimiser only ever runs on the
largest-area wing, so a VTP is not the subject unless it *is* the largest surface.

**Verdict:** both **confirmed safe / as-specified**. `xtr_opt` is compute-only and
never written back (adoption is manual, consistent with ADR 0007);
`symmetry_factor` is `2.0 if main_wing.symmetric else 1.0`, sourced from
`wings.symmetric` through the ASB converter, not inferred. Residual decision:
whether Slice 3 (persisting the optimum) is still wanted — that is a product
decision, not a lookup.

---

## K — `Q-AA-5`: does any ordering guarantee depend on `mark_ops_dirty` preceding `publish`?

**No. The pairing is historical, not an ordering guarantee. Swapping the two
lines would change nothing observable.**

Three facts establish it.

**1. The handlers do not read operating-point status.** They only schedule:

`app/services/invalidation_service.py:39-48`

```python
def _on_geometry_changed(event: GeometryChanged) -> None:
    """Log GeometryChanged events and schedule background retrim."""
    logger.info("GeometryChanged for aeroplane %d (source: %s) — OPs marked DIRTY", ...)
    from app.core.background_jobs import job_tracker
    job_tracker.schedule_retrim(event.aeroplane_id)
```

(The misleading log line the question flags is right there at `:42` — the handler
announces "OPs marked DIRTY" without doing it.) The same is true of
`_on_geometry_changed_recompute_assumptions` (`:51-60`) and
`_on_assumption_changed` (`:63-…`).

**2. `publish` is synchronous but the work is not.** `EventBus.publish`
(`app/core/events.py:36-42`) calls handlers inline; `schedule_retrim`
(`app/core/background_jobs.py:101-126`) only creates an asyncio task, and the
coroutine's first statement is a sleep:

`app/core/background_jobs.py:128-133`

```python
async def _debounced_retrim(self, aeroplane_id: int) -> None:
    await asyncio.sleep(self.debounce_seconds)
```

with `debounce_seconds = 2.0` (`app/core/background_jobs.py:45-46`).

**3. The consumer reads through a different, later session.** `retrim_dirty_ops`
opens its own `SessionLocal()` (`app/services/retrim_service.py:59`, registered
via `job_tracker.set_trim_function(retrim_dirty_ops)` at `app/main.py:155`), so
it sees only what the request transaction committed. `mark_ops_dirty` issues a
bulk `UPDATE` on the *caller's* session
(`app/services/invalidation_service.py:26-36`), which `get_db()` commits at
request end (`app/db/session.py`, `yield db; db.commit()`).

The real constraint is therefore "both must happen before the request commits",
which both orderings satisfy — not "mark before publish".

The seven manual publishers are: `app/models/stability_events.py:52-55`,
`app/models/avl_geometry_events.py:52`,
`app/services/design_assumptions_service.py:188` and `:231`,
`app/services/loading_scenario_service.py:455`,
`app/services/assumption_compute_service.py:808`,
`app/services/mass_cg_service.py:170` and `:220`. Each is literally
`mark_ops_dirty(db, aeroplane.id)` on one line and `event_bus.publish(...)` on
the next.

**Verdict:** **confirmed safe to move** — no ordering guarantee is at stake, so
moving the marking into the handlers is a pure refactor with no behavioural risk,
and it would also make the "OPs marked DIRTY" log line
(`app/services/invalidation_service.py:42`) true. Whether to do it remains a
decision; the factual objection ("maybe the ordering matters") is now closed.

---

## L — `Q-AA-6`: are orphaned operating points cleaned up?

**No — anywhere. And the local database already contains 22 of them.**

**The FK has no `ondelete`:**

`app/models/analysismodels.py:20-25`

```python
class OperatingPointModel(Base):
    __tablename__ = "operating_points"
    id = Column(Integer, primary_key=True)
    ...
    aircraft_id = Column(Integer, ForeignKey("aeroplanes.id"), nullable=True, index=True)
```

The migration that introduced the column created a plain FK with no `ondelete`
either (`alembic/versions/1f3b9c42e3aa_extend_operating_points_for_generation.py`,
`fk_operating_points_aircraft_id`).

**There is no ORM relationship to cascade through.** `AeroplaneModel` declares
relationships for `wings`, `fuselages`, `flight_profile`, `mission_objective`,
`weight_items`, `copilot_messages`, `design_assumptions`, `computation_config`,
`stability_results`, `loading_scenarios`, `branch`
(`app/models/aeroplanemodel.py:719-768`) — **no `operating_points`**, and
`OperatingPointModel` declares no `relationship()` back.

**Deletion does nothing about them:**

`app/services/aeroplane_service.py:177-189`

```python
aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
...
db.delete(aeroplane)
```

**And SQLite does not enforce the constraint** — the connect hook sets three
pragmas and `foreign_keys` is not among them:

`app/db/session.py:38-52`

```python
cursor.execute("PRAGMA journal_mode=WAL")
cursor.execute("PRAGMA synchronous=NORMAL")
cursor.execute("PRAGMA busy_timeout=30000")
```

So the delete succeeds and the rows survive with a dangling `aircraft_id`.

**The only bulk delete of operating points is not a cleanup:**

`app/services/operating_point_generator_service.py:1033-1039`

```python
def _clear_existing_op_sets(db: Session, aircraft: AeroplaneModel) -> None:
    db.query(OperatingPointSetModel).filter(...).delete(synchronize_session=False)
    db.query(OperatingPointModel).filter(OperatingPointModel.aircraft_id == aircraft.id).delete(
        synchronize_session=False
    )
```

It runs when a *new* set is generated for a **still-existing** aircraft. The
per-row deletes at `app/api/v2/endpoints/operating_points.py:362` and `:445` are
explicit user actions.

**Empirical confirmation** — read-only query against the working database
(`db/test.db`, opened `mode=ro`):

```
select count(*) from operating_points
 where aircraft_id is not null
   and aircraft_id not in (select id from aeroplanes);
→ 22          (of 165 rows total)
```

13 % of the operating-point table is already orphaned.

**Verdict:** **confirmed defect** — no `ondelete`, no ORM cascade, no service
cleanup, no FK enforcement, and 22 live orphans in the user's own database.
Residual decision: `ondelete="CASCADE"` on the column vs. a `relationship(...,
cascade="all, delete-orphan")` on `AeroplaneModel` (the latter would also make
the clone-coverage test see the table, per Q-VS-4 / Q-CC-7); either way a
one-off data migration is needed to clear the existing 22.

---

## M — `Q-CG-4`: what would supply the wing schema pickle at hook time?

**Everything the hook needs already exists, in the same repo, in four lines. The
TODO's two stated blockers are both already solved elsewhere in the same module.
The one genuinely open item is the geometry hash.**

The TODO:

`app/services/tessellation_hooks.py:51-55`

```python
# See GH #202: Trigger background re-tessellation.
# This requires re-loading the wing schema from the DB, pickling it,
# and calling tessellation_service.trigger_background_tessellation().
# Deferred because it needs a separate DB session factory and careful
# wiring into the wing service to obtain the wing schema pickle.
```

The signature it would have to satisfy:

`app/services/tessellation_service.py:240-247`

```python
def trigger_background_tessellation(
    aeroplane_id: str,
    wing_name: str,
    wing_schema_pickle: bytes,
    db_session_factory: Callable[[], Any],
    geometry_hash: str,
    wing_scale: float = 1000.0,
) -> None:
```

Argument by argument:

| Argument | Available at hook time? | Source |
|---|---|---|
| `aeroplane_id` | yes | the hook's own `aeroplane_uuid` param (`tessellation_hooks.py:19`) |
| `wing_name` | yes | the hook's own `wing_name` param (`:20`) |
| `wing_schema_pickle` | **yes — 4 lines, already written** | see below |
| `db_session_factory` | **yes — already used inside the same module** | `SessionLocal` |
| `geometry_hash` | **no producer exists** | see below |
| `wing_scale` | yes | defaults to `1000.0` |

**The pickle.** It is a pure function of `(db, aeroplane_id, wing_name)` — exactly
the hook's three arguments — and the code is already written, in the endpoint
that starts a manual tessellation:

`app/api/v2/endpoints/cad.py:161-170`

```python
import pickle
aeroplane_id_str = str(aeroplane_id)
aeroplane = cad_service.get_aeroplane_with_wings(db, aeroplane_id)
wing = cad_service.get_wing_from_aeroplane(aeroplane, wing_name)
from app.converters.model_schema_converters import wing_model_to_asb_wing_schema
wing_schema = wing_model_to_asb_wing_schema(wing)
wing_schema_pickle = pickle.dumps(wing_schema)
```

**The session factory.** `tessellation_service` already imports and uses
`SessionLocal` for precisely this purpose — the done-callback of the *existing*
task path opens its own session to write the cache:

`app/services/tessellation_service.py:204-215`

```python
from app.db.session import SessionLocal
from app.models.aeroplanemodel import AeroplaneModel
from app.services import tessellation_cache_service as cache_svc

db = SessionLocal()
try:
    aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
    if aeroplane:
        cache_svc.cache_tessellation(db, aeroplane.id, "wing", wing_name, geometry_hash or "manual", ...)
```

So "needs a separate DB session factory" was resolved before the TODO was written.

**The genuinely open item — `geometry_hash`.** `compute_geometry_hash` exists:

`app/services/tessellation_cache_service.py:21-28`

```python
def compute_geometry_hash(wing_or_fuselage_data: dict) -> str:
    canonical = json.dumps(wing_or_fuselage_data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
```

but it has **zero callers** — a grep for it across `app/` (excluding tests) finds
only the two *unrelated* same-named functions,
`app/services/stability_service.py:102` and
`app/services/avl_artefact_service.py:33`, which hash different objects. It takes
a `dict`; what is available at hook time is an ASB wing schema object, so
somebody has to decide the canonical dict form. Consequence today: every cached
wing entry is stored with the literal hash string `"manual"`
(`tessellation_service.py:220`, `geometry_hash or "manual"`), so the background
path's stale-hash discard has nothing meaningful to compare against.

**One real subtlety, not mentioned in the TODO.** The hook runs *inside* the
request transaction — `on_wing_changed(db, aeroplane_id, wing_name)` is called
from ten sites in `app/api/v2/endpoints/aeroplane/wings.py` (`:253`, `:285`,
`:328`, `:354`, `:386`, `:473`, `:501`, `:522`, `:588`, …) with the endpoint's
session, and `get_db()` commits only after the endpoint returns. A worker started
at hook time reads through a *new* session; the 2-second debounce
(`tessellation_service.py:238`, `_DEBOUNCE_SECONDS = 2.0`) makes it very likely
to see the committed state, but that is a timing coincidence, not a guarantee.
Pickling the schema **at hook time** (as the TODO proposes) sidesteps it — the
worker never re-reads the DB for geometry — which is an argument for doing it
that way rather than passing IDs.

**Verdict:** **the wiring is small — roughly 6 lines plus one decision.** Both
blockers named in the TODO are already solved in the same module; the only real
open item is defining the dict that feeds `compute_geometry_hash`
(`app/services/tessellation_cache_service.py:21`), which today has no producer at
all. **Still needs a decision** on whether #202 is wanted (product), but not on
whether it is hard.

---

## N — `Q-MC-6`: does any `request=None` path dereference `request`?

**No. All three are guarded. Confirmed safe today.**

Three MCP tools pass `request=None`:

| Tool | MCP line | Endpoint |
|---|---|---|
| `download_export_zip` | `app/mcp_server.py:1034` | `cad.download_aeroplane_zip` |
| `analyze_alpha_sweep_diagram` | `app/mcp_server.py:1114` | `aeroanalysis.analyze_airplane_alpha_sweep_diagram` |
| `get_aeroplane_three_view` | `app/mcp_server.py:1149` | `aeroanalysis.get_aeroplane_three_view_url` |

Every dereference sits behind the same ternary:

`app/api/v2/endpoints/cad.py:399-400`

```python
base_url = str(request.base_url).rstrip("/") if request else settings.base_url.rstrip("/")
base_url = base_url if base_url != "apiserver" else settings.base_url.rstrip("/")
```

`app/api/v2/endpoints/aeroanalysis.py:69-71`

```python
def _resolve_base_url(request: Request | None, settings: Settings) -> str:
    base_url = str(request.base_url).rstrip("/") if request else settings.base_url.rstrip("/")
    return base_url if base_url != "apiserver" else settings.base_url.rstrip("/")
```

- `analyze_airplane_alpha_sweep_diagram` uses it directly
  (`app/api/v2/endpoints/aeroanalysis.py:322`).
- `get_aeroplane_three_view_url` passes `request` into
  `_save_png_and_get_static_url` (`:390`), which calls the same helper (`:88`).

Note that `request` is typed `Request | None` in both helpers, so the contract is
explicit rather than accidental — and `app/api/v2/endpoints/airfoils.py:199-201`
contains a third, identical copy of `_resolve_base_url`. The `settings` fallback
(`settings.base_url`) is what MCP consumers actually get.

### Bonus — a different, confirmed defect on the same path

`download_export_zip` calls its endpoint with **three required arguments
missing**:

`app/mcp_server.py:1030-1036`

```python
payload = await _call_endpoint(
    cad.download_aeroplane_zip,
    aeroplane_id=aeroplane_id,
    request=None,
    settings=get_settings(),
)
```

`app/api/v2/endpoints/cad.py:379-386`

```python
async def download_aeroplane_zip(
    aeroplane_id: str,
    wing_name: str,
    creator_url_type: str,
    exporter_url_type: str,
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request = None,
) -> ZipAssetResponse:
```

`_call_endpoint` injects only `db` (and only if the signature has it) and then
calls `endpoint_fn(**call_kwargs)` with no try/except
(`app/mcp_server.py:96-107`), so `wing_name`, `creator_url_type` and
`exporter_url_type` are simply absent → `TypeError` before `request` is ever
touched. **The `download_export_zip` MCP tool cannot succeed.** That is an
independent finding, not part of Q-MC-6, but it lives in the same three lines and
is exactly the class of latent break the question worries about — arriving via
the *arguments*, not the `Request`.

**Verdict:** `request=None` is **confirmed safe** on all three paths (typed
`Request | None`, guarded with a `settings.base_url` fallback). Residual
decision: whether to pin it with a test — worth it, since nothing else detects a
regression. Separately, **confirmed defect**: `download_export_zip`
(`app/mcp_server.py:1030-1036`) omits three required endpoint arguments and
raises `TypeError` on every invocation.

---

## O — `Q-MB-11`: `print_resolution_mm` — node field or material spec?

**A material spec. Not a component-tree node field.** Both cited lines confirm it,
in the same direction.

It is declared as a field in the `3d_print_material` **component-type schema**:

`app/services/component_type_service.py:335-353`

```python
"description": "3D-print material with density and print type",
"schema": [
    {"name": "density_kg_m3", "label": "Dichte", "type": "number", "unit": "kg/m³",
     "required": True, "min": 100, "max": 20000},
    {"name": "print_resolution_mm", "label": "Druckauflösung", "type": "number",
     "unit": "mm", "min": 0.05, "max": 2.0, "default": 0.4},
    {"name": "print_type", "label": "Drucktyp", "type": "enum",
     "options": ["volume", "surface"], "default": "volume"},
```

and it is read off the **linked material component's `specs`**, never off the
node:

`app/services/component_tree_service.py:446-456`

```python
material = db.query(ComponentModel).filter(ComponentModel.id == node.material_id).first()
if not material:
    return None
specs = material.specs or {}
density = specs.get("density_kg_m3")
if not density:
    return None
if node.print_type == "surface" and node.area_mm2 is not None:
    resolution = specs.get("print_resolution_mm", 0.4)
    return node.area_mm2 * resolution * density / 1e6 * node.scale_factor
```

The distinction the spec must make is visible in that one expression:
`node.print_type` **is** a node column
(`app/models/component_tree.py:60`, `print_type = Column(String, nullable=True)`
— `"volume"` or `"surface"`), while `print_resolution_mm` is a key in
`material.specs`. `print_resolution_mm` appears nowhere in `app/models/`.

Note the default is written **twice**: `"default": 0.4` in the type schema
(`component_type_service.py:352`) and the literal `0.4` fallback in
`specs.get("print_resolution_mm", 0.4)`
(`component_tree_service.py:454`) — two hand-maintained copies of one constant.

**What the spec should say:** *`print_resolution_mm` is an optional spec of the
`3d_print_material` component type (unit mm, range 0.05–2.0, default 0.4). It is
read from the material component linked by `component_tree.material_id`, and it
enters the weight calculation only for nodes whose own `print_type` column is
`"surface"`, as `weight_g = area_mm2 × resolution_mm × density_kg_m3 / 1e6 ×
scale_factor`. Volume-printed nodes ignore it entirely.*

**Verdict:** **confirmed safe** — material spec, not a node field; the only
node-level field in this calculation is `print_type`. Minor cleanup available:
the `0.4` default exists in two places.

---

## P — `Q-FW-8`: is `metricsMock.ts` still referenced?

**No. Zero imports — from production, from tests, from e2e. It is dead, and
dependency-cruiser cannot see it.**

The file: `frontend/components/workbench/metrics-dashboard/metricsMock.ts`,
148 lines.

A grep for `metricsMock` across all `.ts`/`.tsx` outside `node_modules` returns
**four** hits, and every one is a **comment**:

| File | Line | Text |
|---|---|---|
| `frontend/components/workbench/metrics-dashboard/metricsTypes.ts` | 2 | `// Extracted from metricsMock.ts so app code (MetricsDashboard, primitives,` |
| `frontend/lib/metricsAdapters.ts` | 8 | `* metricsMock.ts so the visual appearance stays identical after live wiring.` |
| `frontend/lib/metricsAdapters.ts` | 218 | `// in metricsMock for a ~10% target).` |
| `frontend/lib/metricsAdapters.ts` | 257 | `// Fixed gauge zone definitions — mirrors metricsMock.ts exactly so the` |

No `import` statement anywhere. Separate greps over `frontend/__tests__/` and
`frontend/e2e/` return nothing.

Its own header claims otherwise, and the claim is stale:

`frontend/components/workbench/metrics-dashboard/metricsMock.ts:1-11`

```ts
// Click-dummy (#881): hardcoded representative data for the metrics dashboard.
// No backend wiring — every value here is fake but plausible for a small electric glider.
//
// Types live in metricsTypes.ts; re-exported here so existing test imports remain valid.

import type {
  SpeedData, BalanceData, GaugeData, MetricItem,
} from "./metricsTypes";
```

There are no remaining test imports to keep valid.

**Why `deps:check` does not flag it:** dependency-cruiser's `no-orphans` rule
requires a module to have neither incoming *nor* outgoing dependencies. This file
still imports `./metricsTypes`, so it is invisible to the rule — which is why it
does not appear in the 5-orphan list in §B despite being unreachable. The
`no-orphans` info list is therefore an *undercount* of dead frontend modules.

**Verdict:** **confirmed dead code** — safe to delete outright (`P-DEAD-0`); its
types already live in `metricsTypes.ts` and its gauge-zone values are duplicated
into `frontend/lib/metricsAdapters.ts:257`. No residual decision on the facts;
the only decision is whether the duplicated zone literals should be re-homed
rather than left mirrored by comment.

---

## Q — `Q-CP-5`: does stock snapping run whenever a DB session is present?

**Confirmed — and `wave2-lookups.md` §C.3 is accurate.** Both production entry
points pass a real session, so snapping always runs in production.

`app/services/spar_plan_service.py:573-585`

```python
# gh-1080: snap every piece to the lightest adequate real stock from the
# Component Library (W_stock(Da,Di) ≥ erf_W; minimum ρ·A objective).
# Pass the combined station list so the band filter can reject stock that
# won't fit the printed channel at the governing station.
# Only when a real DB session is provided (fast tests patch the solver
# boundary and may pass db=None to skip).
if db is not None:
    all_stations = list(front_right) + list(rear_right)
    apply_stock_snap_to_plan(db, plan, stations=all_stations)

return plan
```

This is inside `compute_spar_plan_object`
(`app/services/spar_plan_service.py:497-502`), whose docstring names it the
*"Shared core of `compute_spar_plan` (gh-1031) and the spar-insert service
(gh-1049)"* (`:505-506`). `db` is a **required positional parameter with no
default**, so no caller can omit it accidentally.

The two callers, both with the request-scoped session:

| Caller | Line | Session |
|---|---|---|
| `compute_spar_plan` | `app/services/spar_plan_service.py:600` | forwarded from the endpoint |
| `spar_insert_service` | `app/services/spar_insert_service.py:460` | forwarded from the endpoint |

and `compute_spar_plan`'s single HTTP entry point:

`app/api/v2/endpoints/aeroanalysis.py:520,535`

```python
db: Annotated[Session, Depends(get_db)],
...
return spar_plan_service.compute_spar_plan(db, aeroplane_id, request)
```

`db=None` appears nowhere in `app/` outside the explanatory comment at
`spar_plan_service.py:578` — it is a test-only affordance.

This closes the loop on §C.3's tube finding: the intermediate under-strength tube
(`Di = 0.6·Da`, ~15 % below required `W`) is **always** repaired before it leaves
the service, because the snapper re-derives `erf_W = outer_d³/10`
(`app/services/spar_plan_service.py:208-218`) and only accepts stock with
`W_stock ≥ erf_W` (`:158-162`). §C.3's caveat — *"a re-implementation that omits
stock snapping would ship it"* — stands: the guarantee lives in the snapper, not
in the solver.

**Verdict:** **confirmed safe** — snapping runs on 100 % of production paths.
Therefore only the *persistence* half of Q-CP-5 remains open: whether the plan
(sizing parameters, moment distribution, plan id) should be stored so a committed
spar carries provenance and a re-solve can be diffed. **That half still needs a
decision.**

---

## R — `Q-AV-1`: does AVL emit a genuine convergence indicator?

**Yes — a definite one, but on stdout, not in the stability output file. And the
current code's real behaviour is worse *and* better than the question assumes:
`converged = ("CL" in raw)` is unreachable-false, because a non-converged AVL run
never produces a file at all.**

### R.1 — The documentation

The AVL 3.40 primer describes the failure mode but names no marker:

`Avl/avl_doc.txt:1552-1555`

```
Once all the appropriate constraints are set up, the solution
is executed with the X command.  If the variable/constraint
system is ill-posed, the solution probably will not converge.
```

and warns that unconverged run cases carry stale parameter values
(`Avl/avl_doc.txt:2053-2069`). No output flag is documented. So the answer had to
come from the vendored source.

### R.2 — The source: the marker is exact

`Avl/src/aoper.f:1298-1319` — the Newton loop's convergence test and its failure
branch:

```fortran
C------ convergence check
        DELMAX = MAX( ABS(DAL), ABS(DBE), ABS(DWX*BREF/2.0),
     &                ABS(DWY*CREF/2.0), ABS(DWZ*BREF/2.0) )
        DO K = 1, NCONTROL
          DELMAX = MAX( DELMAX , ABS(DDC(K)) )
        ENDDO
C
        IF(DELMAX.LT.EPS) THEN
         LSOL = .TRUE.
C------- mark trim case as being converged
         ITRIM(IR) = IABS(ITRIM(IR))
         GO TO 191
        ENDIF
C
 190  CONTINUE
      IF(NITER.GT.0) THEN
       WRITE(*,*) 'Trim convergence failed'
       LSOL = .FALSE.
       RETURN
      ENDIF
```

with the tolerance at `Avl/src/aoper.f:935-936`:

```fortran
C---- convergence epsilon, max angle limit (radians)
      DATA EPS, DMAX / 0.00002, 1.0 /
```

So:

- **Exact string: `Trim convergence failed`**, written by `WRITE(*,*)` → **stdout**.
- Criterion: max Newton update over `alpha`, `beta`, the three normalised rates
  and every control deflection `< 2e-5` rad.
- On failure the solution flag `LSOL` is set `.FALSE.`

### R.3 — The consequence, and why it matters here

`LSOL` gates every output command. The `ST` command this wrapper uses is guarded:

`Avl/src/aoper.f:594-611`

```fortran
      ELSE IF(COMAND.EQ.'ST  ') THEN
C------ stability derivatives for forces, moments in stability axes
        IF(LSOL) THEN
         CALL GETFILE(LU,COMARG)
         ...
          CALL DERMATS(LU, USEMRF)
         ...
        ELSE
         WRITE(*,*) '* Execute flow calculation first!'
        ENDIF
```

**Second exact string: `* Execute flow calculation first!`** — also stdout. And
critically: on non-convergence **no stability file is written at all**.

Which means the wrapper never reaches its own convergence inference:

`app/services/avl_runner.py:347-356`

```python
output_path = directory / output_filename
if not output_path.exists():
    stderr_text = stdout_bytes.decode(errors="replace") if stdout_bytes else ""
    raise FileNotFoundError(
        f"AVL didn't produce stability output. Check avl_command and input geometry. "
        f"stderr/stdout hint: {stderr_text[:500]}"
    )
raw = output_path.read_text()
result = parse_stability_output(raw)
```

`app/services/avl_trim_service.py:125-132`

```python
except (FileNotFoundError, RuntimeError) as e:
    logger.error("AVL trim execution failed for aeroplane %s with constraints %s: %s", ...)
    raise InternalError(message=f"AVL trim failed: {e}") from e
```

`InternalError` → **HTTP 500** (`app/main.py:291-293`). So today a trim that
fails to converge is reported to the user as *"AVL trim failed: AVL didn't
produce stability output. Check avl_command and input geometry"* — a 500 that
blames the binary or the geometry for what is actually an ill-posed
variable/constraint system the user can fix.

And therefore:

`app/services/avl_trim_service.py:47`

```python
converged = "CL" in raw  # If AVL produced coefficients, it converged
```

is **unreachable-false** on this path: if the file exists, AVL converged and `CL`
is in it. The `if not trimmed.converged` warning at
`app/services/avl_trim_service.py:136-141` is dead code. The comment happens to
state a true implication — but for the wrong reason, and the flag it produces
carries no information.

**The one way this becomes actively dangerous:** `AVLRunner.__init__` accepts
`working_directory` (`app/services/avl_runner.py:102,109`), and when set, the
directory is reused rather than a fresh `TemporaryDirectory`
(`app/services/avl_runner.py:305-312`). With a reused directory, a stale
`output.txt` from a previous successful run would be read and parsed as the
current result, and `converged = ("CL" in raw)` would return **True** for a run
that printed `Trim convergence failed`. Verified: **no production code passes
`working_directory`** — the only occurrences in `app/services/` are the
declaration and the branch itself — so the exposure is latent, not live.

### R.4 — What should replace the inference

Both markers are on stdout, and **stdout is already captured** — it is bound at
`app/services/avl_runner.py:333` (`stdout_bytes, _ = proc.communicate(...)`) and
currently used only for strip forces (`:362`) and the error hint (`:349`). No new
plumbing is needed: check `stdout_bytes` for `Trim convergence failed` and
`* Execute flow calculation first!`, return convergence as a first-class field,
and map a non-converged trim to a **422** with the AVL message rather than a 500
that blames the binary.

**Verdict:** **confirmed defect, and the fix is available.** AVL does emit a
genuine indicator — the literal `Trim convergence failed` (`Avl/src/aoper.f:1317`,
`EPS = 2e-5` at `:935`) plus `* Execute flow calculation first!` (`:610`) — both
on stdout, which the runner already captures and discards. The current inference
`converged = ("CL" in raw)` (`app/services/avl_trim_service.py:47`) is not
merely weak, it is **inert**: non-convergence suppresses the output file
entirely, so the flag is always `True` and the user gets a misleading 500 from
`app/services/avl_runner.py:350`. RF-34 should be respecified as "parse the
stdout markers", not "strengthen the inference".

---

*Method note: `npm run deps:check` (§B) and the read-only SQLite query (§L) were
executed against the working tree. The `.dat` scan (§E) used a throwaway script
in the session scratchpad, not the repository. No file in the repository was
modified except this document.*
