---
name: mu_g_max
symbol: mu_g,max
kind: constant
unit: -
cluster: perf-envelope
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: regulatory-constant
tags:
  - cluster/perf-envelope
  - class/regulatory-constant
  - source/no-source-found
  - surface/user-visible
  - flag/divergence
---

# Pratt-Walker validity upper bound

**Definition.** Upper bound of the mass-ratio range in which the K_g formula is validated.

**Regulatory constant.** Taken from a standard. It carries the clause *and* the class of aircraft that clause applies to.

**Value.** `200.0`

**Formula — as the code writes it.**

```
_MU_G_MAX: float = 200.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:48` — `_MU_G_MAX`

**Consumed by.**

- in this graph: `Pratt validity warning`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🔴 NO SOURCE FOUND

> Same as mu_g_min — 200.0 is not attributable to NACA TN 2964 or FAR 25.341.
>
> — via `scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Unreachable in the 0.5-15 kg class in any case (mu_g > 200 needs W/S far above RC values), so the upper bound is inert while the lower bound fires constantly.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `NACA TN 2964 / FAR-25.341`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
