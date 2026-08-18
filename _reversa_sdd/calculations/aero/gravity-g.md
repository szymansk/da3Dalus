---
name: gravity-g
symbol: g
kind: constant
unit: m/s²
cluster: aero-spanwise
user_visible: false
source_status: PARTIAL
---

# Gravitational acceleration

**Definition.** Gravity used to turn mass into weight for the speed polar.

**Value.** `9.81`

**Formula — as the code writes it.**

```
g: float = 9.81
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:439` — `_compute_speed_polar`

**Consumed by.**

- in this graph: [[weight-n|Weight]]

**Source.** 🟡 PARTIAL

> Standard acceleration of free fall g_n = 9.80665 m/s² — 3rd CGPM (1901), ISO 80000-3. Used implicitly in Scholz 05_PreliminarySizing §5.6.2 Eq. 5.30 (L = m_MTO·g). No numeric value for g found in the consulted expert vaults.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
g_n = 9.80665 m/s²
```

**⚠️ Divergence from the source.** Code hardcodes 9.81 (rounded, +0.034%). Negligible physically; the defect is that _build_speed_polar (analysis_service.py:655) never passes g, so the parameter is unreachable configuration.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Hardcoded default; _build_speed_polar (line 655) never passes g, so 9.81 is always used. NO_SOURCE_FOUND.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
