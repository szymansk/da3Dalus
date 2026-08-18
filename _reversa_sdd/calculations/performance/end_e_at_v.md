---
name: end_e_at_v
symbol: e(V)
kind: quantity
unit: -
cluster: perf-envelope
user_visible: false
source_status: SOURCED
---

# Speed-specific Oswald factor

**Definition.** Reynolds-interpolated Oswald efficiency at V_md / V_min_sink.

**Formula — as the code writes it.**

```
e_at_vmd = lookup_e_oswald_at_v(v_mps=float(v_md), table=polar_re_table)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:359` — `compute_endurance`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟢 SOURCED

> Same basis as end_cd0_at_v (gh-493 Amendment 7).
>
> — via `aero`

**The source states it as.**

```
e(Re(V)) by interpolation over the same table
```

**⚠️ Divergence from the source.** Same undeclared-fallback gap as end_cd0_at_v.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
