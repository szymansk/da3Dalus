---
name: lfop-s-ref
symbol: s_ref
kind: quantity
unit: m²
cluster: aero-strips
user_visible: false
source_status: PARTIAL
code_audit: WRONG_LINE
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - audit/wrong-line
  - flag/anomaly
  - flag/divergence
---

# Reference area (level-flight solve)

**Definition.** Planform area of the first symmetric wing found on the airplane.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
for w in asb_airplane.wings: if getattr(w, "symmetric", False): s_ref = float(w.area()); break
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:494` — `_resolve_level_flight_op`

🟠 **Corrected by the audit** — the extraction claimed `WRONG_LINE`. Original line was `495`. Producer line should be 494 where s_ref is assigned, not 495 which is the loop break

**Consumed by.**

- in this graph: `Level-flight target lift coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> AVL 3.40 User Primer, avl_doc.txt L240-295 (Sref = reference area for all coefficients); Scholz, Flugzeugentwurf 05_PreliminarySizing §5.6.2 (S_W = wing area in the lift-weight balance)
>
> — via `avl-advisor, aircraft-design-scholz`

**The source states it as.**

```
S_ref = main-wing planform area
```

**⚠️ Divergence from the source.** The definition is unambiguous — the MAIN wing. The code takes the FIRST symmetric wing in list order. On a tail-first geometry (which this repo has already been bitten by) it sizes the aircraft on the stabiliser. turbulator_optimizer_service.py:399 resolves the identical concept as max-area; two implementations of one defined quantity.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Takes the FIRST symmetric wing, not the largest — a tail-first wing ordering makes s_ref the stabiliser area; turbulator_optimizer_service:399 uses max-area for the same concept.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:491-497`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
