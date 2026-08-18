---
name: spar-mass-full
symbol: m_spar,full
kind: quantity
unit: kg
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
---

# Full-span spar mass

**Definition.** Total spar mass for both halves, taken as exactly twice the half-span mass.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
spar_mass_full_kg=half_mass * 2.0
```

**Inputs.**

- [[spar-mass-half|Half-span spar mass]]

**Produced by.** `app/services/spar_sizing.py:383` — `compute_spar_sizing`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/schemas/spar_sizing.py:140` · `frontend/hooks/useSparSizing.ts:44` · `frontend/lib/sparSizingHelpers.ts:105`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (no source read states a wing spar's full-span mass is exactly twice the half-span spar mass; in particular RC-Network Wiki "Steckung" describes the wing-fuselage joint as "one of the most highly loaded steckung types" requiring steel/GFK/CFK tubes and sleeves — i.e. real hardware whose mass this doubling omits entirely)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** No carry-through / root-joint mass is added; a reinforcement or joiner piece contributes nothing to this number even when the plan path emits one.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
