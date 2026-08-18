---
name: v-cruise-fallback
symbol: V_cruise
kind: constant
unit: m/s
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Cruise speed fallback

**Definition.** Cruise speed assumed when the v_cruise assumption row is absent.

**Value.** `15.0`

**Formula — as the code writes it.**

```
v_cruise = float(v_cruise_raw) if v_cruise_raw is not None else 15.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/elevator_authority_service.py:590` — `_compute_forward_cg_limit_asb`

**Consumed by.**

- in this graph: [[near-stall-velocity-factor|Near-stall approach speed factor]]
- outside it: `app/services/elevator_authority_service.py:621,682,997,1033`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 15 m/s is a plausible RC cruise speed but is not attributable to any source, and no 'v_cruise' design assumption exists in this app (not in VALID_PARAMETERS or PARAMETER_DEFAULTS, no row in db/test.db), so the fallback is the only value ever used. Sadraey §12.5.4 and Scholz 05_PreliminarySizing both derive the relevant speeds from the flight envelope (V_S, V_APP = 1.3·V_S, V_C) rather than assuming one.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** A design assumption named 'v_cruise' does not exist — it is not in VALID_PARAMETERS or PARAMETER_DEFAULTS, and db/test.db has no such row. The lookup always returns None, so 15.0 is the only value ever used (notes F1).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Load cruise speed for the AeroBuildup runs`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
