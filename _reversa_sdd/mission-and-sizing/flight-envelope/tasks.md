# flight-envelope — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker (🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP).
> Parent: [`../tasks.md`](../tasks.md) T-06.
> Contracts: [`../contracts.md`](../contracts.md) §E.

## Prerequisites

- [ ] [`../design-assumptions/`](../design-assumptions/tasks.md): the effective
      values of `mass`, `cl_max` and `g_limit` — the only three assumptions this
      use case consumes.
- [ ] `aero-analysis`: `assumption_computation_context` carrying
      `cl_alpha_per_rad`, `v_md_mps` and `v_min_sink_mps`.
- [ ] `wing-design` / `fuselage-design`: model→schema→ASB converters able to
      report `s_ref` and `b_ref`.
- [ ] [`../operating-point-sweep/`](../operating-point-sweep/tasks.md): the
      `operating_points` rows plotted as markers (optional — the envelope is
      complete without them).
- [ ] Table `flight_envelopes` with a **unique** FK per aeroplane.
- [ ] AeroSandbox is needed **only** for the two reference-geometry lookups;
      every formula below is closed-form and must be covered in the CI fast
      tier (ADR 0015).

## Tasks

- [ ] **T-01 — The manoeuvre envelope, pure.**
  `compute_vn_curve(...)` with the guard
  `mass_kg <= 0 or cl_max <= 0 or wing_area_m2 <= 0 or v_max_mps <= 0 →
  ValueError`, then

  ```
  W = mass·9.81 · V_stall = sqrt(2W/(ρ·S·CL_max)) · V_dive = 1.4·V_max
  CL_min = −0.8·CL_max
  60 evenly spaced V; n⁺ = min(q·S·CL_max/W, g_limit)
                      n⁻ = max(q·S·CL_min/W, −0.4·g_limit)
  every value round(x, 6)
  ```

  - Legacy origin: `app/services/flight_envelope_service.py:283-368`
  - Definition of done: the function imports and runs with **no** DB and **no**
    solver; `g_limit = 3.0` produces nothing above `3.0` or below `−1.2`; both
    arrays have exactly 60 points spanning `V_stall … V_dive`.
  - 🟢 **Decided (`Q-PT-9`):** one shared ISA helper wrapping `asb.Atmosphere`. Previously `ρ` was a fixed sea-level `1.225`, so the flight
    profile's `altitude_m` — which shapes every operating point — does not reach
    the envelope. Either thread the altitude through, or state in the response
    that the envelope is sea-level.
  - 🟡 The corner speed `V_A` is implicit in the `min`/`max`. Consider emitting
    it explicitly.
  - Confidence: 🟢

- [ ] **T-02 — The gust primitives.**

  ```
  _helmbold_cl_alpha(ar)                     = 2π·AR/(AR+2)     (Anderson 6e §5.3)
  _compute_mu_g(m, S, c_mgc, CL_α, ρ, g)     = 2·(W/S)/(ρ·c_mgc·CL_α·g)
  _compute_k_g(μ_g)                          = 0.88·μ_g/(5.3+μ_g)
  _compute_delta_n(ρ, V, CL_α, U, K_g, m, S) = ½·ρ·V·CL_α·U·K_g/(W/S)
  _extract_cl_alpha_from_context(ctx)        → None for absent, non-numeric,
                                               non-finite or ≤ 0
  ```

  - Legacy origin: `:56-155`
  - Definition of done: all five are pure; the `2π` thin-airfoil limit appears
    nowhere; a context value of `"NaN"`, `float("inf")`, `0` or `-1` all yield
    `None`; the docstrings keep their regulatory citations (FAR-25.341(a)(2),
    CS-VLA.333, NACA TN 2964).
  - 🟡 `_compute_k_g` logs the out-of-range `μ_g` **in addition to** the
    structured warning T-03 emits. Drop the log, or demote it to DEBUG.
  - Confidence: 🟢

- [ ] **T-03 — The gust lines and their three warnings.**
  `_build_gust_lines`: `c_mgc = S/b` (**mean geometric**, not the MAC),
  `V_C = V_D/1.4`, `U = 15.24` for `V ≤ V_C` and a linear taper to `7.62` at
  `V_D`, over the same 60 velocities. Emit **one** `GustValidityWarning` before
  the sweep (direction-specific: optimistic below 3, conservative above 200),
  and **at most one** `GustCriticalWarning` per sign, at the first crossing.
  - Legacy origin: `:157-281`
  - Definition of done: `S_ref = 0.30`, `b_ref = 2.0` ⇒ the chord is `0.15`; a
    second crossing adds no second warning; `μ_g = 1.63` yields a validity
    warning carrying the value and both bounds.
  - 🟡 **Deviation to consider:** the negative `GustCriticalWarning` populates
    its `g_limit` field with `−0.4·g_limit`. Rename the field, or add a `sign`
    discriminator.
  - Confidence: 🟢

- [ ] **T-04 — The gust gate: absent, never zeroed.**
  In `compute_vn_curve`: use `cl_alpha_per_rad` when supplied, else derive
  Helmbold from `AR = b_ref²/S_ref` **only when `b_ref` is known**; build the
  lines only when **both** an effective `CL_α` and a `b_ref` exist; otherwise
  leave `gust_lines_positive` / `gust_lines_negative` as **empty lists** with no
  warnings.
  - Legacy origin: `:337-360`
  - Definition of done: an aircraft with no `b_ref` returns empty gust arrays,
    not zero-filled ones; a consumer can distinguish "unknown" from "no load".
  - 🟡 **Deviation required:** the omission is completely silent today. Emit a
    warning (or a `gust_available: false` flag) saying **why** the envelope is
    absent — a missing span, a missing `CL_α`, or a failed geometry conversion.
  - Confidence: 🟢

- [ ] **T-05 — The six KPIs and the confidence ladder.**
  `derive_performance_kpis` producing exactly six entries in order —
  `stall_speed`, `best_ld_speed`, `min_sink_speed`, `max_speed`,
  `max_load_factor`, `dive_speed` — with the three-tier ladder for the two
  speed KPIs, the `max_turn` marker or `g_limit` for the load factor, and
  `round(x, 4)` throughout. `source_op_id` is set **only** on a marker branch.
  - Legacy origin: `:371-530`
  - Definition of done: six entries always; a cold start yields `estimated`;
    with a context, `computed`; the labels and display names are exact; the
    docstring keeps the gh-475 note that the heuristic tier is wrong by up to
    15 % for high-AR airframes.
  - 🟢 **Decided (`Q-MS-7`):** an explicit `role` field replaces name matching. Previously the lookup keys `best_ld`, `min_sink`
    and `max_turn` are matched against `VnMarker.label`, which is the operating
    point's **name** — and the generator never emits those names, so the
    `trimmed` tier is unreachable. Introduce an explicit **role** on the marker
    (mapping `max_range`/`loiter_endurance`/`turn_60` → `best_ld`/`min_sink`/
    `max_turn`, or deriving the roles from the context speeds), and **check
    `marker.status == "TRIMMED"`** before claiming the `trimmed` tier.
  - Confidence: 🟢

- [ ] **T-06 — Markers.**
  `_load_operating_point_markers`: every `operating_points` row of the aeroplane
  with `velocity` non-null and `> 0` becomes a `VnMarker` with
  `name`/`label` from `op.name` (or `"unnamed"`), `status` from `op.status` (or
  `"NOT_TRIMMED"`), and `load_factor` rounded to 4 decimals.
  - Legacy origin: `:589-618`
  - Definition of done: a row with a null velocity is dropped; the marker count
    matches the qualifying rows.
  - 🟢 **Decided (`Q-MS-6`):** persist `n_target` and `cl_trimmed`; place the marker at the real load factor. Previously hard-coded to `1.0`
    with the note *"without stored CL we cannot derive actual load factor"* — so
    `turn_20/40/60` plot on the 1-g line. The generator **does** know
    `n_target` per target; either persist it on the operating point or recover
    it from `xyz_ref`-independent kinematics
    (`n = 1/cos φ` for a bank target). The function already accepts `mass_kg`
    and `wing_area_m2` for exactly this calculation and never uses them.
  - Confidence: 🟢

- [ ] **T-07 — The assumption and geometry shell.**
  `_load_assumptions` returning `{mass, cl_max, g_limit}` with a catalogue
  fallback; `_get_wing_area_m2` (ASB `s_ref`, raising when `≤ 0`);
  `_get_b_ref` (ASB `b_ref`, `None` on failure); `_get_v_max` (profile goal
  else the fallback).
  - Legacy origin: `:538-587`, `:620-634`
  - Definition of done: a missing assumption row yields the catalogue default;
    a wingless aircraft is reported as a user condition (see the deviations
    below); the two ASB conversions are performed **once** and shared.
  - 🟡 **Deviation required:** `_get_v_max` returns a bare `28.0`, while the
    operating-point sweep uses `max(1.35·V_cruise, V_cruise + 8)` for the same
    quantity (BR-MS8). `V_dive`, `max_speed` and `dive_speed` all ride on it —
    unify the two.
  - 🟡 **Deviation required:** "no wings" raises `InternalError` → **500**, and
    a non-positive input raises a `ValueError` the endpoint reports as
    *"Unexpected error"*. Both are cold-start user conditions; the sibling
    matching-chart and field-length endpoints answer **422** with a remediation
    sentence. Do the same here.
  - 🟡 `_get_b_ref` swallows the failure reason with a bare `except`. Log it, and
    feed it into T-04's "why is the gust envelope absent" signal.
  - 🟡 `_load_assumptions` re-implements the catalogue fallback with a
    `try/except NotFoundError` around the UUID-keyed reader — use
    `design_assumptions_service.get_effective_assumption` once
    [`../design-assumptions/`](../design-assumptions/tasks.md) T-04 consolidates
    the two readers.
  - Confidence: 🟢

- [ ] **T-08 — The orchestration and the upsert.**
  `compute_flight_envelope` in the seven documented steps, then an upsert on the
  aeroplane's single row with `vn_curve_json`, `kpis_json`, `markers_json`
  (all `model_dump(mode="json")`), `assumptions_snapshot` and a tz-aware
  `computed_at`.
  - Legacy origin: `:657-755`
  - Definition of done: two computes leave one row with an advanced
    `computed_at`; the snapshot holds the three effective values used.
  - 🟡 **Deviation to decide:** the snapshot records the three assumptions but
    **not** the context version, even though `cl_alpha_per_rad`, `v_md_mps` and
    `v_min_sink_mps` shape the gust lines and two KPIs. Add the context's
    `computed_at` (or a hash) so a stale row is detectable.
  - Confidence: 🟢

- [ ] **T-09 — The read path and its two 404s.**
  `get_flight_envelope` returning `None` for a missing row;
  `GET …/flight-envelope` turning that into a 404 with *"No flight envelope
  computed yet for this aeroplane."*, distinct from the aeroplane-not-found
  404. `_model_to_read` rehydrating `VnCurve` / KPIs / markers from the JSON
  columns and mirroring `vn_curve.gust_warnings` onto the top-level
  `gust_warnings`.
  - Legacy origin: `:636-655`, `:757-767`,
    `app/api/v2/endpoints/aeroplane/flight_envelope.py`
  - Definition of done: the two 404s carry different messages; the mirrored
    warnings are equal to the nested ones.
  - Confidence: 🟢

- [ ] **T-10 — The transport layer.**
  The two routes of [`../contracts.md`](../contracts.md) §E with
  `_raise_http_from_domain` (`NotFoundError` → 404, `InternalError` → 500,
  anything else → 500) and the generic `except Exception` → 500.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/flight_envelope.py:20-82`
  - Definition of done: the POST recomputes unconditionally; the GET never
    computes.
  - 🟡 `ComputeEnvelopeRequest{force_recompute}` exists in the schema module but
    the POST takes no body — delete it or wire it.
  - 🟡 Align the error envelope with whatever
    [`../tasks.md`](../tasks.md) T-17 settles on, and consider mounting this
    router on `NonFiniteSafeJSONResponse` — a NaN `load_factor` is not
    neutralised today.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Manoeuvre caps.** `g_limit = 3.0` ⇒ `max(n⁺) ≤ 3.0` and
      `min(n⁻) ≥ −1.2`; the parabolic branch matches `q·S·CL_max/W` below the
      corner.
- [ ] **TT-02 — Sixty points, endpoints exact.** First velocity `== V_stall`,
      last `== 1.4·V_max`, length 60 on both arrays.
- [ ] **TT-03 — Non-positive inputs raise.** Each of the four guarded arguments
      at `0` and at `−1`.
- [ ] **TT-04 — Purity.** `compute_vn_curve` and `derive_performance_kpis` are
      called with no session and no solver in `sys.modules`.
- [ ] **TT-05 — Geometric chord.** `S_ref = 0.30`, `b_ref = 2.0` ⇒ the `μ_g`
      computation uses `0.15`, not a MAC value (assert via a patched
      `_compute_mu_g`).
- [ ] **TT-06 — Helmbold, not `2π`.** `AR = 8` ⇒ `CL_α ≈ 5.03`; assert the value
      is **not** `6.283`.
- [ ] **TT-07 — Corrupted `CL_α`.** `"NaN"`, `float("nan")`, `float("inf")`,
      `0`, `−1` and a string all fall through to Helmbold.
- [ ] **TT-08 — Gust absent without a span.** `b_ref = None` ⇒ both gust arrays
      empty and no warnings; `b_ref = None` **and** a context `CL_α` ⇒ still
      empty (the chord needs the span).
- [ ] **TT-09 — `U_gust` schedule.** `15.24` at and below `V_C`; `7.62` at
      `V_D`; the midpoint interpolates linearly.
- [ ] **TT-10 — One critical warning per sign.** A polar that crosses twice
      still yields one positive warning; the negative branch likewise.
- [ ] **TT-11 — Validity warning, both directions.** `μ_g = 1.63` ⇒ "optimistic";
      `μ_g = 250` ⇒ "conservative"; both carry the value and the two bounds;
      `μ_g = 50` ⇒ no validity warning.
- [ ] **TT-12 — Six KPIs, exact labels and order.**
- [ ] **TT-13 — Confidence ladder.** No context, no marker ⇒ `estimated` at
      `1.4·V_s` / `1.2·V_s`; with `v_md_mps` ⇒ `computed`; with a
      **TRIMMED** marker ⇒ `trimmed` with `source_op_id` set.
- [ ] **TT-14 — A non-trimmed marker must not claim `trimmed`** (post-T-05
      regression).
- [ ] **TT-15 — `max_load_factor` falls back to `g_limit`** with confidence
      `limit` when no `max_turn` marker exists.
- [ ] **TT-16 — Marker filtering.** Rows with a null or non-positive velocity
      are dropped; `name`/`status` fall back to `"unnamed"`/`"NOT_TRIMMED"`.
- [ ] **TT-17 — Turn markers carry their real load factor** (post-T-06
      regression): a `turn_60` marker reports `2.0`, not `1.0`.
- [ ] **TT-18 — Upsert.** Two computes ⇒ one row, advanced `computed_at`, JSON
      columns replaced.
- [ ] **TT-19 — Snapshot.** Holds the three effective values; a missing
      assumption row records the catalogue default.
- [ ] **TT-20 — Two distinct 404s.** Unknown aeroplane vs no envelope yet, with
      different messages.
- [ ] **TT-21 — GET never computes.** With `compute_flight_envelope` patched to
      raise, the GET on an existing row still succeeds.
- [ ] **TT-22 — Warning mirroring.** `FlightEnvelopeRead.gust_warnings` equals
      `vn_curve.gust_warnings`.
- [ ] **TT-23 — Rounding.** V-n values at 6 dp, KPI values and warning fields at
      4 dp.
- [ ] **TT-24 — `velocity_mps ≥ 0`** is enforced by the schema validator.
- [ ] **TT-25 — Cold-start user conditions are 422** (post-T-07 regression): a
      wingless aircraft and a zero `cl_max` both return 422 with a remediation
      sentence, not 500.
- [ ] **TT-26 — Fast-tier coverage.** Every task above except T-07's two
      geometry lookups runs without AeroSandbox; the lookups are mocked at the
      converter boundary (ADR 0015).

## Data Migration Tasks

- [ ] **TM-01 — `flight_envelopes`.** `id` PK; `aeroplane_id` FK **UNIQUE**,
      INDEXED, `ON DELETE CASCADE`; `vn_curve_json`, `kpis_json`,
      `markers_json`, `assumptions_snapshot` as JSON NOT NULL; `computed_at`
      DateTime(tz) NOT NULL.
      🟡 Consider widening `assumptions_snapshot` to record the context version
      (T-08), and back-filling existing rows with `null` so a stale row is
      identifiable rather than silently trusted.

## Suggested Order

1. **T-01 → T-05** are pure functions — build and test the whole physics layer
   before touching a session.
2. **T-02, T-03, T-04** in that order: the primitives, the line builder, then
   the gate that decides whether to call it.
3. **T-06** (markers) before **T-05**'s marker branches can be tested
   end-to-end, though T-05 itself only needs a list of `VnMarker`.
4. **T-07** (the DB/geometry shell) once the pure layer is green.
5. **T-08 → T-09** (orchestration, read path), then **T-10** (transport).

Blocking edges: T-03 ⇠ T-02 · T-04 ⇠ T-02, T-03 · T-05 ⇠ T-06 (for the marker
branches) · T-08 ⇠ T-01, T-04, T-05, T-06, T-07 · T-09 ⇠ T-08 · T-10 ⇠ T-09.

## Pending Gaps (🔴)

- **Markers are all at 1 g (T-06).** The generator knows `n_target` per target;
  persist it, or recover it from the bank angle. Until then, turn operating
  points plot on the 1-g line.
- **The `trimmed` KPI tier is unreachable (T-05).** The lookup keys `best_ld` /
  `min_sink` / `max_turn` are matched against the operating point's **name**.
  Which mapping is right — a role field on the marker, or matching the context's
  `v_md_mps` / `v_min_sink_mps` to the nearest point?
- **A marker's status is not checked** before the `trimmed` label is applied
  (T-05).
- **Two `V_max` fallbacks (T-07).** `28.0` here, `max(1.35·V_c, V_c + 8)` in the
  sweep. Which is canonical?
- **`ρ` is fixed at sea level (T-01)** while the profile's `altitude_m` shapes
  every operating point.
- **Cold-start conditions are 500s (T-07).** "No wings" and a zero `cl_max`
  should be 422 with a remediation sentence, matching the sibling endpoints.
- **An absent gust envelope is silent (T-04).** The response cannot say whether
  the span, the `CL_α` or the geometry conversion was the missing piece.
- **The snapshot omits the context version (T-08)**, although the gust lines and
  two KPIs derive from it.
- **The negative `GustCriticalWarning.g_limit` field holds `−0.4·g_limit`**
  (T-03).
- **`_compute_k_g` duplicates the structured validity warning in the log**
  (T-02).
- **`ComputeEnvelopeRequest.force_recompute` is dead surface** (T-10).
- **`V_A` is implicit** in the point cloud (T-01) — a consumer that needs the
  corner speed must find the kink numerically.
