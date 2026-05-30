# Supermarine Spitfire — VSPAERO vs AeroSandbox

- **Topology:** Elliptical planform (e → 1 test)
- **Category:** tool_vs_tool
- **Flight point:** V = 102.0 m/s, altitude = 0.0 m
- **Notes:** Elliptical wing: do both tools recover near-unity span efficiency?

## Real-world anchors

| Metric | Value | Source |
|---|---|---|
| CLmax | 1.36 | Shenstone / RAeS (qualitative) |

## Computed metrics

| Metric | VSPAERO (VLM, wings-only) | ASB VortexLattice (inviscid) | ASB AeroBuildup (app default) |
|---|---|---|---|
| C_L at α=0 | 0.0825 | 0.2625 | 0.3755 |
| C_Lα [1/deg] | 0.07354 | 0.07606 | 0.08889 |
| C_D,min | 0.04272 | 0.00209 | 0.01038 |
| max L/D | 2.977 | 59.18 | 21.36 |
| α at max L/D [deg] | 2 | -1 | -0.999 |
| C_Mα [1/deg] | 0.1786 | 0.1839 | 0.2097 |
| mean span-eff e | 0.05844 | 0.9609 | 0.8296 |
| C_L max (in sweep) | 1.198 | 1.19 | 1.408 |

## ⚠️ Data-quality flags

- **VSPAERO (VLM, wings-only):** non-physical span efficiency e=0.058 (≪ typical 0.7–1.0) — induced-drag solve looks unreliable for this geometry

## Interpretation

> Auto-generated headline comparisons; fill in narrative below.

- **VLM C_Lα agreement (ASB vs VSPAERO):** 0.0761 vs 0.0735 /deg → Δ = +3.4 %.
- **C_L0 offset (ASB vs VSPAERO VLM):** 0.263 vs 0.083 → Δ = +0.180. A matched slope with a C_L0 offset points to an airfoil camber / zero-lift-angle interpretation difference, not reference area.
