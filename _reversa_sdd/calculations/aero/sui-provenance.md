---
name: sui-provenance
symbol: —
kind: quantity
unit: enum
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# target_cl_provenance

**Definition.** Whether the target CLs rest on calculated mass and auto cruise speed, estimates, or a mix.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if mass_is_calculated and v_cruise_auto:
    return "calculated"
if not mass_is_calculated and not v_cruise_auto:
    return "estimated"
return "mixed"
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/suitability_service.py:170` — `_resolve_provenance`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `SuitabilityQuery.target_cl_provenance:694`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Data-lineage label, not an engineering quantity. Doc and code disagree on the accepted set: docstring lists ('CALCULATED','COMPUTED'), code also accepts 'AUTO'.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Docstring at lines 145-149 lists only ('CALCULATED','COMPUTED') and "mass row CALCULATED/auto"; the code additionally accepts 'AUTO' — doc and code disagree on the accepted set.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `mass_is_calculated = src in ("CALCULATED", "COMPUTED", "AUTO")`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
