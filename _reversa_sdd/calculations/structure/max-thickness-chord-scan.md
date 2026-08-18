---
name: max-thickness-chord-scan
kind: constant
unit: dimensionless (x/c)
cluster: structure
user_visible: true
source_status: PARTIAL
---

# Max-thickness chord search grid

**Definition.** Chord positions scanned to find the deepest point of a section — the natural spar-placement reference used when no explicit x/c is requested.

**Value.** `np.linspace(0.05, 0.6, 23)`

**Formula — as the code writes it.**

```
candidates = np.linspace(0.05, 0.6, 23)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `cad_designer/airplane/geometry/section_geometry.py:395` — `SectionGeometry.at_max_thickness`

**Consumed by.**

- outside it: `cad_designer/airplane/geometry/section_geometry.py:397` · `cad_designer/airplane/geometry/section_geometry.py:402` · `cad_designer/airplane/geometry/spar_solver.py:756` · `app/services/section_thickness.py:75`

**Source.** 🟡 PARTIAL

> Lennon, The Basics of R/C Model Aircraft Design (Air Age 1996), Ch. 13, Figs. 6-8 — the main spar is "placed at or near the thickest point of the airfoil so the flanges are as far from the neutral axis as possible"; RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm — the Holmsteg is "located near the maximum depth (typically ~⅓ of chord)"
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Both RC sources state the design intent the scan implements: place the spar at the section's deepest point. RC-Network additionally gives the expected answer (~⅓ chord).
```

**⚠️ Divergence from the source.** The INTENT is well sourced at RC scale by two independent sources. The scan PARAMETERS are not: the 0.05-0.6 chord window and the 23-point resolution have no basis in any source. Two consequences: the 0.6 aft limit silently caps where the front spar can be placed, so a reflexed or aft-max-thickness section's true deepest point would never be found; and the ~2.5%-chord quantisation propagates into SparPieceOut.x_over_chord, a user-visible number. Note both sources land near ⅓ chord, which is aft of the code's assumed 0.30 (see `default-front-x-c`) and well inside the 0.6 window for conventional sections — the limits bite only for unconventional ones.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Three undocumented magic numbers. The 0.6 aft limit silently caps where the front spar can be placed; a reflexed or aft-max-thickness section's true deepest point would never be found. The 23-point resolution (~2.5 % chord steps) quantises the resulting front-spar x/c, which is reported to the user as SparPieceOut.x_over_chord.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Scans a chord grid and returns the point with the greatest thickness — the natural spar-placement reference.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
