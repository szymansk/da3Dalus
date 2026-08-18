---
name: fe_k_g_coeffs
symbol: 0.88 / 5.3
kind: constant
unit: -
cluster: perf-envelope
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: regulatory-constant
tags:
  - cluster/perf-envelope
  - class/regulatory-constant
  - source/sourced
  - audit/confirmed
---

# Pratt gust-alleviation coefficients

**Definition.** Numerator and denominator constants of the Pratt K_g regression.

**Regulatory constant.** Taken from a standard. It carries the clause *and* the class of aircraft that clause applies to.

**Value.** `0.88, 5.3`

**Formula — as the code writes it.**

```
0.88 * mu_g / (5.3 + mu_g)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:112` — `_compute_k_g`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Gust alleviation factor`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> FAR 25.341(c) / CS-25.341(c) state K_g = 0.88*mu_g/(5.3+mu_g) verbatim; regression origin Pratt & Walker, NACA TN 2964 (1953).
>
> — via `scholz`

**The source states it as.**

```
0.88 and 5.3
```

**Cited in the code itself.** `"Sources: FAR-25.341(a)(2); CS-VLA.333; NACA TN 2964."`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
