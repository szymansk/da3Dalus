---
name: design-bending-moment
symbol: M_design
kind: quantity
unit: N·m
cluster: structure
user_visible: true
source_status: PARTIAL
---

# Design bending moment

**Definition.** The bending moment the spar is sized to: the magnitude of the aerodynamic bending moment at the station, scaled by the manoeuvre limit load factor and the safety factor.

**Formula — as the code writes it.**

```
m_design = abs(bm) * g_limit * params.safety_factor_j
```

**Inputs.** [[structure--g-limit|Manoeuvre limit load factor]] · [[structure--safety-factor-j|Safety factor j]]

**Produced by.** `app/services/spar_sizing.py:315` — `compute_spar_sizing`

**Consumed by.**

- in this graph: [[required-section-modulus|Required section modulus]]
- outside it: `app/services/spar_sizing.py:318` · `app/services/spar_sizing.py:342` · `app/schemas/spar_sizing.py:78` · `frontend/hooks/useSparSizing.ts:23` · `frontend/lib/sparSizingHelpers.ts:90`

**Source.** 🟡 PARTIAL

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §10.4.1, Eq. (10.4) — n_ult = 1.5 · n_max; Kirch, "Hauptholm", https://www.flugmodellbau-kirch.de/Hauptholm.htm — procedure step 1: M = P × l with P the G-scaled load
>
> — via `aircraft-design-scholz + direct verification of the kirch source`

**The source states it as.**

```
Sadraey Eq. (10.4): n_ult = 1.5 · n_max, verbatim: "For the purpose of structural safety considerations, the ultimate load factor (n_ult) is usually 1.5 times the maximum load factor (i.e., a safety factor of 1.5)". Kirch: M = P × l, then W_req = M/σ.
```

**⚠️ Divergence from the source.** The two-factor chain M_design = \|M\| · g_limit · j is a COMPOSITION the code makes; no source read writes it as one expression. Sadraey's n_ult = 1.5·n_max is real, but in Sadraey it feeds the weight regression Eq. (10.3) — Sadraey never multiplies an aerodynamic bending-moment distribution by it. Kirch applies the G-load to P and never names a separate j. So the FORM is assembled from two sources that do not use it together. The project's own settled record (BR-W16/BR-W17, gh-1079) documents the consequence: g_limit·j = 3·1.5 with a further k≈2.5 makes the effective factor 3.75, so g_limit=3 means the wing breaks at 11.3 g — and that "neither Sadraey nor Scholz contains a V-n diagram, manoeuvre envelope, gust envelope or §341 at all".

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey's 1.5 is explicitly attributed by Sadraey to "civil and military airworthiness regulations (e.g., FAR 23 for GA, FAR 25 for transport aircraft)". Per the project record (BR-W17) that 1.5 sits on top of A/B-basis statistical material allowables which nobody at 0.5-15 kg can produce. ADR 0023 finding: the factor is transport/GA-certification-derived and its statistical precondition does not hold at RC/UAV scale.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Second, independent producer of the identical formula at cad_designer/airplane/geometry/spar_solver.py:764 (build_stations_from_geometry). The two paths can be given different g_limit and j and will disagree for the same aircraft.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `M_design(y) = \|M(y)\| · g_limit · j`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
