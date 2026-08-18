---
name: prt-cd0-hard-fallback
symbol: —
kind: constant
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/aero-polars
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# cd0 hard fallback 0.03

**Definition.** cd0 returned when the table has no cd0 value at all.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.03`

**Formula — as the code writes it.**

```
return float(all_cd0[0]) if all_cd0 else 0.03
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:124` — `lookup_cd0_at_v`

**Consumed by.**

- outside it: `all lookup_cd0_at_v consumers`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 0.03 is an undeclared magic constant on the live path. The repo already knows it is wrong: assumption_compute_service.py:437-451 exists solely to backfill fallback rows so it is not hit ('eHawk: 0.03 vs the real parasite 0.013'). Substitution emits no DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** 0.03 is in the range quoted for light full-scale aircraft, not for a 0.5–15 kg RC/UAV airframe whose measured parasite here is 0.013 (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Undeclared magic constant; assumption_compute_service.py:437-451 (gh-924) exists purely to backfill fallback rows so this 0.03 is not hit ('eHawk: 0.03 vs the real parasite 0.013') — the constant is a known-wrong value still on the live path.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# All rows are fallback — return first available cd0 or 0.03
all_cd0 = [r.get("cd0") for r in table if r.get("cd0") is not None]
return float(all_cd0[0]) if all_cd0 else 0.03`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
