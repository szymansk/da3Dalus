---
name: max-od-from-stations
symbol: max_od
kind: quantity
unit: mm
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

# Containment-band OD limit at governing station

**Definition.** Hard geometric upper bound on the outer diameter a snapped stock item may have: the contained z-band depth at the station nearest the piece's governing y.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
closest = min(stations, key=lambda s: abs(s.y_mm - governing_y_mm))
return max(0.0, closest.band_hi - closest.band_lo)
```

**Inputs.**

- [[band-lo|Contained band lower bound]]  — *⊣ limit*
- [[band-hi|Contained band upper bound]]  — *⊣ limit*

**Produced by.** `app/services/spar_plan_service.py:234` — `_max_od_from_stations`

**Consumed by.**

- outside it: `app/services/spar_plan_service.py:261` · `app/services/spar_plan_service.py:155` · `app/services/spar_plan_service.py:169`

**Source.** 🟡 PARTIAL

> Lennon, The Basics of R/C Model Aircraft Design (Air Age 1996), Ch. 13, Figs. 6-8 — the spar sits within the airfoil envelope, flanges as far from the neutral axis as the section allows; RC-Network Wiki, "Holm", https://wiki.rc-network.de/wiki/Holm — insufficient section depth produces spar oil-canning visible as ripples in the finished airfoil
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
The principle that the local section depth is a hard geometric bound on the spar is attributable; the specific band arithmetic is not.
```

**⚠️ Divergence from the source.** Independent of any source, the docstring contradicts the code it documents: it says "Return the containment-band half-depth (mm)" and "(band_hi - band_lo) / 2", while the code returns the FULL depth `max(0.0, closest.band_hi - closest.band_lo)`. The code is physically right for a spar centred on the band midpoint; the docstring is wrong and would lead a reader to halve the value and reject all adequate stock.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The docstring contradicts the code. It says 'Return the containment-band half-depth (mm)' and states the value is '(band_hi - band_lo) / 2'; the code returns the FULL depth (band_hi - band_lo). The code is physically right for a spar centred on the band midpoint, so the docstring is the wrong half of the pair — but a reader trusting the docstring would halve this value and reject all adequate stock.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `The governing station is the one whose ``y_mm`` is closest to ``governing_y_mm``.  The band half-depth ``(band_hi - band_lo) / 2`` is the maximum OD a spar centred on ``center_z`` can have without breaching the packing clearance — i.e. the hard upper bound on OD.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
