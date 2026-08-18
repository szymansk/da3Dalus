---
name: v_loiter_endurance
kind: quantity
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# loiter_endurance target speed

**Definition.** Speed assigned to the endurance/loiter operating point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"velocity": max(1.15 * refs["vs_clean"], cruise * 0.80)
```

**Inputs.**

- [[vs_clean|Clean stall speed reference]]
- [[cruise_speed_resolved|Resolved cruise speed]]

**Produced by.** `app/services/operating_point_generator_service.py:450` — `_build_target_definitions`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/models/analysismodels.py (velocity)`

**Source.** 🟡 PARTIAL

> Sadraey §4.2.5.4, Eq. 4.25: 'V_Emax = V_Pmin ≈ 1.2 V_s to 1.4 V_s', with the recommended default V_Emax ≈ 1.3 V_s; Eq. 4.22: (L/D)_Emax = 0.866·(L/D)_max (minimum-power, i.e. max CL^1.5/CD)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_E = V_Pmin ≈ (1.2 … 1.4)·V_s, default 1.3·V_s
```

**⚠️ Divergence from the source.** Method sourced, value not: 1.15·V_s is BELOW the published range, and the source's own default is 1.3·V_s. The alternate branch 0.80·cruise is unsourced. Flying below V_Pmin puts the aircraft on the back side of the power curve, which reduces endurance rather than maximising it — the point is named for an optimum it can sit the wrong side of.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Endurance speed (min-sink, V ≈ 0.76·V_md) is approximated by magic factors 1.15/0.80 while assumption_compute_service already caches a physics-derived min-sink speed.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
