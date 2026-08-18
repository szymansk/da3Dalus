---
name: deflection-bounds
symbol: —
kind: parameter
unit: deg
cluster: stability
user_visible: true
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/stability
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
  - solver-adjacent/aerobuildup
---

# Trim search bounds

**Definition.** Lower and upper deflection limits within which the Brent solver searches for the trim.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
lower, upper = request.deflection_bounds
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/aerobuildup_trim_service.py:166` — `trim_with_aerobuildup`

**Consumed by.**

- in this graph: `Root bracketing test` · `Trimmed control deflection`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/aerobuildup_trim_service.py:169,170,186,214`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.5 step 4 — "Establish the maximum elevator deflection to prevent flow separation (typically 25°)" — this IS the search bound; step 19 compares the required deflection against it. §12.5.4 gives the hard ceiling of ~30°.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
|δ| ≤ δ_max, with δ_max ≈ 25° set by flow separation (Sadraey §12.5.5 step 4)
```

**⚠️ Divergence from the source.** In Sadraey the bound is the physical/aerodynamic limit of THE surface being designed. Here it is caller-supplied and never reconciled with the surface's actual mechanical limits from the TED, so a trim can converge to a deflection the hardware cannot reach — and the enrichment then scores that deflection against the unrelated 25° default (see deflection-limit-default).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey's 25°/30° figures come from transport/GA elevator design; RC surfaces in this app's own database run 20–35°. No RC-scale validation recorded (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Caller-supplied and never reconciled with the surface's actual mechanical limits from the TED — a trim can converge to a deflection the hardware cannot reach, and the enrichment then scores it against the 25° default (see deflection-limit-default).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
