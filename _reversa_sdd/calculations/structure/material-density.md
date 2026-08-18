---
name: material-density
symbol: ρ
kind: parameter
unit: kg/m³
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Material density

**Definition.** Density of the spar material, read from the material component's specs; drives the mass integral.

**Formula — as the code writes it.**

```
density = float(material_specs["density_kg_m3"])
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:299` — `compute_spar_sizing`

**Consumed by.**

- in this graph: [[spar-mass-half|Half-span spar mass]]
- outside it: `app/services/spar_sizing.py:360` · `app/services/spar_sizing.py:375` · `frontend/lib/sparSizingHelpers.ts:117`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer (RC-Network Wiki "CFK" and "Kohlefaser" describe carbon density only qualitatively — "very low density: excellent strength-to-weight ratio" — and give no kg/m³ figure); aircraft-design-scholz (Sadraey Table 10.6 "density of construction material" exists and is referenced by Eq. 10.3, but it was not retrievable in the vault at the granularity needed to attribute a specific CFRP value)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
