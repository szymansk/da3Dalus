---
name: structure--g-limit
symbol: n_lim / g_limit
kind: parameter
unit: g
cluster: structure
user_visible: true
source_status: SOURCED
---

# Manoeuvre limit load factor

**Definition.** Limit load factor from the aeroplane's design assumptions; multiplies the aerodynamic bending moment into the design moment.

**Formula — as the code writes it.**

```
g_limit = float(g_limit_raw)
```

**Inputs.** [[structure--g-limit-default|Default manoeuvre limit load factor]]

**Produced by.** `app/services/analysis_service.py:2162` — `_compute_spar_sizing_for_surfaces`

**Consumed by.**

- in this graph: [[design-bending-moment|Design bending moment]] · [[flight-envelope-n-max|Design limit load factor (published)]]
- outside it: `app/services/spar_sizing.py:315` · `app/services/spar_sizing.py:376` · `frontend/lib/sparSizingHelpers.ts:118` · `frontend/components/workbench/SparSizingPanel.tsx:145`

**Source.** 🟢 SOURCED

> Lennon, The Basics of R/C Model Aircraft Design (Air Age 1996), Ch. 21 "Centrifugal Force and Maneuverability" (p. 98), formula printed Ch. 4 (p. 19); Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §10.4.1, Table 10.9 "Maximum positive load factor for various aircraft" (p. 561)
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
Lennon (verbatim, Ch. 4 p. 19 / Ch. 21): N = 1 + (1.466 × mph)² / (R × G), where N = load factor in G's, mph = speed in mph, R = manoeuvre radius in feet, G = 32.2 ft/s². Worked example: N = 1 + (1.466 × 90)²/(50 × 32.2) = 11.8 G's. Lennon Ch. 19 gives the same formula at 100 mph / 60 ft radius → 12.1 G. Sadraey Table 10.9: GA normal 2.5-3.8; GA utility 4.4; GA acrobatic 6; Home-built 2.5-5; Remote-controlled model 1.5-2; Transport 3-4; Supersonic fighter 7-10.
```

**⚠️ Divergence from the source.** The QUANTITY is well sourced at RC scale — Lennon Ch. 21 is a genuine RC manoeuvre-load method. The code neither implements Lennon's formula nor validates the supplied g_limit against it; it accepts whatever the design assumption holds. Two independent resolvers exist (analysis_service.py:2153 tracks a fallback flag, spar_plan_service.py:351 does not), so the same aircraft can be sized on different load factors by the two endpoints.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey Table 10.9's "Remote-controlled model 1.5-2" row must NOT be used to size a spar: it sits in §10.4.1 Wing Weight and is a regression coefficient co-fitted with K_ρ (Table 10.8, RC row 0.001-0.0015) against wing mass in Eq. (10.3). The project's own settled record (BR-W16, gh-1079) states this explicitly and gives cross-validated real RC n_limit values instead: trainer 4-6, sport 6-8, aerobatic/3D 10-14, pylon 14-19, glider 5-7. Lennon Ch. 21's 11.8 G worked example corroborates that band.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Two independent resolvers of the same design quantity: app/services/analysis_service.py:2153 (sizing path, tracks g_limit_fallback) and app/services/spar_plan_service.py:351 (plan path, does NOT surface a fallback flag).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
