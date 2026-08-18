---
name: polar-j-clamp
symbol: J_clamp
kind: quantity
unit: dimensionless
cluster: powertrain
user_visible: false
source_status: PARTIAL
---

# Clamped advance ratio for interpolation

**Definition.** Requested advance ratio clipped into the polar dataset's [J_min, J_max] range so np.interp never extrapolates.

**Formula — as the code writes it.**

```
J_clamp = float(np.clip(J, J_min, J_max))
```

**Inputs.** [[curve-advance-ratio|Advance ratio per velocity sample]]

**Produced by.** `app/services/powertrain_performance.py:326` — `interpolate_ct_cp_pe`

**Consumed by.**

- in this graph: [[polar-cp|Propeller power coefficient]] · [[polar-ct|Propeller thrust coefficient]] · [[polar-pe|Propeller efficiency from polar]]
- outside it: `app/services/powertrain_performance.py:328` · `app/services/powertrain_performance.py:329` · `app/services/powertrain_performance.py:335` · `app/services/powertrain_performance.py:336`

**Source.** 🟡 PARTIAL

> Brandt, J.B. & Selig, M.S., 'Propeller Performance Data at Low Reynolds Numbers', AIAA 2011-1255, §III eqs. 4-7 defines J = V/(nD) and the measured C_T(J), C_P(J) tables that the clamp operates on. The clamping/no-extrapolation policy itself is an implementation choice with no source.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
J = V / (n D)
```

**⚠️ Divergence from the source.** Brandt & Selig note that beyond the measured J range the propeller enters the windmill state where thrust becomes zero or negative. Holding C_T and C_P at the boundary value, as the clamp does, does not reproduce that behaviour.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Silent clamp — the value is truncated and only a boolean warning flag is returned; the clamp itself is never reported per-sample (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Clamp J to dataset range for interpolation`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
