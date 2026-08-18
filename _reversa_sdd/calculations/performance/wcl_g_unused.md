---
name: wcl_g_unused
symbol: g
kind: parameter
unit: m/s^2
cluster: perf-matching
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-parameter
tags:
  - cluster/perf-matching
  - class/unclassified-parameter
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# Unused gravity parameter in WCL

**Definition.** Gravity parameter accepted by _wcl_constraint but explicitly discarded.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `9.81 (default)`

**Formula — as the code writes it.**

```
_ = g
```

**Inputs.**

- [[g_gravity|Standard gravity]]

**Produced by.** `app/services/matching_chart_service.py:527` — `_wcl_constraint`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> Not a physical quantity - a dead parameter (`_ = g  # kept for future calibration`).
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Complete but unreachable, exactly what ADR 0021 forbids. Distinct from the `g` in _landing_constraint, which is dead but SHOULD be live (see ws_landing_constraint).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Complete but unreachable parameter kept 'for future calibration' — exactly the inert code ADR 0021 forbids.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `_ = g  # currently unused — kept for future calibration`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
