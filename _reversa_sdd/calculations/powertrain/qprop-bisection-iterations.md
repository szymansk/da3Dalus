---
name: qprop-bisection-iterations
symbol: 80
kind: constant
unit: iterations
cluster: powertrain
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Bisection iteration count

**Definition.** Fixed number of bisection halvings used to find the torque-balance RPM; there is no convergence tolerance test.

**Value.** `80`

**Formula — as the code writes it.**

```
for _ in range(80):
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:569` — `solve_qprop_operating_point`

**Consumed by.**

- in this graph: [[qprop-rpm-solution|Solved operating RPM]]
- outside it: `app/services/powertrain_performance.py:576`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Numerical-method parameter, not an engineering constant. No source in any vault; Drela's notes describe the torque-balance root but prescribe no iteration count or tolerance.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number with no explanation; 80 halvings drives the bracket far below double precision, so most iterations are wasted work with no stated rationale.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
