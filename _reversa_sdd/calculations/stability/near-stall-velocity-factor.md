---
name: near-stall-velocity-factor
symbol: —
kind: constant
unit: – (dimensionless)
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Near-stall approach speed factor

**Definition.** Fraction of cruise speed used as the approach/stall operating velocity for the elevator-authority runs.

**Value.** `0.6`

**Formula — as the code writes it.**

```
velocity=v_cruise * 0.6,  # near-stall approach speed
```

**Inputs.** [[v-cruise-fallback|Cruise speed fallback]]

**Produced by.** `app/services/elevator_authority_service.py:621` — `_compute_forward_cg_limit_asb`

**Consumed by.**

- outside it: `app/services/elevator_authority_service.py:621,682,1033`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source relates the approach/near-stall speed to cruise speed by a factor of 0.6. The certified relation runs the other way and via stall speed: Scholz 05_PreliminarySizing §5.1 — V_S,L = √(2·m_ML·g/(ρ·S_W·C_L,max,L)) and V_APP ≥ 1.3·V_S (CS 25.125). The app already knows V_stall; 0.6·V_cruise stands in for a quantity it can compute. Repeated three times.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic factor with no source, repeated three times. The service computes V_stall nowhere and never reads ctx['v_stall'] — 0.6·V_cruise is a stand-in for a quantity the codebase already knows.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# near-stall approach speed`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
