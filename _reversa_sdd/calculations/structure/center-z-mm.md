---
name: center-z-mm
symbol: center_z
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

# Section mid-height (spar placement reference)

**Definition.** Mid-height of the built section at the station, in the wing-local frame — the reference height a spar should be centred on.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
center_z_mm=_lookup_center_z(center_z_by_y, y_m),
```

**Inputs.**

- [[section-center-z-analytic|Section mid-height (analytic)]]
- [[center-z-nearest-key-tolerance|center_z nearest-key lookup tolerance]]

**Produced by.** `app/services/spar_sizing.py:341` — `compute_spar_sizing`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟡 PARTIAL

> Lennon, The Basics of R/C Model Aircraft Design (Air Age 1996), Ch. 13, Figs. 6-8 (D-spar: flanges symmetric about the section's neutral axis); RC-Network Wiki, "Mechanische Spannung (Materialkunde)", https://wiki.rc-network.de/wiki/Mechanische_Spannung — in a beam under bending "the upper region experiences tension, the lower region experiences compression, while stress in the middle becomes minimal"
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
The mid-depth of the section is the neutral axis, the reference a symmetric spar is centred on.
```

**⚠️ Divergence from the source.** The concept is sourced; the specific mapping (a {y_m: mid-height} map with nearest-key lookup) is implementation.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** NO CONSUMER. It is computed, serialised in SparSizingStation (app/schemas/spar_sizing.py:71) and shipped in the API response, but the frontend interface SparSizingStation (frontend/hooks/useSparSizing.ts:16-29) does not declare the field and nothing else in the repo reads it outside app/tests/test_spar_thickness_wirein.py.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Optional mapping {y_m: section mid-height (mm)} from the built CAD section (gh-1022) — surfaced per-station as ``center_z_mm`` for spar placement.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
