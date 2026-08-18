---
name: margin-low-threshold
symbol: —
kind: parameter
unit: – (fraction of MAC)
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
---

# Marginal static margin threshold

**Definition.** Static margin below which a 'marginal static margin' warning is emitted at a trim point.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.05`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/trim_enrichment_service.py:393` — `compute_enrichment`

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:500`

**Source.** 🟢 SOURCED

> Lennon, "Basics of R/C Model Aircraft Design" (1996) Ch. 6: "The minimum suggested margin is 5 percent." rcplanedesigner.com, "Airplane Balance — Finding the First-Flight CG": first-flight floor 5 % of MAC; Trainer minimum 5 %. Sadraey §6.7.1: "Typical design practice: SM = 0.05 to 0.10 … Too low (<0.03): difficult to control."
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
SM ≥ 0.05 as the practical minimum (Lennon Ch. 6; rcplanedesigner first-flight floor)
```

**⚠️ Divergence from the source.** Value is well sourced. What diverges is the app's internal consistency: the same user is shown three different 'low static margin' thresholds — 0.05 here, 0.02 in sm_sizing_service._SM_UNSTABLE_LIMIT, and the 5 %/0 % bands in stability_service.classify_stability (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Disagrees with sm_sizing_service._SM_UNSTABLE_LIMIT = 0.02 and with stability_service.classify_stability's 5 %/0 % bands — three different 'low static margin' thresholds surfaced to the same user.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
