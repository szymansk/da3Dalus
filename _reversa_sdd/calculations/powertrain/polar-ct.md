---
name: polar-ct
symbol: Ct
kind: quantity
unit: dimensionless
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

# Propeller thrust coefficient

**Definition.** Thrust coefficient T/(rho.n^2.D^4) linearly interpolated over J from the APC PER3 polar rows, then clamped at zero to discard the negative windmilling tail.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
Ct_interp = float(np.interp(J_clamp, Js, Cts)) ; Ct_interp = max(Ct_interp, 0.0)
```

**Inputs.**

- [[polar-j-clamp|Clamped advance ratio for interpolation]]  — *⊣ limit*
- [[polar-samples-input|Propeller polar rows]]

**Produced by.** `app/services/powertrain_performance.py:328` — `interpolate_ct_cp_pe`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Thrust per velocity sample` · `Propeller efficiency from polar` · `Propeller thrust (operating-point helper)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:332` · `app/services/powertrain_performance.py:336` · `app/services/powertrain_performance.py:406` · `app/services/powertrain_performance.py:748`

**Source.** 🟢 SOURCED

> Brandt, J.B. & Selig, M.S., 'Propeller Performance Data at Low Reynolds Numbers', AIAA 2011-1255, §III, eqs. 4-7 (UIUC low-Reynolds propeller database): C_T = T / (rho n^2 D^4).
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
C_T = T / (rho * n^2 * D^4)
```

**⚠️ Divergence from the source.** The source states 'The windmill state occurs when J reaches a value where thrust becomes zero or negative' — negative C_T is a real, measured regime in the same dataset the code reads. Clamping C_T at 0 discards it, so windmilling drag is reported as zero drag rather than as drag.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Deliberate clamp at 0 documented as out-of-scope, but no DesignWarning is emitted when it bites (ADR 0020) — a windmilling prop silently reports zero drag.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `module docstring: "Ct is clamped at 0 — the slightly-negative tail past zero-thrust is ignored; windmilling drag is out of scope for this ticket." (UAT note, gh-615 comment #4)`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
