---
name: trim-static-margin-derivative
symbol: SM
kind: quantity
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: SOURCED
---

# Static margin from derivatives

**Definition.** Static margin inferred at a trim point from the ratio of the pitch and lift alpha-derivatives.

**Formula — as the code writes it.**

```
if has_cm_a and abs(cl_a) > 1e-6:
    static_margin = round(-cm_a / cl_a, 4)
```

**Inputs.** [[cl-a-guard-epsilon|CL_alpha division guard]]

**Produced by.** `app/services/trim_enrichment_service.py:146` — `classify_stability`

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:171,487,488` · `frontend/hooks/useOperatingPoints.ts:87 (StabilityClassification)` · `frontend/components/workbench/trim-interpretation/OpComparisonTable.tsx`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §11.6.2, Eq. 11.17: C_mα = C_Lα·(X_cg − X_np). Combined with Eq. 11.18 (SM = (X_np − X_cg)/C̄) this gives SM = −C_mα/C_Lα when both derivatives are taken about the CG and non-dimensionalised on the same reference chord.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_mα = C_Lα · (X_cg − X_np)  ⇒  SM = −C_mα / C_Lα   (Sadraey Eq. 11.17 + 11.18)
```

**⚠️ Divergence from the source.** The identity is exact but conditional, and neither condition is checked. (a) Eq. 11.17 is written about the aircraft CG; if the solver's moment reference is not the CG (see cg-x-from-xyz-ref — this app's default xyz_ref is [0,0,0]) the ratio is not a static margin. (b) Both derivatives must share the reference chord. This is the THIRD independent producer of static margin in the cluster, and it can disagree with stability_service._compute_static_margin for the same aircraft (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** THIRD independent producer of static margin (notes F2), with a formula that is only valid when the moment reference is the CG — nothing here checks that. −Cm_α/CL_α also silently returns a per-radian-ratio that is only a fraction-of-MAC if both derivatives share the reference chord.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
