---
canon: spiral-parameter
entry: formula
kind: law
tool: APP
shape: law
status: approved
output: spiral-parameter-md, spiral-parameter-mp
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
  - dim/procedural
  - shape/law
  - kind/law
  - status/approved
inputs:
  airplane: airplane
  s_ref: wing-reference-area
  b_ref: wing-span
  l_v_cg: vertical-tail-arm
  m: aircraft-mass
  g: gravity
  rho: air-density
  v_md: minimum-drag-speed
  v_mp: minimum-sink-speed
outputs:
  b_spiral_md: spiral-parameter-md
  b_spiral_mp: spiral-parameter-mp
applications:
  - id: with_vertical_tail
    when: has_vertical_tail
---

# Spiral parameter (Drela's B)

**Canonical form**

```
Gamma_eq := geometry(airplane)   # strip-theory equivalent dihedral in degrees, derived below
C_L(V)   = m * g / (0.5 * rho * V^2 * S_ref)
B_md     = l_V_CG * Gamma_eq / (b_ref * C_L(V_md))
B_mp     = l_V_CG * Gamma_eq / (b_ref * C_L(V_mp))
```

Drela's Eq. 8 names no flight condition for `C_L`. The canon computes **both** values as separate
outputs (maintainer 2026-10-26, #1309): `B_md` at the minimum-drag speed and `B_mp` at the minimum-sink
speed, the circling condition. With a parabolic polar `C_L(V_mp) = √3·C_L(V_md)`, so `B_mp ≈ 0.58·B_md`.
Which value governs is a judgement of the evaluation, by control layout (A10).

**Equivalent dihedral `Gamma_eq` of a polyhedral wing — DERIVED, not printed.** No source prints it:
Drela defines a single dihedral, and Beron-Rawdon (1990) is unread. The canon adopts the strip-theory
weighting of the dihedral contribution to `C_lβ` (maintainer 2026-10-26, option (a)), applying Sadraey
Eq. 5.35 (`Δα ≈ β·Γ`) per strip. Over the semi-span of the main wing, with `y` the spanwise coordinate
from the aircraft centre line and `c(y)` the local chord:

```
Gamma_eq = ∫ Gamma(y) * c(y) * y dy  /  ∫ c(y) * y dy
```

For a wing of panels `i` with constant panel dihedral `Gamma_i` and chord linear in `y`,
`W_i = ∫ c(y) * y dy` over panel `i` (closed form: Simpson's rule is exact for this quadratic). Check: inner 60 % flat, outer 40 %
at 10°, constant chord → `Gamma_eq ≈ 6.4°` (the root-to-tip line would give about 4°, which is rejected).

*Conditions.* Constant section lift-curve slope along the span; sweep neglected; induced-flow coupling
between strips neglected. Strip theory therefore **over-weights outboard panels**. *Later cross-check:*
AVL `C_lβ` on a polyhedral fleet member. The `Gamma_eq` of the eHawk prototype script uses the same rule,
so there is one producer (ADR 0022).

`S_ref` and `b_ref` are [[wing-reference-area]] and [[wing-span]], produced by [[airplane-geometry]] (AeroSandbox's
definition, measured on the main wing; maintainer 2026-10-25). This entry does not read the wing area or span
from the airplane itself: one producer per number a user sees (ADR 0022). Only the (equivalent) dihedral `Gamma_eq` is read from the airplane;
the arm `l_V,CG` is [[vertical-tail-arm]], measured from the computed design CG ([[centre-of-gravity-design]]) as Drela defines it
(maintainer 2026-10-25, #1272); the former `l_V,25` is removed (ADR 0021). The arm is an interval over the neutral-point worlds, so `B` is one value per world (A11).

**Produces** [[spiral-parameter-md]] · [[spiral-parameter-mp]]  ·  **from** [[airplane]] · [[wing-reference-area]] · [[wing-span]] · [[vertical-tail-arm]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[minimum-drag-speed]] · [[minimum-sink-speed]]

**Kind: a law.** A geometric spiral-stability measure for aircraft with a tail, deterministic and
independent of any solver — the RC practice's counterpart to the spiral criterion of
[[lateral-static-stability-md]] (K27).
The spiral criterion is also computed at V_mp by [[lateral-static-stability-mp]].

**Precondition.** The aircraft has a fin or a V-tail behind the wing (`l_V,CG` is a tail arm). Not computed
for tailless aircraft.

**Values, not verdicts (A10).** Drela: B > 5 spirally stable, ≈ 5 neutral, 3–4 no difficulty for an
experienced pilot; rudder-only models V̄_V·B = 0.10–0.20 for roll authority. Bands belong to the evaluation.

**Dimensional check.** 🟢 balances by hand — m / m; `Γ_eq` enters as a number in degrees (Drela's definition); the checker sees a geometry extraction (procedural).

**Source.** 🟡 PARTIAL — `B` itself: 🟢 Drela, MIT 16.Unified *Design Rules*, Eqs 8–10. `Gamma_eq` for polyhedral wings: derived
here from Sadraey Eq. 5.35 per strip, **not printed in any source** (Beron-Rawdon, *Model Aviation* 9/1990, is unread);
adopted on the maintainer's authority (2026-10-26, #1309).

**Validity in the RC/UAV regime (ADR 0028).** Stated for RC sailplanes and models; the stability threshold is empirical.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/spiral_parameter.py` | EXACT | 🟢 | `Gamma_eq` is `aero_kernel/dihedral.py`: the weight `∫c y dy` of each panel in closed form (the chord is linear in y, so the integral is exact, as Simpson's rule is for this quadratic), the panel dihedral `atan2(dz, dy)` of the oriented chain, the weighting from the root rib (no wing, no weight, in a centreline gap); an unmirrored main wing has no semi-span and is refused (`unsupported_layout`); `B_md` and `B_mp` per neutral-point world, from the arm |

## Approval

- [x] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [x] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [x] **Dimensions** — the check balances
- [x] **Implementations** — all agree, or each deviation is declared and justified
- [x] **Preconditions** — every binding condition holds, or the violation is ticketed
- [x] **Inputs approved** — no formula is approvable before its inputs are

> **Approved** (maintainer, 2026-10-26): Drela's spiral parameter B = l_V,CG·Γ_eq/(b_ref·C_L) (Design Rules
> Eqs 8–10, after Rawdon), at **both** V_md and V_mp (Drela names no flight condition; B ∝ 1/C_L, so B_mp ≈ 0.58
> B_md for a parabolic polar). The evaluation decides which governs by control layout: aileron aircraft can
> counter-bank (yellow), rudder-only aircraft cannot hold against the spiral while circling (B_mp red) — "einem
> Flugzeug nur mit SL kann man nicht stützen". Γ_eq by strip theory, ∫Γ·c·y dy / ∫c·y dy, **derived, not
> printed** (Sadraey Eq. 5.35 per strip; constant section lift slope, sweep and induced coupling neglected →
> outboard panels over-weighted); source PARTIAL, adopted on the maintainer's authority; to be cross-checked
> against AVL C_lβ on a polyhedral fleet member. The root-to-tip-line rule is rejected as wrong. Arm from the
> design CG (approved [[vertical-tail-arm]]); one value per neutral-point world (A11). No kernel
> implementation yet (#1274).
