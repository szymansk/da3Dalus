---
name: low-re-tip-re-abs-floor
symbol: —
kind: parameter
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/aero-polars
  - class/unclassified-parameter
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Tip-Re absolute floor

**Definition.** Tip Reynolds below which the tip is flagged regardless of root Re.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `80000.0`

**Formula — as the code writes it.**

```
low_re_tip_re_abs_floor: float = 80_000.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/settings.py:110` — `Settings.low_re_tip_re_abs_floor`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `tip_re_flag`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `suitability_service:274`

**Source.** 🟡 PARTIAL

> Sharpe (2024), §7.2.4, Fig. 7-10 — sharp confidence drop near C_L ≈ 1.0 at Re_c ≈ 80×10³, 'where a laminar separation bubble precariously forms and the boundary layer is highly sensitive'
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** 80 000 coincides exactly with a documented regime boundary, which would justify it — but the code cites nothing, so the coincidence cannot be assumed deliberate. Reported as PARTIAL rather than SOURCED for that reason; adopting the citation would make it defensible.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sharpe's figure is for the surrogate's confidence, not for a physical CL_max collapse; the flag's user-facing meaning ('tip in a different regime') is adjacent to, not identical with, the cited evidence.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic threshold, no source cited.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `low_re_tip_re_abs_floor: float = 80_000.0`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
