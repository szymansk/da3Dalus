---
canon: spiral-parameter
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: spiral-parameter
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/law
  - status/draft
inputs:
  airplane: airplane
  s_ref: wing-reference-area
  b_ref: wing-span
  l_v_cg: vertical-tail-arm
  m: aircraft-mass
  g: gravity
  rho: air-density
  v_md: minimum-drag-speed
outputs: {b_spiral: spiral-parameter}
applications:
  - id: with_vertical_tail
    when: has_vertical_tail
---

# Spiral parameter (Drela's B)

**Canonical form**

```
Gamma_eq := geometry(airplane)   # (equivalent) dihedral in degrees
C_L = m * g / (0.5 * rho * V_md^2 * S_ref)
B   = l_V_CG * Gamma_eq / (b_ref * C_L)
```

`S_ref` and `b_ref` are [[wing-reference-area]] and [[wing-span]], produced by [[airplane-geometry]] (AeroSandbox's
definition, measured on the main wing; maintainer 2026-10-25). This entry does not read the wing area or span
from the airplane itself: one producer per number a user sees (ADR 0022). Only the (equivalent) dihedral `Gamma_eq` is read from the airplane;
the arm `l_V,CG` is [[vertical-tail-arm]], measured from the computed design CG ([[centre-of-gravity-design]]) as Drela defines it
(maintainer 2026-10-25, #1272); the former `l_V,25` is removed (ADR 0021). The arm is an interval over the neutral-point worlds, so `B` is one value per world (A11).

**Produces** [[spiral-parameter]]  ·  **from** [[airplane]] · [[wing-reference-area]] · [[wing-span]] · [[vertical-tail-arm]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[minimum-drag-speed]]

**Kind: a law.** A geometric spiral-stability measure for aircraft with a tail, deterministic and
independent of any solver — the RC practice's counterpart to the spiral criterion of
[[lateral-static-stability-md]] (K27).

**Precondition.** The aircraft has a fin or a V-tail behind the wing (`l_V,CG` is a tail arm). Not computed
for tailless aircraft.

**Values, not verdicts (A10).** Drela: B > 5 spirally stable, ≈ 5 neutral, 3–4 no difficulty for an
experienced pilot; rudder-only models V_V·B = 0.10–0.20 for roll authority. Bands belong to the evaluation.

**Dimensional check.** 🟢 balances by hand — m / m; `Γ_eq` enters as a number in degrees (Drela's definition); the checker sees a geometry extraction (procedural).

**Source.** 🟢 SOURCED — Drela, MIT 16.Unified *Design Rules*, Eqs 8–10; Beron-Rawdon, *Model Aviation*
9/1990 (equivalent dihedral for polyhedral).

**Validity in the RC/UAV regime (ADR 0028).** Stated for RC sailplanes and models; the stability threshold is empirical.

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
