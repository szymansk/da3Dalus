---
name: eta_prop_default
symbol: η_prop
kind: parameter
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: SOURCED
---

# Default propeller efficiency

**Definition.** Propeller efficiency assumed at climb speed for the power-loading constraint.

**Value.** `0.7`

**Formula — as the code writes it.**

```
eta_prop: float = 0.7
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:537` — `_power_loading_constraint`

**Consumed by.**

- in this graph: [[tw_power_loading|Power-loading T/W floor]]
- outside it: `_power_loading_constraint:564` · `hover_text:1149`

**Source.** 🟢 SOURCED

> Sadraey 2013 §4.3.4, rate-of-climb sizing inputs (sadraey-rate-of-climb-sizing): 'eta_P in climb. Typically 0.5-0.7 (lower than in cruise, because climb angles change blade incidence). Default 0.7.' For cruise Sadraey gives 0.75-0.85 (sadraey-propeller-aerodynamic-principles) and 'assume 0.8 if no better data'.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
eta_P,climb = 0.5-0.7, default 0.7
```

**⚠️ Divergence from the source.** The value and the context both match - the code uses it at climb speed, which is precisely where Sadraey's 0.7 applies. Remaining issue is architectural, not provenance: it is hardcoded, never overridden, and unrelated to the real propeller data the powertrain services already hold (ADR 0022 risk).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey's band is for full-scale propellers. Small RC props at low Re commonly fall below 0.5 in climb, so 0.7 is optimistic at 0.5-15 kg even though it is correctly sourced for the manned case.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Hardcoded default never overridden by any caller, and unrelated to the real propeller data the powertrain services already hold.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
