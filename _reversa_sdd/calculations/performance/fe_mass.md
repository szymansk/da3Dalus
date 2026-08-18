---
name: fe_mass
symbol: m
kind: parameter
unit: kg
cluster: perf-envelope
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Design mass (envelope)

**Definition.** Effective mass design assumption, defaulting to 1.5 kg when no row exists.

**Value.** `default 1.5`

**Formula — as the code writes it.**

```
result[param] = get_effective_assumption_value(db, ...) except NotFoundError: PARAMETER_DEFAULTS[param]
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:556` — `_load_assumptions`

**Consumed by.**

- in this graph: [[fe_weight|Aircraft weight]] · [[fe_wing_loading|Wing loading (gust path)]]

**Source.** 🔴 NO SOURCE FOUND

> 1.5 kg default is a UI seed value, not an engineering constant.
>
> — via `rc`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Scale (ADR 0023).** Sits inside the 0.5-15 kg target band, so it is a harmless seed — but it is a silent default feeding a user-visible V-n diagram (ADR 0020).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
