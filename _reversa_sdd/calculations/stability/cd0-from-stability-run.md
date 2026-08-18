---
name: cd0-from-stability-run
symbol: CD0
kind: quantity
unit: – (dimensionless)
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/aerobuildup
---

# cd0 auto-populated from stability run

**Definition.** Intended to update the cd0 design assumption from the AeroBuildup drag coefficient after a stability run.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cd0_val = _scalar(getattr(result, "CD", None))
if cd0_val is None:
    cd0_val = _scalar(getattr(getattr(result, "aero", None), "CD", None))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:262` — `_auto_populate_cd0`

**Consumed by.**

- outside it: `NO PRODUCTION CONSUMER — the only call site (app/services/stability_service.py:359-360) is behind a guard that can never be true`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source supports equating total CD from a single operating point with the zero-lift/parasite drag coefficient CD0. Scholz 05_PreliminarySizing and Sadraey Ch. 4 both build CD0 from a component drag buildup and separate it from the induced term via CD = CD0 + CL²/(π·A·e). Taking result.CD at one alpha (app/services/stability_service.py:262) is that decomposition skipped. The docstring says 'parasitic drag'; the code reads total CD.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** UNREACHABLE (verified): `str(analysis_tool).lower()` yields 'analysistoolurltype.aerobuildup', never 'aerobuildup' (app/schemas/AeroplaneRequest.py:49 is a str-Enum, not StrEnum; confirmed by running it on the project's Python 3.11.5). If it ever ran it would write the TOTAL CD as cd0, contradicting the gh-924 parasite-only definition in assumption_compute_service._parasite_cd0:1098 — a second, wrong producer (ADR 0022). Docstring says 'parasitic drag'; the code reads total CD — name contradicts definition.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"""Update cd0 calculated_value from AeroBuildup parasitic drag."""`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
