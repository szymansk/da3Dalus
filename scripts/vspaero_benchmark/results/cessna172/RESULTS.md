# Cessna 172 — VSPAERO vs AeroSandbox

- **Topology:** Conventional GA, strut-braced high wing
- **Category:** anchored
- **Flight point:** V = 50.0 m/s, altitude = 0.0 m
- **Notes:** Multiple wind-tunnel reports; classic validation case.

## Real-world anchors

| Metric | Value | Source |
|---|---|---|
| CD0 | 0.0376 | WT lab report (academic) |
| max_LD | 10.5 | flight test, M=0.32 |
| CLmax | 1.5 | WT / POH stall speed |

## Computed metrics

| Metric | VSPAERO (VLM, wings-only) | ASB VortexLattice (inviscid) | ASB AeroBuildup (app default) |
|---|---|---|---|
| C_L at α=0 | 0.1556 | 0.137 | 0.24 |
| C_Lα [1/deg] | 0.08847 | 0.09137 | 0.1018 |
| C_D,min | 0.008923 | 0.000226 | 0.0236 |
| max L/D | 21.46 | 201.3 | 14.09 |
| α at max L/D [deg] | 3 | -1 | 4.001 |
| C_Mα [1/deg] | -0.0251 | -0.03019 | -0.04175 |
| mean span-eff e | 0.7076 | 0.9313 | 0.8198 |
| C_L max (in sweep) | 1.21 | 1.213 | 1.416 |

## Interpretation

> Auto-generated headline comparisons; fill in narrative below.

- **VLM C_Lα agreement (ASB vs VSPAERO):** 0.0914 vs 0.0885 /deg → Δ = +3.3 %.
- **C_L0 offset (ASB vs VSPAERO VLM):** 0.137 vs 0.156 → Δ = -0.019. A matched slope with a C_L0 offset points to an airfoil camber / zero-lift-angle interpretation difference, not reference area.
- **max L/D — VSPAERO (VLM, wings-only):** 21.5 vs real 10.5 → +104 %.
- **max L/D — ASB VortexLattice (inviscid):** 201.3 vs real 10.5 → +1817 %.
- **max L/D — ASB AeroBuildup (app default):** 14.1 vs real 10.5 → +34 %.
