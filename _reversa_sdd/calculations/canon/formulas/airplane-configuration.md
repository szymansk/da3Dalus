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

**Validity, declared (no threshold, A10).** The configured airplane is evaluated through AeroBuildup. AeroBuildup has no flap model of its own, and NeuralFoil never sees the deflected surface: AeroSandbox evaluates the clean airfoil at `α_eff = α + τ·δ`, `τ = 1 − x_hinge^2.7514` (a δ-independent fit to an XFoil study), and multiplies the drag by a factor fitted to Hoerner, *Fluid Dynamic Drag*, p. 13-13 Fig. 32 (`aerosandbox/geometry/airfoil/kulfan_airfoil.py:211-255`, reached from `aero_buildup.py:784-801`; AeroSandbox 4.2.9 / NeuralFoil 0.3.2). There is no flap separation: the effectiveness is over-predicted at large δ until the clean section stalls, and the δ range of the τ fit is unknown.
The limitation was first noted in ANFORDERUNGEN.md, § "Rollwirkung gegen die gebauten Ruderausschläge"
(lines 544–546: beyond about 25°) and § "Nicht im MVP: die Querruderdifferenzierung" (lines 1007–1008:
15–25° at Re ≈ 60 000, unverified); both describe it as a NeuralFoil flap model, which the code does not
confirm (#1181). Landing settings typically lie above that range.

**Source.** 🔴 NO SOURCE FOUND — a construction step, adopted on the maintainer's statement in
[[stall-speed]] (2026-10-02). No published source exists for a construction step; the rules
above are **adopted on the maintainer's authority** (statement 2026-10-02, confirmed 2026-10-24).

**Validity in the RC/UAV regime (ADR 0028).** Regime-independent as a construction step. The tool limit
is the one declared above: AeroBuildup's τ·δ shift without flap separation over-predicts the flap at large
deflections; landing settings of RC models lie above the unverified 15–25° range.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/airplane_configuration.py` | EXACT | 🟢 | flaps reaching AeroBuildup/AVL are refused until #1212; without flaps the configured airplane is the airplane |

## Approval

- [x] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [x] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [x] **Relation and method** — which equation it solves, and by which named method
- [x] **Implementations** — all agree, or each deviation is declared and justified
- [x] **Inputs approved** — no formula is approvable before its inputs are

> **Approved** (maintainer, 2026-10-24). This is the relation the implementations are measured against.
