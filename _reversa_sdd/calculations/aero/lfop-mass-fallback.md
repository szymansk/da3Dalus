---
name: lfop-mass-fallback
symbol: mass_kg
kind: constant
unit: kg
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Aircraft mass fallback (level-flight solve)

**Definition.** Mass used when the plane schema carries no total_mass_kg.

**Value.** `1.5`

**Formula — as the code writes it.**

```
mass_kg: float = getattr(plane_schema, "total_mass_kg", None) or 1.5
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:485` — `_resolve_level_flight_op`

**Consumed by.**

- in this graph: [[lfop-cl-target|Level-flight target lift coefficient]]

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 1.5 kg sits inside the 0.5-15 kg target class but no source prescribes a default mass. The `or` idiom additionally converts a legitimate total_mass_kg = 0.0 into 1.5 kg.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback: a missing mass silently becomes 1.5 kg, and `or` also swallows a legitimate 0.0 (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:485`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
