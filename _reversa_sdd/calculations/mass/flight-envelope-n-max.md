---
name: flight-envelope-n-max
symbol: n_max
kind: quantity
unit: g (dimensionless load factor)
cluster: mass
user_visible: true
source_status: SOURCED
---

# Design limit load factor (published)

**Definition.** Peak design load factor published to the computation context; currently just the effective g_limit design assumption, guarded to be positive.

**Formula — as the code writes it.**

```
"flight_envelope_n_max": (g_limit_effective if g_limit_effective is not None and g_limit_effective > 0 else None)
```

**Inputs.** [[mass--g-limit|Design load factor limit]]

**Produced by.** `app/services/assumption_compute_service.py:719` — `recompute_assumptions`

**Consumed by.**

- outside it: `app/services/mission_kpi_service.py:247 (_kpi_maneuver)`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §10.4.1 ("Ultimate Load Factor and Safety Factor Relationships"), Table 10.9 and Eq. (10.4): the design procedure is explicitly "1. Selects n_max from Table 10.9 based on aircraft category. 2. Multiplies by 1.5 to get n_ult. 3. Substitutes into the appropriate component weight equation." n_max is therefore a CATEGORY SELECTION, not a value read off a V-n curve.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
n_ult = 1.5 · n_max   (Sadraey Eq. 10.4), with n_max selected from Table 10.9 by aircraft category
```

**⚠️ Divergence from the source.** This vindicates the code and indicts its comment. mission_kpi_service.py:246 documents the value as "n_max from V-n diagram (load factor)" and the context key is named 'flight_envelope_n_max'; Sadraey §10.4.1 defines n_max as a designer-selected category value, which is exactly what the code publishes. The name and the mission-KPI comment are wrong, not the value. Second divergence: Sadraey's n_max is only ever consumed after multiplication by the 1.5 safety factor (Eq. 10.4) to give n_ult; nothing in this cluster applies that factor.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Named 'flight_envelope_n_max' but does not come from the flight envelope (V-n curve) at all — it is the raw g_limit design choice. mission_kpi_service.py:246 documents it as "n_max from V-n diagram (load factor)", which the value is not. Name/definition contradiction, acknowledged in the comment.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"gh-625 Bug A: publish the effective `g_limit` as the design-limit peak load factor so _kpi_maneuver can compute. A physics-aware refinement reading the V-n curve's gust-augmented peak can replace this later; for now the design-limit value is the correct source." — app/services/assumption_compute_service.py:716-718`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
