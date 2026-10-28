---
canon: horizontal-tail-volume
entry: formula
kind: law
tool: APP
shape: law
status: approved
output: horizontal-tail-volume
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/law
  - status/approved
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
S_H := sum_i S_i*cos^2(nu_i)                                          # the one v_tail surface (#1208), per panel
V̄_H = S_H * l_H_CG / (S_ref * c_MAC)
```

`S_ref` and `c_MAC` are [[wing-reference-area]] and [[mean-aerodynamic-chord]], produced by [[airplane-geometry]]
(AeroSandbox's definition, measured on the main wing). This entry does not read the wing area or chord from the
airplane itself: one producer per number a user sees (ADR 0022). Only the tail area `S_H` is read from the airplane,
as AeroSandbox's `Wing.area(type="planform", include_centerline_distance=True)` of the one surface typed
`horizontal_tail` (a `v_tail`: see below), both flags passed explicitly (no library defaults): the gross planform through the fuselage,
the same convention as the reference wing (maintainer 2026-10-25, #1262). The arm `l_H,CG` is
[[horizontal-tail-arm]], from the design CG as Drela defines it (#1272); it is an interval over the neutral-point
worlds, so `V̄_H` is one value per world (A11).

**Reference chord (maintainer decision 2026-10-27, #1273).** Drela writes the average chord `c = S/b`; the canon uses
`c_MAC`, the standard definition (Sadraey) and the one reference chord the canon already has. Drela himself notes that
the MAC is "very nearly equal to the simple-average chord" for most wings. The difference is declared, not hidden:
for a straight-tapered wing `c_MAC/(S/b) = (4/3)(1+λ+λ²)/(1+λ)²` — 1.000 for a rectangular wing, about 1.04 at
λ = 0.5 — so `V̄_H` here is up to a few per cent below Drela's value, and his band is read against it as is.

**V-tail (maintainer decision 2026-10-27, #1208).** A V-tail counts as the horizontal tail (`has_horizontal_tail`
includes `v_tail`): `S_H` is its effective area `S_h,eff = sum_i S_i cos^2(nu_i)` over the panels `i`, with `S_i` the
true area of the panel from AeroSandbox (`Wing.area(type="planform", include_centerline_distance=False)` of the
panel) and `nu_i` the panel angle to the horizontal from the section positions (`cos^2(nu_i) = dy_i^2/(dy_i^2 + dz_i^2)`,
the geometry sections, because AeroSandbox has no panel-angle accessor). It is the same `S_h,eff` the
[[neutral-point]] uses, and the complement of the fin share of [[vertical-tail-volume]]. The arm is to the
V-tail's own quarter-chord MAC ([[horizontal-tail-arm]]). Source: see [[neutral-point]] (Purser and Campbell, NACA Report
823, 🟡; the print was not available).

**Produces** [[horizontal-tail-volume]]  ·  **from** [[airplane]] · [[wing-reference-area]] · [[mean-aerodynamic-chord]] · [[horizontal-tail-arm]]

**Kind: a law.** A geometric ratio, deterministic and independent of any solver. It controls the neutral-point
position and the sensitivity to the CG (Drela, Design Rules, Eq. 5).

**Values, not verdicts (A10).** Drela's band `V̄_H = 0.30…0.60` (Eq. 4; too small: pitch "wanders", very sensitive to
the CG) belongs to the evaluation.

**Dimensional check.** 🟢 balances by hand — m²·m / (m²·m); the checker sees a geometry extraction (procedural).

**Source.** 🟢 SOURCED — Drela, MIT 16.Unified *Design Rules*, Eq. 3 (definition) and Eq. 4 (band); Sadraey,
*Aircraft Design*, horizontal tail volume coefficient with the MAC (§6.4).

**Validity in the RC/UAV regime (ADR 0028).** Exact as geometry; Drela's band is stated for RC and small aircraft.
Inherits the neutral point's limits through the arm (fuselage not modelled → CG aft-biased, arm slightly short).

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/horizontal_tail_volume.py` | EXACT | 🟢 | `S_H` is ASB's `Wing.area(type="planform", include_centerline_distance=True)` of the one `horizontal_tail` surface, from the GEO adapter (`aero_kernel/solvers/geometry.py`, `horizontal_tail_area` → `asb_airplane.horizontal_tail_area`), both flags passed in code; `S_ref`, `c_MAC` and the arm are the canon quantities, none recomputed; one value per neutral-point world. The surface is chosen by `surface_type == horizontal_tail` only (`tail_key`, as the arm): a `v_tail` is the one surface too (`has_horizontal_tail` counts it, `aero_kernel/graph.py`) and `S_H` is then `S_h,eff = sum S_i cos^2(nu_i)` over its panels (`asb_airplane._v_tail_horizontal_share`, #1208); a horizontal tail beside a V-tail, or two of either, is `unsupported_layout`. The reference chord is `c_MAC`, not Drela's `S/b` (declared above, maintainer 2026-10-27) |

## Approval

- [x] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [x] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [x] **Dimensions** — the check balances
- [x] **Implementations** — all agree, or each deviation is declared and justified
- [x] **Preconditions** — every binding condition holds, or the violation is ticketed
- [x] **Inputs approved** — no formula is approvable before its inputs are

> **Approved** (maintainer, 2026-10-27): V̄_H = S_H · l_H,CG / (S_ref · c_MAC) (Drela Design Rules Eq. 3, band Eq. 4
> in the evaluation; Sadraey §6.4), with the reference chord c_MAC rather than Drela's S/b (decision 2026-10-27,
> #1273; difference declared: ≤ a few per cent for straight-tapered wings), the arm from the design CG (approved
> [[horizontal-tail-arm]]), S_ref and c_MAC from the approved [[airplane-geometry]], and S_H as AeroSandbox's
> `Wing.area(type="planform", include_centerline_distance=True)` of the one horizontal_tail surface — the gross
> planform through the fuselage, the same convention as the reference wing (#1262). One value per neutral-point
> world (A11). V-tail: S_H = Σ S_i·cos²ν_i per panel (maintainer decision 2026-10-27, #1208).
