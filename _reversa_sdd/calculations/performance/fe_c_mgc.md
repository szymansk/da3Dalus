---
name: fe_c_mgc
symbol: c_bar
kind: quantity
unit: m
cluster: perf-envelope
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/divergence
---

# Mean geometric chord

**Definition.** Reference chord for the gust mass ratio, defined as S/b, deliberately not MAC.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
c_mgc = wing_area_m2 / b_ref_m
```

**Inputs.**

- [[fe_wing_area|Reference wing area]]  — *× unit*
- [[fe_b_ref|Reference span]]  — *× unit*

**Produced by.** `app/services/flight_envelope_service.py:186` — `_build_gust_lines`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Gust mass ratio`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> FAR 25.341(c) / CS-25.341 definition list: 'c = mean geometric chord'. The regulation asks for MGC, not MAC.
>
> — via `scholz`

**The source states it as.**

```
c_bar = S/b (mean geometric chord)
```

**⚠️ Divergence from the source.** None — this is the best-provenanced choice in the file. The code is right and its comment ('not MAC') correctly reflects the regulation. Leave it alone.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"Mean Geometric Chord = S/b (not MAC)"; "For trapezoidal wings MGC ≈ MAC; for double-trapezoid the difference can be relevant (see gh-487 spec)"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
