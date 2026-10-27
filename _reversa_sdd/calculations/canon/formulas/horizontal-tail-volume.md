---
canon: horizontal-tail-volume
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: horizontal-tail-volume
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/law
  - status/draft
inputs: {airplane: airplane, s_ref: wing-reference-area, c_mac: mean-aerodynamic-chord, l_h_cg: horizontal-tail-arm}
outputs: {v_h: horizontal-tail-volume}
applications:
  - id: with_horizontal_tail
    when: has_horizontal_tail
---

# Horizontal tail volume

**Canonical form**

```
S_H := Wing.area(type="planform", include_centerline_distance=True)   # ASB, the one horizontal_tail surface
V_H = S_H * l_H_CG / (S_ref * c_MAC)
```

`S_ref` and `c_MAC` are [[wing-reference-area]] and [[mean-aerodynamic-chord]], produced by [[airplane-geometry]]
(AeroSandbox's definition, measured on the main wing). This entry does not read the wing area or chord from the
airplane itself: one producer per number a user sees (ADR 0022). Only the tail area `S_H` is read from the airplane,
as AeroSandbox's `Wing.area(type="planform", include_centerline_distance=True)` of the one surface typed
`horizontal_tail`, both flags passed explicitly (no library defaults): the gross planform through the fuselage,
the same convention as the reference wing (maintainer 2026-10-25, #1262). The arm `l_H,CG` is
[[horizontal-tail-arm]], from the design CG as Drela defines it (#1272); it is an interval over the neutral-point
worlds, so `V_H` is one value per world (A11).

**Reference chord (maintainer decision 2026-10-27, #1273).** Drela writes the average chord `c = S/b`; the canon uses
`c_MAC`, the standard definition (Sadraey) and the one reference chord the canon already has. Drela himself notes that
the MAC is "very nearly equal to the simple-average chord" for most wings. The difference is declared, not hidden:
for a straight-tapered wing `c_MAC/(S/b) = (4/3)(1+λ+λ²)/(1+λ)²` — 1.000 for a rectangular wing, about 1.04 at
λ = 0.5 — so `V_H` here is up to a few per cent below Drela's value, and his band is read against it as is.

**V-tail.** A V-tail has no horizontal tail, so this application does not apply to it. Its horizontal share
`S·cos²ν` (ν = panel angle to the horizontal) comes with the V-tail neutral point, #1208.

**Produces** [[horizontal-tail-volume]]  ·  **from** [[airplane]] · [[wing-reference-area]] · [[mean-aerodynamic-chord]] · [[horizontal-tail-arm]]

**Kind: a law.** A geometric ratio, deterministic and independent of any solver. It controls the neutral-point
position and the sensitivity to the CG (Drela, Design Rules, Eq. 5).

**Values, not verdicts (A10).** Drela's band `V_H = 0.30…0.60` (Eq. 4; too small: pitch "wanders", very sensitive to
the CG) belongs to the evaluation.

**Dimensional check.** 🟢 balances by hand — m²·m / (m²·m); the checker sees a geometry extraction (procedural).

**Source.** 🟢 SOURCED — Drela, MIT 16.Unified *Design Rules*, Eq. 3 (definition) and Eq. 4 (band); Sadraey,
*Aircraft Design*, horizontal tail volume coefficient with the MAC (§6.4).

**Validity in the RC/UAV regime (ADR 0028).** Exact as geometry; Drela's band is stated for RC and small aircraft.
Inherits the neutral point's limits through the arm (fuselage not modelled → CG aft-biased, arm slightly short).

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
