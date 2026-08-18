---
name: v_app
symbol: V_app
kind: quantity
unit: m/s
cluster: perf-matching
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Approach speed

**Definition.** Approach/touchdown speed used for the landing model.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return _V_APP_FACTOR * v_stall_mps
```

**Inputs.**

- [[v_app_factor|Approach speed factor]]
- [[v_stall_ldg|Landing-configuration stall speed]]

**Produced by.** `app/services/field_length_service.py:137` — `_v_app`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `compute_field_lengths:370` · `FieldLengthRead.vapp_mps:444`

**Source.** 🟢 SOURCED

> CS 25.125 / Scholz 05_PreliminarySizing §5.1 (see v_app_factor)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_APP = 1.3 * V_S,L
```

**⚠️ Divergence from the source.** Confirms the inventory anomaly and explains it: in the sourced derivation s_ground = k^2/(mu*g) * (W/S)/(rho*CL_max_L), the touchdown-speed factor k IS the only place V_app enters - and in this code it has been absorbed into the fitted 0.5847. So V_app is reported to the user but is decorative. Restoring the explicit k would re-couple them.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** V_app is reported to the user but is not an input to s_ldg_ground — the landing roll is computed from K_LDG only, so changing V_app never changes the distance.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"V_app = 1.3 · V_S (Roskam standard approach speed)."`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
