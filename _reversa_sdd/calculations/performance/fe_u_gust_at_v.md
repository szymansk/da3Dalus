---
name: fe_u_gust_at_v
symbol: U(V)
kind: quantity
unit: m/s
cluster: perf-envelope
user_visible: false
source_status: PARTIAL
---

# Gust velocity schedule

**Definition.** Gust velocity held at U_VC up to V_C then linearly tapered to U_VD at V_D.

**Formula — as the code writes it.**

```
if v <= v_c: u = gust_u_vc_mps else: frac = (v - v_c)/(v_dive - v_c); u = gust_u_vc_mps + frac*(gust_u_vd_mps - gust_u_vc_mps)
```

**Inputs.** [[gust_u_vc|Design gust velocity at cruise speed]] · [[gust_u_vd|Design gust velocity at dive speed]] · [[fe_v_c|Cruise speed (back-derived)]] · [[fe_v_dive|Dive speed]] · [[fe_v_sweep|Velocity sweep points]]

**Produced by.** `app/services/flight_envelope_service.py:232` — `_build_gust_lines`

**Consumed by.**

- in this graph: [[fe_delta_n|Gust load-factor increment]]

**Source.** 🟡 PARTIAL

> Endpoint values SOURCED (CS-VLA 333(c)(1) / FAR 23.333(c)(1)). The linear taper between them is the conventional gust-envelope construction, not a quoted regulatory rule — CS-VLA/FAR-23 prescribe gust lines at V_C and V_D, not a continuous U(V).
>
> — via `scholz`

**The source states it as.**

```
U held at U_C to V_C, linear to U_D at V_D
```

**⚠️ Divergence from the source.** 'Below V_C, U_vc is used (conservative)' is correct practice and correctly labelled. The interpolation rule should be marked as a construction convention rather than inheriting the regulation's authority.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"Below V_C, U_vc is used (conservative per CS-VLA.333(c)(1))."`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
