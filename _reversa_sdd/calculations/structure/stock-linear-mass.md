---
name: stock-linear-mass
symbol: ρ·A
kind: quantity
unit: kg/m
cluster: structure
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/anomaly
---

# Linear mass of a stock cross-section

**Definition.** Mass per unit length of a candidate stock item — the ranking objective when picking the lightest adequate stock.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
di = inner_d_mm if inner_d_mm is not None else 0.0
area_mm2 = math.pi / 4.0 * (outer_d_mm**2 - max(0.0, di) ** 2)
area_m2 = area_mm2 * 1e-6
return density_kg_m3 * area_m2
```

**Inputs.**

- [[stock-density-fallback|Stock density fallback]]  — *⤵ fallback*
- [[mm2-to-m2-factor|Square-millimetre to square-metre factor]]  — *ε tolerance*

**Produced by.** `app/services/spar_plan_service.py:88` — `_linear_mass`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/spar_plan_service.py:161` · `app/services/spar_plan_service.py:190`

**Source.** 🟡 PARTIAL

> No source states this. Elementary: mass per unit length = density × cross-section area. Nearest attributable context: RC-Network Wiki, "Kohlefaser (Materialkunde)", https://wiki.rc-network.de/wiki/Kohlefaser — carbon fibre selected for "very low density: excellent strength-to-weight ratio", i.e. minimum mass per unit length is the correct selection objective.
>
> — via `rc-aircraft-designer`

**⚠️ Anomaly.** The selected stock's linear mass is computed and used only for ordering — it is never returned, never summed into a spar mass, and never reaches the response. The plan endpoint reports no mass at all, so a snap that changes OD by 50 % has no visible mass consequence.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Used as the ranking objective: minimum ρ·A = lightest per unit length.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
