---
name: resolved-cd0
symbol: cd0
kind: quantity
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Resolved zero-lift drag coefficient

**Definition.** cd0 resolved by a three-tier priority: explicit request field, then the aeroplane's assumption_computation_context, then the RC-typical default with a warning.

**Formula — as the code writes it.**

```
cd0 = _pick(request.cd0, "cd0", _DEFAULT_CD0, "Zero-lift drag coefficient (cd0)", "cd0")
```

**Inputs.** [[default-cd0-sizing|Default zero-lift drag coefficient (sizing)]]

**Produced by.** `app/services/powertrain_sizing_service.py:165` — `_resolve_aero_params`

**Consumed by.**

- in this graph: [[combo-cruise-power|Estimated cruise power]] · [[combo-required-power|Power required for a motor+battery combo]]
- outside it: `app/services/powertrain_sizing_service.py:245` · `app/services/powertrain_sizing_service.py:312`

**Source.** 🟢 SOURCED

> Sadraey (2013), Table 4.12 (cited in §4.6): typical turboprop transport C_Do ~ 0.025-0.035; Sadraey Eq. 4.62 gives the back-calculation of C_Do from flight data as the preferred alternative to table lookup.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_D = C_Do + K C_L^2  (Sadraey §4.6); C_Do from Table 4.12 or back-calculated via Eq. 4.62
```

**⚠️ Divergence from the source.** The three-tier resolution (request -> computation context -> default) matches Sadraey's own preference order, since Eq. 4.62 explicitly favours back-calculating C_Do from data over adopting a table value.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The third tier resolves to 0.03, whose only attribution is Sadraey's transport-category Table 4.12 band (0.025-0.035). No RC/UAV-scale validation exists for it — see default-cd0-sizing (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `docstring: "Priority order per parameter: 1. Explicit request field (user-supplied → most trusted) 2. aeroplane.assumption_computation_context (computed from analysis, gh-924) 3. RC-typical default → emits a warning note"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
