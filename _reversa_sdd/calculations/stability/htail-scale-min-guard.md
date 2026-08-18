---
name: htail-scale-min-guard
symbol: —
kind: constant
unit: – (dimensionless)
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Minimum htail scale

**Definition.** Lower bound on the chord scale factor; below it the apply is rejected.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.1`

**Formula — as the code writes it.**

```
if scale <= 0.1:
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:983` — `apply_htail_scale`

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:983-987`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 0.1 (10 % of original chord) is unattributed. Sadraey §6.7 bounds the tail through aspect ratio (4–6) and taper (typically 0.3–0.5), not through a minimum chord fraction; a 10 %-chord tail would be far outside those bounds long before the guard fires. The error message says 'non-positive chord' but the guard rejects at 10 %, not at zero.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number; the error message says 'non-positive chord' but the guard rejects at 10 % of original chord, not at zero.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"delta_pct must be greater than -0.9."`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
