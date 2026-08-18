---
name: vlm-cd-total
symbol: CD
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/vlm
---

# Whole-airplane drag coefficient (VLM run)

**Definition.** Total CD taken directly from the VLM run dict.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"CD": float(run["CD"]),
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:319` — `compute_vlm_strip_forces`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟢 SOURCED

> AeroSandbox docs_aero_3d.md ('VLM-only CD is induced drag only')
>
> — via `aerosandbox-expert`

**The source states it as.**

```
CD = CD,induced from the ASB aero dict
```

**⚠️ Divergence from the source.** Emitted but unread. If it ever gains a consumer, note that it is CDi, not total CD — the same field name means total drag elsewhere in the app.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No consumer: result["CD"] is emitted but never read by any caller.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:319`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
