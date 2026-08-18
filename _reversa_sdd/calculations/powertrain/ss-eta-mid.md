---
name: ss-eta-mid
symbol: eta_mid
kind: quantity
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Mid-band propeller efficiency

**Definition.** Midpoint of the propeller-efficiency band; the value behind every scalar (non-band) field in the response.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
eta_mid = (assumptions.eta_prop_lo + assumptions.eta_prop_hi) / 2.0
```

**Inputs.**

- [[ss-eta-prop-lo|Propeller efficiency band lower bound]]  — *⊣ limit*
- [[ss-eta-prop-hi|Propeller efficiency band upper bound]]  — *⊣ limit*

**Produced by.** `app/services/powertrain_solution_space_service.py:357` — `compute_solution_space`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Required motor continuous shaft power` · `Required motor peak shaft power` · `Electrical cruise power (mid band)` · `Electrical peak power (mid band)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:360` · `app/services/powertrain_solution_space_service.py:361` · `app/services/powertrain_solution_space_service.py:421` · `app/services/powertrain_solution_space_service.py:422`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Taking the arithmetic midpoint of an assumed efficiency band is a presentation choice, not a method any source states. The band endpoints themselves are separately assessed (ss-eta-prop-lo is supported, ss-eta-prop-hi is not).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The frontend never uses eta_mid — it sizes the motor with eta_prop_lo instead (PowertrainTab.tsx:110), so the mid-band motor power the backend computes is never the one the user sees (notes F5).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `schema docstring: "Scalar fields are computed at the mid-point of the η_prop band (eta_prop_lo + eta_prop_hi) / 2."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
