---
canon: airplane-configuration
entry: formula
kind: procedure
tool: GEO
shape: law
status: approved
output: airplane-takeoff, airplane-landing
source_status: NO_SOURCE_FOUND
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/no-source-found
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/approved
inputs: {airplane: airplane, flap_deflection: null}
outputs: {airplane_cfg: null}
optional: [flap_deflection]
applications:
  - id: takeoff
    bind: {flap_deflection: flap-deflection-takeoff}
    produce: {airplane_cfg: airplane-takeoff}
  - id: landing
    bind: {flap_deflection: flap-deflection-landing}
    produce: {airplane_cfg: airplane-landing}
---

# The airplane in its take-off or landing configuration

**Canonical form**

```
airplane_cfg := airplane with its flaps at delta_f,cfg      (cfg = take-off | landing)
```

**Produces** [[airplane-takeoff]] · [[airplane-landing]]  ·  **from** [[airplane]] · [[flap-deflection-takeoff]] · [[flap-deflection-landing]]

**Kind: a procedure — an evaluation of the model.** The same airplane with its flaps set for the
configuration: the flap is in the geometry, not a factor on `C_L,max` ([[stall-speed]], 2026-10-02).
The configured airplane is what the take-off and landing applications of [[stall-speed]] bind
(A2: a named condition is a quantity, produced by its own application — #1181, architect
2026-10-14).

**Without flaps there is no configuration — the same aircraft, not a fallback** ([[stall-speed]],
maintainer 2026-10-02): if the geometry has flaps, they are used as constructed for that
configuration; if it has none, the configured airplane is the airplane itself.

**The deflection is a design input** ([[flap-deflection-takeoff]], [[flap-deflection-landing]];
maintainer, 2026-10-14), not bounded by the geometry's stop `positive_deflection_deg`: the canon is
used to find out which stop the wanted speed needs.

**Four cases** (architect, 2026-10-14; `flap_deflection` is optional):

| aircraft | deflection | result |
|---|---|---|
| no flaps | absent | the unchanged aircraft, no warning — the canon's own definition ([[stall-speed]], maintainer 2026-10-02) |
| no flaps | given | the unchanged aircraft and a `practice` warning `deflection_without_flap`: the supplied value is not used |
| flaps | absent | no value: `missing_input` for the configured airplane; its dependents fail; the clean stall speed still computes |
| flaps | given | the deflection applied exactly, also beyond the stop |

**What counts as a flap** (maintainer, 2026-10-14): every control surface that acts as a flap —
flaperons too. In the geometry format these are the trailing-edge devices with `role: flap` or
`role: flaperon` (`docs/geometry-format/airplane-geometry.schema.json`, `TrailingEdgeDevice.role`). In
the take-off and landing configuration all of them are set to the given deflection angle.

**Validity, declared (no threshold, A10).** The configured airplane is evaluated through AeroBuildup. **The flap is geometry, not a lift-curve shift** (maintainer 2026-10-26, #1212, route A): the airfoil contour behind the hinge is rotated by the deflection (`Airfoil.add_control_surface`, trailing edge down positive; AeroSandbox 4.2.9, `airfoil.py:1191-1298`), the deflected contour is handed to NeuralFoil by AeroBuildup (`aero_buildup.py:800-805`), which normalises it to its leading-edge to trailing-edge chord and corrects the angle of attack by the rotation. `ControlSurface.deflection` stays 0 for the flap, so ASB's Hoerner drag factor is 1 and nothing is counted twice; the `τ·δ` shift (`τ = 1 − x_hinge^2.7514`, `kulfan_airfoil.py:211-255`) stays the model of the **aileron** only, adequate in its linear range ([[roll-rate]]). A shift alone cannot raise `C_L,max` — it moved RV-7's first peak below the clean one (clean 1.22, 15° 0.98, 30° 1.15) and made `V_S,LDG` higher than the clean `V_S` — which is why the flap is geometry. **Measured** (RV-7's NACA 23013.5, Re 1·10⁵, hinge 0.75): section `C_l,max` 1.23 clean, 1.64 at 15° (NeuralFoil `analysis_confidence` 0.95), 1.81 at 30° (confidence 0.53). **Limits, declared:** NeuralFoil was not trained on deflected contours as such, so its `analysis_confidence` of a flapped section falls with the deflection (the confidence is reported as a value in `control_surface_fit_range_unknown`); there is no flap separation model; the flap is a **single-element plain flap** (slotted and Fowler flaps are out of scope); the flapped panel is a strip with the deflected contour on both bounding sections. Thresholds for a confidence warning and a deflection warning (above 30°) are proposed as the rule `flap-model-validity` (`rules.yaml`, status pending) and are not read by the kernel until the maintainer adopts them. The textbook increment of the maximum lift of a plain flap (Scholz, *Aircraft Design*, Eq. 8.6; DATCOM) is a cross-check only and never a second value: its data are transport-Reynolds-number data (ADR 0028).
The limitation was first noted in ANFORDERUNGEN.md, § "Rollwirkung gegen die gebauten Ruderausschläge"
(lines 544–546: beyond about 25°) and § "Nicht im MVP: die Querruderdifferenzierung" (lines 1007–1008:
15–25° at Re ≈ 60 000, unverified); those concern the aileron's `τ·δ` model, not the flap (#1181).

**How the tools are given the flaps (#1212).** The deflection is the angle itself, trailing edge down positive, the same on both halves. AeroBuildup receives the deflected contour on the airfoils of the flapped strip, with one zero-width strip written at a rib where the flap state changes (so the next strip keeps its own airfoil); the hinge is the mean of the segment's root and tip hinge (`hinge_line_averaged` where they differ); AVL a `flap` control (SgnDup +1) on the stations of the flap, driven at the deflection (linear in δ, `avl_flap_linearised`). A flaperon carries the deflection as its symmetric bias (geometry in AeroBuildup); the aileron command comes on top ([[roll-rate]]). `stall-speed-takeoff`/`-landing` are the kernel's regression values, not validated against a flapped wing.

**Source.** 🔴 NO SOURCE FOUND — a construction step, adopted on the maintainer's statement in
[[stall-speed]] (2026-10-02). No published source exists for a construction step; the rules
above are **adopted on the maintainer's authority** (statement 2026-10-02, confirmed 2026-10-24).

**Validity in the RC/UAV regime (ADR 0028).** Regime-independent as a construction step. The tool limit
is the one declared above: AeroBuildup's τ·δ shift without flap separation over-predicts the flap at large
deflections; landing settings of RC models lie above the unverified 15–25° range.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/airplane_configuration.py` | EXACT | 🟢 | the configured flaps reach AeroBuildup (deflected contour) and AVL (symmetric control `flap`) since #1212; without flaps the configured airplane is the airplane |

## Approval

- [x] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [x] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [x] **Relation and method** — which equation it solves, and by which named method
- [x] **Implementations** — all agree, or each deviation is declared and justified
- [x] **Inputs approved** — no formula is approvable before its inputs are

> **Approved** (maintainer, 2026-10-24). This is the relation the implementations are measured against.
