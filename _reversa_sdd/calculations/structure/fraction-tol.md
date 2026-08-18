---
name: fraction-tol
kind: constant
unit: dimensionless (fraction of segment length)
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Split-position boundary tolerance

**Definition.** Relative tolerance keeping a computed segment-split position strictly inside the host segment, so the split helper accepts it.

**Value.** `1e-6`

**Formula — as the code writes it.**

```
_FRACTION_TOL = 1e-6
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_insert_service.py:54` — `_FRACTION_TOL`

**Consumed by.**

- in this graph: [[split-local-length|Segment-local split position]]
- outside it: `app/services/spar_insert_service.py:310`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (float boundary tolerance. Independent of provenance: a joint falling outside the host segment is silently DROPPED from split_lengths at app/services/spar_insert_service.py:310, so a telescoping spar can be persisted with fewer sub-segments than it has pieces, with no warning — ADR 0020)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Undeclared truncation (ADR 0020): a joint that falls outside the host segment is silently DROPPED from split_lengths at line 310, so a telescoping spar can be persisted with fewer sub-segments than it has pieces, with no warning. The defensive branch at line 396 catches only the all-joints-dropped case.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Keep strictly inside the host segment so the split helper accepts it.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
