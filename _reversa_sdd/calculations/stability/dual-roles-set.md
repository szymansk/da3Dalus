---
name: dual-roles-set
symbol: —
kind: constant
unit: – (set of strings)
cluster: stability
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Dual-role surface set

**Definition.** Roles whose surfaces carry both a symmetric and an antisymmetric control component.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `{"elevon", "flaperon", "ruddervator"}`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/trim_enrichment_service.py:26` — `DUAL_ROLES`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:253,288`

**Source.** 🟢 SOURCED

> Lennon, "Basics of R/C Model Aircraft Design" (1996) Ch. 23 — elevons combine pitch and roll on one surface via mixing. Sadraey §12.8 (unconventional control surfaces) covers elevon, ruddervator and taileron as combined-function surfaces; §6.7 covers the V-tail ruddervator's pitch/yaw split.
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
elevon = pitch + roll ; ruddervator = pitch + yaw ; flaperon = roll + flap (lift)
```

**⚠️ Divergence from the source.** Content matches the sources. It duplicates control_surface_mixing._DUAL_ROLE_AXES — the very source of the PRIMARY_AXES/SECONDARY_AXES that this same function imports at line 277 — so the codebase holds two independent definitions of which roles are dual.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Duplicates control_surface_mixing._DUAL_ROLE_AXES (the source of PRIMARY_AXES/SECONDARY_AXES this same function imports at line 277) — two independent definitions of which roles are dual.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
