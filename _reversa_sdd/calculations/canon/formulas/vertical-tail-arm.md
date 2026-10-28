---
canon: vertical-tail-arm
entry: formula
kind: procedure
tool: GEO
shape: law
status: approved
output: vertical-tail-arm
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/approved
tex: l_{V,CG} = x_{v,25} - x_{cg,design}
inputs: {airplane: airplane, x_cg: centre-of-gravity-design}
outputs: {l_v_cg: vertical-tail-arm}
applications:
  - id: with_vertical_tail
    when: has_vertical_tail
---

# Vertical tail arm from the design CG

**Canonical form**

```
x_v_25 := Wing.aerodynamic_center()[0]   # ASB, x of the quarter-chord MAC of the vertical tail (fin or V-tail)
l_v_cg = x_v_25 - x_cg_design
```

**Produces** [[vertical-tail-arm]]  ·  **from** [[airplane]] · [[centre-of-gravity-design]]

**Kind: a procedure — an evaluation of the model, then a difference.** The position of the vertical tail (fin or V-tail)'s
quarter-chord MAC is read from the geometry; the arm is its distance, along x, from the computed design CG.


**Why from the design CG (maintainer, 2026-10-25, epic #1259).** Drela's tail volumes and spiral parameter
measure the arm from the CG. "Wenn wir Drelas Bewertung wollen, dann können wir nicht x_cg,25 nehmen, sondern
den berechneten x_cg,SM. Ansonsten würden wir eine falsche Bewertung vornehmen." The CG is
[[centre-of-gravity-design]] = x_NP − SM_target·c_MAC, so the arm is an **interval over the neutral-point worlds**
(A11): the formula runs once per world, nothing is combined across worlds. The chain is one-directional —
geometry → x_NP (textbook / Pappas / AVL) → x_cg,design → arm → Drela's quantities; x_NP does not come from
Drela's Eq. 5, so there is no circularity. A caller who knows the real CG of an existing aircraft does not
use this arm; that is the measured direction ([[centre-of-gravity-measured]]) and is not computed here.

**Geometry (ADR 0022, one producer).** `x_v,25` is `Wing.aerodynamic_center(chord_fraction=0.25)[0]` of the
surface, ASB's own value (the same quarter-chord MAC the neutral point uses for the tail), obtained from the GEO
adapter; the kernel integrates no planform of its own. No area or span enters, so a vertical surface needs no
planform. The surface is the one wing of `surface_type` `vertical_tail` or `v_tail`; none or several are refused as `unsupported_layout` (a fin typed `winglet` is no tail arm). For a V-tail the arm is to the V-tail's own quarter-chord MAC; what the V-tail projects to (`sum S_i sin^2 nu_i`) is the business of the tail volume (#1208).

**Values, not verdicts (A10).** The arm is a length in m. Bands for the quantities built on it belong to the
evaluation.

**Dimensional check.** 🟢 balances by hand — m − m; the checker sees a geometry extraction (procedural).

**Source.** 🟢 SOURCED — Drela, MIT 16.Unified *Design Rules*, Eqs 3 and 7–10 for the definition of the arms
from the CG; AeroSandbox 4.2.9 `Wing.aerodynamic_center` for the position; the CG from [[cg-for-target-margin]].

**Validity in the RC/UAV regime (ADR 0028).** Exact as geometry. It inherits the limits of [[neutral-point]]
(the interval, the aft bias from the missing fuselage, `fuselage_not_modelled` in every world) through the CG:
a CG placed at the aft end of the interval gives a shorter arm than a fuselage-corrected one would.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/vertical_tail_arm.py` | EXACT | 🟢 | the quarter-chord MAC position is ASB's, from the GEO adapter (`aero_kernel/solvers/geometry.py`); the difference to the design CG is taken per neutral-point world |

## Approval

- [x] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [x] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [x] **Relation and method** — which equation it solves, and by which named method
- [x] **Implementations** — all agree, or each deviation is declared and justified
- [x] **Inputs approved** — no formula is approvable before its inputs are

> **Approved** (maintainer, 2026-10-26): l_V,CG = x_v,25 − x_cg,design, the quarter-chord MAC of the one surface
> typed `vertical_tail` or `v_tail` from AeroSandbox and the design CG from the approved
> [[cg-for-target-margin]], once per neutral-point world (A11); Drela Design Rules Eqs 3, 7–10 (decision
> 2026-10-25, #1259). A V-tail's arm is to its own quarter-chord MAC; the projection belongs to the tail volume
> (#1208); the neutral point covers the V-tail since the maintainer decision of 2026-10-27 (#1208), so a V-tail aircraft has a value. Inherits the neutral
> point's limits (fuselage not modelled). Kernel EXACT (🟢), goldens BRYAN/JAGUAR (#1305), BELEMNITOS (#1208).
