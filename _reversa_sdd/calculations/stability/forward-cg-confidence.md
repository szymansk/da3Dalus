---
name: forward-cg-confidence
symbol: confidence
kind: quantity
unit: – (enum)
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Forward CG confidence tier

**Definition.** Six-tier label describing how the forward CG limit was obtained (solver path × configuration × flap availability).

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if elevator_role is None or elevator_role not in _PITCH_ROLES:
    return ForwardCGConfidence.stub
is_warn_tier = elevator_role in _WARN_ROLES
if is_warn_tier:
    return (ForwardCGConfidence.asb_warn_with_flap if has_flap_run else ForwardCGConfidence.asb_warn_clean)
else:
    return (ForwardCGConfidence.asb_high_with_flap if has_flap_run else ForwardCGConfidence.asb_high_clean)
```

**Inputs.**

- [[pitch-roles|Pitch-control roles]]

**Produced by.** `app/services/elevator_authority_service.py:165` — `_determine_confidence_tier`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/elevator_authority_service.py:734,742,755,768,776,829` · `app/schemas/forward_cg.py:61` · `app/api/v2/endpoints/aeroplane/forward_cg.py:99`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** A solver-provenance label, not an engineering quantity; 'Amendment S2' is an internal spec note, not a literature source. No consulted source defines confidence tiers for a forward CG limit. The closest methodological analogue is Sadraey §12.5.5 step 14, which requires lifting-line theory or CFD to VERIFY the analytic result rather than to label it — i.e. the source's answer to low confidence is a better calculation, not a tier. Note the AVL path bypasses this function and hardcodes avl_full (:1075) even when it skips the flap run.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The AVL path bypasses this function entirely and hardcodes avl_full (line 1075) even when it skips the flap run — so the highest confidence tier is assigned to the LESS complete calculation.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Tiers (Amendment S2)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
