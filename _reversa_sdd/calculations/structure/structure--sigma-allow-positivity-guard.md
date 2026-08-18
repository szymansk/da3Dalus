---
name: structure--sigma-allow-positivity-guard
kind: constant
unit: MPa
cluster: structure
user_visible: true
source_status: PARTIAL
---

# Allowable-stress positivity guard

**Definition.** Guard threshold: σ_allow ≤ 0 raises ValueError rather than dividing by zero. Added because the material schema permits allowable_bending_stress_mpa = 0.

**Value.** `0`

**Formula — as the code writes it.**

```
if sigma_allow_mpa <= 0:
```

**Inputs.** [[sigma-allow-mpa|Allowable bending stress (sizing path)]]

**Produced by.** `app/services/spar_sizing.py:86` — `required_section_modulus`

**Consumed by.**

- outside it: `app/services/analysis_service.py:2137` · `app/services/spar_plan_service.py:335`

**Source.** 🟡 PARTIAL

> Kirch, "Hauptholm", https://www.flugmodellbau-kirch.de/Hauptholm.htm — the procedure divides by σ_allowable, and the page tabulates only strictly positive allowables (pine grade A per Fliegwerkstoff-Leistungsblatt 4001: 400 kg/cm² compression, 700 kg/cm² tension; steel 52.1: 3600 kg/cm²)
>
> — via `direct verification of the kirch source`

**The source states it as.**

```
W_req = M / σ_allowable — the relation is undefined for σ_allowable ≤ 0.
```

**⚠️ Divergence from the source.** The guard is a defensive programming decision (gh-1008 review), not an engineering constant. The source implies σ > 0 but never states a guard; no literature prescribes raising ValueError. Attributable as "the relation requires σ > 0", not as a cited threshold.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `Raises ValueError on σ_allow ≤ 0 (callers resolve σ from a material whose schema permits 0; guard here so we never divide by zero — gh-1008 review).`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
