---
name: stability-slope-thresholds
kind: constant
unit: 1/deg
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/aero-spanwise
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Stability classification thresholds

**Definition.** Slope bands separating Stable / Neutral / Unstable.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `-0.01 / 0.01`

**Formula — as the code writes it.**

```
if slope < -0.01: Stable; if slope <= 0.01: Neutral; else Unstable
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:827` — `_classify_longitudinal_stability`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Cm-gradient stability colours`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Sign criterion sourced: Sadraey §11.6.2 Eq. 11.17 (C_mα < 0 ⇔ stable, X_cg < X_np). The ±0.01 dead-band is NOT in Sadraey, Scholz, Anderson, or Lennon.
>
> — via `aircraft-design-scholz, rc-aircraft-designer`

**The source states it as.**

```
stable ⇔ C_mα < 0; neutral ⇔ C_mα = 0 (X_cg = X_np); unstable ⇔ C_mα > 0
```

**⚠️ Divergence from the source.** The literature criterion is a SIGN test at zero, with the degree of stability measured by static margin (Sadraey Eq. 11.18), not by an absolute Cm-slope band. The ±0.01/deg dead-band = ±0.57/rad is wider than the entire practical stable range: a model with C_mα = −0.5/rad (−0.0087/deg), genuinely and adequately stable, is labelled 'Neutral' by this code.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** ADR 0023: no RC/UAV validation. Lennon (Basics of R/C Model Aircraft Design, 1996, Ch. 6) classifies RC stability by static margin in % MAC (10% healthy, 5% minimum, NP at 35% MAC = neutral), never by an absolute dCm/dα threshold.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic numbers, NO_SOURCE_FOUND, not validated at RC/UAV scale (ADR 0023); duplicated verbatim in _compute_cm_strip_colors (lines 1037-1041).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
