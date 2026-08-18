---
name: dutch_roll_beta_deg
kind: constant
unit: deg
cluster: perf-oppoints
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Dutch-roll start sideslip

**Definition.** Sideslip angle of the dutch_role_start excitation point.

**Value.** `2.0`

**Formula — as the code writes it.**

```
"beta_target_deg": 2.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:506` — `_build_target_definitions`

**Consumed by.**

- in this graph: [[beta_candidates|Sideslip candidate list]]
- outside it: `app/services/operating_point_generator_service.py:896 (beta_candidates)` · `app/services/operating_point_generator_service.py:660 (asb.OperatingPoint beta)`

**Source.** 🔴 NO SOURCE FOUND

> The mode is sourced — Sadraey §12.3.3 (Table 12.16, MIL-F-8785C): dutch roll is a second-order lateral-directional mode characterised by damping ratio ζ_d and natural frequency ω_nd — but no excitation amplitude is specified.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 2° sideslip has no source. More fundamentally, the source defines dutch roll as an EIGENVALUE property (ζ_d, ω_nd from C_nβ, C_nr, I_zz), not as a trimmed operating point at a fixed β. A static trim solve at β = 2° cannot produce the quantity the target is named for. Separately: the target name 'dutch_role_start' is a misspelling persisted to the DB and shown in the UI.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Target name is misspelled "dutch_role_start" (should be dutch_roll) and the misspelling is persisted to the DB and shown in the UI.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
