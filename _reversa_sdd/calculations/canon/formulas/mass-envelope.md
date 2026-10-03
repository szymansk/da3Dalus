---
canon: mass-envelope
entry: formula
kind: optimization
tool: OPT
shape: law
status: draft
output: speed-range-over-mass, climb-rate-over-mass, max-mass-level-flight, max-mass-lift-off, cg-envelope-over-mass
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/optimization
  - status/draft
---

# Mass envelope — what narrows with the take-off mass

**Canonical form**

```
for each mass m (a sweep; the airplane's mass is one point of it):
  V_S(m), V_max(m)          stall-speed problem / max-level-speed problem at mass m
  ROC_max(m)                best-rate-of-climb problem at mass m
  m_max,level:  maximize m   s.t.  exists V, alpha, n_prop:  L = m g,  T(V, n_prop) >= D(V, alpha)
  m_max,TO:     maximize m   s.t.  at V_TO(m), take-off configuration:  L = m g,  T - D >= 0
  x_fwd(m):     most forward x_CG trimmable at the stall, landing configuration, full up elevator
  x_aft(m):     most aft x_CG trimmable at V_max(m), full down elevator           (both as constructed)
```

**Produces** [[speed-range-over-mass]] · [[climb-rate-over-mass]] · [[max-mass-level-flight]] · [[max-mass-lift-off]] · [[cg-envelope-over-mass]]  ·  **from** [[airplane]] · [[gravity]] · [[air-density]] · [[thrust-at-airspeed]] · [[stall-speed-takeoff]] · [[takeoff-speed]]

**Kind: an optimisation problem family, swept over the mass** (maintainer, 2026-10-02 —
replaces the payload question: payload is *"how much mass may be added"*). Everything that
narrows with the take-off mass, as curves over `m`, and the masses at which it closes:

- **Speed range.** `V_S(m)` rises, `V_max(m)` falls; where they meet is `m_max,level` — beyond
  it no level flight is possible.
- **Climb.** `ROC_max(m)` falls with the mass and is zero at `m_max,level`.
- **Lift-off — the overloaded-bomber limit.** Whether the aircraft can still climb at its
  take-off speed in take-off configuration: `m_max,TO`, where the excess thrust at `V_TO(m)`
  vanishes. It lies **below** `m_max,level`: an aircraft can still cruise and yet no longer climb
  out of the lift-off. (`V_TO(m)` keeps the take-off reserve: `V_TO(m) = V_S,TO(m) · V_TO/V_S,TO`.)
- **Trim.** The CG range `[x_fwd(m), x_aft(m)]` in which the elevator, **as constructed**, trims
  the aircraft over its whole speed range (Sadraey Eq. 12.90: trim from `V_S` to `V_max` at both
  CG extremes): full up at the slow end (stall, landing configuration), full down at the fast
  end (`V_max(m)`). The neutral point stands beside it as the physical stability boundary; the
  canon reports which edge comes first and judges nothing (A10). A load `Δm` at `x_load` moves the
  CG by `Δm·(x_load − x_CG)/(m + Δm)` — whether that stays inside is read off, not computed here.

**How the front edge is solved (BRYAN, 2026-10-02).** Hold the angle of attack at the stall angle
`α_S(m)` of the stall-speed problem and leave the speed free: with full up elevator the tail
download raises the trimmed stall speed, so trimming at the clean `V_S` is infeasible. Bound
`x_CG < x_NP`: with full elevator, `Cm = 0` has a second root aft of the neutral point (the unstable
branch). For a conventional tail the aft edge from full down elevator at `V_max` lies far behind the
neutral point (BRYAN: > 90 % MAC), so the neutral point is the edge that comes first.

**Front edge across methods (BRYAN, 2026-10-03, `bryan_fwd_trim_avl.py`):** AeroBuildup 14.3 % MAC, AVL
10.4 % (CLAF thickness rule) and 13.5 % (CLAF 1.0). AeroBuildup lacks the wing downwash at the tail,
which *helps* the download at the front edge, so it is conservative here. AVL lacks the low-Re viscous
flap losses that NeuralFoil's flap model carries. The two errors run in opposite directions; spread
10.4–14.3 % MAC. **Kept crisp (A11 rule 5, maintainer 2026-10-03):** the front edge is computed with
AeroBuildup, which is conservative here. **Validity condition, declared (ADR 0020):** methods carrying the
wing–tail downwash place the front edge up to about 4 % MAC further forward. Revisit if a reference aircraft
shows a first-flight reserve of the order of that spread.

**Absorbs** `forward-cg-limit` (2026-10-02): its value is this envelope's front edge at the
current mass — a separate entry would be a second authority (ADR 0022).

**Validity conditions, declared (ADR 0020).** The tail must not itself be stalled at the trim
points; ground effect is not modelled (optimistic in the flare); at model scale the elevator works
at low Reynolds number, NeuralFoil's flap model there is unchecked.

**Source.** 🟢 Sadraey §11.6.3, §12.4, Eq. 12.90 (trim over the speed range); the level-flight
and climb problems as in §3.10.
