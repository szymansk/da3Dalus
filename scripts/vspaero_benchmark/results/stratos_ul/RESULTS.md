# Ligeti Stratos — VSPAERO vs AeroSandbox

- **Topology:** Closed-tandem / joined-tip Boxwing
- **Category:** anchored
- **Flight point:** V = 50.0 m/s, altitude = 0.0 m
- **Notes:** Boxwing topology stress-test; joined tips. Original 1985 prototype.

## Real-world anchors

| Metric | Value | Source |
|---|---|---|
| max_LD | 20 | Ligeti open-source spec sheet |
| CLmax | 1.45 | from published Vs 58-61 km/h |

## Computed metrics

| Metric | VSPAERO (VLM, wings-only) | ASB VortexLattice (inviscid) | ASB AeroBuildup (app default) |
|---|---|---|---|
| C_L at α=0 | 0.611 | 0.2227 | — |
| C_Lα [1/deg] | 0.1128 | 0.1395 | — |
| C_D,min | 0.003418 | -5.2e-05 | — |
| max L/D | 484.1 | 1087 | — |
| α at max L/D [deg] | 12 | -2 | — |
| C_Mα [1/deg] | -0.1514 | -0.2349 | — |
| mean span-eff e | 2.48 | 1.35 | 0.7811 |
| C_L max (in sweep) | 1.647 | 1.867 | — |

## ⚠️ Data-quality flags

- **VSPAERO (VLM, wings-only):** span efficiency e=2.48 > 1.0 — expected for a box wing (beats the monoplane limit), but the AR-based formula is only indicative here
- **ASB VortexLattice (inviscid):** span efficiency e=1.35 > 1.0 — expected for a box wing (beats the monoplane limit), but the AR-based formula is only indicative here
- **ASB AeroBuildup (app default):** method produced all-NaN (failed for this geometry)

## Interpretation

> Auto-generated headline comparisons; fill in narrative below.

- **VLM C_Lα agreement (ASB vs VSPAERO):** 0.1395 vs 0.1128 /deg → Δ = +23.7 %.
- **C_L0 offset (ASB vs VSPAERO VLM):** 0.223 vs 0.611 → Δ = -0.388. A matched slope with a C_L0 offset points to an airfoil camber / zero-lift-angle interpretation difference, not reference area.
- **max L/D — VSPAERO (VLM, wings-only):** 484.1 vs real 20.0 → +2321 %.
- **max L/D — ASB VortexLattice (inviscid):** 1087.1 vs real 20.0 → +5336 %.
- ⚠️ **VSPAERO (VLM, wings-only): mean span efficiency e = 2.480 > 1.0** — non-physical; flag rather than hide (VLM tip discretisation / back-computed-e artifact).
- ⚠️ **ASB VortexLattice (inviscid): mean span efficiency e = 1.350 > 1.0** — non-physical; flag rather than hide (VLM tip discretisation / back-computed-e artifact).
