---
name: stall-alpha-fallback
symbol: α_stall
kind: constant
unit: deg
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# Stall alpha fallback

**Definition.** Angle of attack assumed for the near-stall operating point when the stall_alpha assumption row is absent.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `12.0`

**Formula — as the code writes it.**

```
stall_alpha_deg = float(stall_alpha_raw) if stall_alpha_raw is not None else 12.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/elevator_authority_service.py:618` — `_compute_forward_cg_limit_asb`

**Consumed by.**

- in this graph: `Landing stall alpha`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/elevator_authority_service.py:623,632,999,1034`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 12° is a plausible stall angle for a moderately cambered low-Re section but is unattributed, and the assumption row it reads ('stall_alpha') does not exist anywhere in this app. Sadraey §12.5.4 Eq. 12.91 derives the tail angle at the critical condition from α_TO(1 − dε/dα) + i_h − ε_o rather than assuming an aircraft stall alpha; the app itself already publishes a computed ctx['alpha_stall_deg'] (assumption_compute_service.py:747) that this service never reads.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No 'stall_alpha' assumption exists anywhere (same as v_cruise). assumption_compute_service DOES publish ctx['alpha_stall_deg'] (:747) but this service never reads it — the real value is available and ignored.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Use stall alpha from assumptions or moderate angle.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
