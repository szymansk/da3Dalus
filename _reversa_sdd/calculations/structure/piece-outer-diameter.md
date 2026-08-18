---
name: piece-outer-diameter
symbol: OD
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Spar piece outer diameter

**Definition.** Final outer diameter of a spar piece: its own governing strength-required OD, then possibly grown so its bore can admit the next outboard piece plus clearance (tube shapes only), then possibly replaced by a snapped real-stock OD.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
ods = [_governing_od(r.governing) for r in runs]
```

**Inputs.**

- [[governing-od|Governing required OD of a piece]]
- [[min-od-for-bore|Minimum OD to carry a bore]]  — *⊣ limit*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:403` — `plan_spar`

**Consumed by.**

- in this graph: `Spar piece feasibility` · `Spar piece utilisation` · `Spar piece wall thickness` · `Buildable front pieces` · `Telescoping bore demand`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:434` · `cad_designer/airplane/geometry/spar_solver.py:463` · `app/services/spar_plan_service.py:193` · `app/services/spar_plan_service.py:501` · `frontend/hooks/useSparPlan.ts:43` · `frontend/lib/sparPlanHelpers.ts:132`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm — Rohrholm (a single CFK tube as main spar) is a standard RC configuration; Kirch, "Hauptholm", procedure step 4 (verify W_available > W_required)
>
> — via `rc-aircraft-designer + direct verification of the kirch source`

**The source states it as.**

```
Kirch step 4: the chosen section must satisfy W_available > W_required.
```

**⚠️ Divergence from the source.** The strength premise is sourced. The two subsequent overwrites are not, and they break the source's step-4 guarantee: bore-propagation (cad_designer/airplane/geometry/spar_solver.py:426) inflates OD for telescoping reasons unrelated to strength, and snap_piece_to_stock (app/services/spar_plan_service.py:193) replaces the solved OD with a Component-Library value after the solver has finished — so downstream code that reconstructs erf_W from outer_d (spar_plan_service.py:218) reads a number that is no longer the strength requirement.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Overwritten in place by a second, independent producer: app/services/spar_plan_service.py:193 (snap_piece_to_stock) replaces the solved OD with a Component-Library stock OD after the solver has finished. Downstream code that reconstructs erf_W from outer_d (_erf_w_for_piece:218) therefore reads a snapped value on any second snap pass.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Confirmed priority rule: keep a piece continuous only while its strength-required OD fits the local section at every covered station. Otherwise split + telescope. **Strength beats part-count.**`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
