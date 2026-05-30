# Glaser-Dirks DG-101G — VSPAERO vs AeroSandbox

- **Topology:** High-AR Standard-Class sailplane
- **Category:** anchored
- **Flight point:** V = 29.17 m/s, altitude = 1500.0 m
- **Notes:** Strongest external anchor; community VSPAERO reference exists.

## Real-world anchors

| Metric | Value | Source |
|---|---|---|
| max_LD | 38.3 | Akaflieg flight polar (POH) |
| max_LD_vspaero_ref | 26 | Luka, OpenVSP groups (VSPAERO VLM) |

## Computed metrics

| Metric | VSPAERO (VLM, wings-only) | ASB VortexLattice (inviscid) | ASB AeroBuildup (app default) |
|---|---|---|---|
| C_L at α=0 | 0.8726 | 0.3815 | 0.5522 |
| C_Lα [1/deg] | 0.1021 | 0.1039 | 0.1141 |
| C_D,min | 0.02221 | 0.000603 | 0.01005 |
| max L/D | 30.05 | 287.4 | 39.06 |
| α at max L/D [deg] | -1 | -2 | 1.001 |
| C_Mα [1/deg] | -0.03084 | -0.03149 | -0.04168 |
| mean span-eff e | 0.8129 | 0.9912 | 0.8033 |
| C_L max (in sweep) | 2.071 | 1.606 | 1.579 |

## Interpretation

> Auto-generated headline comparisons; fill in narrative below.

- **VLM C_Lα agreement (ASB vs VSPAERO):** 0.1039 vs 0.1021 /deg → Δ = +1.7 %.
- **C_L0 offset (ASB vs VSPAERO VLM):** 0.382 vs 0.873 → Δ = -0.491. A matched slope with a C_L0 offset points to an airfoil camber / zero-lift-angle interpretation difference, not reference area.
- **max L/D — VSPAERO (VLM, wings-only):** 30.1 vs real 38.3 → -22 %.
- **max L/D — ASB VortexLattice (inviscid):** 287.4 vs real 38.3 → +650 %.
- **max L/D — ASB AeroBuildup (app default):** 39.1 vs real 38.3 → +2 %.
