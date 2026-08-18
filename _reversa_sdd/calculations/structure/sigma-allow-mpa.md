---
name: sigma-allow-mpa
symbol: σ_allow
kind: parameter
unit: MPa (N/mm²)
cluster: structure
user_visible: true
source_status: PARTIAL
---

# Allowable bending stress (sizing path)

**Definition.** Allowable bending stress used in erf_W. Taken from the request override if set, else from the material component's specs.

**Formula — as the code writes it.**

```
sigma_allow = (
    params.sigma_allow_mpa_override
    if params.sigma_allow_mpa_override is not None
    else float(material_specs["allowable_bending_stress_mpa"])
)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:294` — `compute_spar_sizing`

**Consumed by.**

- in this graph: [[required-section-modulus|Required section modulus]] · [[structure--sigma-allow-positivity-guard|Allowable-stress positivity guard]]
- outside it: `app/services/spar_sizing.py:318` · `app/services/spar_sizing.py:374` · `frontend/lib/sparSizingHelpers.ts:117`

**Source.** 🟡 PARTIAL

> Kirch, "Hauptholm", Flugmodellbau Kirch, https://www.flugmodellbau-kirch.de/Hauptholm.htm — tabulated allowable stresses: pine (Kiefernholz) grade A per Fliegwerkstoff-Leistungsblatt 4001, compression 400 kg/cm², tension 700 kg/cm²; steel 52.1, 3600 kg/cm²
>
> — via `direct verification of the kirch source + rc-aircraft-designer (RC-Network CFK and Kohlefaser pages are qualitative only — "very high strength and stiffness", "very low density" — and give NO numeric allowable)`

**The source states it as.**

```
σ_allowable enters as the divisor in W_req = M / σ_allowable.
```

**⚠️ Divergence from the source.** The concept and its role are sourced. The VALUES are not: the code reads σ from a Component-Library material record and cites nothing. The one RC source that tabulates allowables gives wood and steel only — it states NO allowable bending stress for carbon/CFK, which is the material this app actually sizes spars in. Note also the source distinguishes compression (400) from tension (700) allowables for the same material; the code carries a single scalar `allowable_bending_stress_mpa`, so the compression-critical case (the upper flange / Druckgurt, which RC-Network "Holm" explicitly calls buckling-vulnerable) cannot be expressed.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second, independent producer of the same user-facing quantity at app/services/spar_plan_service.py:344 (_resolve_sigma_allow) — a different resolution path with its own error handling for the plan endpoint.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
