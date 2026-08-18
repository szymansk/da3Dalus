---
name: prt-e-range-guard
symbol: —
kind: parameter
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: PARTIAL
---

# Oswald physical-range guard (0.4, 1.0]

**Definition.** Band rows whose fitted e falls outside this interval are demoted to fallback rows.

**Value.** `0.4 / 1.0`

**Formula — as the code writes it.**

```
if not (0.4 < e_oswald <= 1.0):
```

**Inputs.** [[prt-e-oswald-band|Band Oswald efficiency]]

**Produced by.** `app/services/polar_re_table_service.py:284` — `_fit_band_with_ar`

**Consumed by.**

- outside it: `_fit_band_with_ar:291 (_fallback_row)`

**Source.** 🟡 PARTIAL

> Anderson 6e §6.7.2 (Oswald typical 0.70–0.85, approaching 0.90) and §5.3.1 (elliptical distribution is the optimum, e = 1)
>
> — via `aerodynamics-expert`

**⚠️ Divergence from the source.** Upper bound 1.0 is sourced — a planar wing cannot exceed the elliptical optimum. Lower bound 0.4 has NO source; it sits far below Anderson's 0.70–0.85 band with no stated rationale. Rejection also converts a fit into a fallback with only a logger.warning, no DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Anderson's 0.70–0.85 band and the quoted Raymer correlation are full-scale aircraft data; neither is validated at 0.5–15 kg (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic bounds with no cited source; rejecting the row silently converts a fit into a fallback (ADR 0020 relevance — only a logger.warning, no DesignWarning).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Physical range guard
if not (0.4 < e_oswald <= 1.0):`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
