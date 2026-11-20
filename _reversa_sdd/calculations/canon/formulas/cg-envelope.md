---
canon: cg-envelope
entry: formula
kind: optimization
tool: OPT
shape: law
status: draft
output: cg-envelope-over-mass
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/optimization
  - status/draft
inputs:
  airplane: airplane
  m_current: aircraft-mass
  g: gravity
  rho: air-density
  mu: dynamic-viscosity
  a: speed-of-sound
  m_max_level: max-mass-level-flight
  x_np: neutral-point
  v_range: speed-range-over-mass
  airplane_ldg: airplane-landing
  delta_e_up: elevator-deflection-up
  delta_e_down: elevator-deflection-down
outputs:
  cg_envelope: cg-envelope-over-mass
embeds:
  - stall-speed.landing
variables: [aircraft-mass]
cost: minutes
---

# CG envelope — the trimmable centre-of-gravity range over the mass

**Split off from `mass-envelope` (gh-1420).** The entry `mass-envelope` produced this quantity beside the
speed range, the climb rate and the two largest masses. The trim range needs machinery the kernel does not
have (a pitching-moment evaluation at a given centre of gravity and elevator angle, a trim solve in the
centre of gravity), so it is its own formula. The text below is the part of the `mass-envelope` entry that
concerns it, moved unchanged.

**Depends on the mass sweep, produces no second `V_max`.** The sweep of this entry runs over the same masses
as [[mass-envelope]], from the current mass up to `m_max,level` ([[mass-envelope]] produces it:
input `m_max_level`). Its `V_max(m)` is the upper edge of the speed range that [[mass-envelope]]
produces (input `v_range`); this entry reads it and solves no level-speed problem of its own. Only the
stall problem in landing configuration (`stall-speed.landing`) is embedded.

**Maintainer decision (2026-11-19, gh-1420):** the trimmable CG range is its own entry until the kernel has a trim solve. The curves it reads belong to [[mass-envelope]]: `climb-rate-over-mass` is a curve result there, `speed-range-over-mass` (a curve pair) is not requestable yet, pending the maintainer.

**Canonical form**

```
for each mass m (a sweep; the airplane's mass is one point of it):
  x_fwd(m):     most forward x_CG trimmable at the stall, landing configuration, elevator at delta_e,up
  x_aft(m):     most aft x_CG trimmable at V_max(m), elevator at delta_e,down     (both given design inputs)
```

**Produces** [[cg-envelope-over-mass]]  ·  **from** [[airplane]] · [[gravity]] · [[air-density]] · [[dynamic-viscosity]] · [[speed-of-sound]] · [[neutral-point]] · [[max-mass-level-flight]] · [[speed-range-over-mass]] · [[airplane-landing]] · [[elevator-deflection-up]] · [[elevator-deflection-down]] · [[aircraft-mass]]

- **Trim.** The CG range `[x_fwd(m), x_aft(m)]` in which the elevator, **at the given deflections** `δ_e,up` / `δ_e,down`, trims
  the aircraft over its whole speed range (Sadraey Eq. 12.90: trim from `V_S` to `V_max` at both
  CG extremes): `δ_e,up` at the slow end (stall, landing configuration), `δ_e,down` at the fast
  end (`V_max(m)`). The neutral point stands beside it as the physical stability boundary; the
  canon reports which edge comes first and judges nothing (A10). A load `Δm` at `x_load` moves the
  CG by `Δm·(x_load − x_CG)/(m + Δm)` — whether that stays inside is read off, not computed here.

**How the front edge is solved (BRYAN, 2026-10-02).** Hold the angle of attack at the stall angle
`α_S(m)` of the stall-speed problem and leave the speed free: with the elevator at `δ_e,up` the tail
download raises the trimmed stall speed, so trimming at the clean `V_S` is infeasible. Bound
`x_CG < x_NP`: with the elevator at its given deflection, `Cm = 0` has a second root aft of the neutral point (the unstable
branch). For a conventional tail the aft edge from the elevator at `δ_e,down` at `V_max` lies far behind the
neutral point (BRYAN: > 90 % MAC), so the neutral point is the edge that comes first.

**Front edge across methods (BRYAN, 2026-10-03, `bryan_fwd_trim_avl.py`):** AeroBuildup 14.3 % MAC, AVL
10.4 % (CLAF thickness rule) and 13.5 % (CLAF 1.0). AeroBuildup lacks the wing downwash at the tail,
which *helps* the download at the front edge, so it is conservative here. AVL lacks the profile drag of the deflected
surface, which AeroBuildup carries only as a Hoerner drag factor on the clean section (no flap separation;
`kulfan_airfoil.py:211-255`). The two errors run in opposite directions 🟡 INFERRED — the conclusion
rested on AeroBuildup carrying NeuralFoil's low-Re flap losses, a premise the #1181 correction withdrew,
so it is not re-established (open, STAND §10); spread 10.4–14.3 % MAC. **Kept crisp (A11 rule 5, maintainer 2026-10-03):** the front edge is computed with
AeroBuildup, which is conservative here. **Validity condition, declared (ADR 0020):** methods carrying the
wing–tail downwash place the front edge up to about 4 % MAC further forward. Revisit if a reference aircraft
shows a first-flight reserve of the order of that spread.

**Absorbs** `forward-cg-limit` (2026-10-02): its value is this envelope's front edge at the
current mass — a separate entry would be a second authority (ADR 0022).

**Validity conditions, declared (ADR 0020).** The tail must not itself be stalled at the trim
points; ground effect is not modelled (optimistic in the flare); at model scale the elevator works
at low Reynolds number, and AeroBuildup represents its deflection only as an effective-angle shift on the
clean airfoil with a Hoerner drag factor (no flap separation, δ range of the fit unknown; `kulfan_airfoil.py:211-255`).

**Source.** 🟢 Sadraey §11.6.3, §12.5.4, Eq. 12.90 (trim over the speed range).

**Validity in the RC/UAV regime (ADR 0028).** The trim edges rest on AeroBuildup, which ignores main-wing downwash on the horizontal tail and so over-predicts tail effectiveness (Sharpe 2024 §5.4), consistent with the declared 10.4–14.3 % MAC spread. Above about 30° of elevator deflection the flow over the horizontal tail separates (Sadraey §12.5.4, context of Eq. 12.90), which bounds the "tail not stalled" condition the entry declares. `V_S(m)` inherits the Reynolds sensitivity of `C_L,max` (Anderson §4.3; Lennon Ch. 1–3).

## Implementations (0)

None in aero_kernel; no register node is mapped to this entry.

Blocked, and why (new text, gh-1420, undated): the entry needs two things the kernel does not have. First, a trim solve: a pitching-moment evaluation at a given centre of gravity and elevator angle, and a root in the centre of gravity for each mass. Second, a curve result: its output is a curve pair, and a curve is not a result of the kernel yet (ARCHITECTURE ch. 8.3; gh-1424 adds it). It also depends on `speed-range-over-mass`, a curve pair that is not requestable yet: until the maintainer decides how the speed range is expressed (as a curve pair result or as two curve quantities) this entry has no input it can read as a result, which blocks it in addition to the missing trim solve.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Assumptions** — the conditions the method requires (bracketing, continuity, range)
- [ ] **Convergence** — the criterion, and what is returned and declared on failure
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
