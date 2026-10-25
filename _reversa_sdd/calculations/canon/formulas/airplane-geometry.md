---
canon: airplane-geometry
entry: formula
kind: procedure
tool: GEO
shape: law
status: draft
output: wing-reference-area, wing-span, mean-aerodynamic-chord
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
inputs: {airplane: airplane}
preconditions:
  - {id: main_wing_has_spanwise_extent, parameter: airplane, on_violation: error}
outputs:
  s_ref: wing-reference-area
  b_ref: wing-span
  c_mac: mean-aerodynamic-chord
---

# Geometric properties of the airplane

**Canonical form**

```
S_ref, b_ref, c_MAC := geometry of the airplane model
```

**Produces** [[wing-reference-area]] · [[wing-span]] · [[mean-aerodynamic-chord]]  ·  **from** [[airplane]]

**Kind: a procedure — an evaluation of the model.** These are properties of the aircraft, read from its
geometry: reference area, span and mean aerodynamic chord of the main wing (the wing with surface_type main_wing,
#1187), chosen by type and never by list position.

**Definition (maintainer, 2026-10-25).** The reference values are AeroSandbox's, measured on the main wing:

- `S_ref = Wing.area()` (ASB default: `type="planform"`, `include_centerline_distance=False`),
- `b_ref = Wing.span(include_centerline_distance=True)`,
- `c_MAC = Wing.mean_aerodynamic_chord()`,

that is exactly what `asb.Airplane` infers when the main wing is its first wing. The kernel passes them
explicitly to `asb.Airplane` and to AVL, so every coefficient stays referenced to the same area (ADR 0022);
ASB's own default would take the first wing in the list, not the main wing. A mirrored wing is built from its
oriented chain (root first, y ≥ 0); sections that fold back in y are not supported.

**Precondition `main_wing_has_spanwise_extent` (error; maintainer 2026-10-25, #1253).** A wing typed `main_wing`
must extend further in y than in z: over its stored sections, `max y − min y > max z − min z`. Equal or less
means the mean inclination of the whole wing is 45° or more, a vertical surface. AeroSandbox would measure it
without complaint (a slant planform), so the kernel refuses it before the measurement, as
`unsupported_configuration` (`precondition_violated`), with the hint to check the surface type. Criterion and
threshold are the proposal of #1253 and **await the maintainer's approval**: the dihedral of a real main wing
stays far below 45° (even a strong V, 10–15°; a winglet adds little y-extent and little z-extent to a wing
whose y-extent dominates), whereas a fin or a V-tail typed `main_wing` has y ≤ z.

**Declared, not changed.** ASB's `area()` excludes the gap at the centreline (a root off y = 0 contributes no
area inboard of it), while `b_ref` includes the centreline distance (`2·max|y|`). For a wing whose root lies on
y = 0 the two agree; for an offset root, S_ref and b_ref do not describe the same planform. This is ASB's
definition and is stated here, not corrected. ASB measures the panels along the quarter-chord line, so twist
and dihedral move the values; that is part of the definition.

**Superseded (maintainer 2026-10-25).** The rule of 2026-10-22 (sections projected onto the x-y plane,
twist-independent, the mirrored root extended to y = 0 with the root chord, the kernel integrating the sections
itself) no longer holds. The decision: "Wenn ich was ausgeschlossen habe, das bei asb anders gemacht wird, dann
gilt die Rechnung nach asb! Das ist von einem Experten implementiert." With it the warning
`reference_wing_at_centreline` is gone. The neutral point's own planform integration
(`aero_kernel/geometry_properties.py`, `x_le_MAC` and the tail terms) is a separate matter and is unchanged.

**Why this entry exists.** These quantities used to stand as free inputs. They are not: a
change to the wing changes all of them, and the graph has to say so, or invalidation (A1)
would leave every number computed from them standing after a geometry edit.

**Source.** 🟢 AeroSandbox 4.2.9 (Sharpe; version from `poetry.lock`) for the computation: `Wing.area()`, `Wing.span()` and `Wing.mean_aerodynamic_chord()` as `asb.Airplane` uses them for its reference values, adopted on the maintainer's authority (2026-10-25: the expert's implementation is the definition). 🟢 Scholz, *Flugzeugentwurf*, Wing Design §7.1 for the concept: `c_MAC = (2/S)·∫₀^{b/2} c(y)² dy`, and the reference wing area as a definitional convention.

**Validity in the RC/UAV regime (ADR 0028).** Regime-independent: S_ref, b_ref and c_MAC are geometric properties of the planform, and no Reynolds number, Mach number or equipment enters them. The reference area is a convention: Scholz (Wing Design §7.1) shows that manufacturers define it differently and that changing it changes only the coefficients. The one regime requirement is consistency: every coefficient in the chain must use the S_ref and c_MAC this entry produces.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/airplane_geometry.py` | EXACT | 🟢 | the values are ASB's own, measured by the GEO adapter (`aero_kernel/solvers/geometry.py`) on the wing `aero_kernel/solvers/asb_airplane.py` builds; `area()` excludes the centreline gap while `b_ref` includes it (declared above) |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
