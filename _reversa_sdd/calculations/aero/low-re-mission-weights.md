---
name: low-re-mission-weights
symbol: —
kind: parameter
unit: mixed
cluster: aero-polars
user_visible: true
source_status: PARTIAL
---

# Mission weighting table

**Definition.** Per-mission preferred families, thickness band and cl_max_weight driving score_mission.

**Value.** `slope_soarer: {thickness_min_pct 8.0, thickness_max_pct 12.0, cl_max_weight 0.45, preferred_families [semi_symmetric, cambered]} (+ trainer/sport/aerobatic/glider/flying_wing entries above line 50)`

**Formula — as the code writes it.**

```
low_re_mission_weights: dict[str, dict[str, Any]] = Field(default_factory=lambda: dict(_DEFAULT_MISSION_WEIGHTS))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/settings.py:116` — `Settings.low_re_mission_weights`

**Consumed by.**

- in this graph: [[alr-family-bonus|Mission family bonus]] · [[alr-thickness-match|Mission thickness match multiplier]]
- outside it: `suitability_service:255` · `score_mission:911`

**Source.** 🟡 PARTIAL

> rcplanedesigner.com, 'Wing — Airfoils': Airfoils Families (flat-bottom→trainer, semi-symmetrical→sport, symmetrical→aerobatic, under-cambered→gliders/slow flyers) and the Relative Thickness table (trainer 12/15/18%, sport 10/11/12%, aerobatic 7/8.5/10%); Lennon (1996), Ch. 2 (reflexed E184 → tailless/delta)
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
t/c: trainer 12–18%, sport 10–12%, aerobatic 7–10%
```

**⚠️ Divergence from the source.** The preferred_families lists match both sources item for item. The thickness bands do NOT match the table the code claims to come from ('hobbyist heuristics from the RC-aircraft-designer skill', settings.py:11-13): code trainer 11–14 vs source 12–18 — the source's *average* trainer value of 15% falls outside the code's band, so a classic thick trainer section is actively penalised. Code sport 9–13 vs source 10–12 (wider both ways); code aerobatic 8–12 vs source 7–10 (shifted up). Glider, slope_soarer and flying_wing have no thickness table in either source at all. All cl_max_weight values are unsourced.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sources are hobbyist RC material (lower authority) — correct for this use, but they cover RC models only and say nothing about UAVs in the 5–15 kg band.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** No source cited for any of the thickness bands or weights.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `low_re_mission_weights: dict[str, dict[str, Any]] = Field(
    default_factory=lambda: dict(_DEFAULT_MISSION_WEIGHTS)
)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
