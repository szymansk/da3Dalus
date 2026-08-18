---
name: flap_roles
kind: constant
unit: dimensionless
cluster: perf-oppoints
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Flap control role set

**Definition.** Role tags counted as lift-augmentation flaps.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `{flap}`

**Formula — as the code writes it.**

```
FLAP_ROLES = {"flap"}
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:51` — `FLAP_ROLES`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Control capability flags` · `Governing flap deflection limit`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:83, 637, 645, 969` · `app/services/assumption_compute_service.py:905 (_detect_first_flap_name, re-implemented)`

**Source.** 🟡 PARTIAL

> Sadraey §12.2, 'Flaperon' — combined flap + aileron on one trailing-edge surface (X-29, F-16)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
flaperon symmetric deflection = flap function
```

**⚠️ Divergence from the source.** Code defines FLAP_ROLES = {"flap"} only. Per Sadraey a flaperon IS a flap when both halves deflect down, so an aircraft with flaperons instead of separate flaps reports has_flap=False and the stall_with_flaps target is skipped, plus takeoff/approach get no flap. Source-backed defect.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** assumption_compute_service.py:905-921 re-implements the role-tag parse locally instead of importing, so the flap-role definition has two producers.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
