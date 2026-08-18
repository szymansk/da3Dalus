---
name: max-static-margin-pct-default
symbol: max_margin
kind: parameter
unit: % MAC
cluster: stability
user_visible: true
source_status: PARTIAL
---

# Maximum static margin (CG-range default)

**Definition.** Upper static-margin bound used to place the forward CG limit. Read from a design_assumptions row named 'max_static_margin', otherwise this default.

**Value.** `25.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:230` — `_get_margin_bounds`

**Consumed by.**

- in this graph: [[cg-range-forward|Forward CG limit from margin bounds]]
- outside it: `app/services/stability_service.py:254,331,334` · `app/services/stability_service.py:88 (same literal repeated as compute_cg_range default)`

**Source.** 🟡 PARTIAL

> No source states a maximum static margin of 25 %. Closest attributable numbers: Sadraey §11.4 gives CG *envelope width* 20–30 % MAC (large transport) and 10–20 % MAC (general aviation); Scholz 10_BoxWingSystematic §4.2 gives "operational envelope typically 15–25 % MAC". Both are envelope widths, not a static-margin ceiling.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**⚠️ Divergence from the source.** The code uses 25 % as an SM ceiling; the cited-adjacent literature uses 20–30 % as a CG *travel* range. At RC scale the ceiling is far tighter: rcplanedesigner.com gives Trainer max 15 % MAC, Sport max 5 %, Acrobatic max 3 %; Lennon Ch. 6 works with SM = 10 % as "healthy". An SM of 25 % is outside every RC band found.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The 20–30 % figure it most resembles is Sadraey's large-transport CG envelope. Applying it as a static-margin ceiling for a 0.5–15 kg RC/UAV aircraft is unvalidated at scale (ADR 0023) and contradicts the RC-scale sources by 10–20 percentage points.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Same as min: 'max_static_margin' has no writer and no row in db/test.db; the DB branch is dead. 25 % MAC is also inconsistent with _SM_FORWARD_CLIP_LIMIT / _STUB_FORWARD_SM / margin_high_threshold, all 0.30.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
