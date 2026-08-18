---
name: mu_g_min
symbol: mu_g,min
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

# Pratt-Walker validity lower bound

**Definition.** Lower bound of the mass-ratio range in which the K_g formula is validated.

**Regulatory constant.** Taken from a standard. It carries the clause *and* the class of aircraft that clause applies to.

**Value.** `3.0`

**Formula — as the code writes it.**

```
_MU_G_MIN: float = 3.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:47` — `_MU_G_MIN`

**Consumed by.**

- in this graph: `Pratt validity warning`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🔴 NO SOURCE FOUND

> NACA TN 2964 (Pratt & Walker, 1953) is a real and correctly named work, but neither it nor FAR 25.341 states a validity band mu_g in [3, 200]. The bound 3.0 could not be attributed to either cited source.
>
> — via `scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** This is the most consequential citation defect in the cluster: the bound is user-visible (GustValidityWarning) AND ships the citation with it, so an unattributable number is presented to the user as regulator-backed. The warning's own prose — 'RC/UAV with low W/S frequently produce mu_g < 3' — is sound engineering judgement and should be labelled as such, not as NACA TN 2964.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"Pratt-Walker μ_g validity range (NACA TN 2964 / FAR-25.341 applicability)"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
