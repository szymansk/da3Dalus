---
name: flap-default-deflection
symbol: δf
kind: constant
unit: deg
cluster: stability
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Default flap deflection

**Definition.** Flap deflection used in the landing-configuration run when the TED does not declare positive_deflection_deg.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `30.0`

**Formula — as the code writes it.**

```
flap_deg = getattr(ted, "positive_deflection_deg", None) or 30.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/elevator_authority_service.py:869` — `_run_flap_analysis`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Swept flapped CL_max`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/elevator_authority_service.py:870`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §5.12.2: "Typical values: C_f/C ≈ 0.20, b_f/b ≈ 0.6, δ_f ≈ 30° at takeoff and 60° at landing for older designs"; §5.17 worked example uses 30°. Scholz 05_PreliminarySizing §5.1: full landing deflection typically 35–40° for commercial transports; 08_HighLift §8.2 uses a reference deflection of ~35°.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
δ_f ≈ 30° take-off / 60° landing (Sadraey §5.12.2); 35–40° landing for transports (Scholz §5.1)
```

**⚠️ Divergence from the source.** 30° is the sources' TAKE-OFF setting; the code uses it for the LANDING configuration, where the same sources call for 35–60°. Since the run's purpose is CL_max,landing, this understates the flap contribution. Separately, `or 30.0` also overrides a legitimately stored 0.0 deflection (falsy), not just a missing one.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey §5.12.2 and Scholz §5.1 are GA/transport-category. RC flap practice is not covered by either; no RC-scale validation recorded (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** `or 30.0` also overrides a legitimate stored 0.0 deflection (falsy), not just a missing one. Magic value, no source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Use positive deflection for flap (TE-down for lift)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
