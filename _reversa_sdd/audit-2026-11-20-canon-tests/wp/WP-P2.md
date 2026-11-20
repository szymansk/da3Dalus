# WP-P2 — Aerodynamik- und Stabilitätsformeln

Self-contained brief for one implementer subagent. Frozen review state: commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

- **Production code under test:** aero_kernel/formulas/butterfly_approach.py, stall_break.py, solvers/stall_math.py
- **Requirement sources:** Kanon-Einträge, ADR 0020, ARCHITECTURE §8.13
- **Test files you may change:** `aero_kernel/tests/test_aileron_deflection_required_engine.py`, `aero_kernel/tests/test_butterfly_approach.py`, `aero_kernel/tests/test_hinge_moment_engine.py`, `aero_kernel/tests/test_minimum_drag_speed_engine.py`, `aero_kernel/tests/test_neutral_point.py`, `aero_kernel/tests/test_roll_rate_engine.py`, `aero_kernel/tests/test_stall_break.py`, `aero_kernel/tests/test_stall_math.py`, `aero_kernel/tests/test_stall_speed_engine.py`, `aero_kernel/tests/test_stall_wing_loading_limit.py`, `aero_kernel/tests/test_v_tail_neutral_point.py`, `aero_kernel/tests/test_zero_lift_angle_real.py`
- **Findings:** 17 (1 high, 5 medium, 11 low)

A finding marked **DECISION** needs the maintainer's answer first: do not write its test, list it in your report as open.

## P2-F01 · high · untested_warning

- **Test file:** `aero_kernel/tests/test_butterfly_approach.py` · existing test `test_the_forwarded_caveats_are_the_reference_solves_and_the_worst_case_of_the_sweep` (line 372)
- **Production:** `aero_kernel/formulas/butterfly_approach.py:152-157`
- **Gap:** butterfly-approach can drop every caveat of its reference solves (Reynolds regime, drag messages of the landing stall and of the closing sample) and no test fails; ADR 0020 requires them declared. The early-return path (s_max = 0) forwards nothing testable either.
- **Evidence:** assert len(regime) <= 2  # the landing stall and the bracketing sample, not one per mix
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P2-M09:** in `aero_kernel/formulas/butterfly_approach.py` line 155: 'if warning.code != FIT_RANGE and key not in seen' -> 'if False and ...' (no reference-solve caveat forwarded). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_butterfly_approach.py, with the existing Noisy stub (its stall emits reynolds_bubble_sensitive with message 'Re <v_s*1e4>' per mix) and default inputs (v_app = 1.05 V_S0(0), crossing between mix 0.6 and 0.7): assert the forwarded regime messages are exactly {f'Re {V_S0(0)*1e4:.0f}', f'Re {V_S0(0.7)*1e4:.0f}'} with V_S0(s) = sqrt(2 m g/(rho 0.28 (1.25-0.18 s))). Second test with v_app = 0.9 V_S0(0) (s_max = 0 path): exactly one regime warning, that of the landing stall, plus the fit-range warning.

## P2-F02 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_stall_math.py` · no test exists
- **Production:** `aero_kernel/solvers/stall_math.py:52-53`
- **Gap:** first_extremum_from_zero may scan a peak from the first sample (-15 deg) instead of from alpha = 0 (K32): a local maximum at negative alpha (lift recovering past the negative stall) would become C_L,max. No fast test calls the function with a maximum below zero; the upward start is only implied by aero goldens.
- **Evidence:** test_stall_math.py imports only first_extremum: 'from aero_kernel.solvers.stall_math import first_extremum'; production: 'start = min(range(len(alphas_deg)), key=lambda k: abs(alphas_deg[k]))'
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P2-M05:** in `aero_kernel/solvers/stall_math.py` line 53: upright scan range(start, n) -> range(0, n) (peak searched from the first sample, not from alpha = 0). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_stall_math.py: alphas = (-4,-3,-2,-1,0,1,2,3,4), cl = (-0.4,-0.3,-0.5,-0.2,0.0,0.3,0.6,0.5,0.4): a local maximum at -3 deg and the first peak from zero at +2 deg. Assert first_extremum_from_zero(alphas, cl, upright=True) == 6 and, mirrored series, upright=False gives the trough below zero, not the one above; also an alpha grid without 0.0 (nearest sample) and an empty series -> None.

## P2-F03 · medium · mirror_or_tautology

- **Test file:** `aero_kernel/tests/test_v_tail_neutral_point.py` · existing test `test_the_horizontal_and_fin_shares_add_up_to_the_true_area_for_every_angle` (line 157)
- **Production:** `aero_kernel/solvers/asb_airplane.py:357-372`
- **Gap:** Four tests of this file (lines 68, 139, 157, 168; 12 parametrised cases) assert properties of the test stand-in aero_kernel/tests/asb_fakes.py, not of production. The 'trace test' is a tautology: the stand-in defines the fin share as true_area - effective. Dropping cos^2 in production _v_tail_surface leaves all P2 files green; it is caught only by test_solvers_asb_airplane.py.
- **Evidence:** shares = stand_in_horizontal_tail_area(wing) + stand_in_fin_area(wing); assert close(shares, true_area, 1e-12)  -- asb_fakes: 'return mirrored * (true_area - effective)'
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P2-M15b:** in `aero_kernel/solvers/asb_airplane.py` line 372: same mutation as M15. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Move the angle sweep onto production: fast, test_solvers_asb_airplane.py (fake aerosandbox), for rise in (0, 0.05, 0.2, 0.5, 1.5) m on a 0.2 m half span, chord 0.1 m: asb_airplane.horizontal_tail_area == 2*0.1*L*(0.2/L)^2 and fin_area == 2*0.1*L*(rise/L)^2 with L = hypot(0.2, rise), each against its own closed form (not their sum), tolerance 1e-12. Rename or delete the stand-in tests as helper self-checks.

## P2-F04 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_butterfly_approach.py` · existing test `test_the_validity_follows_the_largest_deflection_not_full_crow` (line 386)
- **Production:** `aero_kernel/formulas/butterfly_approach.py:290-291`
- **Gap:** The test cannot tell 'mix with the largest deflection' from 'always full crow': at s = 1 the raised aileron is carried as a flap at -40 deg, above the 30 deg limit, so the declaration appears either way and only its presence is asserted.
- **Evidence:** assert "flap_deflection_beyond_validity" in {w.code for w in context_.warnings}
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P2-M08:** in `aero_kernel/formulas/butterfly_approach.py` line 290: worst = mix with the largest deflection -> worst = last mix (full crow). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, same file: delta_f_ldg = 60, delta_f_crow = 20, delta_a_crow = 10 (full crow: flap 20, aileron -10, both below 30). Assert the single flap_deflection_beyond_validity warning has detail['flaps'] == [{'wing': 'Main', 'device': 'device 0', 'deflection_deg': 60.0}] (the landing flap at s = 0). Add a CrowStub variant whose diagnostics differ per mix and assert flap_confidence_low carries the confidence of mix 0.

## P2-F05 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_stall_break.py` · existing test `test_a_non_positive_peak_is_invalid_input` (line 224)
- **Production:** `aero_kernel/formulas/stall_break.py:95`
- **Gap:** The guard 'cl_max finite and > 0' can shrink to 'cl_max != 0': a negative or infinite C_L,max then yields a negative or infinite level and not_converged or a number instead of invalid_input.
- **Evidence:** x = break_x(cl_max=0.0) ... assert raised.value.category is ErrorCategory.INVALID_INPUT
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P2-M23:** in `aero_kernel/formulas/stall_break.py` line 95: 'not (isfinite(cl_max) and cl_max > 0.0)' -> 'cl_max == 0.0'. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, parametrise the existing test over cl_max in (0.0, -1.19, math.inf, math.nan): each raises FormulaError with category INVALID_INPUT and parameter == 'cl_max', and stub.sweep_calls == [].

## P2-F06 · medium · over_mocked

- **Test file:** `aero_kernel/tests/test_minimum_drag_speed_engine.py` · existing test `test_level_flight_best_glide_from_the_shipped_canon` (line 42)
- **Production:** `aero_kernel/formulas/minimum_drag_speed.py:33-43`
- **Gap:** For minimum-drag-speed, minimum-sink-speed and zero-lift-angle the fast 'hand values' are the stub's own closed form recomputed in the test (stall_stubs.consistent_glide / consistent_min_sink / stub_zero_lift). They pin bindings, units and call counts, not the optimum; two tests per file (mass scaling, V_mp = V_md/3^(1/4)) assert only the stub. The kernel rule 'every formula: a unit test against a hand-computed value' is met for these formulas only in the aero tier, outside this package.
- **Evidence:** V_MD = math.sqrt(2 * MASS * 9.80665 / (RHO * 0.28)) * (K / CD0) ** 0.25  -- stub: 'v_md = math.sqrt(2.0 * n_load * mass * gravity / (air.density * area)) * (K / CD0) ** 0.25'
- **Status:** READ_ONLY
- **Test to write:** Fast, test_solvers_opti_glide.py / test_solvers_opti_min_sink.py level (worker with a fake model function CL = a*alpha, CD = CD0 + k CL^2, CD0 = 0.03, k = 0.05, S = 0.28 m^2, m = 1.5 kg, rho = 1.225): the worker's optimum must be V_md = sqrt(2 m g/(rho S)) (k/CD0)^(1/4) = 10.529 m/s, CL_md = 0.7746, E_max = 12.910, and V_mp = V_md/3^(1/4), CL_mp = 1.3416, rel 1e-4. If such tests already exist there, rename the engine tests here to say 'plumbing' and drop the two stub-only tests.

## P1-F14 · low · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_neutral_point.py` · no test exists
- **Production:** `aero_kernel/formulas/static_margin.py:25`
- **Gap:** static-margin has no dedicated test file and no direct formula test with a literal hand value; it is pinned only through engine tests of the neutral point, with expected values written as the production expression over fixture constants, and only for a CG ahead of the neutral point.
- **Evidence:** `"neutral-point=avl": (X_NP_AVL - CG) / C_MAC,` (test_neutral_point.py:167 ff.); the sign flip P1-M11 is killed by test_cg_for_target_margin.py:62.
- **Status:** READ_ONLY
- **Acceptance mutation P1-M11:** in `aero_kernel/formulas/static_margin.py` line 25: `x_np - x_cg` -> `x_cg - x_np`. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, new test_static_margin.py: static_margin(x from inputs_from_model: neutral-point 0.14 m, centre-of-gravity-measured 0.12 m, mean-aerodynamic-chord 0.20 m) == 0.10; with CG 0.16 m == -0.10 (unstable is a number, no error, A10); result keys == {'sm'}.

## P2-F07 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_butterfly_approach.py` · existing test `test_an_approach_speed_at_or_below_the_landing_stall_speed_has_the_largest_mix_zero` (line 253)
- **Production:** `aero_kernel/formulas/butterfly_approach.py:91`
- **Gap:** At V_app exactly equal to the landing stall speed the formula must take the 'no glide' path (empty gamma_curve); with '<=' instead of '<' it reads eleven glides at the stall speed and still returns s_max = 0.
- **Evidence:** out = await run(CrowStub(), v_app=v_stall_landing()); assert out["s_max"] == 0.0
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P2-M07:** in `aero_kernel/formulas/butterfly_approach.py` line 91: speed < v_app -> speed <= v_app in _crossing. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Same test: also assert out['gamma_curve'].x == () and stub.glide_speeds == [].

## P2-F08 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_stall_break.py` · existing test `test_a_half_step_sweep_that_agrees_within_one_step_is_silent` (line 148)
- **Production:** `aero_kernel/formulas/stall_break.py:136`
- **Gap:** The resolution tolerance is bracketed only by shifts of 0.2 and 0.4 deg: comparing against 0.375 deg instead of 0.25 deg passes (the constant itself is asserted, its use is not).
- **Evidence:** stub.sweep_answer = lambda alphas: lift_curve_at((ALPHA_S + 0.2, CL_MAX), True, alphas) ... assert context.warnings == ()
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P2-M10:** in `aero_kernel/formulas/stall_break.py` line 136: > RESOLUTION_TOLERANCE_DEG -> > 1.5 * RESOLUTION_TOLERANCE_DEG. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast: parametrise the shift over (0.24, False) and (0.26, True) for 'warning emitted'; the stub's crossing moves by exactly the shift (slope 0.2/deg on both sweeps).

## P2-F09 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_stall_break.py` · existing test `test_a_sample_exactly_on_the_level_is_the_crossing` (line 64)
- **Production:** `aero_kernel/solvers/stall_math.py:81-83`
- **Gap:** Two edges of first_crossing_below are not discriminated: '<= level' vs '< level' gives the same 11.0 on the test's series, and the fallback share 1.0 for a non-falling bracket (start sample already at or below the level) is never executed with an assert.
- **Evidence:** assert close(first_crossing_below([10.0, 11.0, 12.0], [1.0, 0.9, 0.8], 10.0, 0.9), 11.0, 1e-12)
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P2-M20:** in `aero_kernel/solvers/stall_math.py` line 81: cl[k] <= level -> cl[k] < level. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast: first_crossing_below([10, 11, 12], [1.0, 0.9, 0.95], 10.0, 0.9) == 11.0 (the on-level sample is last below; '<' would return None), and first_crossing_below([10, 11], [0.8, 0.85], 10.0, 0.9) == 11.0 (start already below the level: the next sample is the crossing, share 1.0), or decide that this case is an error and test that.

## P2-F10 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_butterfly_approach.py` · existing test `test_the_forwarded_caveats_are_the_reference_solves_and_the_worst_case_of_the_sweep` (line 372)
- **Production:** `aero_kernel/formulas/butterfly_approach.py:129`
- **Gap:** The worst-case fit-range warning must carry the lowest mean confidence per device; taking the highest passes, because only 'flaps' and 'min_confidence' are asserted.
- **Evidence:** assert flaps == {"F": 60.0, "A": -40.0}; assert fit.detail["min_confidence"] == pytest.approx(0.4)
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P2-M18:** in `aero_kernel/formulas/butterfly_approach.py` line 129: per-device worst confidence min(...) -> max(...). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Same test: assert fit.detail['devices'] == [{'wing': 'Main', 'device': 'F', 'mean_confidence': pytest.approx(0.4)}] (Noisy gives 1 - flap/100, lowest at the 60 deg flap).

## P2-F11 · low · over_mocked

- **Test file:** `aero_kernel/tests/test_hinge_moment_engine.py` · existing test `test_each_role_is_one_adapter_call_at_the_lift_of_the_operating_point` (line 101)
- **Production:** `aero_kernel/formulas/control_surface_hinge_moments.py:60`
- **Gap:** The air state handed to the hinge adapter (it drives the Reynolds warnings the notice refers to) is not recorded by StubAvl.hinge_moments, so a wrong density or viscosity passes. The per-surface numbers of the engine tests are the stub's 1e-3*sign*delta: they prove the union and the pass-through, not q S c Chinge or the sign convention (adapter tests outside P2).
- **Evidence:** self.hinge_calls.append({"airplane": airplane, "cl": cl, "role": role, "delta": delta_deg, "speed": speed_ms})
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P2-M21:** in `aero_kernel/formulas/control_surface_hinge_moments.py` line 60: air=air_state(x) -> air state with doubled density. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** np_builders.StubAvl.hinge_moments: record 'air'; in the test assert every call has air.density == 1.225 and the stub atmosphere's viscosity and speed of sound.

## P2-F12 · low · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_stall_speed_engine.py` · existing test `test_the_inverted_application_solves_at_minus_one_g` (line 176)
- **Production:** `aero_kernel/formulas/stall_speed.py:161-187`
- **Gap:** Static-scan check: alpha_range_past_inverted_stall, optimum_at_first_cl_trough, approach_speed_positive and air_density_positive ARE tested on both sides, as imported functions (not string literals). What is missing is the engine side: no test makes the inverted application, or butterfly with v_app <= 0, or spanwise-loads with rho <= 0, end in postcondition_violated / precondition_violated, so the application scoping ['inverted'] of the two postconditions is unpinned.
- **Evidence:** assert only.status is QuantityStatus.OK; assert only.value == INVERTED_TROUGH[1]; assert opti.calls[0][3] == -1.0
- **Status:** READ_ONLY
- **Test to write:** Fast, test_stall_speed_engine.py: StubOpti(answer=StallSolution(v_s=sqrt(2*1.5*9.80665/(1.225*0.28*0.7)), cl_max=-0.7, alpha_s=-15.0, polar=<cl falling monotonically to the first sample at -15 deg>)) requested as 'inverted-max-lift-coefficient': status ERROR, code postcondition_violated, detail postcondition in {'alpha_range_past_inverted_stall', 'optimum_at_first_cl_trough'}; and the same answer requested as 'stall-speed' must NOT report an inverted postcondition.

## P2-F13 · low · over_mocked

- **Test file:** `aero_kernel/tests/test_roll_rate_engine.py` · existing test `test_a_negative_command_gives_the_mirrored_roll_in_both_worlds` (line 148)
- **Production:** `aero_kernel/formulas/roll_rate.py:105-115`
- **Gap:** Sign conventions that live in adapters are invisible in this package's fast tier: both roll stubs return copysign(rate, delta), the AVL neutral point is the canned 0.14, C_l,beta is the canned -0.05. A sign flip inside an adapter passes every P2 fast file; the formula-level signs are pinned.
- **Evidence:** return SteadyRoll(p_rad_s=math.copysign(self.roll_rad_s, delta_a_deg), ...)  /  return AvlRoll(p_hat=math.copysign(self.p_hat, delta_a_deg), ...)
- **Status:** READ_ONLY
- **Test to write:** Aero, one test per convention on the aileron trainer: delta_a = +10 deg gives p > 0 in both worlds (OptiAdapter.steady_roll and AvlAdapter.steady_roll); a wing with 5 deg dihedral gives C_l,beta < 0 from AvlAdapter.lateral_derivatives. Confirm they exist in test_solvers_opti_roll_real.py / test_solvers_avl_roll_real.py / test_solvers_avl_lateral.py before adding.

## P2-F14 · low · golden_without_independent_check

- **Test file:** `aero_kernel/tests/test_zero_lift_angle_real.py` · existing test `test_bryan_zero_lift_angle_and_slope_at_both_optima_through_compute` (line 105)
- **Production:** `aero_kernel/formulas/zero_lift_angle.py:34`
- **Gap:** The six GOLDEN values (rel 1e-6) are regression snapshots, re-recorded three times (#1346, #1355, #1358) with the old value in a comment; the file says so. The independent content of the file is the first test (residual and finite difference) and the third (L = CL q S against a one-point sweep).
- **Evidence:** GOLDEN = {"minimum-drag-speed": 7.711509030755531,  # #1358: was 7.664926694158355 ...}; assert close(quantities[slug].value, golden, 1e-6)
- **Status:** READ_ONLY
- **Test to write:** No new test needed; keep the goldens labelled as regression. Optional independent anchor, aero: for a symmetric NACA 0012 untwisted wing alpha_0 = 0 deg within 0.05 deg at 10 m/s.

## P2-F15 · low · mirror_or_tautology

- **Test file:** `aero_kernel/tests/test_stall_wing_loading_limit.py` · existing test `test_bryans_limit_through_the_public_compute_closes_on_its_own_inputs` (line 82)
- **Production:** `aero_kernel/formulas/stall_wing_loading_limit.py:29`
- **Gap:** The aero test recomputes the limit with the production expression from rho and C_L,max of the same result: it proves one producer per input, not the formula (the fast hand value 42.24 does that).
- **Evidence:** assert close(quantities[QUANTITY].value, 0.5 * rho * 6.0**2 * cl_max, 1e-12)
- **Status:** READ_ONLY
- **Test to write:** None required; the fast test test_the_limit_is_half_rho_v_squared_cl_max is the independent one.

## P2-F16 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_aileron_deflection_required_engine.py` · existing test `test_the_approach_application_uses_the_approach_speed` (line 235)
- **Production:** `aero_kernel/formulas/aileron_deflection_required.py:232`
- **Gap:** The approach application is pinned only by 'the speed is not V_cruise': a wrong approach speed or the clean airplane instead of the landing configuration passes.
- **Evidence:** speeds = {call[4] for call in opti.roll_calls}; assert len(speeds) == 1; assert V_CRUISE not in speeds
- **Status:** READ_ONLY
- **Test to write:** Fast: assert the one speed equals v_app(plane()) = 1.3*sqrt(2*0.15*9.80665/(1.225*0.16*1.19)) (rel 1e-12, helper in test_roll_rate_engine.py), and with flap_and_aileron() and flap-deflection-landing = 30 that every roll call's airplane has deflections {'flap': 30.0, 'aileron': 0.0}.
