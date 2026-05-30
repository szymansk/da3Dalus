# Titan Dynamics Falcon V2 — VSPAERO vs AeroSandbox

- **Topology:** 3D-printed RC/UAV; cambered wing (NACA 4411→3411), 4° washout, V-tail
- **Category:** anchored
- **Flight point:** V = 15.0 m/s, altitude = 0.0 m
- **Notes:** Real 3D-printed RC model — exact app target audience. Anchors are Titan Dynamics' own CFD (not WT/flight). CFD drag is full-aircraft (incl. fuselage), so only AeroBuildup compares on total C_D; C_Di, C_Lα, AoA are the clean comparisons. Known airfoils (NACA 4411 root) make this the test for the importer camber fidelity (#791).

## Real-world anchors

| Metric | Value | Source |
|---|---|---|
| CLmax | 1.42 | Titan Dynamics manual (CFD) |
| max_LD | 12 | Titan CFD drag plot, AUW 3 kg, full aircraft |

## Computed metrics

| Metric | VSPAERO (VLM, wings-only) | ASB VortexLattice (inviscid) | ASB AeroBuildup (app default) |
|---|---|---|---|
| C_L at α=0 | 0.4461 | 0.3722 | 0.5128 |
| C_Lα [1/deg] | 0.0922 | 0.09563 | 0.1019 |
| C_D,min | 0.0216 | 0.001646 | 0.01684 |
| max L/D | 17.26 | 109.5 | 20.82 |
| α at max L/D [deg] | 2 | -2 | 0.001 |
| C_Mα [1/deg] | -0.01913 | -0.02298 | -0.03498 |
| mean span-eff e | 0.7084 | 1.028 | 0.8106 |
| C_L max (in sweep) | 1.531 | 1.495 | 1.254 |

## Interpretation

> Auto-generated headline comparisons; fill in narrative below.

- **VLM C_Lα agreement (ASB vs VSPAERO):** 0.0956 vs 0.0922 /deg → Δ = +3.7 %.
- **C_L0 offset (ASB vs VSPAERO VLM):** 0.372 vs 0.446 → Δ = -0.074. A matched slope with a C_L0 offset points to an airfoil camber / zero-lift-angle interpretation difference, not reference area.
- **max L/D — VSPAERO (VLM, wings-only):** 17.3 vs real 12.0 → +44 %.
- **max L/D — ASB VortexLattice (inviscid):** 109.5 vs real 12.0 → +812 %.
- **max L/D — ASB AeroBuildup (app default):** 20.8 vs real 12.0 → +74 %.
