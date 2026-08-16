# control-surface-mixing

> Use-case specification, nested under the module [`wing-design`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: wing-design
> (Control-surface mixing, gh-772), `_reversa_sdd/data-dictionary.md`
> §Module: wing-design, ADR 0008.

## Overview

`control-surface-mixing` owns the trailing-edge device and its **role → control
axis** decomposition (gh-772). A dual-role surface — elevon, flaperon,
ruddervator — is one piece of hardware serving two flight axes, so it must emit
**two** AVL `CONTROL` variables on the same section with opposite duplication
signs. `app/services/control_surface_mixing.py` is the single source of truth
shared by the AVL geometry builder, the AeroSandbox airplane builder and the
trim-enrichment service. 🟢

## Responsibilities

- CRUD for trailing-edge devices (`GET` / `PATCH` / `DELETE`) with role-gated
  mixing validation. 🟢
- CRUD for the TED's 1:1 servo child. 🟢
- Read/patch/delete the ASB `control_surface` projection, plus the CAD-only
  `cad_details` and `servo_details` subsets. 🟢
- Decompose a control-surface **role** into one or two **control axes**. 🟢
- Emit the correct `sgn_dup`, gain, symmetry flag and baseline deflection per
  axis. 🟢
- Generate globally unique control-variable names and **assert** their
  uniqueness before any AVL geometry is written. 🟢
- Keep `differential_ratio` strictly out of the aero/trim solution. 🟢

**Explicitly NOT this use case's responsibility:** the station/segment model and
the unit boundary (→ [`../cross-section-crud/`](../cross-section-crud/requirements.md)),
the spar pipeline (→ [`../spar-sizing/`](../spar-sizing/requirements.md)), the
turbulator (→ [`../turbulator-optimizer/`](../turbulator-optimizer/requirements.md)),
writing the actual `.avl` file (→ `avl-integration`), and running trim
(→ `aero-analysis`).

## Business Rules

> IDs are inherited verbatim from [`../requirements.md`](../requirements.md).

- **BR-9 — A role decomposes into control axes (gh-772).** 🟢 *(module-level
  BR-9; this use case is its owner. ADR 0008.)*

  ```
  _DUAL_ROLE_AXES = { "elevon":      ("pitch", "roll"),
                      "flaperon":    ("lift",  "roll"),
                      "ruddervator": ("pitch", "yaw") }     (control_surface_mixing.py:29-33)

  PRIMARY_AXES   = {"pitch", "lift"}   # symmetric component
  SECONDARY_AXES = {"roll",  "yaw"}    # antisymmetric component
  ```

  A **dual-role** surface emits **two** AVL `CONTROL` variables on the same
  section — AVL sums multiple `CONTROL` lines per section:

  | axis | `sgn_dup` | gain | `symmetric` | baseline deflection |
  |---|---|---|---|---|
  | primary | `+1.0` | `mix_gain_primary` | `True` | the surface's deflection |
  | secondary | `−1.0` | `mix_gain_secondary` | `False` | **`0.0`** |

  The secondary baseline is **0.0** so the AeroBuildup fallback never feeds a
  roll/yaw deflection into the single-axis ASB model
  (`control_surface_mixing.py:126-128`). A **single-axis** role keeps its
  existing tagged name and `±1` sign **verbatim** (l.134-146).
- **BR-10 — `SgnDup` is a sign flag, never a magnitude.** 🟢 Called out
  explicitly in the module docstring (`control_surface_mixing.py:14-15`).
  `differential_ratio` is a **reporting-only kinematic** applied *after* trim for
  left/right display; it never alters the aero or trim solution
  (`app/schemas/aeroplaneschema.py:372-381`).
- **BR-11 — Control-variable names must be globally unique.** 🟢
  `axis_control_name` produces

  ```
  [{role}]{axis}_{wing_key}_{xsec_index}       e.g. [ruddervator]pitch_htail_1
  ```

  (l.76-84). **AVL silently collapses identically named `CONTROL` variables into
  a single DOF** — there is no error, just a wrong answer — so
  `assert_unique_control_names` raises on any duplicate **before** the geometry
  is written (l.149-164).
- **BR-12 — Mixing fields are role-gated.** 🟢
  `differential_ratio ≠ 1.0` is legal only for
  `DIFFERENTIAL_ROLE_VALUES = {aileron, elevon, flaperon, ruddervator}`;
  `mix_gain_secondary ≠ 1.0` only for
  `DUAL_ROLE_VALUES = {elevon, flaperon, ruddervator}`. Comparison uses
  `math.isclose(rel_tol=1e-9, abs_tol=1e-9)`, and a `None` role (a partial
  patch) **skips the check entirely** (`_validate_mix_fields`,
  `app/schemas/aeroplaneschema.py:51-78`). Schema ranges: `mix_gain_*`
  `0 < x ≤ 5`, `differential_ratio` `0.3 < x ≤ 3`.
- **BR-13 — 🟢 This use case owns a resolver that the consumers are REQUIRED to
  call** (`Q-WD-1`, maintainer-answered). The canonical control name is the
  gh-772 mixing name (`axis_control_name`), and `trim_enrichment_service`,
  `retrim_service` and `stability_service` obtain it **through the resolver**
  rather than reconstructing it. **The silent hard-coded ±25° fallback is
  removed.** This is the structural fix for bug #955: keying on the raw DB TED
  name becomes impossible rather than merely discouraged, so the defect cannot
  recur when a fourth consumer is added. Until it lands, a dual-role aircraft
  still reports ±25° limits and a phantom 0° surface.
- **BR-C1 — The TED is the source, `control_surface` is a projection.** 🟢
  *(refines BR-W1.)* `WingXSecModel.control_surface` is a **computed** ASB
  projection over the 1:1 `trailing_edge_device` row
  (`app/models/aeroplanemodel.py:241-276`), not a second stored copy. The
  converter overwrites the x-sec-derived control surface with the TED-derived
  one, otherwise `_merge_ted_with_control_surface` resurrects a phantom TED on
  round-trip (`app/converters/model_schema_converters.py:960-995`).
- **BR-C2 — `role` is mandatory and defaults to `other`.** 🟢
  `wing_xsec_trailing_edge_devices.role` is `NOT NULL` with default `'other'`
  (`app/models/aeroplanemodel.py:147`). A role of `other` is neither dual nor
  differential-capable, so both gates in BR-12 reject a non-unity value on it.
- **BR-C3 — Mixing gains are stored `NOT NULL` with a unity default.** 🟢
  `mix_gain_primary`, `mix_gain_secondary` and `differential_ratio` are all
  required columns defaulting to `1.0` (gh-772), so "no mixing" is representable
  without nulls.
- **BR-C4 — Servo geometry is validated above the topology layer.** 🟡 Every
  `wing_xsec_ted_servos` column is nullable, while the Pydantic `Servo` schema
  makes every dimension a **required `NonNegativeFloat`**
  (`app/schemas/Servo.py:6-13`). This is the deliberate
  "validate-above-the-topology-layer" split (ADR 0002), but it means a legacy
  row with a `NULL` dimension cannot be validated into the schema.

## Functional Requirements

> The `RF-xx` ids refine the module-level requirements in
> [`../requirements.md`](../requirements.md).

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-10 | Trailing-edge-device CRUD (`GET` / `PATCH` / `DELETE`) with role-gated mixing validation | Must | `differential_ratio = 1.5` on role `flap` → 422; the same patch on role `aileron` → 200 |
| RF-11 | TED servo CRUD as a 1:1 child of the TED | Should | `PATCH .../trailing_edge_device/servo` → 200; `DELETE` removes only the servo, leaving the TED intact |
| RF-12 | ASB `control_surface` projection read/patch/delete, plus the CAD-only `cad_details` and `servo_details` subsets | Should | Patching `cad_details` leaves the ASB projection fields untouched |
| RF-20 | Decompose a dual-role surface into two control variables with the documented sign/gain/baseline table | Must | An `elevon` yields `[elevon]pitch_…` (`+1`, gain `mix_gain_primary`, symmetric `true`, baseline = deflection) and `[elevon]roll_…` (`−1`, gain `mix_gain_secondary`, symmetric `false`, baseline `0.0`) |
| RF-21 | Reject duplicate control-variable names across surfaces | Must | Two surfaces resolving to the same name raise **before** the AVL file is written |
| RF-C1 | Pass a single-axis role through unchanged | Must | An `aileron` keeps its existing tagged name and its `±1` sign verbatim; no second variable is emitted |
| RF-C2 | Reject a non-unity `mix_gain_secondary` on a non-dual role | Must | `mix_gain_secondary = 1.4` on role `flap` → 422; on role `elevon` → 200 |
| RF-C3 | Skip mixing validation on a partial patch that omits `role` | Must | A `PATCH` carrying only `label` succeeds even on a `flap`, because `role` is `None` |
| RF-C4 | Enforce the schema ranges on the mixing fields | Must | `mix_gain_primary = 0` → 422; `= 5.0` → 200; `= 5.1` → 422. `differential_ratio = 0.3` → 422; `= 0.31` → 200; `= 3.0` → 200; `= 3.1` → 422 |
| RF-C5 | Keep `differential_ratio` out of the aero solution | Must | Changing `differential_ratio` alone produces a byte-identical AVL/ASB geometry and an identical trim result |
| RF-C6 | Reject an empty TED patch | Should | `PATCH` with `{}` → 422 (`TrailingEdgeDevicePatchSchema` non-empty-patch validator) |
| RF-C7 | Reject unknown fields on TED and control-surface patches | Should | An unexpected key → 422 (`extra="forbid"`) |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Control-variable names are asserted unique **before** an AVL file is emitted, because AVL fails silently rather than loudly | `control_surface_mixing.py:149-164` | 🟢 |
| Correctness | The secondary axis carries a **zero** baseline so the AeroBuildup fallback cannot receive a roll/yaw deflection it has no model for | `control_surface_mixing.py:126-128` | 🟢 |
| Correctness | A single-axis role is passed through verbatim, so introducing gh-772 could not change existing single-axis aircraft | `control_surface_mixing.py:134-146` | 🟢 |
| Correctness | The TED is the single stored source; `control_surface` is computed, so the two cannot drift | `aeroplanemodel.py:241-276`; `model_schema_converters.py:960-995` | 🟢 |
| Correctness | Float comparison in the role gate uses `math.isclose(rel_tol=1e-9, abs_tol=1e-9)` rather than `==`, so a round-tripped `1.0` is not spuriously rejected | `aeroplaneschema.py:51-78` | 🟢 |
| Consistency | One module is the single source of truth for the AVL builder, the ASB builder and trim enrichment | `control_surface_mixing.py` (module docstring); ADR 0008 | 🟢 |
| Robustness | Mixing gains are `NOT NULL` with a `1.0` default, so "no mixing" needs no null handling downstream | `aeroplanemodel.py:147` (gh-772) | 🟢 |
| Integrity | Servo, TED and detail rows cascade `ON DELETE CASCADE`; the TED↔servo and detail↔TED relations are `unique` (1:1) | `aeroplanemodel.py:147`, `:190` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Control-surface mixing

  Scenario: A dual-role surface emits two control variables
    Given a trailing-edge device with role "elevon" and deflection 10 degrees
    When the control axes are resolved
    Then a "[elevon]pitch_<wing>_<i>" variable exists with sgn_dup +1, gain mix_gain_primary, symmetric true and baseline 10
    And a "[elevon]roll_<wing>_<i>" variable exists with sgn_dup -1, gain mix_gain_secondary, symmetric false and baseline 0.0

  Scenario: A flaperon maps to lift and roll
    Given a trailing-edge device with role "flaperon"
    When the control axes are resolved
    Then the primary axis is "lift"
    And the secondary axis is "roll"

  Scenario: A ruddervator maps to pitch and yaw
    Given a trailing-edge device with role "ruddervator" on wing key "htail" at x-sec index 1
    When the control axes are resolved
    Then a variable named "[ruddervator]pitch_htail_1" exists
    And a variable named "[ruddervator]yaw_htail_1" exists

  Scenario: A single-axis role is passed through unchanged
    Given a trailing-edge device with role "aileron"
    When the control axes are resolved
    Then exactly one control variable is emitted
    And its name and its plus-or-minus-one sign are unchanged from before gh-772

  Scenario: Duplicate control names are rejected
    Given two surfaces that resolve to the same control name
    When assert_unique_control_names runs
    Then it raises before any AVL geometry is written

Feature: Role-gated mixing validation

  Scenario: Differential ratio on a non-differential role is rejected
    Given a trailing-edge device with role "flap"
    When I PATCH differential_ratio to 1.5
    Then the response status is 422
    And the same patch on role "aileron" returns 200

  Scenario: Secondary gain on a non-dual role is rejected
    Given a trailing-edge device with role "flap"
    When I PATCH mix_gain_secondary to 1.4
    Then the response status is 422
    And the same patch on role "elevon" returns 200

  Scenario: A partial patch without a role skips the gate
    Given a trailing-edge device with role "flap"
    When I PATCH only the label
    Then the response status is 200
    And no mixing validation is performed

  Scenario: A unity value is legal on every role
    Given a trailing-edge device with role "flap"
    When I PATCH differential_ratio to 1.0 and mix_gain_secondary to 1.0
    Then the response status is 200
    # comparison is math.isclose(rel_tol=1e-9, abs_tol=1e-9), not equality

  Scenario: Mixing gains are range-checked
    Given any trailing-edge device
    When I PATCH mix_gain_primary to 5.1
    Then the response status is 422
    And a value of 5.0 returns 200
    And a value of 0 returns 422

  Scenario: An empty patch is rejected
    Given a trailing-edge device
    When I PATCH with an empty body
    Then the response status is 422

Feature: differential_ratio is reporting-only

  Scenario: Changing the differential ratio does not change the aero solution
    Given a trimmed aircraft with an aileron whose differential_ratio is 1.0
    When I PATCH differential_ratio to 2.0
    And I re-run the trim
    Then the trim solution is unchanged
    And only the reported left and right deflections differ

Feature: TED, servo and control-surface projection

  Scenario: The control_surface projection follows the TED
    Given a trailing-edge device with rel_chord_root 0.75
    When I GET the station's control_surface
    Then the projection reflects the TED's hinge position
    And no separate control_surface row exists

  Scenario: Patching cad_details leaves the ASB projection alone
    Given a station with a trailing-edge device
    When I PATCH control_surface/cad_details
    Then the ASB projection fields are unchanged

  Scenario: Deleting the servo leaves the TED
    Given a trailing-edge device with a servo
    When I DELETE the servo
    Then the response status is 200
    And the trailing-edge device still exists

  Scenario: Deleting the TED removes the servo
    Given a trailing-edge device with a servo
    When I DELETE the trailing-edge device
    Then the servo row is removed by cascade
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Control-axis decomposition (RF-20) | Must | The core of gh-772 / ADR 0008; without it a dual-role aircraft cannot be trimmed at all |
| Name uniqueness assertion (RF-21) | Must | AVL fails **silently** on a collision — the assertion is the only thing standing between a duplicate name and a quietly wrong answer |
| Single-axis passthrough (RF-C1) | Must | The compatibility guarantee that let gh-772 ship without invalidating every existing aircraft |
| Zero baseline on the secondary axis (part of RF-20) | Must | Prevents the AeroBuildup fallback receiving a roll/yaw deflection its single-axis model cannot represent |
| TED CRUD with role gating (RF-10, RF-C2, RF-C3) | Must | Role drives trim, operating-point capability gating and the axis decomposition itself |
| Mixing-field range checks (RF-C4) | Must | Out-of-range gains produce physically meaningless AVL geometry |
| `differential_ratio` isolation from the aero solution (RF-C5) | Must | Explicitly documented invariant (BR-10); violating it would make trim results depend on a display-only field |
| Servo CRUD (RF-11) | Should | A convenience projection over data writable through the TED route |
| `control_surface` / `cad_details` / `servo_details` subsets (RF-12) | Should | Convenience projections; the TED route can express everything they can |
| Empty-patch and unknown-field rejection (RF-C6, RF-C7) | Should | Defensive contract hygiene; a typo'd field would otherwise be silently dropped |
| Owning the name resolver that trim / retrim / stability must call | **Must** | 🟢 decided (`Q-WD-1`): ownership sits here because this use case defines the canonical name; the consumers are required to call it and the ±25° fallback is removed |
| Normalising the `servo` union (`Servo` vs `int` index) | **Should** | 🟢 decided (`Q-WD-3 ①`): `servo_data` is canonical for new records, `servo_index` deprecated; the union stays readable so existing rows resolve |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/control_surface_mixing.py` | `_DUAL_ROLE_AXES` (l.29-33), `PRIMARY_AXES` / `SECONDARY_AXES` (l.29-33), dual-role emission (l.126-128), single-axis passthrough (l.134-146), `axis_control_name` (l.76-84), `assert_unique_control_names` (l.149-164), invariants docstring (l.14-15) | 🟢 |
| `app/schemas/aeroplaneschema.py` | `_validate_mix_fields` (l.51-78), `ControlSurfaceSchema` (l.102), `ControlSurfaceCadDetailsSchema` (l.156), `…PatchSchema` (l.184), `TrailingEdgeDeviceDetailSchema` (l.287), `TrailingEdgeDevicePatchSchema` (l.397), `differential_ratio` reporting-only note (l.372-381) | 🟢 |
| `app/models/aeroplanemodel.py` | `WingXSecTrailingEdgeDeviceModel` (l.147), `servo` union property (l.183-187), `WingXSecTedServoModel` (l.190), computed `control_surface` projection (l.241-276) | 🟢 |
| `app/schemas/Servo.py` | `Servo` (l.6-13) — all `NonNegativeFloat`, all required | 🟢 |
| `app/converters/model_schema_converters.py` | `_build_segment_details` (l.960-995), `_merge_ted_with_control_surface` | 🟢 |
| `app/api/v2/endpoints/aeroplane/wings.py` | `trailing_edge_device`, `.../servo`, `control_surface`, `control_surface/cad_details`, `.../cad_details/servo_details` routes | 🟢 |
| `app/services/trim_enrichment_service.py`, `retrim_service.py`, `stability_service.py` | consumers required to call this use case's name resolver | 🟢 (`Q-WD-1`) — currently still key on the raw DB TED name (#955); the resolver makes that impossible |
| `cad_designer/airplane/aircraft_topology/wing/TrailingEdgeDevice.py` | topology defaults (`positive/negative_deflection_deg = 25`, `hinge_type = "top"`, `trailing_edge_offset_factor = 1.0`) | 🟢 read-only (ADR 0002) |
