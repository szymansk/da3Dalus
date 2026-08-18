# Mechanical findings

> Computed from the graph, not judged by an agent. Every row here is a **structural**
> observation — a shape in the data, not a verdict about the code. Confirm before citing.

Corpus: **1112 nodes** across 10 clusters, 285 of them constants, 697 user-visible.

## Same literal value, independent definitions

One value defined in several places is the shape ADR 0022 forbids: a change to one
does not reach the others. Not every row is a defect — but every row is a question.

| value | defined in | nodes |
|---|---|---|
| `1.225` | 9× | [[alr-rho]] · [[end_rho]] · [[fe_rho_default]] · [[lfop-rho]] · [[prt-rho-default]] · [[rho-default-ss-dead]] · [[rho-sea-level-perf]] · [[rho_sl]] … |
| `0.3` | 8× | [[default-front-x-c]] · [[end_battery_dev_threshold]] · [[lfop-s-ref-fallback]] · [[mac-m-fallback]] · [[phase1-prop-diameter]] · [[sm-elevator-limit]] · [[sm-forward-clip-limit]] · [[stub-forward-sm]] |
| `0.8` | 7× | [[alr-score-bucket-ref]] · [[default-e-oswald-sizing]] · [[default_e_oswald_mc]] · [[end_fallback_e]] · [[prt-fallback-e-oswald]] · [[tos-confidence-threshold]] · [[usable-capacity-fraction-sizing]] |
| `0.5` | 6× | [[alr-cl-max-weight-default]] · [[default-s-ref-sizing]] · [[mu_belly]] · [[roskam-flap-cl-bonus]] · [[telescope-clearance-mm]] · [[trim-score-critical-threshold]] |
| `9.81` | 6× | [[fe_gravity]] · [[g_gravity]] · [[gravity-constant]] · [[gravity-g]] · [[gravity_g]] · [[mkpi_gravity_inline]] |
| `0.2` | 6× | [[alpha-vh-clamp-max]] · [[end_p_margin_comfortable]] · [[mass--sm-heavy-nose-warn]] · [[saoa-chord-fallback]] · [[stability--sm-heavy-nose-warn]] · [[v-h-physical-min]] |
| `0.03` | 5× | [[default-cd0-sizing]] · [[end_cd0_inline_default]] · [[prt-cd0-hard-fallback]] · [[rear-clearance-fraction]] · [[tol_line_binding]] |
| `9.80665` | 5× | [[alr-g]] · [[end_g]] · [[g-default-ss-dead]] · [[g-perf-dead]] · [[lfop-g]] |
| `2` | 5× | [[default_target_turn_n]] · [[dutch_roll_beta_deg]] · [[spar-index-invariant]] · [[tos-symmetry-factor]] · [[vlm-min-panels-per-segment]] |
| `1.2` | 5× | [[default_min_speed_margin_vs_clean]] · [[hand_throw_warn]] · [[kpi_min_sink_heuristic]] · [[v-h-physical-max]] · [[v_lof_factor]] |
| `25` | 5× | [[default-delta-e-deg]] · [[default_max_alpha_deg]] · [[deflection-limit-default]] · [[pitch_control_bounds]] · [[yaw_control_bounds]] |
| `0.1` | 5× | [[alpha-vh-fallback]] · [[htail-scale-min-guard]] · [[infeasibility-threshold-w]] · [[sm-tailless-fwd-cg]] · [[trim-score-warning-threshold]] |
| `3` | 4× | [[aero-spanwise--g-limit-default]] · [[mu_g_min]] · [[sm-apply-max-iters]] · [[structure--g-limit-default]] |
| `15` | 4× | [[lfop-cruise-v]] · [[saoa-velocity-fallback]] · [[target_flap_takeoff_deg]] · [[v-cruise-fallback]] |
| `30` | 4× | [[default_max_beta_deg]] · [[flap-default-deflection]] · [[lfop-brentq-bracket]] · [[target_flap_landing_deg]] |
| `1.4` | 4× | [[cl-max-clean-fallback]] · [[fe_dive_factor]] · [[kpi_best_ld_heuristic]] · [[ss-v-top-factor]] |
| `0.05` | 4× | [[min-rear-x-c]] · [[min-spar-spacing]] · [[sm-tailless-aft-cg]] · [[tol_vert_binding]] |
| `0.6` | 4× | [[de-da-factor]] · [[near-stall-velocity-factor]] · [[s-ref-m2-fallback]] · [[wall-factor]] |
| `0.01` | 4× | [[alpha-vh-clamp-min]] · [[center-z-nearest-key-tolerance]] · [[tc-nearest-key-tolerance]] · [[v-v-physical-min]] |
| `4` | 3× | [[alr-min-window-points]] · [[hyperbola-plot-span]] · [[lfop-alpha-fallback]] |
| `0.02` | 3× | [[alr-cd0-reference-fallback]] · [[mass--sm-unstable-limit]] · [[stability--sm-unstable-limit]] |
| `60` | 3× | [[alr-score-ld-ref]] · [[avl-runner-timeout]] · [[fe_n_points]] |
| `1.3` | 3× | [[default_approach_speed_margin_vs_ldg]] · [[v-axis-max-factor]] · [[v_app_factor]] |
| `0.12` | 3× | [[tc-fallback-analysis]] · [[tc-fallback-ratio]] · [[v-v-physical-max]] |
| `0.85` | 3× | [[default-eta-motor-endurance]] · [[default-eta-motor-perf]] · [[end_eta_motor]] |
| `3.7` | 3× | [[cell-v-nom]] · [[volts-per-cell-sizing]] · [[volts-per-lipo-cell]] |
| `5` | 3× | [[inboard-collinear-tolerance]] · [[max-x-wing-shift-mac]] · [[sm-classify-stable-threshold-pct]] |
| `0.005` | 3× | [[cm-delta-e-threshold]] · [[sm-convergence-threshold]] · [[sm-tailless-min-envelope]] |
| `1.5` | 2× | [[alr-score-cl-max-ref]] · [[lfop-mass-fallback]] |
| `40` | 2× | [[hyperbola-samples]] · [[vlm-spanwise-panels-per-half]] |

## Nodes nothing reads

A computed value with no consumer anywhere (ADR 0021).

- [[alr-classify-unused-masks]] · [[alr-interp-re-grid-param]] · [[center-z-mm]] · [[cg-agg-legacy-dead]] · [[default_loiter_s]] · [[default_target_turn_n]] · [[default_wind_mps]] · [[g-default-ss-dead]] · [[g-perf-dead]] · [[motor-continuous-electrical-power]] · [[prt-fit-band-v-array]] · [[prt-top-band-fallback]] · [[rho-default-ss-dead]] · [[scenarios-eval]] · [[tc-fallback-analysis]] · [[vlm-cd-total]] · [[vlm-cl-total]] · [[vlm-total-drag]] · [[vlm-total-lift]] · [[wcl_g_unused]]

## User-visible numbers with no attributable source

178 quantities reach an API response or the UI and have no citable origin.

- [[aero-model-label]] · [[aero-spanwise--packing-factor]] · [[aero-spanwise--sigma-allow-positivity-guard]] · [[air-density-perf]] · [[air-density-sizing]] · [[aircraft-class-default]] · [[alr-cl-bonus]] · [[alr-family-bonus]] · [[alr-score-bucket-ref]] · [[alr-score-cd-min-ref]] · [[alr-score-cl-max-ref]] · [[alr-score-ld-ref]] · [[alr-score-mission]] · [[alr-score-re-agnostic]] · [[alr-score-target-cl]] · [[alr-score-weights]] · [[alr-thickness-match]] · [[applicable_for_profile]] · [[ar_resolved]] · [[atmosphere-scale-height-perf]] · [[axis-autorange-guard]] · [[base-mass-fallback]] · [[battery-current-fallback-100a]] · [[binding_flag_propagation]] · [[binding_for_warning]] · [[candidate-cutoff]] · [[cd0-from-stability-run]] · [[cell-v-sag]] · [[center-z-by-y]] · [[chart_warnings]] · [[combo-confidence]] · [[combo-estimated-top-speed]] · [[constraint_category]] · [[curve-estimated-flag]] · [[default-eta-esc-endurance]] · [[default-s-ref-sizing]] · [[default_cruise_speed_mps]] · [[default_max_alpha_deg]] · [[default_max_beta_deg]] · [[default_max_level_speed_mps]] · [[dutch_roll_beta_deg]] · [[effective_field_length]] · [[effective_keys_custom]] · [[end_battery_dev_threshold]] · [[end_battery_deviation]] · [[end_eta_esc]] · [[end_p_margin_class]] · [[end_p_margin_comfortable]] · [[fe_dive_factor]] · [[fe_mass]] · [[fe_v_dive]] · [[fe_v_max_default]] · [[field_length_warnings]] · [[flap_factors]] · [[forward-cg-confidence]] · [[g-limit-fallback-flag]] · [[grid_best_controls]] · [[hand_launch_ws_max]] · [[hand_throw_default]] · [[hand_throw_floor]] …

## Constants with no attributable source

143 of 285 constants carry no citation. ADR 0023 asks every engineering constant to name its source **and** its scale.

- [[aero-spanwise--sigma-allow-positivity-guard]] · [[aircraft-class-default]] · [[alpha-vh-clamp-max]] · [[alpha-vh-clamp-min]] · [[alpha-vh-fallback]] · [[alr-cd0-reference-fallback]] · [[alr-cl-max-weight-default]] · [[alr-family-bonus]] · [[alr-gentleness-scale]] · [[alr-min-window-points]] · [[alr-score-bucket-ref]] · [[alr-score-cd-min-ref]] · [[alr-score-cl-max-ref]] · [[alr-score-ld-ref]] · [[atmosphere-scale-height-perf]] · [[avl-runner-timeout]] · [[axis-autorange-guard]] · [[base-mass-default]] · [[base-mass-fallback]] · [[battery-current-fallback-100a]] · [[bwsd-airfoil-fallback]] · [[candidate-cutoff]] · [[cell-v-sag]] · [[center-z-nearest-key-tolerance]] · [[cg-change-epsilon]] · [[cl-a-guard-epsilon]] · [[cl_target_guards]] · [[default-eta-esc-endurance]] · [[default-s-ref-sizing]] · [[default_cruise_speed_mps]] · [[default_loiter_s]] · [[default_max_alpha_deg]] · [[default_max_beta_deg]] · [[default_max_level_speed_mps]] · [[default_wind_mps]] · [[divide-guard-epsilon]] · [[dutch_roll_beta_deg]] · [[end_battery_dev_threshold]] · [[end_cd0_inline_default]] · [[end_eta_esc]] · [[end_p_margin_comfortable]] · [[fallback_speed_factors]] · [[fe_cl_min_factor]] · [[fe_dive_factor]] · [[fe_n_points]] · [[fe_v_max_default]] · [[fit-tol-mm]] · [[flap-alpha-sweep]] · [[flap_clip_epsilon]] · [[flap_factors]] · [[fraction-tol]] · [[grid_alpha_sweep]] · [[grid_fallback_trigger]] · [[hand_launch_ws_max]] · [[hand_throw_floor]] · [[hand_throw_warn]] · [[has-cadquery]] · [[htail-scale-min-guard]] · [[hyperbola-plot-span]] · [[hyperbola-samples]] · [[inboard-collinear-tolerance]] · [[infeasibility-threshold-w]] · [[is-v-tail-flag]] · [[k_ldg_50ft]] · [[k_ldg_hard]] · [[lennon_lb_ft_to_si]] · [[lfop-alpha-fallback]] · [[lfop-cl-target-clip]] · [[lfop-cruise-v]] · [[lfop-mass-fallback]] · [[lfop-s-ref-fallback]] · [[mac-m-fallback]] · [[mass-dedup-tolerance]] · [[max-x-wing-shift-mac]] · [[min-rear-x-c]] · [[min-spar-spacing]] · [[min_margin_clean_floor]] · [[mu_belly]] · [[mu_g_max]] · [[mu_g_min]] …

## Physical constants — where duplication is a defect by construction

A value of nature has one true value. Every extra definition is a place the others
cannot be corrected from. Unlike the table above, **no row here has an innocent reading**.

| constant | distinct values in code | definitions | nodes |
|---|---|---|---|
| **g** | `9.81` ×6 / `9.80665` ×5 | **11** | [[fe_gravity]] · [[g_gravity]] · [[gravity-constant]] · [[gravity-g]] · [[gravity_g]] · [[mkpi_gravity_inline]] · [[alr-g]] · [[end_g]] · [[g-default-ss-dead]] · [[g-perf-dead]] · [[lfop-g]] |
| **ρ₀** | `1.225` ×9 | **9** | [[alr-rho]] · [[end_rho]] · [[fe_rho_default]] · [[lfop-rho]] · [[prt-rho-default]] · [[rho-default-ss-dead]] · [[rho-sea-level-perf]] · [[rho_sl]] · [[sui-rho]] |
| **ν** | `1.5e-5` ×2 / `1.46e-5` ×1 | **3** | [[bwsd-nu]] · [[saoa-nu]] · [[sui-nu]] |
| **μ** | `1.81e-5` ×2 | **2** | [[prt-mu-isa-sl]] · [[sui-mu]] |

> `g` is defined **eleven times in two different values**. `ρ₀` nine times. `ν` three
> times in two values. None of this is a modelling choice.

## Edge types

Edges are typed where the data supports it. The **fallback** class is the ADR 0020
surface made visible: each one is a substitution that has to declare itself.

| role | edges |
|---|---|
| ⊣ limit | 216 |
| ⤵ fallback | 178 |
| ε tolerance | 20 |
| × unit | 20 |

*Untyped edges are plain functional inputs. Typing is mechanical and therefore
conservative — an edge is only labelled when the target node's own name says so.*

