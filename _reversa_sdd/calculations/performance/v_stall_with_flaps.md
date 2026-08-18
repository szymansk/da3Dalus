---
name: v_stall_with_flaps
kind: quantity
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# stall_with_flaps target speed

**Definition.** Speed of the flapped near-stall operating point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"velocity": max(2.0, refs["vs_ldg"] * 1.05)
```

**Inputs.**

- [[vs_ldg|Landing-config stall speed reference]]

**Produced by.** `app/services/operating_point_generator_service.py:483` — `_build_target_definitions`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/models/analysismodels.py (velocity)`

**Source.** 🔴 NO SOURCE FOUND

> Related: Scholz 05_PreliminarySizing §5.1 defines V_S0 (landing-config stall) — the correct reference speed
>
> — via `aircraft-design-scholz, rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 1.05·V_S0 gives only a 10 % load-factor margin to stall (1.05² = 1.10 g). No source recommends a margin that thin; the smallest cited margin is Lennon's 20 % (Ch. 4). The 2.0 m/s floor is unsourced (see vs_floors).

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
