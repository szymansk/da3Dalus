---
name: saoa-velocity-fallback
symbol: velocity
kind: constant
unit: m/s
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Velocity fallback for Reynolds

**Definition.** Velocity used when the operating point's velocity cannot be read.

**Value.** `15.0`

**Formula — as the code writes it.**

```
velocity = 15.0  # safe default
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:145` — `_compute_alpha_l0_per_section`

**Consumed by.**

- in this graph: [[saoa-re-local|Local chord Reynolds number (alpha_L0 lookup)]]

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 15 m/s is inside the RC/UAV band but no consulted source prescribes a default airspeed. It is also reached through a bare except, so a genuine operating point failure is indistinguishable from a design at 15 m/s.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback: a bare except swallows the failure and substitutes 15 m/s with no DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:143-145`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
