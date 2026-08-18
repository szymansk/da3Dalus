---
name: aircraft-class-tail-targets
symbol: —
kind: constant
unit: – (dimensionless)
cluster: stability
user_visible: true
source_status: PARTIAL
---

# Tail-volume target ranges by aircraft class

**Definition.** Per-class target bands for V_H and V_V with their literature citations; drives classification and the recommended tail areas.

**Value.** `rc_trainer (0.55,0.70)/(0.040,0.050); rc_aerobatic (0.35,0.55)/(0.025,0.040); rc_combust (0.45,0.65)/(0.030,0.045); rc_pylon_3d (0.30,0.45)/(0.025,0.035); uav_survey (0.50,0.70)/(0.035,0.060); glider (0.40,0.55)/(0.020,0.030); boxwing (0.55,0.70)/(0.035,0.050)`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/tail_sizing_service.py:39` — `AIRCRAFT_CLASS_TARGETS`

**Consumed by.**

- in this graph: [[s-h-recommended-mm2|Recommended horizontal tail area]] · [[s-v-recommended-mm2|Recommended vertical tail area]] · [[tail-volume-classification|Tail volume classification]]
- outside it: `app/services/tail_sizing_service.py:85,237,239,240,258,262` · `app/api/v2/endpoints/aeroplane/tail_sizing.py:92-97` · `frontend/components/workbench/TailVolumeCard.tsx` · `frontend/lib/metricsAdapters.ts:552-630`

**Source.** 🟡 PARTIAL

> Verifiable per-class RC bands: rcplanedesigner.com, "Tail — Horizontal Tail Placement and Sizing" § Practical Limits and Mission-Consistent Ranges — V_h Trainer 0.55/0.65/0.75, Sport 0.45/0.55/0.65, Acrobatic 0.40/0.50/0.60. Lennon, "Basics of R/C Model Aircraft Design" Ch. 7 gives a single rule (AR 6, TMA 2.5×MAC, tail area 20 % of wing area ⇒ V_H ≈ 0.50), not per-class bands. Sadraey Tables 6.4/6.5 (§6.7.1) give per-type V_H/V_V: glider 0.6/0.03, home-built 0.5/0.04, GA single prop 0.7/0.04. The code's citations 'Roskam Vol II Table 8.13' and 'Thomas, Fundamentals of Sailplane Design Ch. 7' could not be verified in any consulted vault.
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
V_H = S_H·l_H/(S_w·c̄), V_V = S_V·l_V/(S_w·b) — Sadraey §6.7.1; per-class values as tabulated above
```

**⚠️ Divergence from the source.** Three citation defects. (1) 'Lennon Ch.5' is the wrong chapter — Lennon Ch. 5 is 'Wing Design'; horizontal tail area, tail moment arm and tail volume are Ch. 7. (2) Lennon gives no per-class V_H table at all, so rc_trainer, rc_aerobatic and rc_pylon_3d cannot come from him; his single rule implies V_H ≈ 0.50 for all. (3) Value drift against the verifiable RC source: rc_aerobatic (0.35–0.55) sits below rcplanedesigner's Acrobatic band (0.40–0.60), and rc_pylon_3d (0.30–0.45) is below every RC band found. Sadraey's glider V_H = 0.6 / V_V = 0.03 also sits above the code's glider band (0.40–0.55 / 0.020–0.030). No V_V per-class RC source was found anywhere — the vertical-tail numbers are unattributed for all seven classes.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** rc_combust, uav_survey and boxwing all cite 'Roskam Vol II Table 8.13', transport/GA-category literature, applied unmodified at 0.5–15 kg with no scale validation (ADR 0023). boxwing carries an explicit in-code admission it is not boxwing data ('use generic GA-trainer range').

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** rc_combust, uav_survey and boxwing cite 'Roskam Vol II Table 8.13' — a transport/GA table applied at 0.5–15 kg with no scale validation (ADR 0023). boxwing carries an explicit admission it is not boxwing data: '# boxwing has different empennage philosophy; use generic GA-trainer range'.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Roskam Vol II §8.2 / Table 8.13
Raymer 6e §6.4 Eq. 6.27/6.28
Lennon "R/C Model Aircraft Design" Ch. 5
Thomas "Fundamentals of Sailplane Design" Ch. 7`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
