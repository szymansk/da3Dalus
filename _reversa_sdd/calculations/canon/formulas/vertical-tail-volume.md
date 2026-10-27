---
canon: vertical-tail-volume
entry: formula
kind: law
tool: APP
shape: law
status: approved
output: vertical-tail-volume
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/law
  - status/approved
inputs: {airplane: airplane, s_ref: wing-reference-area, b_ref: wing-span, l_v_cg: vertical-tail-arm}
outputs: {v_v: vertical-tail-volume}
applications:
  - id: with_vertical_tail
    when: has_vertical_tail
---

# Vertical tail volume

**Canonical form**

```
S_V := Wing.area(type="planform", include_centerline_distance=False)   # ASB, the one vertical_tail/v_tail surface; V-tail: times sin^2(nu)
V̄_V = S_V * l_V_CG / (S_ref * b_ref)
```

`S_ref` and `b_ref` are [[wing-reference-area]] and [[wing-span]], produced by [[airplane-geometry]] (AeroSandbox's
definition, measured on the main wing; maintainer 2026-10-25). This entry does not read the wing area or span
from the airplane itself: one producer per number a user sees (ADR 0022). Only the fin area `S_V` is read from the airplane, as AeroSandbox's `Wing.area(type="planform", include_centerline_distance=False)` of the one surface typed `vertical_tail` or `v_tail`, both flags passed explicitly (maintainer 2026-10-26, no library defaults): `planform` is the true area of the mean camber surface, unprojected, which is right for a vertical surface (the `xy` projection of a fin is nearly zero); a fin has no centreline gap to count;
the arm `l_V,CG` is [[vertical-tail-arm]].

`S_V` is the fin area, for a V-tail its fin share `S_Vtail·sin²ν` (ν = panel angle to the horizontal);
`l_V,CG` runs from the computed design CG ([[centre-of-gravity-design]]) to the fin's quarter-chord MAC, exactly
Drela's definition (maintainer 2026-10-25, #1272, superseding the reading of the CG as 25 % MAC). The arm is an interval
over the neutral-point worlds, so `V̄_V` is one value per world (A11); the former `l_V,25` is removed, no formula needs it (ADR 0021).

**Produces** [[vertical-tail-volume]]  ·  **from** [[airplane]] · [[wing-reference-area]] · [[wing-span]] · [[vertical-tail-arm]]

**Kind: a law.** A geometric ratio, deterministic and independent of any solver. It is the robust anchor
next to the AVL derivatives (K27): RC practice and preliminary design size the fin with it, not with
`C_nβ` (Sadraey §6.7.1; Drela, desrules Eq. 7).

**Precondition.** The aircraft has a fin or a V-tail behind the wing. For a tailless aircraft (winglets,
centre fin on the wing) the lever is not a tail arm and the value is not computed — not computed
differently. No sourced rule for flying-wing fins exists (research 2026-10-04).

**Values, not verdicts (A10).** The bands — RC/UAV 0.02–0.05, gliders ≈ 0.03 (Sadraey Tab. 6.4; Drela)
— belong to the evaluation.

**Dimensional check.** 🟢 balances by hand — m²·m / (m²·m); the checker sees a geometry extraction (procedural).

**Source.** 🟢 SOURCED — Sadraey Eq. 6.74; V-tail projection sin²ν: McCombs, *Model Aviation* 7/1996;
Drela's V-tail rule (BAENDER §3b).

**Validity in the RC/UAV regime (ADR 0028).** Exact as geometry; the bands are RC values.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/vertical_tail_volume.py` | EXACT | 🟢 | `S_V` is ASB's `Wing.area(type="planform", include_centerline_distance=False)` of the one `vertical_tail`/`v_tail` surface, from the GEO adapter (`aero_kernel/solvers/geometry.py`, `fin_area`), both flags passed in code; a V-tail's fin share is the sum over its panels of ASB's planform area of that panel times sin²(panel angle); one value per neutral-point world, from the arm |

## Approval

- [x] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [x] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [x] **Dimensions** — the check balances
- [x] **Implementations** — all agree, or each deviation is declared and justified
- [x] **Preconditions** — every binding condition holds, or the violation is ticketed
- [x] **Inputs approved** — no formula is approvable before its inputs are

> **Approved** (maintainer, 2026-10-26): V̄_V = S_V · l_V,CG / (S_ref · b_ref) (Sadraey Eq. 6.74; Drela Eq. 7),
> with the arm from the design CG (approved [[vertical-tail-arm]]), S_ref and b_ref from the approved
> [[airplane-geometry]], and S_V as AeroSandbox's `Wing.area(type="planform", include_centerline_distance=False)`
> of the one vertical_tail/v_tail surface, flags explicit (added at approval); V-tail fin share S·sin²ν
> (McCombs 1996). One value per neutral-point world (A11). Bands belong to the evaluation (A10). Formula approved;
> no kernel implementation yet (#1274); a V-tail gets a value with #1208.
