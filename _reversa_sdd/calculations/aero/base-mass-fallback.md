---
name: base-mass-fallback
kind: constant
unit: kg
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/aero-spanwise
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Speed-polar mass fallback

**Definition.** Mass substituted when the aeroplane has no 'mass' assumption.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.0`

**Formula — as the code writes it.**

```
base_mass = 1.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:619` — `_build_speed_polar`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> 1.0 kg has no source and is not a plausible default in the 0.5–15 kg class.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Silently rescales every V and w by sqrt(m_true/1.0) — for a 5 kg model every speed is under-reported by a factor 2.24. Logger-only, no DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** 1.0 kg sits at the bottom edge of the 0.5–15 kg target band, so the substitution is never obviously wrong to the user.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Undeclared fallback (ADR 0020): only a logger.warning; the API returns base_mass_kg=1.0 with no DesignWarning, silently scaling every V and w by sqrt(m_true/1.0).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
