---
name: wcl_ws_max
symbol: (W/S)_max,WCL
kind: quantity
unit: N/m^2
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# WCL-derived W/S ceiling

**Definition.** Wing-loading upper bound derived from the profile's wing-cube-loading target.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
base = (wcl_lb * _LENNON_LB_FT_TO_SI) ** (2.0 / 3.0); ar_factor = max(ar, 1.0) ** 0.25; return base * ar_factor
```

**Inputs.**

- [[wcl_upper_table|Lennon WCL upper bounds]]  — *⊣ limit*
- [[lennon_lb_ft_to_si|Lennon WCL conversion factor]]  — *× unit*
- [[ar_resolved|Resolved aspect ratio]]  — *⤵ fallback*

**Produced by.** `app/services/matching_chart_service.py:531` — `_wcl_constraint`

**Consumed by.**

- outside it: `_build_rc_additive_constraints:1110,1112` · `constraints 'Wing-Cube-Loading':1117` · `MatchingChartResponse.constraints`

**Source.** 🔴 NO SOURCE FOUND

> No source for the mapping from wing cube loading to a W/S ceiling, and none for the exponents 2/3 and 0.25.
>
> — via `aircraft-design-scholz (no coverage)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Two independent defects. (1) The exponents are unsourced magic. (2) The function does not produce the values its own comment promises: approx 71 N/m^2 (trainer, claimed ~120) and approx 112 N/m^2 (sport, claimed ~250) at AR = 7 - off by 1.7-2.2x. Since it is built on the dimensionally invalid 47.88 factor, the whole chain is unsound; the underlying intent (a mission-consistent W/S ceiling) is legitimate but needs rebuilding from WCL = W/S^1.5 directly.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The formula does not produce the values its own comment promises: at AR=7 it returns ≈71 N/m² for trainer (claimed ~120) and ≈112 N/m² for sport (claimed ~250) — off by ~1.7–2.2×, and the exponents 2/3 and 0.25 are unsourced magic.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"we expose a direct numerical upper W/S bound that reproduces Lennon's RC sizing intuition: trainer ≤ ~120 N/m², sport ≤ ~250 N/m² at typical AR=7. AR factors in lightly: higher AR → smaller chord → larger W/S allowed at the same WCL because S grows with span²."`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
