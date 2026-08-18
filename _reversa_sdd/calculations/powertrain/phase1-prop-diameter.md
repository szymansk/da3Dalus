---
name: phase1-prop-diameter
symbol: _PHASE1_PROP_DIAMETER_M
kind: constant
unit: m
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Phase-1 propeller diameter estimate

**Definition.** A single fixed propeller diameter used for every aircraft when estimating the required motor KV.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.30`

**Formula — as the code writes it.**

```
prop_d = _PHASE1_PROP_DIAMETER_M
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_solution_space_service.py:72` — `_PHASE1_PROP_DIAMETER_M`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Target propeller RPM`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:157`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**The source states it as.**

```
Sadraey (2013) §8.7 Eq. 8.8/8.13 gives the actual sizing relation: D_P = K_np sqrt(2 P eta_P AR_P / (rho V_av^2 C_LP V_C)), with AR_P = 7-15, C_LP = 0.2-0.4, K_np = 1.00 for 2 blades down to 0.72 for 6+.
```

**⚠️ Divergence from the source.** A single fixed 0.30 m (11.8 in) diameter for every aircraft in the 0.5-15 kg range has no source, and a sizing equation for exactly this quantity exists in the lead authority (Sadraey Eq. 8.8/8.13) using inputs the service already has (P, eta_P, rho, V_C). Because J = V/(nD), holding D fixed makes the downstream RPM and KV estimates wrong by roughly the ratio of true to assumed diameter.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** 0.30 m is 11.8 in — a single hardcoded diameter applied across the whole 0.5-15 kg RC/UAV range. Because J = V/(nD), holding D fixed scales the KV estimate inversely with the true diameter, so kv_approx is wrong by roughly the ratio of true to assumed diameter for every aircraft that is not an ~12 in prop. The 'Phase 2 (#615)' promise points at a ticket whose deliverable (powertrain_performance.py) is already merged but is not wired into this service.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Phase-1 prop diameter estimate (see module docstring). Module docstring: "and   prop_d_m   = 0.3  [m]  (fixed Phase-1 estimate — see note below)" / "Note on KV: Phase 1 uses a fixed prop diameter estimate (0.30 m) as a first approximation.  This is documented as approximate in the schema. Phase 2 (#615) will replace this with APC performance data."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
