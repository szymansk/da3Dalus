# Wave-2 lookup answers (Q-AF-3, Q-CP-4, Q-WD-8)

Every claim below was read out of the working tree on `main`. Citations are
`path:line`. Nothing here is inferred from documentation or naming — where a
fact could not be established from the code, that is stated explicitly.

---

## A — `Q-AF-3`: airfoil-suitability confidence tiers

### Answer

**Two tiers. Boundary = `settings.low_re_low_confidence_flag` = `0.85`. It is
literally the same constant as the UI badge/caveat threshold — one setting,
read once, used for both.**

### The tier function

`app/services/suitability_service.py:623-625`

```python
def _conf_tier(item: SuitabilityItem) -> int:
    """Return 0 for confident items (ranked first), 1 for low-confidence."""
    return 0 if item.min_analysis_confidence >= low_conf_flag else 1
```

The function returns exactly `0` or `1` — there is no third bucket, no
"unknown" tier, and no separate handling of a missing confidence value at this
point (a missing value was already coerced to `0.0` upstream, see below), so
every item lands in one of two tiers. The comparison is `>=`, i.e. an item at
exactly `0.85` is **confident** (tier 0).

### The sort

`app/services/suitability_service.py:627-635` — the tier is the primary key in
all three ranking lenses:

```python
if has_mission:
    active_lens = "mission"
    items.sort(key=lambda i: (_conf_tier(i), -(i.mission or 0.0)))
elif has_cruise:
    active_lens = "target_cl_cruise"
    items.sort(key=lambda i: (_conf_tier(i), -(i.target_cl_cruise or 0.0)))
else:
    active_lens = "re_agnostic"
    items.sort(key=lambda i: (_conf_tier(i), -i.re_agnostic))
```

So BR-C25's `(confidence tier, -score)` description is accurate, and the tier is
lens-independent.

### Same constant as the badge threshold — confirmed

`low_conf_flag` is bound once per request at
`app/services/suitability_service.py:256`:

```python
low_conf_flag = settings.low_re_low_confidence_flag
```

and the same local is used for the per-item badge/caveat at
`app/services/suitability_service.py:537-543`:

```python
if min_conf < low_conf_flag:
    recommend_xfoil = True

# Per-item caveat
item_caveat = ""
if min_conf < low_conf_flag:
    item_caveat = "Low analysis confidence — validate with XFoil."
```

The setting itself is defined at `app/settings.py:100`:

```python
# Flag threshold: any item with min_analysis_confidence < flag → caveat.
low_re_low_confidence_flag: float = 0.85
```

Note there is a **second, different** confidence constant nearby that is *not*
the tier boundary: `low_re_confidence_gate: float = 0.90`
(`app/settings.py:98`), which gates which NeuralFoil metrics are accepted during
the backfill. Do not confuse the two — `0.90` never reaches the ranking sort.

Missing confidence is coerced to `0.0` before the tier is computed
(`app/services/suitability_service.py:534-536`), so an item with no polar data
deterministically lands in tier 1 rather than raising.

**Verdict for the spec:** BR-C25 can be stated as *two* tiers with the boundary
`min_analysis_confidence >= 0.85` (inclusive), sourced from the single setting
`low_re_low_confidence_flag`, shared with the badge.

---

## B — `Q-CP-4`: the real field list of the spar-plan result schema

### The name in the spec does not exist in the backend

**There is no Python class named `SparPlanResult`.** A repo-wide grep over
`app/` and `cad_designer/` (`*.py`) returns zero hits. The backend response
model is **`SparPlanResponse`** (`app/schemas/spar_plan.py:266`).

`SparPlanResult` *is* a real name — it is the **frontend TypeScript interface**
that mirrors the response: `frontend/hooks/useSparPlan.ts:67`. The spec is
citing the client-side name for a server-side contract. Both shapes are
field-for-field identical (9 fields, same names), so the spec's *content* was
right even though the *name* points at the wrong layer.

`app/schemas/spar_plan.py` declares **5 classes**:

| Class | Line | Fields | Direction |
|---|---|---|---|
| `MomentSample` | 20 | 2 | request (nested) |
| `TorsionSample` | 35 | 2 | request (nested) |
| `SparPlanRequest` | 56 | 13 | request |
| `SparPieceOut` | 178 | 18 | response (nested) |
| `SparPlanResponse` | 266 | 9 | response |

Units: the request's moments are N·m; **all lengths in the response are metres**
(`app/schemas/spar_plan.py:5-6, 179`) — the solver core works in millimetres and
the service converts with `_MM_TO_M = 0.001` (`app/services/spar_plan_service.py:32`).

### `MomentSample` — 2 fields (`app/schemas/spar_plan.py:20-32`)

| Field | Type | Default | Constraints |
|---|---|---|---|
| `y_span` | `float` | required (`...`) | `ge=0.0`, `le=1.0` |
| `bending_moment_Nm` | `float` | required (`...`) | none |

### `TorsionSample` — 2 fields (`app/schemas/spar_plan.py:35-53`)

| Field | Type | Default | Constraints |
|---|---|---|---|
| `y_span` | `float` | required (`...`) | `ge=0.0`, `le=1.0` |
| `torsion_moment_Nm` | `float` | required (`...`) | none |

### `SparPlanRequest` — 13 fields (`app/schemas/spar_plan.py:56-175`)

| # | Field | Type | Default | Constraints | Line |
|---|---|---|---|---|---|
| 1 | `material_id` | `int` | required (`...`) | none | 73 |
| 2 | `moments` | `list[MomentSample]` | required (`...`) | `min_length=1` | 80 |
| 3 | `wing_name` | `Optional[str]` | `None` | none | 88 |
| 4 | `front_x_over_chord` | `Optional[float]` | `None` | `gt=0.0`, `lt=1.0` | 92 |
| 5 | `rear_x_over_chord` | `float` | `0.65` | `gt=0.0`, `lt=1.0` | 101 |
| 6 | `n_span` | `int` | `6` | `ge=2`, `le=200` | 107 |
| 7 | `packing_factor` | `float` | `0.8` | `gt=0.0`, `le=1.0` | 113 |
| 8 | `safety_factor_j` | `float` | `1.5` | `gt=0.0` | 122 |
| 9 | `sigma_allow_mpa_override` | `Optional[float]` | `None` | `gt=0.0` | 127 |
| 10 | `torsion_moments` | `Optional[list[TorsionSample]]` | `None` | none (no `min_length`) | 135 |
| 11 | `rear_secondary_bending_fraction` | `float` | `0.0` | `ge=0.0`, `le=1.0` | 144 |
| 12 | `pitching_moment_proxy_ratio` | `float` | `0.10` | `ge=0.0` (no upper bound) | 154 |
| 13 | `shape` | `Literal["tube", "rod", "rectangular", "capped"]` | `"tube"` | 4 literal members | 166 |

`front_x_over_chord = None` means "use the section's max-thickness location"
(`app/schemas/spar_plan.py:96-99`) — it is not merely an omitted value.

### `SparPieceOut` — 18 fields (`app/schemas/spar_plan.py:178-263`)

| # | Field | Type | Default | Constraints | Line |
|---|---|---|---|---|---|
| 1 | `role` | `str` | required (`...`) | none (**not** a `Literal`; documented values `'front'` / `'rear'`) | 181 |
| 2 | `spare_origin` | `list[float]` | required (`...`) | none (no length constraint; is an (x, y, z) triple) | 182 |
| 3 | `spare_vector` | `list[float]` | required (`...`) | none (unit direction, dimensionless) | 186 |
| 4 | `outer_d` | `float` | required (`...`) | none | 190 |
| 5 | `inner_d` | `float` | required (`...`) | none (`0` for a solid rod) | 191 |
| 6 | `wall` | `float` | required (`...`) | none (`= (outer_d - inner_d)/2`) | 192 |
| 7 | `shape` | `str` | required (`...`) | none (**not** a `Literal` on the response side) | 193 |
| 8 | `governing_y` | `float` | required (`...`) | none | 194 |
| 9 | `x_over_chord` | `float` | required (`...`) | `ge=0.0`, `le=1.0` | 198 |
| 10 | `y_start` | `float` | required (`...`) | none | 209 |
| 11 | `y_end` | `float` | required (`...`) | none | 215 |
| 12 | `utilisation` | `float` | required (`...`) | none — **may exceed 1.0 by design** (see below) | 223 |
| 13 | `joint_to_next` | `Optional[str]` | `None` | none (`'telescoping'` / `'joiner'` / `None`) | 230 |
| 14 | `feasible` | `bool` | `True` | none | 234 |
| 15 | `infeasibility_reason` | `Optional[str]` | `None` | none | 238 |
| 16 | `width` | `Optional[float]` | `None` | none (documented: rectangular only) | 243 |
| 17 | `height` | `Optional[float]` | `None` | none (documented: rectangular only) | 249 |
| 18 | `cap_width` | `Optional[float]` | `None` | none (documented: capped only) | 257 |

Two behavioural notes a re-implementation must preserve:

- `utilisation` is deliberately unclamped: `> 1` signals that no round tube
  strong enough fits the section (`app/schemas/spar_plan.py:226-228`, produced at
  `cad_designer/airplane/geometry/spar_solver.py:499-505`). Adding a `le=1.0`
  would break the contract.
- `width` / `height` / `cap_width` are documented as the rectangular/capped
  dimensions, but **no production code ever assigns them** — see C.3. They are
  always `None` in practice today.

### `SparPlanResponse` — 9 fields (`app/schemas/spar_plan.py:266-321`)

| # | Field | Type | Default | Constraints | Line |
|---|---|---|---|---|---|
| 1 | `front_pieces` | `list[SparPieceOut]` | required (`...`) | none (may be empty — the whole span can be negligible) | 269 |
| 2 | `rear_pieces` | `list[SparPieceOut]` | required (`...`) | none (empty for a single-half surface) | 274 |
| 3 | `front_joint` | `str` | required (`...`) | none (**not** a `Literal`; documented `'continuous'` \| `'reinforcement+joiner'`) | 277 |
| 4 | `rear_joint` | `str` | required (`...`) | none (**not** a `Literal`; documented `'continuous'` \| `'bent-pin'`) | 282 |
| 5 | `reinforcement` | `Optional[SparPieceOut]` | `None` | none | 285 |
| 6 | `feasible` | `bool` | `True` | none | 292 |
| 7 | `infeasibility_reason` | `Optional[str]` | `None` | none | 300 |
| 8 | `front_no_spar_from_y` | `Optional[float]` | `None` | none (metres, starboard half) | 304 |
| 9 | `rear_no_spar_from_y` | `Optional[float]` | `None` | none (metres, starboard half) | 314 |

The response is assembled at `app/services/spar_plan_service.py:602-616`; the
two `*_no_spar_from_y` fields are the only ones that are conditionally scaled
(`* _MM_TO_M` when not `None`).

The four "joint" string values are produced by the solver at
`cad_designer/airplane/geometry/spar_solver.py:643, 645, 652, 659, 661` and the
per-piece joint at `:405` (`"telescoping"` for tubes, `"joiner"` otherwise) and
`:434` (`None` on the last piece).

**Verdict for the spec:** rename `SparPlanResult` → `SparPlanResponse` for the
backend contract (keep `SparPlanResult` only when talking about
`frontend/hooks/useSparPlan.ts`). With the tables above, the response shape is
no longer a re-implementation blocker.

---

## C — `Q-WD-8`: four numerically load-bearing spar-sizing facts

### C.1 — `moment_fn` provenance and whether `g_limit`/`j` are applied twice

**Verdict: applied exactly ONCE. Confirmed safe — no ~4.5× oversizing.**

**Producer.** The bending-moment distribution comes from
`app/services/spanwise_loads.py`, driven by
`analysis_service.analyze_airplane_spanwise_loads`
(`app/services/analysis_service.py:1987`), exposed as
`GET/POST /aeroplanes/{id}/spanwise_loads`
(`app/api/v2/endpoints/aeroanalysis.py:438-462`).

**Load case.** It is a plain aerodynamic integration of the Trefftz-plane strip
forces at the *resolved operating point* — no manoeuvre factor anywhere:

`app/services/spanwise_loads.py:58, 70`

```python
lifts = [q * float(s["Area"]) * float(s["cl"]) for s in strips_outboard_first]
...
bm = sum(lifts[k] * (ys[k] - y_j) for k in range(j + 1))
```

with `q` computed straight from the operating-point atmosphere and velocity at
`app/services/analysis_service.py:2052-2053`:

```python
rho = float(atmosphere.density())
q_dyn = 0.5 * rho * float(resolved_op.velocity) ** 2
```

There is no `g_limit` and no `safety_factor_j` anywhere in
`app/services/spanwise_loads.py` (the module has no such identifiers). So the
distribution handed out is the **un-factored M(y) at the requested α/V** — call
it the 1-solution aero moment, not a design moment.

**The client passes it through unfactored.** The frontend maps the loads result
into `MomentSample`s using only `Math.abs`:

`frontend/lib/sparPlanHelpers.ts:38-41`

```ts
return entries.map((e) => ({
  y_span: Math.min(1, Math.max(0, Math.abs(e.y_m) / maxY)),
  bending_moment_Nm: Math.abs(e.bending_moment_Nm),
}));
```

**The spar-plan pipeline factors it once.** `_make_moment_fn` only sorts,
absolutes and interpolates — no factor:

`app/services/spar_plan_service.py:372-375`

```python
samples = sorted(request.moments, key=lambda m: m.y_span)
ys = [s.y_span for s in samples]
ms = [abs(s.bending_moment_Nm) for s in samples]
return _make_interpolator(ys, ms)
```

The single application happens at the geometry seam:

`cad_designer/airplane/geometry/spar_solver.py:730-734`

```python
m_design = abs(moment_fn(y_span)) * g_limit * safety_factor_j
erf_w = required_section_modulus(m_design, sigma_allow_mpa)
# strength OD as the minimum solid-rod diameter meeting required W.
sol = solve_dimension(shape="rod", erf_w=erf_w, outer_mm=max(band_hi - band_lo, 1.0))
required_od = float(sol["solved_mm"]) if sol["solved_mm"] else 0.0
```

`g_limit` and `safety_factor_j` are threaded in from
`app/services/spar_plan_service.py:543-556` (`common` dict), with `g_limit`
resolved from design assumptions (default `3.0`,
`app/services/spar_plan_service.py:36, 324-336`) and `safety_factor_j` from the
request (default `1.5`).

**Is it applied a second time downstream?** No.
`cad_designer/airplane/geometry/spar_solver.py:33` imports only
`required_section_modulus` and `solve_dimension` from `app.services.spar_sizing`
— it never calls `compute_spar_sizing`. Everything the solver does afterwards
works off `StationData.required_od`, and where it needs the load again it
*inverts* the already-factored OD rather than re-factoring:

`cad_designer/airplane/geometry/spar_solver.py:480-487`

```python
def required_section_modulus_from_od(od: float) -> float:
    """Section modulus a solid rod of diameter ``od`` provides (mm³)."""
    return od**3 / 10.0
```

The *other* `g_limit * safety_factor_j` in the codebase —
`app/services/spar_sizing.py:315` (`m_design = abs(bm) * g_limit * params.safety_factor_j`)
inside `compute_spar_sizing` — belongs to the **separate #1008 sizing path**
(`/spanwise_loads_with_sizing`, orchestrated at
`app/services/analysis_service.py:2073-2078`, `2152-2191`). That path is never
entered from the spar plan. Two code paths, one application each.

**Residual risk (not a defect today, but a re-implementation hazard):** the
factoring lives in the *consumer*, and the request schema documents it —
`safety_factor_j` is described as "Safety factor applied to
`M_design = |M|·g_limit·j`" (`app/schemas/spar_plan.py:122-126`). Nothing in the
schema or the service validates that the caller did not already factor
`moments`. A client that posted design moments instead of aero moments would
silently get a `g·j ≈ 4.5×` oversized spar. Worth an explicit spec sentence:
**`moments` must be un-factored aerodynamic M(y) as returned by the
spanwise-loads endpoint.**

---

### C.2 — is `packing_factor` applied twice?

**Verdict: two different quantities in two different code paths. Confirmed
safe.** In the spar-plan path `packing_factor` does **not** enter the strength
sizing at all — it only defines the containment band.

**Application 1 — containment band (spar-plan path).**
`cad_designer/airplane/geometry/spar_solver.py:727-729`

```python
clr = (1.0 - packing_factor) / 2.0 * pt.thickness
band_lo = pt.bottom_z + clr
band_hi = pt.top_z - clr
```

Band depth `= band_hi - band_lo = thickness * packing_factor`. This band is
purely a *geometric containment* limit; it is what `_run_fits` /
`_max_od_for_run` test the candidate OD against
(`cad_designer/airplane/geometry/spar_solver.py:240-260`) and what the stock
snapper uses as `max_od_mm` (`app/services/spar_plan_service.py:221-234`).

**Application 2 — `outer(y)` in the sizing formula — is in the OTHER path.**
`app/services/spar_sizing.py:320-323`

```python
# Outer dimension (mm) = chord (m → mm) · t/c · packing
chord_mm = chord_m * 1000.0
profile_thickness_mm = chord_mm * tc_ratio
outer_mm = profile_thickness_mm * params.packing_factor
```

This line lives inside `compute_spar_sizing`, which — as established in C.1 —
is the #1008 `/spanwise_loads_with_sizing` path and is **never called by
`compute_spar_plan`**. So there is no path on which both lines run against the
same quantity.

**And even the shared call is band-independent.** The spar plan does call into
`spar_sizing.solve_dimension` from the seam, passing the band as `outer_mm`:

`cad_designer/airplane/geometry/spar_solver.py:733`

```python
sol = solve_dimension(shape="rod", erf_w=erf_w, outer_mm=max(band_hi - band_lo, 1.0))
```

But for `shape="rod"` the solved dimension ignores `outer_mm` entirely —
`outer_mm` only decides the *feasibility flag*:

`app/services/spar_sizing.py:158-169`

```python
def _solve_rod(erf_w: float, outer_mm: float) -> dict[str, Any]:
    d = (10.0 * erf_w) ** (1.0 / 3.0)
    if d > outer_mm + 1e-9:
        return {
            "solved_mm": d,
            "feasible": False,
            ...
```

and the caller reads only `solved_mm`, discarding `feasible`
(`cad_designer/airplane/geometry/spar_solver.py:734`). Therefore
`required_od = (10·erf_W)^(1/3)` is **completely independent of
`packing_factor`**; the packing factor influences only the later containment
test, which is a genuinely different quantity (does the strength-required tube
*fit*, vs how big must it *be*).

Summary of the two roles, both legitimate:

| Where | Expression | Quantity |
|---|---|---|
| `spar_solver.py:727` | `clr = (1 - packing)/2 * thickness` → band depth `= thickness · packing` | geometric room available |
| `spar_sizing.py:323` (other path) | `outer_mm = thickness · packing` | the fixed outer dimension the free dimension is solved against |

---

### C.3 — rod-equivalent OD for every shape

**Verdict: confirmed — every station's `required_od` is solved as a solid rod
regardless of the requested `shape`. Strength-wise conservative; but for
`rectangular` and `capped` it is a confirmed contract defect — those shapes
never receive their own dimensions and are emitted as solid round rods.**

**The rod solve is unconditional.** `cad_designer/airplane/geometry/spar_solver.py:733`
hard-codes `shape="rod"`; the user's `request.shape` is not in scope in
`build_stations_from_geometry` at all (its signature,
`cad_designer/airplane/geometry/spar_solver.py:681-692`, has no `shape`
parameter). The requested shape only reaches the solver later, via `SparSpec`
(`app/services/spar_plan_service.py:561-562`). So `required_od` is always
`d = (10·erf_W)^(1/3)` (`app/services/spar_sizing.py:159`), the minimum solid
round diameter meeting `W = d³/10` (`app/services/spar_sizing.py:57-62`).

**What that means per shape.**

*rod* — exact. The piece is what was sized. `inner_d = 0` because bore
propagation is tube-only (`cad_designer/airplane/geometry/spar_solver.py:381-396`).

*tube* — the OD is inherited from the rod solve and the bore is then solved for
that OD. Note that this bore solve can never succeed on its own terms: with
`erf_w = od³/10` and `outer_mm = od`, the tube discriminant
(`app/services/spar_sizing.py:137`) is
`od⁴ − 32·(od³/10)·od/π = od⁴·(1 − 3.2/π) ≈ −0.0186·od⁴ < 0` for every `od > 0`,
so `_bore_for` always takes its documented fallback branch
(`cad_designer/airplane/geometry/spar_solver.py:475-477`, `bore = od · wall_factor`,
`wall_factor = 0.6`, `:92`). A tube of `Di = 0.6·Da` provides
`W = π(Da⁴−Di⁴)/(32·Da) ≈ 0.0854·Da³`, i.e. ~15 % **below** the required
`0.1·Da³`. This is repaired downstream by stock snapping, which re-derives
`erf_W = outer_d³/10` (`app/services/spar_plan_service.py:208-218`) and only
accepts stock with `W_stock ≥ erf_W` (`app/services/spar_plan_service.py:158-162`).
Stock snapping runs whenever a DB session is present
(`app/services/spar_plan_service.py:579-583`), which covers both production
entry points (`compute_spar_plan` and `spar_insert_service.py:460`). So the
under-strength tube is an intermediate state, not a shipped one — but a
re-implementation that omits stock snapping would ship it.

*rectangular / capped* — **confirmed defect.** `_piece_from_run_with_od`
(`cad_designer/airplane/geometry/spar_solver.py:490-529`) constructs `SparPiece`
without ever setting `width`, `height` or `cap_width`, so they keep their
dataclass defaults of `None` (`cad_designer/airplane/geometry/spar_solver.py:118-120`).
A repo-wide grep for assignments to `piece.width` / `piece.height` /
`piece.cap_width` in `app/` and `cad_designer/` returns nothing. The consequence
chain:

- the piece carries `shape="rectangular"` but `outer_d` = the *rod* diameter and
  `inner_d = 0` (bores stay zero for non-tube shapes,
  `cad_designer/airplane/geometry/spar_solver.py:396`);
- `_piece_to_out` passes the three dims through as `None`
  (`app/services/spar_plan_service.py:491-493`);
- stock snapping treats it as solid and snaps it to solid **round** stock
  (`app/services/spar_plan_service.py:131, 141`);
- CAD insertion writes it as a square/round section of side `outer_d`:
  `spare_support_dimension_width = spare_support_dimension_height = float(piece.outer_d)`
  (`cad_designer/airplane/geometry/spar_cad_insertion.py:62-64`, `91-92`).

Strength-wise this is **not unsafe** — the delivered member has exactly the
required `W = d³/10` for the design moment — but it is not the requested
cross-section, it is heavier than a properly sized rectangular/capped spar of the
same band depth, and `SparPlanResponse.shape` reports a shape the returned
dimensions do not describe. The `rectangular` and `capped` members of the
`shape` `Literal` (`app/schemas/spar_plan.py:166`) are therefore **accepted but
not implemented end-to-end** in the plan path.

---

### C.4 — `_MIN_REAR_X_C = 0.05` vs hinge clearance

**Verdict: two findings. (a) The floor *can* place the rear spar inside the
control surface — confirmed defect in the function. (b) More importantly, the
guard is never invoked in production — confirmed dead code, needs a design
decision.**

**(a) The expression.** `cad_designer/airplane/geometry/spar_solver.py:217-221`

```python
if control_surface_hinge_x_c is None:
    return requested_x_c
limit = control_surface_hinge_x_c - clearance
safe = min(requested_x_c, limit)
return max(safe, _MIN_REAR_X_C)
```

with `_REAR_CLEARANCE_FRACTION = 0.03` (`:184`) and `_MIN_REAR_X_C = 0.05`
(`:188`).

The final `max(..., _MIN_REAR_X_C)` is applied **after** the hinge clamp and is
unconditional, so it can override the clamp. Worked cases:

| `hinge_x_c` | `limit = hinge − 0.03` | returned `x_c` | spar behind the hinge? |
|---|---|---|---|
| 0.75 | 0.72 | 0.72 | no |
| 0.10 | 0.07 | 0.07 | no |
| 0.08 | 0.05 | 0.05 | no — exactly on the clearance line |
| 0.07 | 0.04 | **0.05** | **yes — 0.05 > 0.07 − 0.03, but still forward of 0.07** → inside the clearance band, not yet inside the surface |
| 0.04 | 0.01 | **0.05** | **yes — 0.05 > 0.04, the spar is inside the control surface** |

So the precise boundary is: the clearance is *eroded* as soon as
`hinge_x_c < 0.08`, and the spar is placed **inside** the movable surface as soon
as `hinge_x_c < 0.05`. The existing test suite documents the erosion case but not
the overlap case — `cad_designer/tests/test_spar_clearance_and_secondary.py:56`
asserts `rear_spar_x_c_with_clearance(0.5, control_surface_hinge_x_c=0.02, clearance=0.10)`
returns the `0.05` floor, i.e. the behaviour where the spar ends up behind a
0.02 hinge is currently *asserted as correct*. Whether that is acceptable is a
design decision: a hinge below 5 % chord is not a normal trailing-edge control
surface, so the real question is whether that input should be rejected (or
flagged infeasible) rather than silently floored.

**(b) The guard is never reached from production code.** `build_stations_from_geometry`
takes `control_surface_hinge_x_c: float | None = None`
(`cad_designer/airplane/geometry/spar_solver.py:691`) and only applies the clamp
when it is not `None` (`:708-709`). The only two production call sites are
`app/services/spar_plan_service.py:551-556`:

```python
front_right = build_stations_from_geometry(
    geometry, x_c=request.front_x_over_chord, moment_fn=front_moment_fn, **common
)
rear_right = build_stations_from_geometry(
    geometry, x_c=request.rear_x_over_chord, moment_fn=rear_moment_fn, **common
)
```

with `common` defined at `app/services/spar_plan_service.py:543-549` as exactly
`sigma_allow_mpa`, `n_span`, `packing_factor`, `safety_factor_j`, `g_limit` — no
hinge. A repo-wide grep for `control_surface_hinge_x_c` outside the solver module
returns **only test files**
(`cad_designer/tests/test_spar_clearance_and_secondary.py:38, 43, 47, 51, 56, 60, 91`).
Nothing reads a `TrailingEdgeDevice` hinge line and feeds it in.

Consequence: today the rear spar is placed at `request.rear_x_over_chord`
(default `0.65`, `app/schemas/spar_plan.py:101`) with **no** control-surface
awareness at all. On a wing with a flap or aileron hinged forward of 0.65c the
computed rear spar lands inside the movable surface — a much larger hole than
the `_MIN_REAR_X_C` edge case. The gh-1059 guard exists and is unit-tested, but
is not wired into the pipeline it was written for.

---

## Verdict summary for C

1. **`moment_fn` provenance / double factoring — confirmed safe.** `g_limit · j`
   is applied exactly once, at `cad_designer/airplane/geometry/spar_solver.py:730`;
   the producer (`app/services/spanwise_loads.py`) emits un-factored aero M(y),
   and the second `g·j` in `app/services/spar_sizing.py:315` belongs to a
   disjoint code path. (Spec should state the un-factored input contract
   explicitly.)
2. **`packing_factor` twice — confirmed safe.** Two different quantities:
   containment band (`spar_solver.py:727`) vs. the fixed outer dimension in the
   #1008 path (`spar_sizing.py:323`). In the spar-plan path `packing_factor` does
   not affect `required_od` at all, because `_solve_rod` ignores `outer_mm`.
3. **Rod-equivalent OD for all shapes — confirmed defect (contract), strength-conservative.**
   `spar_solver.py:733` always solves a rod; `rectangular` / `capped` never get
   `width` / `height` / `cap_width` (never assigned anywhere) and are shipped as
   solid round rods that are strength-adequate but heavier and mislabelled.
4. **`_MIN_REAR_X_C` vs hinge clearance — confirmed defect + needs a design decision.**
   `max(safe, 0.05)` (`spar_solver.py:221`) erodes the clearance for
   `hinge_x_c < 0.08` and places the spar inside the surface for
   `hinge_x_c < 0.05`; and separately, `control_surface_hinge_x_c` is never
   passed by any production caller, so the whole gh-1059 guard is dead in the
   spar-plan pipeline.
