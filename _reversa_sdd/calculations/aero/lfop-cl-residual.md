---
name: lfop-cl-residual
symbol: _cl_at_alpha
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: PARTIAL
---

# CL residual for the root search

**Definition.** AeroBuildup CL at a trial alpha minus the target CL.

**Formula — as the code writes it.**

```
return float(np.atleast_1d(result.get("CL", 0.0))[0]) - cl_target
```

**Inputs.** [[lfop-cl-target-clip|Target CL clamp]]

**Produced by.** `app/services/section_aoa_service.py:521` — `_cl_at_alpha`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟡 PARTIAL

> AeroSandbox docs_aero_3d.md, AeroBuildup (returns the standard aero dict including 'CL')
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** Residual form is correct. The except branch returning -cl_target is the defect: it makes every failed evaluation look like the same-signed end of a valid bracket, so a wholly broken solve presents as a clean monotone problem.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** On any AeroBuildup exception the residual becomes -cl_target (line 523), which makes a totally failed solve look like a monotone bracket rather than an error.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:521,523`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
