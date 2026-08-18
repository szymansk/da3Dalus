---
name: sm-elevator-limit
symbol: SM_max
kind: constant
unit: fraction of MAC
cluster: mass
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/mass
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Static-margin elevator-authority limit

**Definition.** Static margin above which elevator authority at the landing stall is deemed insufficient — ERROR; also used directly as the forward-CG stability stub (x_NP − 0.30·MAC).

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.30`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/loading_scenario_service.py:53` — `_SM_ELEVATOR_LIMIT`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Forward CG stability limit (0.30·MAC stub)` · `Static-margin classification`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/loading_scenario_service.py:79 (classify_sm)` · `app/services/loading_scenario_service.py:116 (cg_stability_fwd_m stub)`

**Source.** 🟡 PARTIAL

> The MECHANISM is sourced: Sadraey, M.H., Wiley 2013, §11.6.3 ("Longitudinal Controllability Requirements for Weight Distribution") — "The forward cg limit is therefore set by elevator effectiveness during rotation", with the trim/control-power derivatives at Eqs. (11.23)–(11.25); elevator sizing case at Sadraey §12.5.3 (take-off rotation, V_R = 1.1–1.3·V_S). The VALUE 0.30 is NO_SOURCE_FOUND — no consulted source states an SM ceiling of 0.30.
>
> — via `aircraft-design-scholz + aerodynamics-expert`

**The source states it as.**

```
δ_E = − ( C_Lα·C_mo + C_mα·C_L ) / ( C_Lα·C_mδE − C_LδE·C_mα )   (Sadraey Eq. 11.23); C_LδE = (S_h/S)·(dC_L_t/dδ_E) (11.24); C_mδE = −V̄_H·(dC_L_t/dδ_E) (11.25)
```

**⚠️ Divergence from the source.** Two hard misattributions plus a wrong flight condition. (1) The code cites "Anderson §7.7" (loading_scenario_service.py:12-13, :113-114). Verified against Anderson, J.D., "Fundamentals of Aerodynamics" 6e: Chapter 7 is "Compressible Flow: Some Preliminary Aspects"; §7.5 is "Definition of Total (Stagnation) Conditions" and §7.7 is the chapter "Summary". The strings 'static margin', 'neutral point' and 'longitudinal static stability' do not occur anywhere in that book. The citation is void. (2) The code attributes the forward limit to "elevator authority at landing stall". Sadraey §11.6.3 attributes the forward cg limit to TAKE-OFF ROTATION, not landing: the elevator must rotate the aircraft about the main gear at 80% of take-off speed, 6–8 deg/s² initial angular acceleration, rotation complete in 3–4 s. Sadraey §12.5.4 does treat the low-speed case, but it sizes the maximum POSITIVE (down) deflection at the most AFT cg — the opposite end of the envelope from the one the code is bounding. (3) Sadraey's forward limit is not a fixed SM number at all; it falls out of Eq. (11.23) with the actual elevator geometry, which is why the code's own elevator_authority_service.py exists (gh-500) and why sm_sizing_service.py:39 calls the duplicate literal "the hardcoded 0.30 orphan".

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey §11.6.3's rotation criteria (80% V_TO, 6–8 deg/s², 3–4 s, tricycle gear, tip-back on the main gear) are transport/GA-category and assume a runway take-off with a nosewheel. Many 0.5–15 kg RC/UAV aircraft are hand-launched, bungee-launched or belly-landed, so the sizing case that produces the forward limit may not exist for them. And 0.30 is 2× to 10× every RC recommendation: rcplanedesigner.com "Airplane Balance — Finding the First-Flight CG" caps Trainer at 15% MAC, and Lennon Ch. 6 calls 10% "healthy". No RC/UAV validation of 0.30 exists (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Three independent definitions of the same 0.30 constant: here, app/services/sm_sizing_service.py:78 (_SM_FORWARD_CLIP_LIMIT = 0.30) and app/services/elevator_authority_service.py:92 (_STUB_FORWARD_SM = 0.30). elevator_authority_service.py:39 itself calls the sm_sizing copy "the hardcoded 0.30 orphan".

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"sm > 0.30              ERROR   (elevator authority at landing stall insufficient)" — app/services/loading_scenario_service.py:22; "# Stub forward limit: SM = 0.30 is the conservative upper bound before elevator authority at landing stall becomes critical (Anderson §7.7)." — lines 113-114`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
