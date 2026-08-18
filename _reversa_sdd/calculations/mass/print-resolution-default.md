---
name: print-resolution-default
symbol: t_wall
kind: constant
unit: mm
cluster: mass
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/mass
  - class/unclassified-constant
  - source/no-source-found
  - flag/anomaly
---

# Default print wall resolution

**Definition.** Fallback wall thickness used to turn a printed surface area into a printed volume when the material component's specs carry no 'print_resolution_mm'.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.4`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/component_tree_service.py:454` — `_weight_from_cad_shape`

**Consumed by.**

- in this graph: `CAD shape own weight — surface print`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/component_tree_service.py:455 (surface-print weight)`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Magic number with no explanatory comment and no cited source in this file. The same value appears independently as a component-type field default in app/services/component_type_service.py:347 and alembic/versions/28a13fbeac90_...py:34 — three independent copies of the same default with no single authority.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
