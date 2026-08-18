---
name: fe_effective_cl_alpha
symbol: CL_alpha_eff
kind: quantity
unit: 1/rad
cluster: perf-envelope
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Effective lift-curve slope for gust

**Definition.** Cached alpha-sweep CL_alpha when available, else the Helmbold fallback.

**Formula — as the code writes it.**

```
effective_cl_alpha = cl_alpha_per_rad; if None and b_ref>0: _helmbold_cl_alpha(ar)
```

**Inputs.** [[ctx_cl_alpha_per_rad|Cached lift-curve slope]] · [[fe_cl_alpha_helmbold|Finite-span lift-curve slope (Helmbold fallback)]]

**Produced by.** `app/services/flight_envelope_service.py:341` — `compute_vn_curve`

**Consumed by.**

- in this graph: [[fe_delta_n|Gust load-factor increment]] · [[fe_mu_g|Gust mass ratio]]

**Source.** 🔴 NO SOURCE FOUND

> Substitution policy, not a physical quantity — no source applies.
>
> — via `aero`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** ADR 0020: swapping a measured CL_alpha for the (mis-named) analytic one silently changes every gust number with no DesignWarning. Given fe_cl_alpha_helmbold overestimates by 4-12%, the undeclared substitution biases gust loads high in exactly the cases where no sweep has been run.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared substitution: the Helmbold fallback silently replaces the measured CL_alpha with no DesignWarning in the response (ADR 0020). Only the confidence-free gust line changes.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
