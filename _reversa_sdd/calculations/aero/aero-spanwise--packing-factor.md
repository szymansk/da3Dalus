---
name: aero-spanwise--packing-factor
kind: parameter
unit: -
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Packing factor

**Definition.** Fraction of the local profile thickness the spar may occupy.

**Value.** `0.8`

**Formula — as the code writes it.**

```
packing_factor: Annotated[float, Query(gt=0, le=1.0, description="Packing factor (default 0.8)")] = 0.8
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/api/v2/endpoints/aeroanalysis.py:612` — `get_airplane_spanwise_loads_with_sizing`

**Consumed by.**

- in this graph: [[spar-outer-dimension|Spar outer dimension]] · [[station-clearance|Station packing clearance]]
- outside it: `compute_spar_sizing via spar_params`

**Source.** 🔴 NO SOURCE FOUND

> 0.8 has no attribution. Scholz 07_WingDesign §7.4 discusses box depth and EI ∝ h³ but gives no fraction of profile thickness the spar may occupy; RC-Network 'Holm' describes boom placement at maximum separation without a numeric packing fraction.
>
> — via `aircraft-design-scholz, rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Scale (ADR 0023).** ADR 0023: unvalidated at 0.5–15 kg, where skin/sheeting thickness is a much larger fraction of section depth than at transport scale, so the usable fraction is plausibly lower than 0.8.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
