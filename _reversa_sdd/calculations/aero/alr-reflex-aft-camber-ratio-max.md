---
name: alr-reflex-aft-camber-ratio-max
symbol: —
kind: parameter
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: PARTIAL
node_class: unclassified-parameter
tags:
  - cluster/aero-polars
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Reflex Signal A threshold

**Definition.** Aft camber ratio below which a sharp-TE airfoil is labelled reflexed.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.06`

**Formula — as the code writes it.**

```
_REFLEX_AFT_CAMBER_RATIO_MAX = (0.06)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:82` — `_REFLEX_AFT_CAMBER_RATIO_MAX`

**Consumed by.**

- outside it: `classify_family:262`

**Source.** 🟡 PARTIAL

> Lennon (1996), Ch. 2 — reflexed section (E184) has the mean line turned up near the trailing edge, giving near-zero or nose-up pitching moment for tailless/delta models
>
> — via `rc-aircraft-designer`

**⚠️ Divergence from the source.** The reflex concept is sourced; the 0.06 ratio is calibrated only against an in-repo sample named in the comment (NACA 4412: 0.31, Clark Y: 0.28). Honest empirical calibration, not a citation.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Threshold calibrated against a named airfoil sample in the comment (NACA 4412: 0.31, Clark Y: 0.28) — empirical, no external source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# For reflexed sharp-TE
#   airfoils this ratio is always < 0.06 (camber almost vanishes at 90% chord).  For
#   non-reflexed cambered (NACA 4412: 0.31) or flat-bottom (Clark Y: 0.28) it is >> 0.06.`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
