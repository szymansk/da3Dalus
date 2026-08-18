---
name: reserve-critical-threshold
symbol: —
kind: parameter
unit: – (fraction)
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-parameter
tags:
  - cluster/stability
  - class/unclassified-parameter
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Deflection reserve critical threshold

**Definition.** Usage fraction above which a 'near mechanical limit — redesign needed' critical warning is emitted.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.95`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/trim_enrichment_service.py:392` — `compute_enrichment`

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:426`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Same as reserve-warning-threshold: unattributed, never overridden by any caller.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Never overridden by any caller. No source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
