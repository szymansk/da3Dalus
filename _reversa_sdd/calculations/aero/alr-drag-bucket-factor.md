---
name: alr-drag-bucket-factor
symbol: —
kind: constant
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: PARTIAL
---

# Drag-bucket CD threshold factor

**Definition.** CD multiple of CD_min bounding the low-drag bucket.

**Value.** `1.15`

**Formula — as the code writes it.**

```
cd_threshold = 1.15 * cd_min
```

**Inputs.** [[alr-cd-min|Section CD_min]]

**Produced by.** `app/services/airfoil_low_re_service.py:638` — `_extract_metrics`

**Consumed by.**

- in this graph: [[alr-drag-bucket-width|Drag bucket width]]

**Source.** 🟡 PARTIAL

> Abbott & von Doenhoff, Theory of Wing Sections (Dover 1959), Ch. 6 (NACA 6-series) and Appendix IV section data — the 'low-drag range' / drag bucket
>
> — via `aerodynamics-expert`

**⚠️ Divergence from the source.** The drag bucket is a genuinely defined section characteristic, but A&vD bound it by the abrupt drag break at the ends of the low-drag range, not by a fixed multiple of c_d,min. The 1.15 factor is unattributable.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number 1.15 with no cited source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Drag bucket width: ΔCL where CD ≤ 1.15 * CD_min
cd_threshold = 1.15 * cd_min`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
