---
name: low-re-bucket-tolerance-ref
symbol: —
kind: parameter
unit: dimensionless (ΔCL)
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Bucket tolerance reference width

**Definition.** Drag-bucket width earning full tolerance credit in the Match formula.

**Value.** `0.6`

**Formula — as the code writes it.**

```
low_re_bucket_tolerance_ref: float = 0.6
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/settings.py:104` — `Settings.low_re_bucket_tolerance_ref`

**Consumed by.**

- in this graph: [[alr-tolerance-half|Match tolerance half-width]]
- outside it: `score_target_cl:1034,1049`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source for 0.6, and it contradicts BUCKET_REF = 0.8 at score_re_agnostic:857 (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Contradicts BUCKET_REF = 0.8 in score_re_agnostic:857 — two different 'reference wide bucket' values in the same scoring module.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Drag-bucket width that earns full tolerance credit in Match formula (gh-825).
low_re_bucket_tolerance_ref: float = 0.6`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
