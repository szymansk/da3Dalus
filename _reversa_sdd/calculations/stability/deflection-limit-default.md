---
name: deflection-limit-default
symbol: —
kind: constant
unit: deg
cluster: stability
user_visible: true
source_status: SOURCED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Default control-surface deflection limit

**Definition.** Mechanical deflection limit assumed when a trailing-edge device does not declare one.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `25.0`

**Formula — as the code writes it.**

```
max_pos, max_neg = limits.get(surface_name, (25.0, 25.0))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/trim_enrichment_service.py:413` — `compute_enrichment`

**Consumed by.**

- in this graph: `Deflection usage fraction`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/trim_enrichment_service.py:414,415,417,418` · `app/services/trim_enrichment_service.py:79,114,115 (second declaration `default = 25.0`)`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.5 (Elevator Design Procedure) step 4: "Establish the maximum elevator deflection to prevent flow separation (typically 25°)"; the worked example uses δ_Emax,up = −25°. §12.5.4 sets the hard ceiling: "If the required δ_E exceeds about 30°, the elevator must be enlarged or the tail arm extended."
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
δ_max ≈ 25° before flow separation; ~30° absolute ceiling (Sadraey §12.5.4, §12.5.5 step 4)
```

**⚠️ Divergence from the source.** The number matches the source, but it is applied to the wrong thing and in the wrong role. Sadraey's 25° is a design constraint on the ELEVATOR that the designer must not exceed; the code uses it as a fallback MECHANICAL limit for every surface type including ailerons and rudders, for which Sadraey gives no such figure. Because build_deflection_limits_from_schema keys the dict by the raw TED name while compute_enrichment looks up the tagged `[role]name` (trim_enrichment_service.py:105-116 vs :413), the .get() always misses and the 25° fallback is used unconditionally — verified against db/test.db, where an elevator declaring 28°/23° is scored against 25.0/25.0.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey §12.5.5's 25° derives from transport/GA elevator design (worked example: 20,000 kg twin-jet). RC control surfaces routinely exceed it — this app's own database holds 35°/35° elevators, 28°/23° elevators and 30°/30° ailerons. No RC/UAV-scale validation is recorded (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** CONFIRMED ALWAYS-ON FALLBACK: because build_deflection_limits_from_schema keys by the raw TED name while compute_enrichment looks up the tagged `[role]name`, this .get() always misses. Verified against db/test.db — a stored deflection_reserves entry reads {'max_pos_deg': 25.0, 'max_neg_deg': 25.0} for an aeroplane whose elevator TED declares 28°/23°. Declared twice as separate literals (lines 79 and 413).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Falls back to ``(25.0, 25.0)`` if TED limits are not set.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
