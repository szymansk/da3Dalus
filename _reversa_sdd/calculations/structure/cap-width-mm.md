---
name: cap-width-mm
symbol: b
kind: parameter
unit: mm
cluster: structure
user_visible: true
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/structure
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Cap/flange width

**Definition.** Flange width of a capped (I/C-beam) spar. Required for shape='capped'; ignored for other shapes.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
cap_width_mm: Optional[float] = Field(
    None,
    gt=0,
    description=("Flange/cap width b (mm) — required for shape='capped', ignored otherwise."),
)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/spar_sizing.py:47` — `SparSizingParams.cap_width_mm`

**Consumed by.**

- in this graph: `Capped-spar cross-section area` · `Capped-spar inner-height cube`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:330` · `app/services/spar_sizing.py:196` · `frontend/hooks/useSparSizing.ts:64`

**Source.** 🟢 SOURCED

> Kirch, "Hauptholm", Flugmodellbau Kirch, https://www.flugmodellbau-kirch.de/Hauptholm.htm — "b = flange width (mm)" in W = b(H³−h³)/(6H); RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm (Holmgurt width)
>
> — via `direct verification of the kirch source + rc-aircraft-designer`

**The source states it as.**

```
b is the source's own symbol for flange width and is a free input to the source's formula, exactly as in the code.
```

**⚠️ Divergence from the source.** The parameter is sourced. Its ABSENCE from SparPlanRequest is a real gap: the plan path accepts shape='capped' (app/schemas/spar_plan.py:166) with no cap_width field, so the one shape the cited source actually documents in closed form cannot be sized through the plan endpoint.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Exists only in SparSizingParams. SparPlanRequest accepts shape='capped' (app/schemas/spar_plan.py:166) but has NO cap_width field, so the plan path can never size a real capped section.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Flange/cap width b (mm) — required for shape='capped', ignored otherwise.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
