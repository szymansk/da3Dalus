---
name: aero-spanwise--safety-factor-j
symbol: j
kind: parameter
unit: -
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
---

# Safety factor j

**Definition.** Multiplier applied with g_limit to form the design bending moment.

**Value.** `1.5`

**Formula — as the code writes it.**

```
safety_factor_j: Annotated[float, Query(gt=0, description="Safety factor j (default 1.5)")] = 1.5
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/api/v2/endpoints/aeroanalysis.py:609` — `get_airplane_spanwise_loads_with_sizing`

**Consumed by.**

- in this graph: [[design-bending-moment|Design bending moment]] · [[station-design-moment|Station design moment (plan path)]]
- outside it: `compute_spar_sizing via spar_params`

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §10.4.1 Eq. 10.4
>
> — via `aircraft-design-scholz, rc-aircraft-designer`

**The source states it as.**

```
n_ult = 1.5 · n_max   (10.4) — 'the factor 1.5 is the standard structural safety factor for aircraft … a long-established convention in civil and military airworthiness regulations (e.g. FAR 23 for GA, FAR 25 for transport aircraft)'
```

**⚠️ Divergence from the source.** The 1.5 itself is exactly sourced. What is NOT sourced is the combination: endpoint default j=1.5 × g_limit default 3.0 = 4.5 ultimate, which per Sadraey §10.4.1 is the TRANSPORT n_ult band (4.5–6.0). Applying Sadraey's own RC row (n_max 1.5–2) would give n_ult = 2.25–3.0.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** ADR 0023. Sadraey attributes the 1.5 to FAR 23 / FAR 25 — certification standards for MANNED aircraft. No RC/UAV airworthiness basis for 1.5 was found; RC practice (RC-Network 'Holm', Lennon Ch. 19/21) sizes spars against measured manoeuvre G, not against a certification factor. The user sees neither 1.5 nor its product with g_limit as a declared ultimate factor.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Endpoint-level default (1.5) combined with g_limit default (3.0) gives an undeclared 4.5× ultimate factor; NO_SOURCE_FOUND for 1.5 at RC/UAV scale.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
