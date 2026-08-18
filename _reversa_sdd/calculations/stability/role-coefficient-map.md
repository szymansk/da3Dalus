---
name: role-coefficient-map
symbol: —
kind: constant
unit: – (mapping)
cluster: stability
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Role → primary coefficient map

**Definition.** Maps each control-surface role to the aerodynamic coefficient it primarily drives.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `{elevator: Cm, stabilator: Cm, aileron: Cl, rudder: Cn, elevon: Cm, flaperon: Cl, ruddervator: Cm, flap: CL}`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/trim_enrichment_service.py:29` — `ROLE_COEFFICIENT_MAP`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Control effectiveness (state-derivative proxy)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/trim_enrichment_service.py:201`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.2 (elevator → C_m), §12.6.2 (rudder → C_n), §12.4 (aileron → C_l), and §12.5.2's statement that the same derivative structure applies across surfaces: "C_nδR (yaw control power) — analog of C_mδE; C_yδR (side force) — analog of C_LδE; C_lδA (roll control power)." Dual-role surfaces: Lennon Ch. 23 (elevon = pitch + roll), Sadraey §6.7 (ruddervator = pitch + yaw).
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
elevator/stabilator → C_m ; aileron → C_l ; rudder → C_n ; flap → C_L
```

**⚠️ Divergence from the source.** The single-axis mappings match the sources. The dual-role collapses do not: Sadraey §12.5.2 explicitly gives each surface a family of derivatives (e.g. the rudder has both C_nδR AND C_yδR), and Lennon Ch. 23 defines the elevon by having two. Mapping ruddervator → C_m alone loses the yaw authority the V-tail exists to provide, and flaperon → C_l alone loses the lift increment.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Collapses genuinely dual-axis surfaces to one coefficient, so a ruddervator's yaw authority and a flaperon's lift authority are never reported.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"elevon": "Cm",  # dual-role: pitch is primary, roll via differential
"flaperon": "Cl",  # dual-role: roll is primary, flap (lift) via symmetric
"ruddervator": "Cm",  # V-tail: pitch is primary, yaw via differential`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
