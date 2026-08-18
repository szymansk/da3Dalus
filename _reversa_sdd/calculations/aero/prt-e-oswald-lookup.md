---
name: prt-e-oswald-lookup
symbol: e(V)
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# e_oswald at query velocity (constant mean)

**Definition.** Oswald efficiency returned as the V-independent mean of all non-fallback table rows.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return float(sum(valid_e) / len(valid_e))
```

**Inputs.**

- [[prt-e-oswald-band|Band Oswald efficiency]]

**Produced by.** `app/services/polar_re_table_service.py:208` — `lookup_e_oswald_at_v`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/speed_polar_service.py:143` · `app/services/matching_chart_service.py:830` · `app/services/assumption_compute_service.py:580,2068` · `app/services/endurance_service.py:359,360`

**Source.** 🟡 PARTIAL

> Anderson 6e §6.7.2 — Oswald factor is a configuration property (AR, planform, parasite-drag lift dependence), containing no Reynolds term
>
> — via `aerodynamics-expert`

**⚠️ Divergence from the source.** Treating e as V-independent is consistent with the source: nothing in Anderson's definition varies with Re. But the function takes v_mps and ignores it, and averaging fitted band values is an aggregation with no source. The docstring's supporting claim ('Drela: span efficiency dominated by planform, not Re') is uncited.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Signature takes v_mps but the docstring says '(ignored — mean is V-independent)': a parameter with no effect on the result.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `valid_e = [
    r["e_oswald"]
    for r in table
    if not r.get("fallback_used", True) and r.get("e_oswald") is not None
]
if valid_e:
    return float(sum(valid_e) / len(valid_e))`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
