---
name: target_flap_takeoff_deg
kind: constant
unit: deg
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
  - flag/scale
---

# Takeoff flap deflection target

**Definition.** Fixed flap deflection requested for the takeoff-climb point before TED clipping.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `15.0`

**Formula — as the code writes it.**

```
"flap_deflection_deg": 15.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:421` — `_build_target_definitions`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Clipped flap deflection`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:75-114 (_clip_flap_to_ted_limit)` · `app/services/operating_point_generator_service.py:635-647`

**Source.** 🟡 PARTIAL

> (transport) Scholz, Flugzeugentwurf, 05_PreliminarySizing §5.2: takeoff CL_max is obtained 'with partial flap deflection (typically 15–25°)'. (RC) Lennon, Basics of R/C Model Aircraft Design, slotted-flap chapter: '20° deflection — low drag, suitable for takeoff'.
>
> — via `aircraft-design-scholz, rc-aircraft-designer`

**The source states it as.**

```
delta_f,TO ∈ [15°, 25°] (transport) / 20° (RC slotted flap)
```

**⚠️ Divergence from the source.** 15° is at the bottom edge of the transport range and below the RC-scale recommendation of 20°. A defensible but conservative choice; it is a fixed constant rather than a function of the aircraft's actual flap type, which both sources make it depend on (a plain flap needs far more deflection than a Fowler for the same ΔCL).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The 15–25° band is Scholz's transport-category high-lift practice; the RC-scale source (Lennon) says 20° for a slotted flap on a model. Small divergence, low consequence.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `the OPG historically hard-coded 15° (takeoff) and 30° (landing) flap deflections without checking the aircraft's ``TrailingEdgeDevice.positive_deflection_deg```

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
