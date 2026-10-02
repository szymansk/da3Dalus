---
canon: max-level-speed
entry: formula
kind: optimization
tool: OPT
shape: law
status: draft
output: max-level-speed
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/optimization
  - status/draft
tex: \begin{aligned}V_{max} = \max_{V,\,\alpha,\,n_{prop}}\; & V \\ \text{u.d.N.}\; & L(V,\alpha) = m\,g \\ & T(V,n_{prop}) \ge D(V,\alpha) \\ & Q_m(n_{prop}) = Q_p(V,n_{prop})\end{aligned}
---

# Maximum level speed at full throttle

**Canonical form**

```
maximize over V, alpha, n_prop:   V
subject to:   L(V, alpha) = m * g
              T(V, n_prop) >= D(V, alpha)
              motor-propeller torque balance at (V, n_prop)
```

**Produces** [[max-level-speed]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[thrust-at-airspeed]]

**Kind: an optimisation problem**, the same shape as climb and turn: the highest speed at which full-throttle thrust still equals drag in level flight. Thrust and rpm from [[motor-propeller-equilibrium]] (route declared, `Q-PT-6`).

**Source.** 🟢 Sadraey §4.3.3 — maximum speed where thrust available equals thrust required.

**Was an input until 2026-10-01** — "maximum level-flight speed goal, defaulting to 28 m/s", the same for every aircraft. A computed property now. A *goal* for the maximum speed, if a mission needs one, is a requirement compared against this value in the Probe, not a substitute for it.

**Termination.** No bound active at the optimum; a failed solve returns no value (ADR 0020). If the thrust runs past the propeller's zero-thrust advance ratio first, the propeller — not the drag — limits the speed, and that is named.

**Full throttle is a ceiling, not an equality** (corrected 2026-10-01 after the first run on BRYAN). The thrust constraint reads `T(V, n_prop) ≥ …`: the pilot can always throttle back. Written as an equality, an aircraft with a large thrust excess has no level or steady solution at low speed — on BRYAN half the problems failed and the "tightest turn" came out at 26 m/s. At the optimum the inequality binds wherever thrust is what limits.

**Multi-start.** The problem has a spurious branch below the stall, where the polar's post-stall drag rise also satisfies `T ≥ D`; on BRYAN one start converged there (5.9 m/s at α = 16.7°). Solve from several starting speeds and keep the largest feasible `V` with no stall-side bound active.
