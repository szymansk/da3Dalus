---
name: reserve-warning-threshold
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

# Deflection reserve warning threshold

**Definition.** Usage fraction above which a 'surface may be undersized' warning is emitted.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.80`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/trim_enrichment_service.py:391` — `compute_enrichment`

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:438`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source specifies a fractional reserve threshold. Sadraey §12.5.5 step 19 uses a hard comparison against δ_E,max, not a fraction; the only quantitative margin in the consulted sources is the tail-stall guidance in §12.5.4 ("keep tail within 2° of its stall angle"), which is an angular margin, not a usage fraction. Also a constant dressed as a parameter — no caller overrides it.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No caller ever overrides it (grep over app/ finds no keyword use outside the definition), so it is a constant dressed as a parameter. No source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
