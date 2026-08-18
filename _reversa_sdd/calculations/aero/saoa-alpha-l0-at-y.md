---
name: saoa-alpha-l0-at-y
symbol: alpha_L0_at_y
kind: quantity
unit: deg
cluster: aero-strips
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - flag/anomaly
  - flag/divergence
---

# Interpolated zero-lift angle at panel y

**Definition.** Section zero-lift angle interpolated from xsec positions onto panel y positions.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
alpha_L0_at_y = np.interp(y_arr, alpha_L0_per_section[0], alpha_L0_per_section[1])
```

**Inputs.**

- [[saoa-alpha-l0|Section zero-lift angle]]
- [[saoa-y|Panel spanwise position]]

**Produced by.** `app/services/section_aoa_service.py:298` — `compute_section_aoa`

**Consumed by.**

- in this graph: `Effective angle of attack`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Sadraey, Aircraft Design (Wiley 2013) §5.14, Step 1 ('different segments may have different airfoils (aerodynamic twist)' — each segment carries its own alpha_o)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
alpha_o varies per spanwise segment; interpolate between defined sections
```

**⚠️ Divergence from the source.** Interpolating alpha_L0 along the span is the documented treatment of aerodynamic twist. The np.interp clamping on the mirrored half (xsec y covers one semispan only) is an implementation defect, not a modelling choice.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** np.interp requires ascending x; for a symmetric wing the xsec y array covers only one half-span, so panels on the mirrored half are clamped to the endpoint value.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:296-298`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
