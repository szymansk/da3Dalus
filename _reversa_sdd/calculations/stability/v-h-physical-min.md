---
name: v-h-physical-min
symbol: V_H,min
kind: constant
unit: – (dimensionless)
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# V_H physical minimum

**Definition.** Lower bound of physically credible horizontal tail volume coefficients.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.20`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/tail_sizing_service.py:29` — `V_H_PHYSICAL_MIN`

**Consumed by.**

- in this graph: `Tail volume classification`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/tail_sizing_service.py:248,268`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source names 0.20 as a physical floor for V_H. Sadraey Table 6.4 goes as low as 0.1 (fighter with canard) and 0.4 (fighter) — both below or at the code's floor while being real, flying aircraft. At RC scale, rcplanedesigner.com's lowest mission minimum is 0.40 (Acrobatic). The code's own rc_pylon_3d target band starts at 0.30, so a pylon racer at V_H = 0.25 is inside the app's own target philosophy yet flagged 'out_of_physical_range'. The bound is both unsourced and internally inconsistent.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** An unsourced physical bound that is TIGHTER than one of the service's own target ranges: rc_pylon_3d has v_h_range = (0.30, 0.45) and glider (0.40, 0.55), but a pylon racer at V_H = 0.25 — squarely inside published RC practice — is classified 'out_of_physical_range'.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `NO_SOURCE_FOUND — the block is headed only '# Physical validity guards'; the module's Sources list (lines 11-15) is attached to the class-target table, not to these bounds`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
