---
name: cm-baseline
symbol: Cm_0
kind: quantity
unit: – (dimensionless)
cluster: stability
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Baseline pitching moment (zero deflection)

**Definition.** Pitching moment coefficient at the landing-stall alpha with the elevator at zero deflection.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
asb_baseline = asb_airplane.with_control_deflections({elevator_surface_name: 0.0})
...
cm_baseline = _extract_cm(result_baseline)
```

**Inputs.**

- [[alpha-stall-landing|Landing stall alpha]]  — *⊣ limit*

**Produced by.** `app/services/elevator_authority_service.py:692` — `_compute_forward_cg_limit_asb`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Aerodynamic-centre pitching moment` · `Elevator authority (finite difference)` · `Flap-induced pitching moment`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/elevator_authority_service.py:709,731` · `app/services/elevator_authority_service.py:1050 (AVL twin)`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.4 Eq. 12.85 — the zero-deflection pitching moment C_mo + C_mα·α is the baseline against which the elevator contribution C_mδE·δ_E is measured. Two-point evaluation of a control derivative at fixed α is standard practice (Sadraey §12.5.2 defines C_mδE = ∂C_m/∂δ_E).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_m(α, δ_E) = C_mo + C_mα·α + C_mδE·δ_E   (Sadraey Eq. 12.85)
```

**⚠️ Divergence from the source.** Sadraey's baseline and elevator term share one operating point. The code runs a SECOND baseline (cm_baseline_clean, elevator_authority_service.py:644) at the clean stall alpha purely as the ΔCm_flap reference, then sums ΔCm_flap with C_m,ac at line 236 — so the two moment contributions are referenced to baselines at different angles of attack and are not additive in the way Eq. 12.85 requires.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** A second, separate baseline (cm_baseline_clean, line 644) is run at the CLEAN stall alpha purely as the ΔCm_flap reference — so ΔCm_flap and Cm_ac are referenced to baselines at different angles of attack, and the two are then summed at line 236.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
