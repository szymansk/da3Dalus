---
canon: horizontal-tail-arm
entry: formula
kind: procedure
tool: GEO
shape: law
status: draft
output: horizontal-tail-arm
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
tex: l_{H,CG} = x_{h,25} - x_{cg,design}
inputs: {airplane: airplane, x_cg: centre-of-gravity-design}
outputs: {l_h_cg: horizontal-tail-arm}
---

# Horizontal tail arm from the design CG

**Canonical form**

```
x_h_25 := Wing.aerodynamic_center()[0]   # ASB, x of the quarter-chord MAC of the horizontal tail
l_h_cg = x_h_25 - x_cg_design
```

**Produces** [[horizontal-tail-arm]]  ·  **from** [[airplane]] · [[centre-of-gravity-design]]

**Kind: a procedure — an evaluation of the model, then a difference.** The position of the horizontal tail's
quarter-chord MAC is read from the geometry; the arm is its distance, along x, from the computed design CG.


**Why from the design CG (maintainer, 2026-10-25, epic #1259).** Drela's tail volumes and spiral parameter
measure the arm from the CG. "Wenn wir Drelas Bewertung wollen, dann können wir nicht x_cg,25 nehmen, sondern
den berechneten x_cg,SM. Ansonsten würden wir eine falsche Bewertung vornehmen." The CG is
[[centre-of-gravity-design]] = x_NP − SM_target·c_MAC, so the arm is an **interval over the neutral-point worlds**
(A11): the formula runs once per world, nothing is combined across worlds. The chain is one-directional —
geometry → x_NP (textbook / Pappas / AVL) → x_cg,design → arm → Drela's quantities; x_NP does not come from
Drela's Eq. 5, so there is no circularity. A caller who knows the real CG of an existing aircraft does not
use this arm; that is the measured direction ([[centre-of-gravity-measured]]) and is not computed here.

**Geometry (ADR 0022, one producer).** `x_h,25` is `Wing.aerodynamic_center(chord_fraction=0.25)[0]` of the
surface, ASB's own value (the same quarter-chord MAC the neutral point uses for the tail), obtained from the GEO
adapter; the kernel integrates no planform of its own. No area or span enters, so a vertical surface needs no
planform. Refused as `unsupported_layout`, decided from `surface_type`: no horizontal tail, or more than one. A canard or a V-tail is no horizontal tail here (#1207, #1208).

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
| `aero_kernel/formulas/horizontal_tail_arm.py` | EXACT | 🟢 | the quarter-chord MAC position is ASB's, from the GEO adapter (`aero_kernel/solvers/geometry.py`); the difference to the design CG is taken per neutral-point world |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
