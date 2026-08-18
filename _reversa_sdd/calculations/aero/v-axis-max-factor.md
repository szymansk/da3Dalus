---
name: v-axis-max-factor
kind: constant
unit: -
cluster: aero-spanwise
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Upper axis-bound factor

**Definition.** Multiplier on V_dive for the chart's right edge.

**Value.** `1.3`

**Formula — as the code writes it.**

```
1.3 * v_dive
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:561` — `_compute_speed_polar`

**Consumed by.**

- in this graph: [[v-axis-max|Speed-polar X-axis upper bound]]

**Source.** 🔴 NO SOURCE FOUND

> 1.3 is a plotting margin with no source.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Physically questionable: V_D is by definition the maximum design speed, so drawing the polar to 1.3·V_D renders the aircraft at speeds past its own structural envelope with no annotation.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** For a 0.5–15 kg model whose V_D is set by dive/flutter, showing +30% beyond it invites the user to read performance off a region the airframe cannot survive.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic display factor, NO_SOURCE_FOUND; drawing the polar 30% beyond V_dive shows speeds past the structural limit.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
