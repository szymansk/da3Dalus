---
name: prt-top-band-fallback
symbol: —
kind: quantity
unit: boolean
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# top_band_fallback flag (in build_re_table)

**Definition.** Local flag marking the highest-Re band as unfitted.

**Formula — as the code writes it.**

```
top_band_fallback = True  ... return table, False
```

**Inputs.** [[prt-min-samples-per-band|Minimum samples per V-band / per OLS window]]

**Produced by.** `app/services/polar_re_table_service.py:476` — `build_re_table`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Dead computation — set on three paths, then line 513 returns the literal False. The caller re-derives the same flag at assumption_compute_service.py:428-430. Nothing to source (ADR 0021/0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Dead computation: `top_band_fallback` is set on three paths but line 513 returns the literal `False`; the caller re-derives the same flag independently at assumption_compute_service.py:428-430 — two producers, one of them unreachable (ADR 0021/0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `top_band_fallback = False
...
            if v_center == v_anchors[-1]:
                top_band_fallback = True
...
    return table, False`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
