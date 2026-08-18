---
name: end_mass
symbol: m
kind: parameter
unit: kg
cluster: perf-envelope
user_visible: true
source_status: SOURCED
---

# Total aircraft mass (endurance)

**Definition.** Effective mass design assumption; hard failure if absent.

**Formula — as the code writes it.**

```
_mass_raw = da.get("mass"); if _mass_raw is None: raise ValueError(...)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:264` — `compute_endurance`

**Consumed by.**

- in this graph: [[end_cl|Level-flight lift coefficient]]

**Source.** 🟢 SOURCED

> Effective mass design assumption; hard failure when absent. gh-490 explicitly removed the 2.0 kg silent default.
>
> — via `rc`

**⚠️ Divergence from the source.** Model case for the rest of the cluster: a missing critical input raises rather than inventing a value. fe_mass (1.5 kg), fe_v_max_default (28.0) and end_cd0_inline_default (0.03) should follow this precedent.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"must be explicitly provided; 2.0 kg silent default removed (gh-490)"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
