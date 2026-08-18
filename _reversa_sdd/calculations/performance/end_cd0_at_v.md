---
name: end_cd0_at_v
symbol: C_D0(V)
kind: quantity
unit: -
cluster: perf-envelope
user_visible: false
source_status: SOURCED
---

# Speed-specific C_D0

**Definition.** Reynolds-interpolated zero-lift drag at V_md / V_min_sink when a Re table is cached.

**Formula — as the code writes it.**

```
cd0_at_vmd = lookup_cd0_at_v(v_mps=float(v_md), table=polar_re_table, mac_m=float(mac_m), rho=RHO_SEA_LEVEL)
```

**Inputs.** [[end_rho|Sea-level air density]]

**Produced by.** `app/services/endurance_service.py:347` — `compute_endurance`

**Consumed by.**

- in this graph: [[end_cd_total|Total drag coefficient]]

**Source.** 🟢 SOURCED

> Deters, Ananda & Selig, AIAA 2014-2151 (Reynolds-number effects at small scale) establishes that Re-dependence is first-order in this class; gh-493 Amendment 7 records the design decision.
>
> — via `rc, aero`

**The source states it as.**

```
C_D0(Re(V)) by interpolation over a cached Re table
```

**⚠️ Divergence from the source.** Methodologically the strongest choice in the endurance service — Re-dependent drag is exactly right for 0.5-15 kg. ADR 0020 gap only: falling back to the scalar C_D0 when the table is absent changes the result, emits no warning, and is not reflected in `confidence`.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Falling back to the scalar cd0 when the Re table is absent changes the result but emits no warning and is not reflected in `confidence` (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Re-table for V-specific cd0/e lookup (gh-493 Amendment 7)"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
