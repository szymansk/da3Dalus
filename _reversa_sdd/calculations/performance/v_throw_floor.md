---
name: v_throw_floor
symbol: v_floor
kind: quantity
unit: m/s
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Hand-launch minimum throw speed

**Definition.** Minimum acceptable throw speed below which hand launch is rejected.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_floor = _HAND_THROW_FLOOR * v_stall
```

**Inputs.**

- [[hand_throw_floor|Hand-launch physics floor]]  — *⊣ limit*

**Produced by.** `app/services/field_length_service.py:378` — `compute_field_lengths`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `compute_field_lengths:380 (ServiceException)`

**Source.** 🔴 NO SOURCE FOUND

> Inherits hand_throw_floor; no hand-launch model in Scholz or Sadraey.
>
> — via `aircraft-design-scholz (confirmed gap)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Uses the CLEAN v_stall while V_LOF on the same code path uses the takeoff-configuration v_stall_to - two different stall references inside one function. The sources are consistent on using the configuration-appropriate V_S (Scholz §5.1/§5.2).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Uses the CLEAN v_stall while V_LOF on line 369 uses the takeoff-configuration v_stall_to — two different stall references inside one function.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
