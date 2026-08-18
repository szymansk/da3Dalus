---
name: qprop-rpm-solution
symbol: rpm_sol
kind: quantity
unit: rpm
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Solved operating RPM

**Definition.** The RPM at which motor torque equals propeller torque demand, found by bisection between the current-ceiling floor and the free-running bound. Degenerate cases snap to a bracket end.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
rpm_mid = 0.5 * (rpm_lo + rpm_hi) ... rpm_sol = 0.5 * (rpm_lo + rpm_hi)
```

**Inputs.**

- [[qprop-residual|Torque-balance residual]]
- [[qprop-rpm-free|Free-running RPM]]
- [[qprop-rpm-at-imax|RPM at the current ceiling]]  — *⊣ limit*
- [[qprop-bisection-iterations|Bisection iteration count]]

**Produced by.** `app/services/powertrain_performance.py:576` — `solve_qprop_operating_point`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Advance ratio per velocity sample` · `Thrust per velocity sample` · `Nearest-RPM polar row group` · `Solved terminal current` · `Solved shaft power (QPROP)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:578` · `app/services/powertrain_performance.py:579` · `app/services/powertrain_performance.py:590` · `app/services/powertrain_performance.py:724`

**Source.** 🟢 SOURCED

> Drela, 'DC Motor / Propeller Matching' theory notes, §1.1 — the motor-propeller operating point is the simultaneous solution of the voltage equation V = iR + Omega/Kv and the torque equation Q_m = (I - i0)/K_Q against the propeller torque demand Q_prop(n).
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Solve Q_motor(I(n)) = Q_prop(n) for n, with I(n) from V = i R + Omega/Kv
```

**⚠️ Divergence from the source.** The source states the solution is the root of the torque balance. The code's three degenerate branches return a bracket endpoint instead of a root and label it identically, so a saturated (non-converged) case is indistinguishable from a solved one.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The three degenerate branches (lines 556, 564, 567) silently return a bracket endpoint instead of a solved root and emit no DesignWarning (ADR 0020) — the caller cannot tell a converged solution from a saturated one.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "Eliminating I via the back-EMF relation gives a single monotone equation in n; we bracket and bisect on RPM."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
