---
name: saoa-twist-at-y
symbol: twist_at_y
kind: quantity
unit: deg
cluster: aero-strips
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - audit/confirmed
---

# Interpolated twist at panel y

**Definition.** Geometric twist linearly interpolated onto panel spanwise positions.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
twist_at_y = np.interp(y_arr, xsec_y, xsec_twist)
```

**Inputs.**

- [[saoa-xsec-twist|Cross-section twist array]]
- [[saoa-y|Panel spanwise position]]

**Produced by.** `app/services/section_aoa_service.py:324` — `compute_section_aoa`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Geometric angle of attack`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> AVL 3.40 User Primer, avl_doc.txt L583-633 (Ainc linearly interpolated between SECTIONs); Sadraey, Aircraft Design (Wiley 2013) §5.14 Step 1 (geometric twist assigned per segment)
>
> — via `avl-advisor, aircraft-design-scholz`

**The source states it as.**

```
twist(y) linear between defined sections
```

**Cited in the code itself.** `app/services/section_aoa_service.py:324`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
