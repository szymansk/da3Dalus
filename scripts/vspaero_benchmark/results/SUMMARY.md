# VSPAERO × da3Dalus — Benchmark Summary

Offline cross-validation on identical `.vsp3` geometry and reference quantities. VSPAERO runs VLM (wings-only); ASB AeroBuildup is the app's default method.

## Max L/D — tool vs reality

| Aircraft | Topology | VSPAERO VLM | ASB VLM | ASB AeroBuildup | Real |
|---|---|---|---|---|---|
| Glaser-Dirks DG-101G | High-AR Standard-Class sailplane | 30.05 | 287.4 | 39.06 | 38.3 |
| Cessna 172 | Conventional GA, strut-braced high wing | 21.46 | 201.3 | 14.09 | 10.5 |
| Supermarine Spitfire | Elliptical planform (e → 1 test) | 2.977 | 59.18 | 21.36 | — |
| Ligeti Stratos | Closed-tandem / joined-tip Boxwing | 484.1 | 1087 | — | 20 |
| Titan Dynamics Falcon V2 | 3D-printed RC/UAV; cambered wing (NACA 4411→3411), 4° washout, V-tail | 17.26 | 109.5 | 20.82 | 12 |

## VLM lift-slope agreement (ASB VortexLattice vs VSPAERO)

| Aircraft | VSPAERO C_Lα | ASB-VLM C_Lα | Δ | C_L0 offset |
|---|---|---|---|---|
| Glaser-Dirks DG-101G | 0.1021 | 0.1039 | +1.7 % | -0.4911 |
| Cessna 172 | 0.08847 | 0.09137 | +3.3 % | -0.01861 |
| Supermarine Spitfire | 0.07354 | 0.07606 | +3.4 % | 0.18 |
| Ligeti Stratos | 0.1128 | 0.1395 | +23.7 % | -0.3884 |
| Titan Dynamics Falcon V2 | 0.0922 | 0.09563 | +3.7 % | -0.07389 |

## Span efficiency (mean over sweep)

| Aircraft | VSPAERO | ASB VLM | ASB AeroBuildup |
|---|---|---|---|
| Glaser-Dirks DG-101G | 0.8129 | 0.9912 | 0.8033 |
| Cessna 172 | 0.7076 | 0.9313 | 0.8198 |
| Supermarine Spitfire | 0.05844 | 0.9609 | 0.8296 |
| Ligeti Stratos | 2.48 | 1.35 | 0.7811 |
| Titan Dynamics Falcon V2 | 0.7084 | 1.028 | 0.8106 |

> See each aircraft's `RESULTS.md` for full metrics + interpretation, and `dashboard.html` for interactive polars.