---
name: fe_cl_max
symbol: CL_max
kind: parameter
unit: -
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: user-input
tags:
  - cluster/perf-envelope
  - class/user-input
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/scale
---

# Maximum lift coefficient (envelope)

**Definition.** Effective CL_max design assumption, defaulting to 1.4.

**User input.** Supplied from outside the calculation (assumption store or request), not derived.

**Value.** `default 1.4`

**Formula — as the code writes it.**

```
_load_assumptions -> PARAMETER_DEFAULTS['cl_max'] = 1.4
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:556` — `_load_assumptions`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Inverted maximum lift coefficient` · `Positive maneuver load factor` · `Stall speed (1 g)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> No direct source for 1.4 as an aircraft-level default. RC-scale reference points: Lennon (1996) gives NACA 0012 CL_max ~ 1.05 and NACA 64-012 ~ 0.9 at Rn = 700,000.
>
> — via `rc, aero`

**The source states it as.**

```
CL_max = 1.4 (default)
```

**⚠️ Scale (ADR 0023).** 1.4 is optimistic for the target class. RC models operate at Re 100,000-300,000, well below Lennon's Rn 700,000, where CL_max degrades further; and aircraft CL_max is below section c_l,max. Because V_s ~ 1/sqrt(CL_max), an optimistic CL_max understates stall speed by ~10-20%, and V_s anchors the entire V-n x-axis plus three KPIs.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
