---
name: mass--sm-heavy-nose-warn
symbol: SM_warn
kind: constant
unit: fraction of MAC
cluster: mass
user_visible: true
source_status: PARTIAL
---

# Static-margin heavy-nose warning limit

**Definition.** Static margin above which the design is flagged as nose-heavy (trim drag, sluggish pitch) — WARN.

**Value.** `0.20`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/loading_scenario_service.py:52` — `_SM_HEAVY_NOSE_WARN`

**Consumed by.**

- in this graph: [[sm-classification|Static-margin classification]]
- outside it: `app/services/loading_scenario_service.py:77 (classify_sm)`

**Source.** 🟡 PARTIAL

> Consistent with, but not stated by, Sadraey, M.H., Wiley 2013, §11.6.1 recommended CG limits table (GA subsonic: forward cg 15–20% MAC, aft cg 25–30% MAC) combined with §11.4 ("The neutral point … typically lies at 40–50% MAC"), which implies SM ≈ 0.20–0.25 at a GA forward cg. No consulted source states a threshold "SM > 0.20 ⇒ nose-heavy warning".
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**⚠️ Divergence from the source.** The code's inline attribution "SM classification thresholds (Scholz §4.2)" (loading_scenario_service.py:48) is not supported: the Scholz Box Wing Systematic §4.2 material gives 5–10% MAC as the typical stability-margin requirement and 15–25% MAC as the operational cg envelope — it contains no 0.20 SM threshold. Scholz's own Design Sequence §2.2 (Step 10, 'Weight and Balance Analysis') likewise states "static margin — positive static margin required for stability (typically 5–10% of MAC)". Under either Scholz figure, 0.20 is already double the upper end of 'typical', so calling everything up to 0.20 'ok' is a departure from the cited author, not an application of him.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** 0.20 exceeds every RC/UAV recommendation found. rcplanedesigner.com, "Airplane Balance — How to Find the Center of Gravity for an RC Airplane", §'Center of Gravity and Static Margin': Trainer 5%/10%/15% MAC (min/avg/max), Sport 3%/4%/5%, Acrobatic 0%/1.5%/3%. Lennon, A., "Basics of R/C Model Aircraft Design", Air Age 1996, Ch. 6 'CG Location': NP at 35% MAC power-on, CG at 25% MAC ⇒ "the stability margin is a healthy 10 percent"; "the minimum suggested margin is 5 percent". A 0.5–15 kg model at SM = 0.18 is beyond the trainer maximum in both RC sources yet is classified 'ok' by this code. The threshold is transport/GA-derived (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Duplicated as an independent literal in app/services/sm_sizing_service.py:54 (_SM_HEAVY_NOSE_WARN = 0.20).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"0.20 < sm ≤ 0.30       WARN    (heavy nose, trim drag, sluggish pitch)" — app/services/loading_scenario_service.py:21`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
