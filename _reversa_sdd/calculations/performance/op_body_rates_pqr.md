---
name: op_body_rates_pqr
symbol: p, q, r
kind: quantity
unit: rad/s
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
---

# Operating-point body rates

**Definition.** Body-axis roll/pitch/yaw rates for a turn target, zeros for non-turns.

**Formula — as the code writes it.**

```
tk = turn_kinematics(bank_deg=float(bank_deg), velocity=float(velocity)); return (round(tk.p, 6), round(tk.q, 6), round(tk.r, 6))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:152` — `_op_turn_rates`

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:657-659 (asb.OperatingPoint)` · `app/services/operating_point_generator_service.py:992-994 (TrimmedPoint p/q/r)` · `app/models/analysismodels.py (p/q/r columns)`

**Source.** 🟡 PARTIAL

> AeroSandbox 4.2 OperatingPoint reference: 'p, q, r are body-axes roll, pitch, yaw rates in rad/s' — unit contract confirmed. No turn-kinematics derivation found in Scholz/Sadraey vault (no turn-performance page), none in Anderson Fundamentals of Aerodynamics 6e (turning flight is not in that book).
>
> — via `aerosandbox-expert, aircraft-design-scholz, aerodynamics-expert`

**The source states it as.**

```
psi_dot = g·tan(phi)/V ; p = -psi_dot·sin(theta) ; q = psi_dot·cos(theta)·sin(phi) ; r = psi_dot·cos(theta)·cos(phi)
```

**⚠️ Divergence from the source.** The Euler-rate-to-body-rate transformation for a steady turn is standard flight mechanics, but is NOT attributable inside any of the four expert sources consulted — it needs a flight-dynamics reference (Etkin/Stevens class) that this project does not have. Additionally the caller passes alpha_deg=0 by default, so theta=0 and p is always 0 and q/r carry no angle-of-attack correction. The round(...,6) is an undocumented precision constant.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Rounded to 6 decimals with no stated reason; a magic precision constant.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
