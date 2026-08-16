# turbulator-optimizer — Technical Design

> Use-case design, nested under the module [`wing-design`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full module REST contract: [`../contracts.md`](../contracts.md). ADR 0012.

## Interface

### REST surface owned by this use case 🟢

| Method | Path | Operation | Status codes |
|---|---|---|---|
| GET | `/aeroplanes/{id}/wings/{wing_name}/cross_sections/{i}/turbulator` | read the segment's turbulator | 200 · 404 · 500 |
| PUT | `/aeroplanes/{id}/wings/{wing_name}/cross_sections/{i}/turbulator` | upsert the turbulator | 200 · 404 · **422 on the terminal station** · 500 |
| DELETE | `/aeroplanes/{id}/wings/{wing_name}/cross_sections/{i}/turbulator` | delete the turbulator | 200 · 404 · 500 |
| POST | `/aeroplanes/{id}/turbulator/optimize` | per-section trip-location optimisation | 200 · 404 · 422 · 500 |

The optimisation route is aircraft-scoped, not segment-scoped
(`app/api/v2/endpoints/aeroplane/turbulator_optimizer.py:173`).

### Optimiser surface — `app/services/turbulator_optimizer_service.py` 🟢

| Symbol | Value / purpose | Line |
|---|---|---|
| `XTR_GRID` | `linspace(0.2, 0.9, 15)` — the `x/c` sweep | l.53 |
| `_CONFIDENCE_THRESHOLD` | `0.80` — the warning gate | l.56 |
| `_ALPHA_GRID` | `linspace(-4.0, 14.0, 37)` — the α grid for the cd-at-CL lookup | l.60 |
| warning emission | all-NaN, low confidence, boundary optimum | l.223-268, l.294-331 |

### Data model 🟢

`wing_xsec_turbulators` (`WingXSecTurbulatorModel`,
`app/models/aeroplanemodel.py:83`, gh-934):

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `wing_xsec_detail_id` | Integer FK → `wing_xsec_details.id` `ON DELETE CASCADE` | yes | — | **unique** (enforces 1:1) |
| `form` | String | no | `NULL` | `zigzag` \| `dots` \| `thread`; schema default `zigzag` |
| `height_mm` | Float | no | `NULL` | **mm**; schema default `0.3`, constraint `≥ 0` |
| `position_root` | Float | no | `NULL` | x/c 0–1 at the segment root; **required in the schema** |
| `position_tip` | Float | no | `NULL` | x/c 0–1 at the segment tip; **falls back to `position_root`** |
| `enabled` | Boolean | **yes** | `True` | whether it is rendered in CAD |

Schema: `TurbulatorDetailSchema` (`app/schemas/aeroplaneschema.py:233`) —
`position_* ∈ [0, 1]`, `height_mm ≥ 0`.

Topology (the one approved gh-934 exception to ADR 0002):
`Turbulator(position_root, form="zigzag", height_mm=0.3, position_tip=None,
enabled=True)`.

## Main Flow

### F1 — Turbulator upsert (`PUT .../turbulator`) 🟢

1. Resolve the aeroplane, wing and station index (404 if absent).
2. `_assert_non_terminal_xsec_or_raise(wing, i)`
   (`app/services/wing_service.py:151-156`) → **422** when `i` is the terminal
   station: the turbulator is segment-scoped and the terminal station carries
   geometry only.
3. Validate against `TurbulatorDetailSchema`: `position_root` required,
   `position_* ∈ [0, 1]`, `height_mm ≥ 0`; apply the defaults `form = "zigzag"`,
   `height_mm = 0.3`, `enabled = True`.
4. Resolve `position_tip` — when absent it **falls back to `position_root`**,
   giving a strip parallel to the leading edge in `x/c` terms.
5. Upsert the 1:1 `wing_xsec_turbulators` row against the segment's
   `wing_xsec_details`.
6. Return; `get_db()` commits.

### F2 — Per-section optimisation (`POST /turbulator/optimize`) 🟢

For each wing section returned by `section_aoa_service` (**half-span sections
only**):

1. Establish the section's operating point `(CL, Re)`.
2. Compute the natural-transition baseline:

   ```
   cd_clean = cd(CL, Re, xtr_upper = 1.0)
   ```

   `xtr_upper = 1.0` means "no forced transition" — transition happens
   naturally. This is the reference every tripped result is measured against.
3. Sweep the 15-point grid:

   ```
   XTR_GRID    = linspace(0.2, 0.9, 15)
   _ALPHA_GRID = linspace(-4.0, 14.0, 37)     # used to look cd up at the target CL
   ```

   For each grid point, evaluate `cd` at the section's `CL` and `Re` with the
   trip forced at that `x/c`.
4. Select the optimum over **finite** values only — NaN entries are skipped, not
   propagated:

   ```
   i_opt    = argmin over FINITE cd values
   xtr_opt  = XTR_GRID[i_opt]
   delta_cd = cd_tripped − cd_clean          # negative = improvement
   ```

5. Emit warnings (F3) without substituting any value.

### F3 — Warning emission (BR-W15, ADR 0012) 🟢

Three independent conditions, each producing an explicit warning and **no
fallback** (`turbulator_optimizer_service.py:223-268, 294-331`):

| Condition | Test | Reported outcome |
|---|---|---|
| No optimum | every `cd` in the sweep is NaN | warning; **no `xtr_opt`** for that section |
| Low confidence | mean `analysis_confidence < 0.80` (`_CONFIDENCE_THRESHOLD`) | the result **is** returned, plus a confidence warning |
| Boundary optimum | `i_opt ∈ {0, len−1}` | the boundary value **is** reported, plus a warning that the true minimum may lie outside `[0.2, 0.9]` |

The boundary case is deliberately *not* handled by extending the grid — doing so
would hide the fact that the search space was insufficient.

### F4 — Aircraft-level roll-up 🟢

```
ΔCD0 = symmetry_factor · Σ (Δcd_i · S_i) / S_ref

symmetry_factor = 2 for a symmetric wing
                  (section_aoa_service returns half-span sections only)
```

The factor exists precisely because the section list covers one half of the
wing. Applying it to an asymmetric surface, or to an already-full-span section
list, would silently double `ΔCD0` — and the error is undetectable from the
resulting number alone.

## Alternative Flows

- **Unknown aeroplane / wing / station:** `NotFoundError` → **404**.
- **Turbulator write to the terminal station:** `ValidationError` → **422**.
- **`position_root` omitted:** rejected by the schema → **422**.
- **`position_*` outside `[0, 1]` or `height_mm < 0`:** rejected → **422**.
  `height_mm = 0` is legal (a degenerate but valid strip height).
- **`position_tip` omitted:** falls back to `position_root`.
- **`enabled = false`:** the row is retained; the CAD build omits the trip strip.
  This is a toggle, not a delete.
- **Partially NaN sweep:** the argmin is taken over the finite values; a finite
  `xtr_opt` is still returned.
- **Entirely NaN sweep:** warning, no `xtr_opt`, **no fallback**.
- **Mean confidence below 0.80:** the result is returned *with* a warning — it is
  a trust signal, not a rejection.
- **Boundary optimum:** the value is returned *with* a warning; the grid is not
  extended.
- **AeroSandbox / NeuralFoil unavailable (e.g. `linux/aarch64`):** consumers must
  import defensively (ADR 0017). 🔴 What this route returns in that case — a 500,
  an empty result, or a warning — was not captured in the source analysis.

## Dependencies

- **`section_aoa_service` (`aero-analysis`)** — supplies the per-section
  operating `(CL, Re)` and reference areas `S_i`, for **half-span sections
  only**. The `symmetry_factor = 2` in F4 is a direct consequence of that
  convention.
- **NeuralFoil (via AeroSandbox)** — the `cd(CL, Re, xtr_upper)` surrogate and
  the `analysis_confidence` signal that drives the 0.80 gate. Optional heavy
  dependency (ADR 0017).
- **[`../cross-section-crud/`](../cross-section-crud/design.md)** — owns the
  station addressing, the `wing_xsec_details` side table the turbulator hangs
  off, and the terminal-station guard.
- **`cad-generation`** — renders the trip strip when `enabled` is true; consumes
  `form`, `height_mm` and the two positions.
- **`cad_designer` topology (`Turbulator`, `WingSegment`,
  `WingConfiguration`)** — the mm-world representation. gh-934 is the **one
  approved extension** of the otherwise-frozen topology layer (ADR 0002).
- **`app/db/session.py` (`get_db`)** — owns the transaction (ADR 0009).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The trip location is found by a **fixed-grid sweep**, not a continuous optimiser, keeping cost constant and results reproducible | `XTR_GRID = linspace(0.2, 0.9, 15)`, l.53 | 🟢 |
| The baseline is a genuine natural-transition run (`xtr_upper = 1.0`) rather than the first grid point, so `delta_cd` measures real benefit | `cd_clean` definition | 🟢 |
| The argmin ignores non-finite values instead of failing, so a partially failed surrogate sweep still yields an answer | `i_opt = argmin over FINITE cd values` | 🟢 |
| All three anomaly classes become **warnings with the result still returned** (or withheld, for all-NaN) rather than substituted fallbacks | `turbulator_optimizer_service.py:223-268, 294-331`; ADR 0012 | 🟢 |
| A boundary optimum is reported rather than resolved by widening the grid, because widening would hide an inadequate search space | boundary warning at l.294-331 | 🟢 |
| The half-span convention of `section_aoa_service` is compensated by an explicit named `symmetry_factor` rather than being absorbed silently | ΔCD0 roll-up | 🟢 |
| The confidence gate is a **mean** over the section, not a minimum, and is a warning threshold rather than a rejection threshold | `_CONFIDENCE_THRESHOLD = 0.80`, l.56 | 🟢 |
| `enabled` is a stored toggle rather than delete-and-recreate, preserving the configured position across comparisons | `aeroplanemodel.py:83` (`NOT NULL`, default `True`) | 🟢 |
| `position_tip` falls back to `position_root` rather than being required, so the common case needs one number | `TurbulatorDetailSchema`, `aeroplaneschema.py:233` | 🟢 |
| Extending the frozen topology layer was accepted for this one domain object | gh-934 exception to ADR 0002 | 🟢 |

## Internal State

Stateless between requests. The optimiser is a **pure computation** over the
section list and the surrogate — no cache, no persisted intermediate.

Persistent state is only the `wing_xsec_turbulators` row: `form`, `height_mm`,
`position_root`, `position_tip`, `enabled`.

🟢 **The optimiser is compute-only today, and that is confirmed, not assumed**
(`Q-WD-10`): no DB write occurs between `_call_optimizer` and
`_result_to_response` (`turbulator_optimizer.py:184-199`). **Slice 3 adds an
explicit write-back** behind a user "apply" action (`Q-WD-10 ①`), which keeps
the ADR 0007 propose/adopt boundary intact while making the optimum
manufacturable — the position is stored as a fraction of the segment's own root
and tip chord, i.e. the existing `position_root` / `position_tip` pair.

## Observability

- The three warning classes are **response payload content**, not log lines —
  they are part of the contract the UI renders (ADR 0012). 🟢
- `logger.exception` on 5xx via the global handlers; 4xx logged at INFO. 🟢
- No metrics or traces are emitted by this use case. 🟢
- 🔴 The per-section surrogate call count is `15 × sections` plus one baseline
  each, but nothing measures the wall-clock cost of an optimise request, so a
  slow surrogate would be invisible until a timeout. **Not addressed by the
  validation interview**, and under ADR 0024 (single-user desktop) timing
  telemetry has no consumer — left open rather than assumed away.

## Risks and Gaps

- 🟢 **Persistence is confirmed absent today and deliberately added in Slice 3**
  (`Q-WD-10`, `Q-WD-10 ①`). The endpoint is compute-only — verified, not
  inferred — and the write-back arrives behind an explicit "apply" affordance,
  so the propose/adopt boundary is never crossed silently.
- 🟢 **`symmetry_factor` is read, not inferred, and the feared failure mode does
  not occur** (`Q-WD-10`). It is `2.0 if main_wing.symmetric else 1.0`
  (`turbulator_optimizer_service.py:330-331`), with `wing_symmetric` read at both
  call sites from the **largest-planform-area** wing
  (`turbulator_optimizer.py:99-102`, `assumption_compute_service.py:144-148`),
  and ASB's `Wing.symmetric` comes straight from the DB column
  (`model_schema_converters.py:796-806`). The vertical-stabiliser case cannot go
  wrong for two independent reasons: the flag is **read** rather than inferred,
  and the optimiser only ever runs on the largest-area surface. **Verdict:
  confirmed safe / as-specified.**
- 🟡 **Behaviour without AeroSandbox / NeuralFoil** — on `linux/aarch64` the
  surrogate is unavailable (ADR 0017). Per `P-WARN-0` the ADR-0012-consistent
  answer applies: the route reports a declared platform `DesignWarning` rather
  than a 500 or a silently empty result set. Derived from the policy rather than
  decided directly, so INFERRED.
- 🔴 **No cost instrumentation.** `15 × sections + sections` surrogate calls per
  request with no timing signal. Not addressed by the validation interview.
- 🟡 **`height_mm` does not enter the optimisation.** The optimiser sweeps the
  *position* only; the trip height — physically the parameter that determines
  whether transition is actually forced — appears nowhere in the drag model. The
  result is therefore a position optimum conditioned on an unmodelled height.
- 🟡 **`form` does not enter the optimisation either.** `zigzag`, `dots` and
  `thread` have materially different tripping behaviour, but the surrogate call
  takes only an `xtr_upper` location. The stored `form` is a CAD-rendering
  choice that the drag prediction does not see.
- 🟡 **`position_root` / `position_tip` versus a single `xtr_opt`.** The stored
  turbulator supports a **tapered** strip (root and tip positions), while the
  optimiser reports one `xtr_opt` per section. How a per-section optimum maps
  onto a per-segment root/tip pair is not spelled out.
- 🟡 **The columns are nullable while the schema requires `position_root`.** A
  row written outside the API (or a legacy row) can hold `NULL` and would fail
  schema validation on read — the same pattern flagged for `Servo` in
  [`../control-surface-mixing/design.md`](../control-surface-mixing/design.md).
- 🟡 **`_ALPHA_GRID` resolution is fixed at 37 points over `[-4°, 14°]`.** A
  section whose operating `CL` falls outside the `CL` range spanned by that α
  grid cannot be looked up. Whether that surfaces as a NaN (and therefore the
  all-NaN warning) or as a silent clamp was not captured.
