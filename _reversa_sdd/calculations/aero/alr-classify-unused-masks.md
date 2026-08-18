---
name: alr-classify-unused-masks
symbol: —
kind: quantity
unit: n/a
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# upper_mask / lower_mask

**Definition.** Two boolean arrays allocated in classify_family and never used.

**Formula — as the code writes it.**

```
upper_mask = np.zeros(n, dtype=bool)
lower_mask = np.zeros(n, dtype=bool)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:174` — `classify_family`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Dead code — allocated, never read. No quantity to source (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Dead code — allocated then never read (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `upper_mask = np.zeros(n, dtype=bool)
lower_mask = np.zeros(n, dtype=bool)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
