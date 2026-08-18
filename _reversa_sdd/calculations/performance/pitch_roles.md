---
name: pitch_roles
symbol: —
kind: constant
unit: dimensionless
cluster: perf-oppoints
user_visible: false
source_status: SOURCED
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/sourced
  - flag/anomaly
  - flag/divergence
---

# Pitch control role set

**Definition.** Role tags counted as pitch-capable control surfaces.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `{elevator, stabilator, elevon, ruddervator}`

**Formula — as the code writes it.**

```
PITCH_ROLES = {"elevator", "stabilator", "elevon", "ruddervator"}
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:48` — `PITCH_ROLES`

**Consumed by.**

- in this graph: `Control capability flags`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:613 (_pick_control_name)` · `app/services/operating_point_generator_service.py:549 (_detect_control_capabilities)`

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §12.2 (Table 12.4 + 'Unconventional Control Surfaces')
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
elevon = aileron+elevator (pitch & roll); ruddervator = rudder+elevator (pitch & yaw); stabilator = all-moving HT (pitch)
```

**⚠️ Divergence from the source.** Set matches Sadraey exactly. The divergent copy at elevator_authority_service.py:99 does NOT: it adds flaperon (Sadraey §12.2 defines flaperon as flap+aileron — no pitch function) and drops stabilator (an all-moving HT is the pitch surface). That copy is wrong against the source, not merely inconsistent.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Three divergent copies of the same set exist: app/services/elevator_authority_service.py:99 has {elevator, ruddervator, elevon, flaperon} (adds flaperon, drops stabilator) and app/services/retrim_service.py:31 duplicates the OPG version.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `PITCH_ROLES = {"elevator", "stabilator", "elevon", "ruddervator"}`

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
