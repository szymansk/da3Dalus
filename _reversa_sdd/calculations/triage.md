# Triage — which claimed defects survive scrutiny

> **Read the caveat before the list.** This is a work list for review, not a defect
> register. Nothing here justifies a refactor on its own.

## What the adversarial pass actually showed

26 agents re-tested 571 of 638 anomaly claims (one batch failed), each instructed to
**default to REFUTED** and to confirm only with a concrete failure case.

| verdict | claims |
|---|---|
| CONFIRMED_DEFECT | 260 |
| NEEDS_HUMAN | 106 |
| COSMETIC | 100 |
| REFUTED | 62 |
| BY_DESIGN | 43 |

**A 46 % confirmation rate under an instruction to refute is not an adversarial result.**
The verdict column is therefore not usable as it stands. The *severity* column is:

- **wrong-number** — a caller gets a wrong value on a normal path: **98**
- wrong-when-unlucky — only on a rare branch: 43
- maintainability: 46 · none: 152

## Two filters the swarm could not apply

**10 of the wrong-number claims are in `elevator_authority_service.py`** — the service
this register already proved **cannot execute** (it reads `x_np` / `mac` assumption rows
that nothing writes; see gh-1132). The swarm confirmed defects in code that never runs,
because it read one file and could not know that. A defect in unreachable code is a
deletion candidate, not a fix.

**9 more describe a missing or mislabelled output**, not a wrong number — a value
computed and discarded, a stale comment, an unexposed result.

## The 78 that survive

Each carries the reviewer's evidence and a concrete failure case. **Confirm against the
code before acting.** They are grouped by file so one reading settles several.

### `app/services/airfoil_low_re_service.py` — 13

**[[alr-max-camber-pct]]** — An inverted airfoil with max(abs(camber))=0.1 stored in DB, but max(camber)=-0.1 in classify_family, yields max_camber_pct = -10%, triggering symmetric gate (line 274) and mis-classifying as symmetric.
  · *evidence:* Line 214: `max_camber_pct = max_camber * 100.0` uses `np.max(camber)` without abs(). Verified: backfill script uses `np.max(np.abs(camber))`. Disagreement produces wrong classifier output for reflexed/inverted sections.

**[[alr-alpha-sweep]]** — A high-lift airfoil stalling at 22° → sweep stops at 18°, cl_max is computed as the 18° value (wrong). The code does not warn that the sweep was truncated before stall.
  · *evidence:* Lines 414-415: `alpha_end: float = 18.0` is a hard cap. Line 464: `alpha_deg = np.arange(alpha_start, alpha_end + alpha_step*0.5, alpha_step)` truncates the sweep. No warning when stall > 18°.

**[[alr-cl-valid-range]]** — Polar fitted over cl_valid=[0.2, 1.2], query cl_target=1.5 → extrapolates parabola 0.3 CL units beyond fit boundary, cd_at_target is computed from stale fit coefficients outside their validation range.
  · *evidence:* Lines 673-674: `cl_valid_lo/hi` are stored but line 1045 evaluates `cd_at_target = cd0 + k*(cl_target-cl0)^2` without checking bounds. Extrapolates parabolic fit beyond fitted range.

**[[alr-re-cd0-reference]]** — Two identical airfoils score differently depending on what other airfoils are in the DB. Adding a drag-clean airfoil raises the fleet's cd0 reference, lowering every other airfoil's efficiency score.
  · *evidence:* Line 823: `return float(np.percentile(cd0_arr, percentile))` computes fleet-wide percentile. Efficiency score in `score_target_cl` (line 1081) depends on DB population, violating ADR 0022 (one authority per quantity).

**[[alr-cd0-reference-fallback]]** — Empty DB or all-None cd0 values → silently returns 0.020, user sees efficiency=1.0 with no indication it is based on fallback constant, not real data.
  · *evidence:* Line 768: `_CD0_REFERENCE_FALLBACK = 0.020`. Line 820: returns fallback with no `DesignWarning` emitted. Violates ADR 0020: 'every substitution, clamp, retry or truncation emits a DesignWarning'.

**[[alr-score-cl-max-ref]]** — Maintainer updates one 1.5 to 1.6, forgets the other; score_re_agnostic and score_mission diverge, same airfoil scores differently depending on which scoring lens is used.
  · *evidence:* Line 856: `CL_MAX_REF = 1.5` and line 935: `cl_norm = min(cl_max / 1.5, 1.0)`. Same constant re-hardcoded in two places, violating ADR 0022 (one authority per user-facing quantity).

**[[alr-score-bucket-ref]]** — Same airfoil bucket width 0.7 CL: score_re_agnostic normalizes to 0.7/0.8 = 0.875 (excellent), score_target_cl normalizes to 0.7/0.6 = 1.0 (capped), inconsistent scoring.
  · *evidence:* Line 857: `BUCKET_REF = 0.8` in score_re_agnostic. Settings.py line 104: `low_re_bucket_tolerance_ref: float = 0.6` used in score_target_cl (line 1034). Two different 'wide bucket' references (0.8 vs 0.6).

**[[alr-score-weights]]** — Airfoil A: all 5 metrics present, stall_gentleness=-0.20 (bad). Airfoil B: missing stall data (only 4 metrics). B's score renormalizes without the 0.10 penalty, effectively upweighting its other components. B scores higher despite worse known gentleness.
  · *evidence:* Lines 886-891: `total_weight = sum(w for _, w in components) / total_weight` renormalizes weights if a component is None. Missing the worst metric (e.g. stall_gentleness, 0.10 weight) redistributes that 0.10 to remaining

**[[alr-gentleness-scale]]** — High-camber airfoil stalling at 22°, sweep stops at 18° with positive stall slope ~0.05 → formula gives 1.0 + 0.05/0.15 = 1.33 → clipped to 1.0 (full credit), masks the truncation issue.
  · *evidence:* Line 875: `gentleness_score = max(0.0, min(1.0, 1.0 + stall/0.15))`. Positive stall slopes (rising CL at 18°, indicating truncated sweep per CLAIM 11) are clipped to 1.0 without warning, hiding the truncation defect.

**[[alr-thickness-match]]** — Mission config omits thickness bounds → defaults to (0, 100). Any airfoil max_thickness 0–100% gives thickness_match = 1.0. Thickness dimension inert; all airfoils score identically on thickness.
  · *evidence:* Lines 927-930: `thickness_match = max(0.0, 1.0 - gap/5.0)` with default bounds (lines 913-914) `t_min=0.0, t_max=100.0`. Default band (0, 100) spans entire physical range, nullifying thickness scoring.

**[[alr-cl-bonus]]** — Same as CLAIM 24: one producer changes, other doesn't, scores diverge.
  · *evidence:* Line 935: `cl_norm = min(cl_max / 1.5, 1.0)`. Same constant 1.5 as line 856 (CL_MAX_REF), two producers, violates ADR 0022.

**[[alr-cd-at-target]]** — Same as CLAIM 17: fitted over CL=[0.2, 1.2], query CL_target=1.5 extrapolates, cd_at_target wrong.
  · *evidence:* Line 1045: `cd_at_target = cd0 + k*(cl_target - cl0)^2` without validating cl_target ∈ [cl_valid_lo, cl_valid_hi]. Same defect as CLAIM 17: extrapolates beyond fit range.

**[[alr-match]]** — cl_target near r_poor: small ε below r_poor gives match ≈ 0.02 (linear), small ε above r_poor gives match = (cl_max−cl_target)/safety_band, jump of ~0.1+. Score jumps discontinuously.
  · *evidence:* Lines 1052–1077: Three structural branches produce Match: (r≤1.0)→1.0, (r≥r_poor)→fallback or 0.0, (1<r<r_poor)→linear+bonus. At r=r_poor, linear formula gives 0.0 but fallback may give non-zero; discontinuity.

### `app/services/loading_scenario_service.py` — 13

**[[sm-unstable-limit]]** — If 0.02 is corrected to 0.025 in loading_scenario_service, sm_sizing_service still uses 0.02, causing divergent sm classifications in different code paths.
  · *evidence:* loading_scenario_service.py:51 `_SM_UNSTABLE_LIMIT = 0.02` and sm_sizing_service.py:53 defines identical constant independently. Both are used in their respective modules for the same classification thresholds.

**[[sm-heavy-nose-warn]]** — Threshold change requires editing both files; single-point maintenance hazard.
  · *evidence:* loading_scenario_service.py:52 `_SM_HEAVY_NOSE_WARN = 0.20` and sm_sizing_service.py:54 defines identical independent constant.

**[[sm-elevator-limit]]** — Updating stub limit in one place leaves stale values in others.
  · *evidence:* loading_scenario_service.py:53 `_SM_ELEVATOR_LIMIT = 0.30`, sm_sizing_service.py:78 `_SM_FORWARD_CLIP_LIMIT = 0.30`, elevator_authority_service.py:92 `_STUB_FORWARD_SM = 0.30`. Three independent definitions with inconsis

**[[cg-stability-fwd-stub]]** — After recompute_assumptions, endpoint GET /cg-envelope returns stub value 0.30·MAC while ctx has accurate elevator-authority limit. User sees stale forward CG limit.
  · *evidence:* Line 116: `cg_stability_fwd_m = x_np - _SM_ELEVATOR_LIMIT * mac` (stub). Line 587-588: `stability = compute_stability_envelope(...); stab_fwd = stability['cg_stability_fwd_m']` re-derives fresh instead of reading `ctx.ge

**[[scenario-cg-x]]** — User enters y_m/z_m overrides for lateral/vertical balance, but function silently ignores them and returns result based only on x-axis. Lateral/vertical CG shifts are lost.
  · *evidence:* Lines 58-59 in app/schemas/loading_scenario.py: PositionOverride accepts y_m_override and z_m_override. Line 164 in compute_scenario_cg: `pos_ovr_map = {p['component_uuid']: float(p['x_m_override']) for p in position_ove

**[[scenario-total-mass]]** — User adds 500g ballast (adhoc), CG shifts 10mm, but aircraft mass in design view unchanged. Unphysical: CG shift without mass update.
  · *evidence:* Lines 177-189: total_mass accumulated from components and adhoc items. Line 193: `if total_mass <= 0: return base_cg_x; return moment_x / total_mass` — local use only. No caller receives computed total_mass.

**[[base-mass-default]]** — Missing mass assumption: loading_scenario_service uses 1.0 kg, assumption_compute_service uses PARAMETER_DEFAULTS=1.5 kg. CG computed against 50% different base mass.
  · *evidence:* Line 355, 410: `_load_assumption_value(db, aeroplane.id, 'mass', default=1.0)`. app/schemas/design_assumption.py:73: `'mass': 1.5`. Two different fallbacks for same parameter.

**[[base-cg-x-default]]** — Missing cg_x: loading envelope computed from 0.0m, but design stability envelope from 0.15m. CG envelope appears shifted forward by 150mm.
  · *evidence:* Line 356, 411: `_load_assumption_value(db, aeroplane.id, 'cg_x', default=0.0)`. app/schemas/design_assumption.py:74: `'cg_x': 0.15`. Two independent fallbacks.

**[[sm-at-aft-ctx]]** — Cold start: sm_sizing_service re-derives with its defaults. After recompute_assumptions: ctx holds value from enrich_context. REST endpoint (get_cg_envelope) ignores ctx, recomputes with target_sm=0.08. Different code paths report different sm_at_aft for same aircraft.
  · *evidence:* Three producers: (1) enrich_context_with_cg_envelope line 260, (2) get_cg_envelope line 594 re-derives fresh with different target_sm default, (3) sm_sizing_service line 361 re-derives when cache absent.

**[[sm-at-fwd-api]]** — User design target_sm=0.12 (typical), but API computes sm_at_fwd against 0.08 default. If actual sm_at_fwd=0.10: classifies as 'ok' (against 0.08) but contradicts user's 0.12 target (would be 'warn').
  · *evidence:* Line 585: `target_sm = _load_assumption_value(..., default=0.08)`. Line 593: `sm_at_fwd = (x_np - cg_fwd) / mac` uses this 0.08 default. But design assumption 'target_static_margin' defaults to 0.12 in PARAMETER_DEFAULTS

**[[sm-at-aft-api]]** — When recompute_assumptions runs with physics-based cg_stability_fwd_m, sm_at_aft cached with design target_sm. But get_cg_envelope re-derives with default=0.08, producing different sm_at_aft.
  · *evidence:* Line 594: recomputes sm_at_aft fresh instead of reading cached ctx['sm_at_aft'] from enrich_context_with_cg_envelope line 260.

**[[cg-classification-overall]]** — recompute_assumptions hasn't run: sm_at_fwd=None ('unknown'), sm_at_aft='ok'. Line 605: rank[unknown]=0 >= rank[ok]=1 is false, so overall='ok'. User sees all-OK despite unknown forward SM. Frontend type mismatch if 'unknown' reaches UI.
  · *evidence:* Line 604: `_rank = {'error': 3, 'warn': 2, 'ok': 1, 'unknown': 0}`. Lines 605-608: rank[fwd]>=rank[aft] chooses fwd, else aft. So unknown(0) loses to ok(1). Frontend type CgClassification='error'|'warn'|'ok' (hooks/useLo

**[[target-sm-default-cg-envelope]]** — User never sets target_static_margin explicitly. Depending on code path (loading_scenario endpoint vs. sm_suggestions vs. assumption recompute), effective default (0.08, 0.10, or 0.12) determines aft CG limit and SM classification. Same aircraft gets different stability limits.
  · *evidence:* Line 585: `default=0.08`. design_assumption.py:75: `'target_static_margin': 0.12`. sm_suggestions.py:74: `0.10`. Three independent defaults for same parameter.

### `matching_chart_service.py` — 12

**[[mission_min_tw_table]]** — User selects profile='custom'. Mission-Min T/W set to 1.5 (acro) without warning, and Vertical-Climb curve not emitted.
  · *evidence:* Lines 1085-1088: When profile_key is None, builder substitutes 'acro_3d' (1.5 T/W) with no warning. At line 1155, test 'vertical_climb in effective_keys' can never be true because effective_keys contains profile names, n

**[[wcl_ws_max]]** — WCL constraint returns 71 N/m² not 120 N/m² for trainer at AR=7. User sees constraint that contradicts documented design intent.
  · *evidence:* Lines 528-531: Formula `(wcl_lb * 47.88) ** (2/3) * ar ** 0.25` produces ~71 N/m² for trainer at AR=7 but comment claims ~120 N/m². Off by factor 1.7-2.2. Exponents 2/3 and 0.25 are unsourced.

**[[tw_mission_min]]** — User selects profile='custom'. Mission-Min T/W constraint set to 1.5 (acro_3d) with no UI warning.
  · *evidence:* Lines 1085-1088: Custom profile silently substitutes acro_3d 1.5 T/W floor without warning per ADR 0020. User designing custom trainer gets 3D-acro constraint.

**[[tw_vertical_climb]]** — At ws=100, cd0=0.03, e=0.8, ar=7, v_climb=15: formula returns ~1.3 T/W instead of ~1.036 (profile drag only).
  · *evidence:* Line 585: Formula `1 + D/W` includes induced drag term `ws*k/q` where L is assumed non-zero. In true vertical climb, L=0 so induced drag should vanish. Code keeps level-flight induced drag, making constraint non-physical

**[[design_point_ws]]** — Aircraft dict lacks wing area. Design point plots at (0, 0) with no warning.
  · *evidence:* Lines 625-630: No ws_n_m2 or s_ref_m2 silently defaults to ws=0.0 with no DesignWarning per ADR 0020. Missing wing area is critical assumption, not silent default.

**[[v_cruise_resolved]]** — RC aircraft ws=50 N/m² uses V_md at ws=500, yielding higher cruise speed and too-lenient cruise constraint.
  · *evidence:* Line 796: Hard-coded 500 N/m² called 'approximate midpoint' of 10-1500 range, but midpoint is 755. Also 500 is light-GA territory, not RC/UAV (20-150) per ADR 0023. Estimate biased high.

**[[cd0_resolved]]** — Aircraft dict lacks cd0. Matching chart uses cd0=0.03, cruise constraint too slack. No warning to user.
  · *evidence:* Line 803: `cd0: float = float(aircraft.get("cd0", 0.03))` silently defaults to 0.03 with no DesignWarning per ADR 0020. Value inappropriate across RC/UAV to GA scale range.

**[[ar_resolved]]** — Aircraft dict lacks ar. Matching chart uses AR=7.0, climb and cruise constraints computed at unrepresentative aspect ratio. No warning.
  · *evidence:* Line 805: `ar: float = float(aircraft.get("ar", aircraft.get("aspect_ratio", 7.0)))` silently defaults to AR=7.0 with no DesignWarning per ADR 0020. Value inappropriate for RC/UAV range.

**[[cl_max_to_mc]]** — Aircraft CL_max=1.4. Matching chart: CL_max_landing=1.82 (1.4*1.3). Field-length service: may be 1.74 from _FLAP_FACTORS lookup. Two constraints disagree.
  · *evidence:* Line 808: matching_chart endpoint (line 100) passes cl_max_landing = cl_max * 1.3. field_length_service.py:361 uses lookup from _FLAP_FACTORS table. Two services compute different landing CL_max for same aircraft, violat

**[[profile_constraint_map]]** — User selects profile='sport'. Takeoff and landing constraints not emitted. Sport aircraft design ignores field-length.
  · *evidence:* Lines 103-115: No profile includes 'hand_launch'. Every non-STOL profile (trainer/sport/acro/etc) excludes 'takeoff' and 'landing'. Field-length constraints silently absent for non-STOL profiles despite being universal s

**[[effective_keys_custom]]** — User selects profile='custom'. Vertical-Climb curve not added because 'vertical_climb' never in effective_keys=['acro_3d', 'wing_racer', 'sport'].
  · *evidence:* Lines 1074-1078: For None profile, effective_keys = list(_MISSION_MIN_TW_BY_PROFILE.keys()) yields profile names ['acro_3d', 'wing_racer', 'sport']. Line 1155 test 'vertical_climb in effective_keys' can never be true. Ve

**[[chart_warnings]]** — Aircraft dict missing cd0, ar, geometry. Three fallbacks applied silently. User receives 2 warnings but no indication that cd0/AR/design-point are defaults.
  · *evidence:* Lines 772-800 emit only 2 warnings (missing e, cruise estimate). Fallbacks for cd0=0.03 (line 803), AR=7 (line 805), unknown mode (line 240), ws=0 (line 630), strictest mission_min (line 1088) are all silent per ADR 0020

### `app/services/powertrain_solution_space_service.py` — 9

**[[ss-cap-mah]]** — For 2S LiPo with V_nom=7.4V, V_sag=7.0V, energy_wh=10, P_elec=200W: cap_mah=10/7.4*1000=1351 mAh, i_peak=200/7.0=28.6 A, C_rate=28.6/1.351=21.1. The capacity uses one voltage, current uses another, violating pack model consistency.
  · *evidence:* Line 142: cap_mah = energy_wh / v_nom * 1000.0 uses V_nom (3.7V per cell). Line 139: i_peak = p_top_elec_w / v_sag uses V_sag (3.5V per cell). Same battery is modelled at two different voltages, making capacity and C-rat

**[[ss-c-min]]** — User sees hyperbola with c_rate=10 at cap=1000 mAh on the chart. Shopping spec requires c_min=10*1.25=12.5 due to c_margin. Point looks feasible on the plot (10 < 12.5) but exceeds the specification.
  · *evidence:* Line 146: c_min = raw_c * c_margin (includes margin). Line 183: c_rates = [i_peak / (c / 1000.0) for c in caps] (no margin). The plotted hyperbola lacks margin while the shopping spec includes it. Line 218 compares again

**[[hyperbola-c-rate-samples]]** — At capacity=1000 mAh with i_peak=20 A: hyperbola shows c_rate=20, shopping spec requires c_min=25. Chart boundary sits 5 points below the specification.
  · *evidence:* Line 183: c_rates = [i_peak / (c / 1000.0) for c in caps] computed without c_margin. Line 146: c_min = raw_c * c_margin includes margin (default 1.25x). The plotted hyperbola boundary is margin-free while the shopping sp

**[[ss-s-ref]]** — Same aircraft, solution_space computes with S_ref=0.25 m², sizing uses 0.5 m². Power estimates diverge by 100%.
  · *evidence:* Line 278: s_ref_m2 = 0.25 (fallback). powertrain_sizing_service.py:47 defines _DEFAULT_S_REF_M2 = 0.5. Factor-of-2 disagreement. Power required scales inversely with S_ref, so solution_space overestimates power by 2x whe

**[[ss-e-oswald]]** — Same aircraft, solution_space uses e=0.75, sizing uses e=0.8. Induced drag coefficient differs by ~7%, affecting power estimates across services.
  · *evidence:* Line 285: e_oswald = 0.75 (fallback). powertrain_sizing_service.py:45 uses 0.8, endurance_service.py also uses 0.8. Disagreement across three services: 0.75 vs 0.8. Induced drag coefficient k = 1/(π·e·AR) is affected.

**[[ss-ar]]** — Same aircraft, solution_space uses AR=7, sizing uses AR=8. Induced drag coefficient k differs by ~14%.
  · *evidence:* Line 292: ar = 7.0 (fallback). powertrain_sizing_service.py:46 uses 8.0. Same induced-drag scaling: k = 1/(π·e·AR). Disagreement between two services.

**[[ss-eta-mid]]** — Backend computes motor_peak_w = 200/0.715 = 280W. Frontend computes ceil(200/0.65) = 308W. User shops for 308W, backend schema irrelevant.
  · *evidence:* Line 357: eta_mid = (0.65 + 0.78) / 2 = 0.715. Used at lines 360-361 to compute motor power. Frontend PowertrainTab.tsx:110 computes conservativeMotorW(pAeroTop, etaPropLo) using eta_prop_lo=0.65. Backend uses 0.715, fro

**[[ss-band-energy-lo]]** — Row shows energy_wh=10 Wh (mid-band at 0.715 efficiency) and capacity_mah_min_hi=1500 mAh (lo-band at 0.65 efficiency). The mAh was computed assuming higher power drain, Wh assumes lower drain. Inconsistent pack model within one row.
  · *evidence:* Line 400: Computes lo-band energy (high drain scenario). Line 440: SolutionRow.energy_wh carries mid-band energy. Line 443: capacity_mah_min_hi carries lo-band. The Wh and mAh columns in the same table row derive from di

**[[ss-motor-peak-shaft]]** — For p_aero_top=200W: backend=280W, frontend=308W. User sees 308W and shops for that. Backend value unused. Dual production.
  · *evidence:* Line 421: motor_peak_shaft_w = p_aero_top / eta_mid (uses 0.715). Frontend PowertrainTab.tsx:110 computes independently: ceil(p_aero_top / etaPropLo) (uses 0.65). Values differ by ~10%. Backend ships this in SolutionRow 

### `/Users/szymanski/Projects/da3Dalus/cad-modelling-service/app/services/powertrain_performance.py` — 7

**[[default-eta-motor-perf]]** — Motor with missing efficiency_pct silently substitutes 0.85, no warning to user that a datasheet value was missing
  · *evidence:* Line 51: _DEFAULT_ETA_MOTOR = 0.85. Used at line 147 in eta_motor property as fallback when efficiency_pct is None: 'return _DEFAULT_ETA_MOTOR'. This undeclared fallback substitutes 0.85 with no DesignWarning emitted. Pe

**[[qprop-p-shaft]]** — QPROP branch reports p_shaft > motor.max_electrical_power_w * eta_motor, violating power ceiling; user sees physically inconsistent power draws between QPROP and fixed-RPM cases
  · *evidence:* Lines 750-757: When use_qprop=True (line 750), p_shaft_w = float(max(op.p_shaft_w, 0.0)) — clamped only at 0, p_shaft_max is never applied. When use_qprop=False (line 757), p_shaft_w = float(np.clip(p_shaft_uncapped, 0.0

**[[curve-p-shaft-max]]** — QPROP branch can report power above the ceiling while fixed-RPM cannot
  · *evidence:* Line 663: p_shaft_max = p_available_elec * motor.eta_motor is computed as a power ceiling. However, on the QPROP branch (line 753), this ceiling is ignored entirely: p_shaft_w = float(max(op.p_shaft_w, 0.0)) applies no u

**[[curve-eta-prop]]** — Sizing module uses flat 0.65 while performance module uses J-dependent Pe; inconsistent power predictions for same mission
  · *evidence:* Line 760: eta_prop = float(np.clip(Pe, 0.0, 1.0)) uses J-dependent propeller efficiency. Line 759 comment explicitly contrasts this with 'the flat 0.65 scalar'. However, endurance_service.py:53 uses DEFAULT_ETA_PROP=0.65

**[[curve-estimated-flag]]** — estimated=False is returned for QPROP (physics-solved), confusing users into thinking QPROP values are measured datasheet values
  · *evidence:* Lines 726, 730: estimated_flag = False when use_qprop, estimated_flag = True when not. PerformanceSample.estimated description (line 246–247) says: 'True when power was derived from current×voltage rather than a directly

**[[motor-io-input]]** — Motor with missing io_no_load_a silently assumes zero no-load loss, inflating reported efficiency by up to 5–10%
  · *evidence:* Line 523: i0 = motor.io_no_load_a or 0.0. When io_no_load_a is None (not provided in catalog), this substitutes I0=0 A (loss-free no-load assumption) with no DesignWarning emitted. Per ADR 0020, undeclared fallbacks must

**[[motor-max-current-input]]** — A motor with 50 A burst / 30 A continuous uses 50 A as the sustained ceiling in QPROP, allowing longer flights than physically possible
  · *evidence:* Line 100: MotorSpec.max_current_a is a BURST current rating (per datasheet terminology). However, line 704 uses it as the QPROP current ceiling i_ceiling = motor.max_current_a and passes it to solve_qprop_operating_point

### `/Users/szymanski/Projects/da3Dalus/cad-modelling-service/app/services/flight_envelope_service.py` — 6

**[[fe_effective_cl_alpha]]** — Aircraft with no alpha-sweep measurement → gust envelope computed with Helmbold CL_α → user sees load factors labeled with measured-data confidence level but based on formula.
  · *evidence:* Lines 341–344: When cl_alpha_per_rad is None, the code silently substitutes Helmbold-Diederich via `effective_cl_alpha = _helmbold_cl_alpha(ar)` with no DesignWarning or user notification. Per ADR 0020, 'every substituti

**[[fe_b_ref]]** — Corrupted or incomplete aeroplane geometry → conversion fails → gust envelope silently disabled → user sees KPI values and V-n curve without gust critical load-factor warnings.
  · *evidence:* Lines 627–633: Bare `except Exception: return None` swallows all conversion failures (any error from converters or ASB). When None is returned, line 346 skips the gust envelope with no user warning per ADR 0020. The user

**[[fe_v_max_default]]** — Aircraft with no flight profile goals → _get_v_max returns 28.0 → user sees V_dive = 39.2 m/s, gust loads at default speed, KPI values — all based on unvalidated assumption.
  · *evidence:* Lines 285 and 586 both define 28.0 m/s as a default when no flight profile goal is available. The code at line 586 returns this value without warning. Then compute_flight_envelope (line 679–689) uses 28.0 to build the en

**[[fe_marker_load_factor]]** — Operating point created with name='max_turn' and status='TRIMMED' → load_factor=1.0 → if used in kpi_max_load_factor, reports max load as 1.0 g.
  · *evidence:* Line 606: All operating points are assigned `n = 1.0` unconditionally, regardless of name or status. Even if an OP is named 'max_turn' (intended to represent a turning flight condition with n > 1.0), it receives n = 1.0.

**[[kpi_best_ld_speed]]** — Operating point created with name='best_ld' and status='NOT_TRIMMED' → KPI reports confidence='trimmed' despite actual status being untrimmed.
  · *evidence:* Lines 410–421: If a marker named 'best_ld' exists, the code unconditionally assigns `confidence="trimmed"` (line 419) without checking `marker.status`. The docstring (lines 383–386) promises 'TRIMMED operating-point mark

**[[kpi_min_sink_speed]]** — Operating point created with name='min_sink' and status='NOT_TRIMMED' → KPI reports confidence='trimmed' despite untrimmed status.
  · *evidence:* Lines 446–457: Same defect as kpi_best_ld_speed. If a marker named 'min_sink' exists with status='NOT_TRIMMED', the code still assigns `confidence="trimmed"` without validation.

### `app/schemas/powertrain_solution_space.py, app/services/component_tree_service.py` — 5

**[[cad-shape-own-weight-surface]]** — Node with type='cad_shape', node.area_mm2=100, node.quantity=3, density=1, resolution=0.4, scale_factor=1.0 returns 40g instead of 120g
  · *evidence:* Line 455: `return node.area_mm2 * resolution * density / 1e6 * node.scale_factor` does NOT multiply by `node.quantity`, while COTS branch at line 438 does: `return comp.mass_g * (node.quantity or 1)`. Both represent own 

**[[cad-shape-own-weight-volume]]** — Node with type='cad_shape', node.volume_mm3=1000, node.quantity=4, density=0.8, scale_factor=1.0 returns 0.8g instead of 3.2g
  · *evidence:* Line 457: `return node.volume_mm3 * density / 1e6 * node.scale_factor` does NOT multiply by quantity, while COTS (line 438) does.

**[[node-quantity]]** — Node with type='cad_shape', quantity=3 returns 1x weight instead of 3x; node with weight_override_g=100, quantity=2 returns 100g instead of 200g
  · *evidence:* Line 438 shows COTS multiplies by quantity: `comp.mass_g * (node.quantity or 1)`. But _weight_from_cad_shape (lines 455, 457) and weight_override_g (line 463) do not multiply by quantity. The quantity field is defined on

**[[weight-override-g]]** — Node with weight_override_g=100g, quantity=5 returns 100g as own weight instead of 500g
  · *evidence:* Line 463-464: `if node.weight_override_g is not None: return node.weight_override_g, 'override'` returns the override directly without multiplying by node.quantity, unlike the COTS path (line 438).

**[[aircraft-total-weight-kg]]** — Aircraft with component_tree totaling 5kg and weight_items totaling 6kg; if sync_weight_items_to_assumptions executes after sync_component_tree_to_mass, the API returns 6kg instead of 5kg, violating ADR 0022
  · *evidence:* Line 381-403 defines get_aircraft_total_weight_kg which sums top-level roots. This is called by _sync_aircraft_mass (lines 211, 240, 273) which eventually calls sync_component_tree_to_mass, but app/services/mass_cg_servi

### `verification-results.json` — 3

**[[safety-factor-j-aeroanalysis]]** — User calls POST /aeroplanes/{id}/spanwise_loads_with_sizing with only material_id and no safety_factor_j override. If design assumptions lack g_limit, both defaults (1.5 and 3.0) are applied silently, resulting in 4.5× ultimate-load multiplication with no warning that this is a composite ultimate fa
  · *evidence:* Line 609: `safety_factor_j: Annotated[float, Query(gt=0, description="Safety factor j (default 1.5)")] = 1.5` has no source citation. Line 626 documents the formula M_design = |M(y)| · g_limit · j, and line 627 notes g_l

**[[packing-factor]]** — User provides packing_factor=0.8 assuming one behavior (scalar multiplier), but the same value is interpreted as a symmetric inset elsewhere (two-sided margin), causing inconsistent spar sizing results across different code paths.
  · *evidence:* Lines 38-45 in spar_sizing.py declare packing_factor with default 0.8 and no source. Line 323 in app/services/spar_sizing.py applies it as scalar: `outer_mm = profile_thickness_mm * params.packing_factor`. Line 761 in ca

**[[cap-width-mm]]** — User calls POST /aeroplanes/{id}/spar-plan with shape='capped' in the request body. Since SparPlanRequest lacks a cap_width field, there is no way to provide the required flange width, and the sizing solver receives cap_width=None and fails.
  · *evidence:* Line 47-50 in spar_sizing.py declares cap_width_mm as Optional[float] with description 'Flange/cap width b (mm) — required for shape=\'capped\''. However, spar_plan.py SparPlanRequest (lines 56-175) allows shape='capped'

### `app/services/stability_service.py` — 2

**[[trim-elevator-deg]]** — Aircraft with control surface named 'ruddervator' or 'elevon' trims pitch, _find_trim_elevator returns None because 'elevator' substring not in 'ruddervator'.lower(), trim_elevator_deg becomes None instead of the actual trim deflection value
  · *evidence:* Lines 55-62: `for name, defl in control_surfaces.deflections.items(): if "elevator" in name.lower(): return _scalar(defl)`. Substring match will fail for V-tail 'ruddervator', flying-wing 'elevon', and flaperon wing-moun

**[[stability-solver-key]]** — Analysis with AnalysisToolUrlType.AEROBUILDUP runs, database solver column receives 'AnalysisToolUrlType.AEROBUILDUP' instead of 'aerobuildup', subsequent queries for solver='aerobuildup' fail to find the result, schema violates ADR 0019
  · *evidence:* Line 357 `persist_stability_result(db, aeroplane_pk, str(analysis_tool), summary, geometry_hash)` passes the string representation to the solver parameter. Because AnalysisToolUrlType(str, Enum) returns 'AnalysisToolUrlT

### `/Users/szymanski/Projects/da3Dalus/cad-modelling-service/app/services/spar_plan_service.py` — 2

**[[spar-spacing-fraction]]** — Wing section at y=2m with chord=1.0m and torsion=100 N·m, spacing_fraction=0.45: rear moment = 100/0.45 ≈ 222 N·m. Same torsion at y=4m with chord=0.5m: rear moment still ≈ 222 N·m, but should be scaled by 0.5m/1.0m = 0.5, giving 111 N·m. Narrow sections are over-sized.
  · *evidence:* Line 401-413: Returns dimensionless chord fraction (e.g., 0.45 for front=0.30c, rear=0.75c). Line 453: `reaction = torsion_fn(y_span) / spacing` divides moment in N·m by dimensionless fraction, yielding N·m. Physically, 

**[[rear-torsion-reaction]]** — Identical to spar-spacing-fraction claim: wide sections are under-sized, narrow sections are over-sized relative to the actual force couple.
  · *evidence:* Line 453: `reaction = torsion_fn(y_span) / spacing`. Same dimensional problem as spar-spacing-fraction: dividing moment (N·m) by dimensionless fraction (spacing_fraction) yields N·m, but physically should be a force mome

### `/Users/szymanski/Projects/da3Dalus/cad-modelling-service/app/services/spar_sizing.py` — 2

**[[capped-cross-section-area]]** — Any capped spar with non-zero web area. The reported cross_section_area_mm2 excludes the web material. Mass reported is lower than actual.
  · *evidence:* Line 210: `area = 2.0 * b * gurt`. This computes only the flange area (two rectangular flanges, each width b and height gurt). A real capped spar (I-beam) has flanges AND one or more webs connecting them. The web area is

**[[spar-mass-half]]** — Any sized_station with feasible=False contributes area 0.0 to the mass integral. The reported half_mass and full_mass are silently lower than a complete spar would be.
  · *evidence:* Lines 356-359: infeasible stations with `cross_section_area_mm2 is None` are replaced with 0.0. Line 250 (spar_mass_half_kg) integrates with these zero areas. No warning or flag indicates the mass is based on some infeas

### `app/services/mission_kpi_service.py,app/services/assumption_compute_service.py,app/services/suitability_service.py` — 2

**[[sui-per-lens-re]]** — With v_mps=10, chord=0.5: _compute_re produces Re=1.225*10*0.5/1.81e-5 ≈ 338,122; _per_lens_re produces Re=10*0.5/1.46e-5 ≈ 342,466. Same conditions produce different Re values (4,344 difference = 1.2%). Per-lens polars are scored at a different Re than intended.
  · *evidence:* Line 383: `_per_lens_re` uses `_NU = 1.46e-5`, but sibling function `_compute_re` (lines 119-121) uses `rho/mu = 1.225/1.81e-5`. For the same speed and chord, the two functions produce different Reynolds numbers: per_len

**[[sui-cl-max-margin]]** — At low per-lens Re, polars are softer and CL_max is lower. If slider_Re is 100k and per_lens_Re is 50k, cl_max from slider is high but target CLs from per_lens are compared to this high value, producing an artificially large (optimistic) margin.
  · *evidence:* Lines 516-531: cl_max_margin is computed as cl_max_val - max(target_cls). The cl_max_val comes from the slider-Re polar (lines 517-518: polar.get('cl_max')), while the target_cls come from per-lens Re polars (lines 520-5

### `app/services/field_length_service.py` — 1

**[[s_ldg_50ft]]** — Same aircraft queried via two paths: /compute_field_lengths returns s_ldg_50ft from the Roskam formula; the assumption context (consumed by the UI) returns landing_field_length_m from the energy-balance formula. The two values diverge.
  · *evidence:* Lines 436, 771-787 (assumption_compute_service.py): The field_length_service computes 's_ldg_50ft = _apply_obstacle_factor(s_ldg_ground, _K_LDG_50FT)' (line 436). In parallel, assumption_compute_service._compute_landing_

### `app/services/aerobuildup_trim_service.py` — 1

**[[achieved-coefficient]]** — Request trim with target_coefficient that AeroBuildup doesn't compute for the final deflection -> achieved_value=null, converged=True (false positive)
  · *evidence:* Lines 276-282, 333: When `target_coeff` is missing from `final_result`, `achieved = _to_scalar(final_result.get(target_coeff, float("nan")))` sets achieved to NaN. The warning is logged at line 278, but the code proceeds

## What is still untested

- **67 claims** from the batch that failed to return.
- **106 claims** need a domain judgement the code cannot settle — mostly whether a
  constant is right for 0.5–15 kg aircraft (ADR 0023). Those belong to the domain experts,
  not to another code pass.
- The 834 divergence flags between code and literature. Untouched by this pass.

