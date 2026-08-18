---
name: motor-output-kv
symbol: output_kv
kind: quantity
unit: rpm/V
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Output-shaft KV

**Definition.** Motor speed constant referred to the propeller shaft, i.e. raw motor KV divided by the gearbox reduction. The gear-blind raw KV must never be used for prop matching.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return self.kv_rpm_per_volt / (self.gear_ratio or 1.0)
```

**Inputs.**

- [[motor-kv-rpm-per-volt-input|Raw motor KV]]
- [[motor-gear-ratio-input|Gearbox reduction ratio]]

**Produced by.** `app/services/powertrain_performance.py:140` — `MotorSpec.output_kv`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Fixed operating RPM (non-QPROP branch)` · `Motor speed constant in SI`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:131` · `app/services/powertrain_performance.py:643` · `app/services/powertrain_performance.py:783`

**Source.** 🟢 SOURCED

> Sadraey (2013), §8.7, Eq. 8.14: GR = n_P / n_S — the gearbox ratio relating propeller speed n_P to engine shaft speed n_S; worked for the Cessna 172 (GR = 1/2, 4200 rpm shaft -> 2100 rpm prop). Combined with Roxxy Motoren-Fibel, Ch. 1, pp. 15-16: 'No-load RPM = KV x Battery Voltage'.
>
> — via `aircraft-design-scholz / rc-aircraft-designer`

**The source states it as.**

```
n_P = GR x n_S  (Sadraey Eq. 8.14); no-load RPM = KV x V_bat (Roxxy Ch. 1)
```

**⚠️ Divergence from the source.** Sadraey defines GR = n_P/n_S (a fraction < 1 for reduction, e.g. 1/2). The code's gear_ratio is the reciprocal convention — it DIVIDES by gear_ratio, so gear_ratio = 2 means 2:1 reduction. Same physics, inverted convention; a catalog entry populated in Sadraey's convention would multiply rather than divide the KV.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `module docstring: "Gear-aware RPM (UAT note, gh-615 comment #3): output_kv = kv_rpm_per_volt / (gear_ratio or 1)"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
