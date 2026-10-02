---
canon: max-sustained-turn-rate
entry: formula
kind: optimization
shape: law
status: draft
output: max-sustained-turn-rate, max-sustained-turn-rate-speed
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/optimization
  - status/draft
tex: \begin{aligned}\omega_{max} = \max_{V,\,\alpha,\,n,\,n_{prop}}\; & \frac{g\sqrt{n^2-1}}{V} \\ \text{u.d.N.}\; & L(V,\alpha) = n\,m\,g \\ & T(V,n_{prop}) \ge D(V,\alpha) \\ & Q_m(n_{prop}) = Q_p(V,n_{prop}) \\ & 1 \le n \le n_{lim}\end{aligned}
---

# Fastest sustained turn at full throttle

**Canonical form**

```
maximize over V, alpha, n, n_prop:   g * sqrt(n^2 - 1) / V
subject to:   L(V, alpha) = n * m * g
              T(V, n_prop) >= D(V, alpha)
              motor-propeller torque balance at (V, n_prop)
              1 <= n <= n_lim
```

**Produces** [[max-sustained-turn-rate]] · [[max-sustained-turn-rate-speed]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[limit-load-factor]] · [[thrust-at-airspeed]]

**Kind: an optimisation problem**, the same shape as the extremal closures and the climb. Variables: airspeed `V`, angle of attack `alpha`, load factor `n`, propeller speed `n_prop`. A **sustained** turn: level, at constant speed, so thrust equals drag; the drag comes from AeroBuildup at the turn's `alpha`, so the induced drag of the higher lift is in it. Thrust and rpm as in the climb ([[motor-propeller-equilibrium]], route declared per `Q-PT-6`).

**Kinematics of the coordinated level turn.** `omega = g·sqrt(n² − 1) / V`, `r = V² / (g·sqrt(n² − 1))`; equivalently `n = 1/cos(phi)` (Lennon, *Basics of R/C Model Aircraft Design*, Ch. 21, as a vector sum of weight and centrifugal force). The bank angle is the result, not an input.

**Termination — which limit binds is the answer.** Three things can stop the turn, and the optimum says which:
- **thrust** — `T = D` binds, no bound active: the propulsion limits the turn;
- **the wing** — the optimum sits at the lift maximum of the polar: the aircraft can hold the turn only at the edge of stall;
- **the structure** — `n = n_lim` active: the turn is limited by the user's load limit, not by the aircraft's aerodynamics.

The last two are **declared active bounds**, named in the result like `gamma = 90°` in the climb. A failed solve returns no value (ADR 0020).

**Why not a bank angle as input.** A turn at a pilot-chosen bank angle says something about the pilot's choice, not about the aircraft. The stall speed in such a turn is the [[stall-speed]] problem with the load factor bound — one authority — which replaces `V_S,turn = V_S·sqrt(n)`: the shortcut assumes the straight-flight `C_L,max`, while the problem evaluates it at the turn's own Reynolds number. Both `turn-load-factor` and `stall-speed-in-turn` were deleted on 2026-10-01.

**Not here: the instantaneous turn.** Pulling beyond the sustained limit trades speed or height for a tighter turn, bounded by stall and structure. Its key number, the corner speed `V* = V_S·sqrt(n_lim)` — above it a full elevator input can break the aircraft — belongs to the flight envelope (§3.10, dive) and is noted there.

**Full throttle is a ceiling, not an equality** (corrected 2026-10-01 after the first run on BRYAN). The thrust constraint reads `T(V, n_prop) ≥ …`: the pilot can always throttle back. Written as an equality, an aircraft with a large thrust excess has no level or steady solution at low speed — on BRYAN half the problems failed and the "tightest turn" came out at 26 m/s. At the optimum the inequality binds wherever thrust is what limits.
