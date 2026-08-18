---
name: mass--sm-unstable-limit
symbol: SM_min
kind: constant
unit: fraction of MAC
cluster: mass
user_visible: true
source_status: SOURCED
---

# Static-margin lower (unstable) limit

**Definition.** Static margin below which the aircraft is classified as unstable (Phugoid divergent) — hard ERROR in the CG-envelope classification.

**Value.** `0.02`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/loading_scenario_service.py:51` — `_SM_UNSTABLE_LIMIT`

**Consumed by.**

- in this graph: [[sm-classification|Static-margin classification]]
- outside it: `app/services/loading_scenario_service.py:73 (classify_sm)`

**Source.** 🟢 SOURCED

> Sadraey, M.H., "Aircraft Design: A Systems Engineering Approach", Wiley 2013, §11.4 ("Longitudinal Center of Gravity Location"), sub-section 'Stability Boundary: The Neutral Point': "A conventional aircraft becomes dynamically longitudinally unstable when the cg lies within roughly 2–3% MAC of the neutral point." Static boundary at SM = 0: Sadraey §11.6.2 Eq. (11.22), x_np − x_cg > 0.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
cg within 2–3% MAC of the neutral point ⇒ dynamically longitudinally unstable (Sadraey §11.4); x_np − x_cg > 0 (Eq. 11.22)
```

**⚠️ Divergence from the source.** Three divergences. (1) SOURCE ATTRIBUTION IS WRONG IN THE CODE: loading_scenario_service.py:48 cites "Scholz §4.2" for this threshold. The Scholz §4.2 material (Box Wing Systematic Study §4.2, 'Longitudinal Stability and Center of Gravity Range Effects') states only "typical stability margin requirement: 5-10% mean aerodynamic chord" and "operational envelope typically 15-25% MAC" — it does not contain 0.02. The real source is Sadraey §11.4. (2) Sadraey gives a BAND (2–3% MAC); the code hard-codes the permissive end (0.02) as a sharp ERROR boundary. (3) The code labels the failure mode "Phugoid divergent" (loading_scenario_service.py:18). Sadraey attributes the cg-driven dynamic longitudinal degradation to C_mq / M_q / M_α (§11.6.2 Eq. 11.19) and names the SHORT-PERIOD mode as "the principal handling-quality-relevant longitudinal mode" — the phugoid attribution is not supported by the source.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey's 2–3% MAC figure is for "a conventional aircraft" in the GA/transport sense; his own class table (§11.6.1) covers GA subsonic, subsonic/supersonic transport and fighters — RC/UAV at 0.5–15 kg is absent. The RC literature contradicts a hard ERROR at SM < 0.02 outright: rcplanedesigner.com, "Airplane Balance — How to Find the Center of Gravity for an RC Airplane", section 'Center of Gravity and Static Margin', tabulates Acrobatic SM = 0% minimum / 1.5% average / 3% maximum of MAC and notes "Acrobatic can fly with 0% (neutral stability) up to ~3%". An RC aerobat deliberately flown at SM = 0.01 is flagged ERROR by this code. Per ADR 0023 the constant needs RC-scale re-validation or an explicit class gate.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Duplicated as an independent literal in app/services/sm_sizing_service.py:53 (_SM_UNSTABLE_LIMIT = 0.02). Two independent definitions of the same threshold for the same user-visible classification.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"# SM classification thresholds (Scholz §4.2)" — app/services/loading_scenario_service.py:48; "sm < 0.02              ERROR   (unstable / Phugoid divergent)" — line 18`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
