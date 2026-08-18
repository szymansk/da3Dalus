---
name: cd0_at_v
symbol: CD0(V)
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: PARTIAL
---

# Reynolds-dependent CD0

**Definition.** CD0 looked up at a given speed from the polar Re-table, or the scalar fallback.

**Formula — as the code writes it.**

```
if polar_re_table and mac_m and float(mac_m) > 0: from app.services.polar_re_table_service import lookup_cd0_at_v; return lookup_cd0_at_v(v_mps=v, table=polar_re_table, mac_m=float(mac_m), rho=rho); return cd0
```

**Inputs.** [[cd0_resolved|Resolved zero-lift drag]] · [[rho_sl|Sea-level ISA density]]

**Produced by.** `app/services/matching_chart_service.py:817` — `_cd0_at_v`

**Consumed by.**

- outside it: `cd0_cruise:834` · `_climb_tw_at_ws:859`

**Source.** 🟡 PARTIAL

> That C_Do varies with Reynolds number is standard aerodynamics, but neither authority models it at preliminary-sizing level: Sadraey §4.3.3.1 uses a single C_Do from Table 4.12, Scholz likewise. There is no source for a Re-table lookup in a matching chart.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Sadraey Table 4.12: single scalar C_Do per class (no Re dependence)
```

**⚠️ Divergence from the source.** The code is MORE physically faithful than the sources here, which is defensible at RC scale - but it is an extension, not an implementation of a documented method. It is also dead through the API: the endpoint (matching_chart.py:93-121) never supplies polar_re_table or mac_m, so the branch is never taken in production (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** This is the one place the code correctly anticipates low-Re behaviour that the transport-category sources ignore. It should be the part that is kept and wired up, not the part left unreachable.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** The matching-chart endpoint never puts polar_re_table or mac_m into the aircraft dict (matching_chart.py:93-121), so in production this branch is never taken — the Re-table path is dead through the API.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# --- gh-493 Amendment 7: Re-table for V-specific cd0/e --- Look up cd0 at V_md and V_cruise from polar_re_table when available. Backward-compat: if polar_re_table is missing/empty, use scalar cd0/e.`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
