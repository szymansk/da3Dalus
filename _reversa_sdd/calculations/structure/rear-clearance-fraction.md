---
name: rear-clearance-fraction
kind: constant
unit: dimensionless (fraction of chord)
cluster: structure
user_visible: false
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/structure
  - class/unclassified-constant
  - source/partial
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Rear-spar control-surface clearance

**Definition.** Chordwise margin a COMPUTED rear/torsion spar keeps in front of the control-surface hinge line so it never overlaps the movable surface.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.03`

**Formula — as the code writes it.**

```
_REAR_CLEARANCE_FRACTION = 0.03
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:184` — `_REAR_CLEARANCE_FRACTION`

**Consumed by.**

- in this graph: `Clamped rear-spar chord location`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:215` · `cad_designer/airplane/geometry/spar_solver.py:246`

**Source.** 🟡 PARTIAL

> Scholz, Flugzeugentwurf, 07_WingDesign §7.4, p. 7-42 — "Space has to be left between the rear spar and the hinge line to accommodate the drive mechanism of the ailerons"; Sadraey, Aircraft Design (Wiley 2013), §12.4.3 constraint 4 — the rear spar is the most forward limit for the hinge line
>
> — via `aircraft-design-scholz (lead) + rc-aircraft-designer`

**The source states it as.**

```
Both sources state that a chordwise margin between the rear spar and the hinge line is REQUIRED. Neither quantifies it.
```

**⚠️ Divergence from the source.** The requirement is sourced by both authorities; the value 0.03c is not attributable to either, nor to any RC source read.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Scholz's justification for the margin is transport-category hardware — clearance for the aileron/spoiler DRIVE MECHANISM. An RC/UAV wing at 0.5-15 kg has no such mechanism (film or pinned hinge, servo horn), so the physical quantity the margin must accommodate is entirely different. ADR 0023: 0.03c is not validated at RC/UAV scale.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic number with no source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Default chordwise margin (fraction of chord) a COMPUTED rear/torsion spar keeps in front of a control-surface hinge line so it never overlaps the movable surface. gh-1059.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
