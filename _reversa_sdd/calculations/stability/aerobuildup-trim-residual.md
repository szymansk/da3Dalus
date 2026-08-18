---
name: aerobuildup-trim-residual
symbol: r(δ)
kind: quantity
unit: – (coefficient units)
cluster: stability
user_visible: false
source_status: SOURCED
---

# AeroBuildup trim residual

**Definition.** Difference between the achieved and target aerodynamic coefficient at a given control deflection; the function driven to zero.

**Formula — as the code writes it.**

```
return _to_scalar(coeff_val) - target_val
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/aerobuildup_trim_service.py:164` — `trim_with_aerobuildup.residual`

**Consumed by.**

- in this graph: [[trim-bracket-test|Root bracketing test]] · [[trimmed-deflection|Trimmed control deflection]]
- outside it: `app/services/aerobuildup_trim_service.py:169,170,214 (brentq)`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.4 — longitudinal trim is the condition ΣF_z = 0, ΣF_x = 0, ΣM_cg = 0 (Eqs. 12.77–12.79), reduced to the coefficient balance Eq. 12.85 (C_mo + C_mα·α + C_mδE·δ_E = −T·z_T/(qSC̄)). Driving the difference between achieved and target coefficient to zero is exactly the root-finding form of that condition.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
ΣM_cg = 0 ⇒ C_mo + C_mα·α + C_mδE·δ_E + T·z_T/(qSC̄) = 0   (Sadraey Eqs. 12.79, 12.85)
```

**⚠️ Divergence from the source.** Sadraey solves the trim as a 2×2 linear system in (α, δ_E) simultaneously (Eq. 12.86, Cramer's rule Eq. 12.90). The code solves a 1-D root in the deflection alone at fixed α — valid only when α is externally fixed by the operating point, which is the app's convention but is a narrower problem than the source's.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
