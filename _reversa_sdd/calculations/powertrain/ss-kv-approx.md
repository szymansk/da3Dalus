---
name: ss-kv-approx
symbol: kv_approx
kind: quantity
unit: rpm/V
cluster: powertrain
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Approximate required motor KV

**Definition.** Motor KV the designer should shop for: target RPM divided by nominal pack voltage and the under-load RPM factor.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
kv_approx = rpm_target / (v_nom * load_rpm_factor) if v_nom > 0 else 0.0
```

**Inputs.**

- [[ss-rpm-target|Target propeller RPM]]
- [[ss-v-nom|Pack nominal voltage (solution space)]]
- [[ss-load-rpm-factor|Under-load RPM factor]]

**Produced by.** `app/services/powertrain_solution_space_service.py:159` — `_per_cell`

**Consumed by.**

- outside it: `app/services/powertrain_solution_space_service.py:455` · `app/services/powertrain_solution_space_service.py:484` · `frontend/components/workbench/PowertrainTab.tsx:590` · `frontend/components/workbench/PowertrainTab.tsx:464`

**Source.** 🟡 PARTIAL

> Roxxy Motoren-Fibel, Ch. 1, pp. 15-16: 'No-load RPM = KV x Battery Voltage (volts)', rearranged for KV. Drela, 'DC Motor / Propeller Matching' §1.1.3: K_V = Omega/v_m with v_m = v - i_o R.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
KV = RPM_no-load / V_battery
```

**⚠️ Divergence from the source.** The source relation is exact for the NO-LOAD case. The code introduces load_rpm_factor = 0.85 into the denominator to convert to a loaded case; that factor is unattributed (see ss-load-rpm-factor). Drela's model gives the physically grounded alternative — the loaded speed follows from V = iR + Omega/Kv with i set by the propeller torque demand — and requires no empirical factor. The estimate also inherits the unattributed fixed 0.30 m diameter and the zero-slip assumption upstream.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Inherits the fixed-diameter error of phase1-prop-diameter and is rendered to the user as a bare number in the table (PowertrainTab.tsx:590) and shopping line (PowertrainTab.tsx:464) with no approximation marker in the UI text — the 'Phase 1 estimate' caveat lives only in the OpenAPI field description. The code comment itself admits the 0.0 fallback branch is unreachable (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `schema field description: "Approximate motor KV [RPM/V]. KV ≈ RPM_target / (V_nom × load_rpm_factor). Phase 1 estimate — depends on prop_pd and V_top."  Code comment: "v_nom = S · 3.7 is always > 0 for any valid cell count S ≥ 1, so kv_approx is always a float; the defensive fallback (0.0) only guards a degenerate zero-voltage case that real inputs never reach."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
