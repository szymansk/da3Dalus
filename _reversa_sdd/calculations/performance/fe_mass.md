---
name: fe_mass
symbol: m
kind: parameter
unit: kg
cluster: perf-envelope
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: user-input
tags:
  - cluster/perf-envelope
  - class/user-input
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/scale
---

# Design mass (envelope)

**Definition.** Effective mass design assumption, defaulting to 1.5 kg when no row exists.

**User input.** Supplied from outside the calculation (assumption store or request), not derived.

**Value.** `default 1.5`

**Formula — as the code writes it.**

```
result[param] = get_effective_assumption_value(db, ...) except NotFoundError: PARAMETER_DEFAULTS[param]
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:556` — `_load_assumptions`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Aircraft weight` · `Wing loading (gust path)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

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
