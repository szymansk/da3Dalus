---
name: default_max_beta_deg
symbol: β_max
kind: constant
unit: deg
cluster: perf-oppoints
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Default maximum sideslip

**Definition.** Sideslip limit used for the BETA_LIMIT_REACHED check.

**Value.** `30.0`

**Formula — as the code writes it.**

```
"max_beta_deg": 30.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:212` — `_default_profile`

**Consumed by.**

- in this graph: [[warn_beta_limit_reached|BETA_LIMIT_REACHED warning]]
- outside it: `app/services/operating_point_generator_service.py:864-867`

**Source.** 🔴 NO SOURCE FOUND

> Nearest authorities: Sadraey §12.3.3 — control power 'shall be adequate to develop at least 10° of sideslip in the power approach'; FAR 25.147 — ±15° heading change with critical engine inoperative
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 30° is 2–3× the largest sideslip any cited requirement asks an aircraft to demonstrate. The BETA_LIMIT_REACHED check is therefore inert for default profiles. Schema (flight_profile.py:230) says 'typical values are 3 to 10 deg', consistent with Sadraey and inconsistent with the default.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** 30° default vs the schema's own "Typical values are 3 to 10 deg" (app/schemas/flight_profile.py:230), so the check is effectively inert for default profiles.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
