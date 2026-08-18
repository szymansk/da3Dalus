---
name: negligible-od-floor-mm
kind: constant
unit: mm
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/structure
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
---

# Buildable-minimum spar outer diameter

**Definition.** Outer-diameter floor below which a spar piece is considered a non-object: no orderable/cuttable carbon spar exists that small, and the D-box skin plus ribs carry the tip. Trailing sub-floor pieces are dropped and reported as a no-spar region.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.0`

**Formula — as the code writes it.**

```
NEGLIGIBLE_OD_FLOOR_MM = 1.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:53` — `NEGLIGIBLE_OD_FLOOR_MM`

**Consumed by.**

- in this graph: `No-spar region start` · `Buildable front pieces`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:463` · `app/services/spar_insert_service.py:282` · `app/services/spar_insert_service.py:284`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer. No RC source read gives a minimum buildable carbon spar diameter. The nearest attributable statement is RC-Network Wiki, "Steckung" (https://wiki.rc-network.de/wiki/Steckung), that spar joints require "precision-fit components" — but no dimension. The code comment already flags 1.0 mm as provisional pending #1081. Two further problems are independent of provenance: the comment says the threshold is applied to `required_od` while the code applies it to `kept[-1].outer_d` (which bore-propagation may have inflated), and the comment's justification "the D-box skin + ribs carry the tip" is contradicted by the project's settled record (BR-W16, gh-1079: neither manufacturing route builds a D-box, and a film covering cannot form a torsion box at all — this is gh-1136).`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Magic number with a rationale but no source; the comment itself flags it as provisional pending #1081. The comment says the threshold is applied on ``required_od``, but the code at line 463 applies it to ``kept[-1].outer_d`` — which for a tube may have been inflated above required_od by bore propagation (line 426), so a piece can survive the floor on a diameter it did not need for strength.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `gh-1076: buildable-minimum spar outer diameter (mm). A tip station whose design-moment-driven required OD falls below this floor carries negligible bending load — no orderable/cuttable carbon spar exists that small, and the D-box skin + ribs carry the tip. ... The threshold is applied on ``required_od``, which is already the design moment (M·g·j) sizing produced upstream in :func:`build_stations_from_geometry`. Tie to the real CF-pin stock floor (#1081) when that lands.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
