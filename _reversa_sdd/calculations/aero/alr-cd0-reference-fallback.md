---
name: alr-cd0-reference-fallback
symbol: —
kind: constant
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# cd0 reference fallback

**Definition.** cd0 reference used when no finite fleet cd0 can be extracted.

**Value.** `0.020`

**Formula — as the code writes it.**

```
_CD0_REFERENCE_FALLBACK = 0.020
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:768` — `_CD0_REFERENCE_FALLBACK`

**Consumed by.**

- outside it: `compute_re_cd0_reference:820`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 0.020 is a bare magic constant; substitution is silent, no DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** An absolute c_d0 target is Reynolds-dependent at RC scale — a single value cannot serve the whole 40k–750k grid (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic number, no source; substitution is silent (no DesignWarning) per ADR 0020.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Fallback cd0 reference when no finite values can be extracted.
_CD0_REFERENCE_FALLBACK = 0.020`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
