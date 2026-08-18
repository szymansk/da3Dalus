---
name: fe_g_limit
symbol: n_lim
kind: parameter
unit: g
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
node_class: user-input
tags:
  - cluster/perf-envelope
  - class/user-input
  - source/partial
  - surface/user-visible
  - flag/divergence
  - flag/scale
---

# Structural limit load factor

**Definition.** Effective g-limit design assumption, defaulting to 3.0.

**User input.** Supplied from outside the calculation (assumption store or request), not derived.

**Value.** `default 3.0`

**Formula — as the code writes it.**

```
_load_assumptions -> PARAMETER_DEFAULTS['g_limit'] = 3.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:556` — `_load_assumptions`

**Consumed by.**

- in this graph: `Negative gust-critical trigger` · `Positive gust-critical trigger` · `Negative maneuver load factor` · `Positive maneuver load factor` · `KPI: max load factor`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Sadraey §10.4.1 Table 10.9 lists 'Remote-controlled model: n_max = 1.5-2'. Lennon, Basics of R/C Model Aircraft Design (1996) Ch. 21 gives the RC pull-out load formula G = 1 + (1.466*V_mph)^2/(R_ft*32.2) with worked cases: 6.4 g at 90 mph/100 ft, 7.7 g at 100 mph/100 ft, 12.1 g at 100 mph/60 ft.
>
> — via `scholz, rc`

**The source states it as.**

```
n_lim = 3.0 (default)
```

**⚠️ Divergence from the source.** 3.0 matches neither authority and sits in the gap between them. The two sources are not in conflict — they measure different things. Sadraey's 1.5-2 is a structural-sizing regression coefficient feeding component-weight equations, not a flight load. Lennon's 6-12 g are actual manoeuvre loads an RC model reaches in a dive pull-out. So the honest statement is: RC flight loads are 6-12+ g while RC structures are conventionally sized at 1.5-2 with a 1.5 ultimate factor. A single default of 3.0 labelled 'structural limit load factor' conflates the two and is simultaneously too high for the sizing convention and far too low for the real envelope.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** This constant clips fe_n_pos_maneuver, sets the gust-critical threshold, and is the sole authority behind BOTH n_max KPIs. It is the highest-leverage unvalidated number in the cluster.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
