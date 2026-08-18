---
name: fe_k_g
symbol: K_g
kind: quantity
unit: -
cluster: perf-envelope
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - flag/scale
---

# Gust alleviation factor

**Definition.** Factor reducing the sharp-edged gust increment for aircraft inertia and gust penetration.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return 0.88 * mu_g / (5.3 + mu_g)
```

**Inputs.**

- [[fe_mu_g|Gust mass ratio]]
- [[fe_k_g_coeffs|Pratt gust-alleviation coefficients]]

**Produced by.** `app/services/flight_envelope_service.py:112` — `_compute_k_g`

**Consumed by.**

- in this graph: `Gust load-factor increment`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> FAR 25.341(c) / CS-25.341(c); NACA TN 2964 (Pratt & Walker, 1953).
>
> — via `scholz`

**The source states it as.**

```
K_g = 0.88*mu_g/(5.3+mu_g)
```

**⚠️ Scale (ADR 0023).** Pratt's regression was fitted to 1933-1950 civil transport V-G records — the empirical base contains no vehicle within three orders of magnitude of 0.5-15 kg. ADR 0023: adopted because it is standard in transport literature, never validated at RC scale. The code applies the FAR-25 (transport) K_g on top of FAR-23/CS-VLA (light-aircraft) gust velocities — a mixed-basis envelope neither regulation prescribes.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `FAR-25.341(a)(2); CS-VLA.333; NACA TN 2964`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
