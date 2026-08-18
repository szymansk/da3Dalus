---
name: mu_belly
symbol: μ_belly
kind: constant
unit: dimensionless
cluster: perf-matching
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-matching
  - class/unclassified-constant
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Belly-landing friction

**Definition.** Sliding friction coefficient assumed for a belly landing on grass.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.5`

**Formula — as the code writes it.**

```
_MU_BELLY: float = 0.5
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:89` — `_MU_BELLY`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Selected braking friction`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `compute_field_lengths:431`

**Source.** 🔴 NO SOURCE FOUND

> No source in Scholz or Sadraey for belly-landing friction; the literature has no belly-landing model at all.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Confirmed physics defect, not just a sourcing gap. mu_belly (0.5) > mu_brake (0.4) makes a wheels-up belly landing come out SHORTER than a braked wheeled landing. Sadraey Table 4.15 shows surface effects (grass 0.05-0.1 vs concrete 0.03-0.05), but comparing 'fuselage skidding on turf' with 'BRAKED wheels on dry pavement' is not a surface comparison - braked-wheel deceleration on dry pavement legitimately exceeds skidding a fuselage over grass.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** μ_belly > μ_brake makes a wheels-up belly landing come out SHORTER than a braked wheeled landing, and no source is cited for either value.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# belly landing (grass + fuselage scraping)`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
