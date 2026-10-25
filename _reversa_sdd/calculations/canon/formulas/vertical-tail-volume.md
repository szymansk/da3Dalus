---
canon: vertical-tail-volume
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: vertical-tail-volume
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/law
  - status/draft
inputs: {airplane: airplane, s_ref: wing-reference-area, b_ref: wing-span}
outputs: {v_v: vertical-tail-volume}
applications:
  - id: with_vertical_tail
    when: has_vertical_tail
---

# Vertical tail volume

**Canonical form**

```
S_V, l_V_25 := geometry(airplane)   # fin area (V-tail: S_Vtail*sin^2(nu)), tail arm
V_V = S_V * l_V_25 / (S_ref * b_ref)
```

`S_ref` and `b_ref` are [[wing-reference-area]] and [[wing-span]], produced by [[airplane-geometry]] (AeroSandbox's
definition, measured on the main wing; maintainer 2026-10-25). This entry does not read the wing area or span
from the airplane itself: one producer per number a user sees (ADR 0022). Only the tail-specific geometry,
`S_V` and `l_V,25`, is read from the airplane.

`S_V` is the fin area, for a V-tail its fin share `S_Vtail·sin²ν` (ν = panel angle to the horizontal);
`l_V,25` runs from the wing's quarter-chord MAC (25 % MAC) to the fin's quarter-chord MAC.
Drela measures from the CG; for the MVP the CG is taken as 25 % MAC (maintainer 2026-10-25). A CG-referenced variant (`l_V,CG`, `l_H,CG`, Drela's definition) may be added later as a separate quantity; the suffix names the reference point.

**Produces** [[vertical-tail-volume]]  ·  **from** [[airplane]] · [[wing-reference-area]] · [[wing-span]]

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

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
