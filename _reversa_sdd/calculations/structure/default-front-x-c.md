---
name: default-front-x-c
symbol: x/c_front
kind: constant
unit: dimensionless (x/c)
cluster: structure
user_visible: false
source_status: SOURCED
---

# Assumed front-spar chord fraction

**Definition.** Chord fraction assumed for the front spar SOLELY to derive the front–rear spacing for the rear torsion reaction, when the request leaves front_x_over_chord unset. The front spar itself still samples the real max-thickness location.

**Value.** `0.30`

**Formula — as the code writes it.**

```
_DEFAULT_FRONT_X_C = 0.30
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_plan_service.py:43` — `_DEFAULT_FRONT_X_C`

**Consumed by.**

- in this graph: [[spar-spacing-fraction|Front–rear spar chordwise spacing]]
- outside it: `app/services/spar_plan_service.py:411`

**Source.** 🟢 SOURCED

> Scholz, Flugzeugentwurf / Aircraft Design (HAW Hamburg lecture notes), 07_WingDesign §7.4, p. 7-42 — "Typical locations for the spars are as follows: • Front spar: 15% to 30% of the chord"
>
> — via `aircraft-design-scholz (lead) + rc-aircraft-designer (corroboration)`

**The source states it as.**

```
Front spar: 15% to 30% of the chord.
```

**⚠️ Divergence from the source.** 0.30 is the AFT END of Scholz's band, not its centre. Corroborated independently at RC scale by two lower-authority sources that both place the front spar at the section's deepest point rather than at a fixed chord fraction: Lennon, The Basics of R/C Model Aircraft Design (1996), Ch. 13 — the main spar is "placed at or near the thickest point of the airfoil"; RC-Network Wiki, "Holm" — the Holmsteg is "located near the maximum depth (typically ~⅓ of chord)". The code's own comment ("front sits at section max-thickness, typically ~0.30c") matches these. Real divergence: the code uses the ASSUMED 0.30 only for the torsion-couple spacing while the front spar itself is placed at the scanned max-thickness location (cad_designer/airplane/geometry/section_geometry.py:395), and nothing reconciles the two.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Scholz's 15-30% band is CS-25 transport-category, derived from compatibility with leading-edge slats. RC/UAV wings at 0.5-15 kg have no slats; the RC sources (Lennon Ch. 13, RC-Network "Holm") reach a similar location for a different reason — maximum section depth. The number coincides; the justification does not transfer. ADR 0023: validate against max-thickness location, not against the transport band.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic number with a rationale but no citation ('typically ~0.30c on common airfoils'). It is an ASSUMED value that silently diverges from the actual max-thickness location the front spar is placed at — nothing checks the two against each other.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `gh-1038: Front-spar chord fraction assumed for the torsion-couple spacing when ``front_x_over_chord`` is None (front sits at section max-thickness, typically ~0.30c on common airfoils).`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
