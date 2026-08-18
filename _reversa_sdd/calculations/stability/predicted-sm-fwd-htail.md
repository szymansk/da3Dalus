---
name: predicted-sm-fwd-htail
symbol: SM_pred,fwd
kind: quantity
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Predicted forward SM after htail scale

**Definition.** Prediction of the forward-CG static margin limit after enlarging the horizontal tail to gain elevator authority.

**Formula — as the code writes it.**

```
predicted_sm = sm_fwd_current - dsm_dsh * delta_pct * s_h_m2
```

**Inputs.** [[sm-fwd|Static margin at forward CG]] · [[dsm-dsh|SM sensitivity to horizontal tail area]] · [[s-h-m2-fallback|Horizontal tail area fallback]]

**Produced by.** `app/services/sm_sizing_service.py:646` — `_htail_scale_fwd_option`

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:660` · `app/api/v2/endpoints/aeroplane/sm_suggestions.py:85`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source supports using dSM/dS_H — a sensitivity of the static margin — to shift a forward-CG *limit*. The forward limit in Sadraey §11.6.3 depends on the elevator control-power derivatives C_mδE = −V̄_H·(dC_Lt/dδ_E) and C_LδE = (S_h/S)·(dC_Lt/dδ_E) (Eqs. 11.24–11.25), which scale with S_h through a different path. The code's own comment concedes the derivation is an approximation. Sign is opposite to the aft-CG twin at line 709 for the same physical lever.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Sign is opposite to _htail_scale_option:709 for the same lever, and dsm_dsh (a dSM/dS_H sensitivity) is used to shift a LIMIT rather than an SM — the comment concedes the derivation is an approximation with no source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# We approximate: increasing S_H shifts sm_max_fwd by dsm_dsh * ΔS_H,
# meaning the allowable forward margin grows. Here predicted_sm is the new target limit.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
