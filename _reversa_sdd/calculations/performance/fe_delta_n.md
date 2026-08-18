---
name: fe_delta_n
symbol: delta_n
kind: quantity
unit: -
cluster: perf-envelope
user_visible: false
source_status: SOURCED
---

# Gust load-factor increment

**Definition.** Load-factor increment produced by a discrete sharp-edged vertical gust at speed V.

**Formula — as the code writes it.**

```
return 0.5 * rho * v * cl_alpha * u_gust * k_g / wing_loading
```

**Inputs.** [[fe_rho_default|Default air density (flight envelope)]] · [[fe_v_sweep|Velocity sweep points]] · [[fe_effective_cl_alpha|Effective lift-curve slope for gust]] · [[fe_u_gust_at_v|Gust velocity schedule]] · [[fe_k_g|Gust alleviation factor]] · [[fe_wing_loading|Wing loading (gust path)]]

**Produced by.** `app/services/flight_envelope_service.py:136` — `_compute_delta_n`

**Consumed by.**

- in this graph: [[fe_gust_n_neg|Negative gust load factor]] · [[fe_gust_n_pos|Positive gust load factor]]

**Source.** 🟢 SOURCED

> FAR 25.341(a)(2) / CS-VLA 341 (imperial form delta_n = K_g*U_de*V*a/(498*W/S)); unalleviated form in Scholz, Flugzeugentwurf 07_WingDesign §7.3 as n_alpha = 0.5*rho*v^2*CL_alpha/(W/S).
>
> — via `scholz`

**The source states it as.**

```
delta_n = K_g * U_de * V * a / (2*(W/S)) [SI form of FAR 25.341(a)(2)]
```

**⚠️ Divergence from the source.** SI transcription is correct. Docstring's 'Anderson, Introduction to Flight, 6th ed. §6.5' could not be verified and is the same loose book/section pattern as fe_cl_alpha_helmbold — recommend dropping it and keeping the two regulatory citations, which are checkable.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"Sources: FAR-25.341(a); CS-VLA.341; NACA TN 2964 (Pratt & Walker, 1953); Anderson, Introduction to Flight, 6th ed. §6.5."`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
