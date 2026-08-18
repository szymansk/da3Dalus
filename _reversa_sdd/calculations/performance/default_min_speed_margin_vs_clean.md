---
name: default_min_speed_margin_vs_clean
kind: constant
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Default clean stall margin

**Definition.** Multiplier over clean stall speed for the low-speed operating point.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.20`

**Formula — as the code writes it.**

```
"min_speed_margin_vs_clean": 1.20
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:206` — `_default_profile`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Clean-margin floor` · `stall_near_clean target speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:336, 401`

**Source.** 🟢 SOURCED

> (RC scale) Lennon, Basics of R/C Model Aircraft Design (1996), Ch. 4 'Wing Loading Design': 'Adding a 20 percent safety margin to each stall-speed estimate gives landing speeds of 24 and 36 mph'. (Transport) Scholz, Flugzeugentwurf, 05_PreliminarySizing §5.4: second-segment climb at V₂ = 1.2·V_S,TO per CS 25.107.
>
> — via `rc-aircraft-designer, aircraft-design-scholz`

**The source states it as.**

```
V_min = 1.20 · V_S
```

**⚠️ Divergence from the source.** Value matches both an RC-scale and a transport-scale authority independently. This is the best-supported constant in the cluster. It is nevertheless duplicated as an inline literal at lines 336/401 and again in app/schemas/flight_profile.py:101.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No source cited for 1.20; duplicated as an inline default at lines 336 and 401 and again in app/schemas/flight_profile.py:101.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
