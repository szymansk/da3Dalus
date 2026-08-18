---
name: tos-cd-clean-avg
symbol: cd_clean_avg
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Area-weighted mean clean section drag

**Definition.** Wing-average clean profile drag coefficient over sections with finite cd and positive area.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cd_clean_avg = sum(cd * a for cd, a in valid_clean) / total_valid_area if total_valid_area > 0 else float("nan")
```

**Inputs.**

- [[tos-cd-clean|Natural-transition section drag]]
- [[bwsd-section-area-normalised|Normalised section area]]

**Produced by.** `app/services/turbulator_optimizer_service.py:623` — `run_turbulator_optimizer`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Tripped total drag coefficient` · `Clean lift-to-drag ratio`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §5.1 (C_D = c_d + C_D,i, c_d from airfoil data) and §5.3 (spanwise strip integral, stated for lift)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
CD_profile = (1/S) integral c_d(y) c(y) dy — the drag analogue of the cited lift integral
```

**⚠️ Divergence from the source.** Same status as tos-delta-cd0: the construction is standard strip theory and the lift form is cited verbatim, but the drag form is an extension. Implementation note confirmed: the guard `if valid_clean and s_ref > 0` gates on s_ref, which never appears in the expression — a dead condition that would suppress a valid average if s_ref were ever non-positive.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The guard `if valid_clean and s_ref > 0` (line 621) gates on s_ref, but s_ref does not appear in the formula — a dead condition.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:616-629`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
