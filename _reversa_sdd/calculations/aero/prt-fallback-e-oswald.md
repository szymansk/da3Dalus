---
name: prt-fallback-e-oswald
symbol: —
kind: constant
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/aero-polars
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Fallback Oswald efficiency

**Definition.** e returned when the table carries no e_oswald value at all.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.8`

**Formula — as the code writes it.**

```
_FALLBACK_E_OSWALD: float = 0.8
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:59` — `_FALLBACK_E_OSWALD`

**Consumed by.**

- outside it: `lookup_e_oswald_at_v:213`

**Source.** 🟡 PARTIAL

> Anderson 6e §6.7.2 — typical airplane Oswald factor 0.70–0.85
>
> — via `aerodynamics-expert`

**⚠️ Divergence from the source.** 0.8 lies inside the cited band, so the magnitude is not arbitrary — but the code cites nothing, and gh-924 routes around it explicitly (lines 209-211), confirming it is a known-poor default still reachable. No DesignWarning on substitution (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Anderson's 0.70–0.85 band comes from full-scale aircraft data (Raymer correlation, explicitly invalid for AR>25). No RC/UAV validation at 0.5–15 kg (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic constant with no source; the gh-924 comment at lines 209-211 explicitly routes around it, confirming it is a known-poor default still reachable.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `return float(sum(any_e) / len(any_e)) if any_e else _FALLBACK_E_OSWALD`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
