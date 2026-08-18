---
name: reinforcement-reach
kind: quantity
unit: mm
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
---

# Reinforcement half-reach

**Definition.** How far the root reinforcement extends into each half: to the first outboard station of the shorter side, or root y plus the reinforcement OD when a half has only one station.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
reach = min(
    abs(left[1].y_mm) if len(left) > 1 else abs(left[0].y_mm) + root_od,
    abs(right[1].y_mm) if len(right) > 1 else abs(right[0].y_mm) + root_od,
)
```

**Inputs.**

- [[reinforcement-root-od|Reinforcement outer diameter]]
- [[station-y-mm|Station spanwise position]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:621` — `_reinforcement_piece`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Reinforcement length`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:624` · `cad_designer/airplane/geometry/spar_solver.py:649`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer. No source read gives an overlap length for a root carry-through or joiner. Sadraey §7.9.3 and RC-Network "Steckung" both establish that this joint is the most highly loaded in the aircraft, which makes the absence of any sizing criterion more serious, not less: the code sets the reinforcement's structural length from the SAMPLING RESOLUTION (it reaches to station index 1), so doubling n_span halves the reinforcement length. In the single-station fallback branch a LENGTH is formed by adding a DIAMETER (abs(y_mm) + root_od), which no source supports.`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** The reinforcement's structural length is set by the SAMPLING RESOLUTION (n_span), not by any strength or joint criterion: it reaches to whatever station index 1 happens to be. Doubling n_span halves the reinforcement length. In the one-station fallback branch a LENGTH is formed by adding a DIAMETER (abs(y_mm) + root_od) — dimensionally a length, but with no engineering basis stated.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# short symmetric span: reach to the first outboard station of each half`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
