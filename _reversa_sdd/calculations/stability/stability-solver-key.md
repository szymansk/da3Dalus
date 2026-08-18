---
name: stability-solver-key
symbol: solver
kind: quantity
unit: – (string)
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Stability result solver key

**Definition.** Discriminator column used to upsert one stability row per aeroplane+solver.

**Formula — as the code writes it.**

```
persist_stability_result(db, aeroplane_pk, str(analysis_tool), summary, geometry_hash)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:357` — `get_stability_summary`

**Consumed by.**

- outside it: `app/services/stability_service.py:160 filter_by(solver=solver)`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `none — not a design quantity`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Persistence discriminator, not an engineering quantity. No source applies.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** `str(analysis_tool)` on a str-Enum stores 'AnalysisToolUrlType.AEROBUILDUP', not 'aerobuildup' — an implementation detail (the Python class name) leaks into a persisted key (ADR 0019).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
