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

**Kind: a procedure — an evaluation of the model.** These are properties of the aircraft, read or
integrated from its geometry: reference area and span from the main wing (the wing with surface_type main_wing, #1187), the mean
aerodynamic chord as `(2/S)·∫c(y)² dy`.

**Definition (maintainer, 2026-10-22).** The reference values are the sections' chords and leading edges as
given, projected onto the x-y plane, panel by panel; twist does not change them. A mirrored wing is carried to the
centreline: a root off the plane is extended to y = 0 with the root chord, and a stored side that crosses y = 0 is
clipped there, so b_ref = 2·max|y| and S_ref, c_MAC are integrated over 0 … max|y|; a wing that is not mirrored
keeps its stored extent (max y − min y) without extension. Sections that fold back in y are not supported. The kernel integrates the
sections itself. AeroSandbox's `Wing.area()`, `Wing.span()` and `Wing.mean_aerodynamic_chord()` are not used for
the reference values: their projection depends on twist (they measure along the quarter-chord line), and the
mean aerodynamic chord weights panels by their slant area. The app's current values are measured along the
panels and differ by up to about 2 % at 8° dihedral.

**Why this entry exists.** These quantities used to stand as free inputs. They are not: a
change to the wing changes all of them, and the graph has to say so, or invalidation (A1)
would leave every number computed from them standing after a geometry edit.

**Source.** 🟢 Scholz, *Flugzeugentwurf*, Wing Design §7.1: `c_MAC = (2/S)·∫₀^{b/2} c(y)² dy`, and the reference wing area as a definitional convention. The projection and centreline rules (x-y projection, twist-independent, root extended to y = 0 with the root chord, b_ref = 2·max|y|) have no textbook source; they are adopted on the maintainer's authority (definition, 2026-10-22).

**Validity in the RC/UAV regime (ADR 0028).** Regime-independent: S_ref, b_ref and c_MAC are geometric properties of the planform, and no Reynolds number, Mach number or equipment enters them. The reference area is a convention: Scholz (Wing Design §7.1) shows that manufacturers define it differently and that changing it changes only the coefficients. The one regime requirement is consistency: every coefficient in the chain must use the S_ref and c_MAC this entry produces.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/airplane_geometry.py` | EXACT | 🟢 | the reference planform carried to the centreline is declared (`reference_wing_at_centreline`, ADR 0020); the integration is `aero_kernel/geometry_properties.py` |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
