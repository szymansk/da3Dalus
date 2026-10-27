---
canon: rudder-roll-authority
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: rudder-roll-authority-md, rudder-roll-authority-mp
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
inputs:
  v_v: vertical-tail-volume
  b_spiral_md: spiral-parameter-md
  b_spiral_mp: spiral-parameter-mp
outputs:
  rra_md: rudder-roll-authority-md
  rra_mp: rudder-roll-authority-mp
applications:
  - id: without_aileron
    when: has_no_aileron
---

# Rudder roll authority

**Canonical form**

```
V̄_V·B_md = V̄_V * B_spiral,md   (with B_spiral,mp likewise at minimum sink)
```

**Produces** [[rudder-roll-authority-md]] · [[rudder-roll-authority-mp]]  ·  **from** [[vertical-tail-volume]] · [[spiral-parameter-md]] · [[spiral-parameter-mp]]

**Kind: a law.** The product of two approved canon quantities. On an aircraft without ailerons the rudder rolls it
through sideslip: the rudder yaws the aircraft into a sideslip angle, and the dihedral turns that sideslip into a
rolling moment (Drela, Design Rules, Fig. 7). Drela measures the roll authority this gives by the product of the
vertical tail volume coefficient and the spiral parameter, `V̄_V·B` (Eq. 10).

**A canon quantity, not an evaluation product (maintainer decision 2026-10-27, #1274).** The canon computes, the
evaluation judges (A10): the product is computed here and judged in the evaluation layer, not formed there.

**Both speeds (maintainer decision 2026-10-27, #1274).** Like the spiral parameter, `B` exists at `V_md` and at `V_mp`,
so the product does too; `RRA_mp ≈ 0.58·RRA_md` for a parabolic polar. In the Drela evaluation `V_mp` governs — the
circling condition, as decided for the spiral of a rudder-only aircraft (2026-10-26, #1309).

**Applicability.** Only aircraft without ailerons (`has_no_aileron`); an aircraft with ailerons rolls with them.
`B` needs a fin or a V-tail (`has_vertical_tail`), so without one the inputs are not applicable and neither is this.
`V̄_V` and `B` are one value per neutral-point world (A11), so the product is too, world by world.

**Values, not verdicts (A10).** Drela's band `V̄_V·B = 0.10…0.20` (0.10 marginal, 0.20 very effective) belongs to the
evaluation (`drela.yaml`, rule `rudder-roll-authority`).

**Dimensional check.** 🟢 balances by hand — 1 · 1 (`B` numerically with `Γ_eq` in degrees, as Drela defines it, so
the band applies to the product as written).

**Source.** 🟢 SOURCED — Drela, MIT 16.Unified *Design Rules*, "Dihedral Sizing – Roll Control", Eq. 10.

**Validity in the RC/UAV regime (ADR 0028).** Drela's band is stated for RC and small aircraft. Inherits the
limits of its inputs: the strip-theory `Γ_eq` of the spiral parameter (derived, outboard panels over-weighted) and the
neutral point's limits through the arms.

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
