---
name: predicted-sm-htail-scale
symbol: SM_pred
kind: quantity
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Predicted SM after htail chord-scale

**Definition.** First-order prediction of the resulting static margin after chord-scaling the horizontal tail.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
predicted_sm = sm_at_aft + dsm_dsh * delta_pct * s_h_m2
```

**Inputs.**

- [[sm-at-aft|Static margin at aft CG]]
- [[dsm-dsh|SM sensitivity to horizontal tail area]]
- [[delta-pct-htail|Horizontal tail chord-scale fraction]]
- [[s-h-m2-fallback|Horizontal tail area fallback]]  — *⤵ fallback*

**Produced by.** `app/services/sm_sizing_service.py:709` — `_htail_scale_option`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:722` · `app/api/v2/endpoints/aeroplane/sm_suggestions.py:85,184`

**Source.** 🟡 PARTIAL

> First-order Taylor prediction using dSM/dS_H (see dsm-dsh). Underlying physics — larger tail moves the NP aft, raising SM — is Sadraey §11.6.2 ("Increasing tail area … moves the neutral point aft").
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Sadraey §11.6.2: increasing S_h moves x_np aft (and, second-order, the cg aft too)
```

**⚠️ Divergence from the source.** Sadraey explicitly warns that increasing tail area has TWO opposing effects: NP aft (raises SM) and tail weight aft (moves cg aft, lowers SM). The code models only the first. Its forward-CG twin at sm_sizing_service.py:646 applies the OPPOSITE sign for the same lever with only the hedge 'We approximate'.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Duplicated at line 963 in apply_htail_scale. Its forward-CG twin at line 646 uses the OPPOSITE sign (`sm_fwd_current - dsm_dsh * delta_pct * s_h_m2`) for the same physical lever, justified only by the hedged comment 'We approximate' at lines 643-645.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
