---
name: erf-w-for-piece
symbol: erf_W
kind: quantity
unit: mm³
cluster: structure
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - flag/anomaly
  - flag/divergence
---

# Reconstructed required section modulus for a piece

**Definition.** The required section modulus a solved SparPiece must satisfy, reconstructed from the piece's pre-snap outer diameter via the solid-rod relation.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return piece.outer_d**3 / 10.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_plan_service.py:218` — `_erf_w_for_piece`

**Consumed by.**

- outside it: `app/services/spar_plan_service.py:260` · `app/services/spar_plan_service.py:262`

**Source.** 🟡 PARTIAL

> Kirch, "Hauptholm", https://www.flugmodellbau-kirch.de/Hauptholm.htm — the d³/10 rod convention (see `section-modulus-rod`)
>
> — via `direct verification of the kirch source`

**The source states it as.**

```
Source gives a rod W table consistent with d³/10; it never inverts an OD back into a requirement.
```

**⚠️ Divergence from the source.** The reconstruction direction is the code's invention, not the source's. Kirch's procedure carries M forward and compares W_available > W_required (steps 2-4); the code discards erf_W after sizing and RECONSTRUCTS it from the piece OD. The docstring's "~1.8% conservative" claim is correct for this direction (the exact figure is 1.86%). Two real hazards the source cannot cover: the OD may already have been inflated by tube bore-propagation (cad_designer/airplane/geometry/spar_solver.py:426), and on a second snap pass the OD is a stock value (app/services/spar_plan_service.py:193), so the "requirement" drifts away from the real moment.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second independent producer of the identical formula: cad_designer/airplane/geometry/spar_solver.py:521 (required_section_modulus_from_od). Also: it reconstructs erf_W from a piece OD that may already have been inflated by tube bore-propagation (spar_solver.py:426), so for inner telescoping pieces the reconstructed requirement is larger than the real strength requirement.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `This is ~1.8 % conservative vs the exact solid-circular W = π·d³/32; the upstream sizing intentionally uses d³/10 throughout, so staying consistent here avoids a unit inconsistency.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
