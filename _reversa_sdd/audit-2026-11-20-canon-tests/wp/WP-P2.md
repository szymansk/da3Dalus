# WP-P2 — Aerodynamics and stability formulas

Self-contained brief for one implementer subagent. Base commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

Every finding below was checked by an independent verifier on 2026-11-21 (`../rework/`). The line **Verified** says how. Where **Correction** appears, it overrides the text under **Test to write**.

- **Production code under test:** aero_kernel/formulas/butterfly_approach.py, stall_break.py, solvers/stall_math.py
- **Requirement sources:** canon entries, ADR 0020, ARCHITECTURE §8.13
- **Test files you may change:** `aero_kernel/tests/test_aileron_deflection_required_engine.py`, `aero_kernel/tests/test_butterfly_approach.py`, `aero_kernel/tests/test_hinge_moment_engine.py`, `aero_kernel/tests/test_minimum_drag_speed_engine.py`, `aero_kernel/tests/test_neutral_point.py`, `aero_kernel/tests/test_stall_break.py`, `aero_kernel/tests/test_stall_math.py`, `aero_kernel/tests/test_stall_speed_engine.py`, `aero_kernel/tests/test_v_tail_neutral_point.py`
- **Findings to work on:** 14 (2 high, 2 medium, 10 low)

## P2-F01 · high · untested_warning

- **Test file:** `aero_kernel/tests/test_butterfly_approach.py` · existing test `test_the_forwarded_caveats_are_the_reference_solves_and_the_worst_case_of_the_sweep` (line 372)
- **Production:** `aero_kernel/formulas/butterfly_approach.py:152-157`
- **Gap:** butterfly-approach can drop every caveat of its reference solves (Reynolds regime, drag messages of the landing stall and of the closing sample) and no test fails; ADR 0020 requires them declared. The early-return path (s_max = 0) forwards nothing testable either.
- **Evidence:** assert len(regime) <= 2  # the landing stall and the bracketing sample, not one per mix
- **Verified:** CONFIRMED (MUTATION_RERUN). With the mutation no caveat of a reference solve (Reynolds regime, drag messages) is forwarded and all 553 fast tests stay green. The only assert on these warnings is an upper bound that an empty list satisfies: `assert len(regime) <= 2  # the landing stall and the bracketing sample, not one per mix`. The early-return test (`test_an_approach_speed_below_the_landing_stall_gives_zero_without_reading_a_glide`) asserts no warning at all. The only aero test of the formula (test_butterfly_approach_fleet.py) asserts `quantity.status is QuantityStatus.OK` and values, never warnings.
- **Acceptance mutation:** `git apply rework/patches/WP-P2/P2-F01.patch` (from the audit folder; aero_kernel/formulas/butterfly_approach.py:155  `if warning.code != FIT_RANGE and key not in seen:` -> `if False and warning.code != FIT_RANGE and key not in seen:`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_butterfly_approach.py, with the existing Noisy stub (its stall emits reynolds_bubble_sensitive with message 'Re <v_s*1e4>' per mix) and default inputs (v_app = 1.05 V_S0(0), crossing between mix 0.6 and 0.7): assert the forwarded regime messages are exactly {f'Re {V_S0(0)*1e4:.0f}', f'Re {V_S0(0.7)*1e4:.0f}'} with V_S0(s) = sqrt(2 m g/(rho 0.28 (1.25-0.18 s))). Second test with v_app = 0.9 V_S0(0) (s_max = 0 path): exactly one regime warning, that of the landing stall, plus the fit-range warning.

## P2-F04 · high · weak_assertion

- **Test file:** `aero_kernel/tests/test_butterfly_approach.py` · existing test `test_the_validity_follows_the_largest_deflection_not_full_crow` (line 386)
- **Production:** `aero_kernel/formulas/butterfly_approach.py:290-291`
- **Gap:** The test cannot tell 'mix with the largest deflection' from 'always full crow': at s = 1 the raised aileron is carried as a flap at -40 deg, above the 30 deg limit, so the declaration appears either way and only its presence is asserted.
- **Evidence:** assert "flap_deflection_beyond_validity" in {w.code for w in context_.warnings}
- **Verified:** CONFIRMED (MUTATION_RERUN). Always judging full crow leaves all 599 fast tests green. The test named for this rule asserts presence only: `assert "flap_deflection_beyond_validity" in {w.code for w in context_.warnings}`; in its inputs (delta_a_crow default 40) full crow carries the aileron at -40 deg, above the 30 deg limit, so the warning appears either way. Observable difference shown by a probe on the copy with delta_f_ldg=60, delta_f_crow=20, delta_a_crow=10: original warns `{'limit_deg': 30.0, 'flaps': [{'wing': 'Main', 'device': 'device 0', 'deflection_deg': 60.0}]}`, mutant emits no warning.
- **Acceptance mutation:** `git apply rework/patches/WP-P2/P2-F04.patch` (from the audit folder; aero_kernel/formulas/butterfly_approach.py:290  `worst = max(range(len(configurations)), key=lambda k: _largest_deflection(configurations[k]))` -> `worst = len(configurations) - 1`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, same file: delta_f_ldg = 60, delta_f_crow = 20, delta_a_crow = 10 (full crow: flap 20, aileron -10, both below 30). Assert the single flap_deflection_beyond_validity warning has detail['flaps'] == [{'wing': 'Main', 'device': 'device 0', 'deflection_deg': 60.0}] (the landing flap at s = 0). Add a CrowStub variant whose diagnostics differ per mix and assert flap_confidence_low carries the confidence of mix 0.
- **Correction:** (no) The expected detail is right (verified: [{'wing': 'Main', 'device': 'device 0', 'deflection_deg': 60.0}]) and it would fail under the mutation, but as written the call raises: with delta_f_ldg=60, delta_f_crow=20, delta_a_crow=10 and the default v_app = 1.05*V_S0(30 deg flap) the stall speed never reaches v_app, so butterfly_approach raises FormulaError unsupported_configuration (fully mixable). The warning is on the context before the raise, so either wrap the call in pytest.raises(FormulaError) or pass v_app = 1.02 * V_S0 of the 60 deg landing flap (C_L 1.31 -> 1.17 over the mix, V_S0 rises by 5.8 %). The second half (per-mix diagnostics, flap_confidence_low of mix 0) needs a stub that sets StallSolution.diagnostics; not researched here.

## P2-F02 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_stall_math.py` · no test exists
- **Production:** `aero_kernel/solvers/stall_math.py:52-53`
- **Gap:** first_extremum_from_zero may scan a peak from the first sample (-15 deg) instead of from alpha = 0 (K32): a local maximum at negative alpha (lift recovering past the negative stall) would become C_L,max. No fast test calls the function with a maximum below zero; the upward start is only implied by aero goldens.
- **Evidence:** test_stall_math.py imports only first_extremum: 'from aero_kernel.solvers.stall_math import first_extremum'; production: 'start = min(range(len(alphas_deg)), key=lambda k: abs(alphas_deg[k]))'
- **Verified:** CONFIRMED (MUTATION_RERUN). The upright scan from the first sample instead of from alpha = 0 leaves 1986 fast tests green. No fast test calls first_extremum_from_zero directly: test_stall_math.py has `from aero_kernel.solvers.stall_math import first_extremum` only; the single direct call is in the aero tier (test_stall_speed_fleet.py:189, upright=False). Not equivalent: for alphas (-4..4) and cl (-0.4,-0.3,-0.5,-0.2,0.0,0.3,0.6,0.5,0.4) the original returns index 6, the mutant index 1.
- **Verifier's note:** The aero candidates fail only if a real polar has a local C_L maximum between -15 deg and 0 (lift recovering past the negative stall); I could not establish that by reading, so they are the tests that would notice, not tests known to fail.
- **Acceptance mutation:** `git apply rework/patches/WP-P2/P2-F02.patch` (from the audit folder; aero_kernel/solvers/stall_math.py:53  `scan = list(range(start, len(alphas_deg))) if upright` -> `scan = list(range(0, len(alphas_deg))) if upright`). Today every fast test stays green; after your change at least one fast test must fail under it. The aero tier catches it (aero_kernel/tests/test_stall_speed_fleet.py::test_bryan_regression_goldens_with_the_xlarge_model); the new test belongs in the fast tier.
- **Test to write:** Fast, test_stall_math.py: alphas = (-4,-3,-2,-1,0,1,2,3,4), cl = (-0.4,-0.3,-0.5,-0.2,0.0,0.3,0.6,0.5,0.4): a local maximum at -3 deg and the first peak from zero at +2 deg. Assert first_extremum_from_zero(alphas, cl, upright=True) == 6 and, mirrored series, upright=False gives the trough below zero, not the one above; also an alpha grid without 0.0 (nearest sample) and an empty series -> None.

## P2-F05 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_stall_break.py` · existing test `test_a_non_positive_peak_is_invalid_input` (line 224)
- **Production:** `aero_kernel/formulas/stall_break.py:95`
- **Gap:** The guard 'cl_max finite and > 0' can shrink to 'cl_max != 0': a negative or infinite C_L,max then yields a negative or infinite level and not_converged or a number instead of invalid_input.
- **Evidence:** x = break_x(cl_max=0.0) ... assert raised.value.category is ErrorCategory.INVALID_INPUT
- **Verified:** CONFIRMED (MUTATION_RERUN). The guard shrunk to `cl_max == 0.0` leaves 599 fast tests green; the only test of the guard uses the one value both versions reject: `x = break_x(cl_max=0.0)`. Probe on the copy: original raises invalid_input for 0.0, -1.19, inf, nan; mutant gives not_converged for -1.19, returns `{'alpha_break': -inf, 'width': -inf}` for inf and a bare ValueError for nan.
- **Acceptance mutation:** `git apply rework/patches/WP-P2/P2-F05.patch` (from the audit folder; aero_kernel/formulas/stall_break.py:95  `if not (math.isfinite(cl_max) and cl_max > 0.0):` -> `if cl_max == 0.0:`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, parametrise the existing test over cl_max in (0.0, -1.19, math.inf, math.nan): each raises FormulaError with category INVALID_INPUT and parameter == 'cl_max', and stub.sweep_calls == [].

## P1-F14 · low · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_neutral_point.py` · no test exists
- **Production:** `aero_kernel/formulas/static_margin.py:25`
- **Gap:** static-margin has no dedicated test file and no direct formula test with a literal hand value; it is pinned only through engine tests of the neutral point, with expected values written as the production expression over fixture constants, and only for a CG ahead of the neutral point.
- **Evidence:** `"neutral-point=avl": (X_NP_AVL - CG) / C_MAC,` (test_neutral_point.py:167 ff.); the sign flip P1-M11 is killed by test_cg_for_target_margin.py:62.
- **Verified:** CONFIRMED_BY_READING (READING). No test file for static-margin exists (aero_kernel/tests has only test_cg_for_target_margin.py and test_speed_from_stall_margin.py with 'margin' in the name) and no test calls static_margin directly. The engine test writes the expectation as the production expression over fixture constants: `"neutral-point=textbook": (X_NP_TEXTBOOK - CG) / C_MAC,` (test_neutral_point.py:170). The sign is pinned by test_cg_for_target_margin.py:62 `assert close(margin.interval.worlds[key], SM_TARGET, 1e-9), key`, as the finding says.
- **Verifier's note:** Kept because the static margin is the central flyability number and the kernel rule asks for one hand value per formula; cost is one small test. The quote in the finding names the AVL world; at 72c4b5c6 the dict at line 170 shows the textbook world first, same pattern.
- **Test to write:** Fast, new test_static_margin.py: static_margin(x from inputs_from_model: neutral-point 0.14 m, centre-of-gravity-measured 0.12 m, mean-aerodynamic-chord 0.20 m) == 0.10; with CG 0.16 m == -0.10 (unstable is a number, no error, A10); result keys == {'sm'}.

## P2-F03 · low · mirror_or_tautology

- **Test file:** `aero_kernel/tests/test_v_tail_neutral_point.py` · existing test `test_the_horizontal_and_fin_shares_add_up_to_the_true_area_for_every_angle` (line 157)
- **Production:** `aero_kernel/solvers/asb_airplane.py:357-372`
- **Gap:** Four tests of this file (lines 68, 139, 157, 168; 12 parametrised cases) assert properties of the test stand-in aero_kernel/tests/asb_fakes.py, not of production. The 'trace test' is a tautology: the stand-in defines the fin share as true_area - effective. Dropping cos^2 in production _v_tail_surface leaves all P2 files green; it is caught only by test_solvers_asb_airplane.py.
- **Evidence:** shares = stand_in_horizontal_tail_area(wing) + stand_in_fin_area(wing); assert close(shares, true_area, 1e-12)  -- asb_fakes: 'return mirrored * (true_area - effective)'
- **Verified:** CONFIRMED_BY_READING (MUTATION_RERUN). The test-quality claim holds by reading: the trace test sums two stand-in functions (`shares = stand_in_horizontal_tail_area(wing) + stand_in_fin_area(wing)`) and the stand-in defines the fin share as the complement (asb_fakes.py:263 `return mirrored * (true_area - effective)`), so the sum is the true area by construction; test_v_tail_neutral_point.py never imports aero_kernel.solvers.asb_airplane. The production part is not a gap: the mutation is killed by three tests of test_solvers_asb_airplane.py, e.g. `assert near(found.area, 1.0)` (line 428, got 2.0), line 437 and `with pytest.raises(FormulaError, match="no horizontal planform")` (DID NOT RAISE), exactly as the finding itself says.
- **Verifier's note:** In the wide file set two tests of test_engine.py fail with and without the mutation (test_every_debug_line_of_a_node_carries_formula_and_application, test_one_info_line_per_call_and_debug_per_node_all_with_the_same_call_id); test_engine.py alone is green (120 passed), so this is a test-order effect of the log capture, unrelated to this finding. The narrow set above has a clean baseline.
- **Acceptance mutation:** `git apply rework/patches/WP-P2/P2-F03.patch` (from the audit folder; aero_kernel/solvers/asb_airplane.py:372  `effective = sum(area * cos2 for area, _span, cos2 in panels)` -> `effective = sum(area for area, _span, cos2 in panels)`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Move the angle sweep onto production: fast, test_solvers_asb_airplane.py (fake aerosandbox), for rise in (0, 0.05, 0.2, 0.5, 1.5) m on a 0.2 m half span, chord 0.1 m: asb_airplane.horizontal_tail_area == 2*0.1*L*(0.2/L)^2 and fin_area == 2*0.1*L*(rise/L)^2 with L = hypot(0.2, rise), each against its own closed form (not their sum), tolerance 1e-12. Rename or delete the stand-in tests as helper self-checks.
- **Correction:** (no) The recommended sweep calls horizontal_tail_area and fin_area, but the acceptance mutation is in _v_tail_surface (the surface_properties route): under it the existing horizontal_tail_area tests stay green (test_a_v_tail_counts_the_horizontal_share_cos_squared_of_the_panel_angle did not fail) and only the three surface_properties tests fail. A production angle sweep that should see this line must go through surface_properties(document, 'VTail').area. As written it also breaks at rise 0: fin_area raises FormulaError('no fin area') for a flat V-tail (test_solvers_asb_airplane.py:356-359). The existing tests of that file already pin cos^2 and sin^2 at 45 deg, per panel, and their sum.

## P2-F06 · low · over_mocked

- **Test file:** `aero_kernel/tests/test_minimum_drag_speed_engine.py` · existing test `test_level_flight_best_glide_from_the_shipped_canon` (line 42)
- **Production:** `aero_kernel/formulas/minimum_drag_speed.py:33-43`
- **Gap:** For minimum-drag-speed, minimum-sink-speed and zero-lift-angle the fast 'hand values' are the stub's own closed form recomputed in the test (stall_stubs.consistent_glide / consistent_min_sink / stub_zero_lift). They pin bindings, units and call counts, not the optimum; two tests per file (mass scaling, V_mp = V_md/3^(1/4)) assert only the stub. The kernel rule 'every formula: a unit test against a hand-computed value' is met for these formulas only in the aero tier, outside this package.
- **Evidence:** V_MD = math.sqrt(2 * MASS * 9.80665 / (RHO * 0.28)) * (K / CD0) ** 0.25  -- stub: 'v_md = math.sqrt(2.0 * n_load * mass * gravity / (air.density * area)) * (K / CD0) ** 0.25'
- **Verified:** CONFIRMED_BY_READING (READING). The test's expectation is the stub's expression: test_minimum_drag_speed_engine.py:27 `V_MD = math.sqrt(2 * MASS * 9.80665 / (RHO * 0.28)) * (K / CD0) ** 0.25` against stall_stubs.py:106 `v_md = math.sqrt(2.0 * n_load * mass * gravity / (air.density * area)) * (K / CD0) ** 0.25`; the mass-scaling test and test_the_minimum_sink_speed_is_the_minimum_drag_speed_over_the_fourth_root_of_three exercise only that stub. The production formula (minimum_drag_speed.py:33-43) is a pass-through of ctx.solvers.opti.best_glide, which these tests do pin (one call, arguments, four outputs, unit, errors). The optimum itself is tested with closed-form answers in the aero tier: test_solvers_opti_glide_real.py::test_a_parabolic_polar_gives_the_closed_form_answers and the same test in test_solvers_opti_min_sink_real.py.
- **Test to write:** Fast, test_solvers_opti_glide.py / test_solvers_opti_min_sink.py level (worker with a fake model function CL = a*alpha, CD = CD0 + k CL^2, CD0 = 0.03, k = 0.05, S = 0.28 m^2, m = 1.5 kg, rho = 1.225): the worker's optimum must be V_md = sqrt(2 m g/(rho S)) (k/CD0)^(1/4) = 10.529 m/s, CL_md = 0.7746, E_max = 12.910, and V_mp = V_md/3^(1/4), CL_mp = 1.3416, rel 1e-4. If such tests already exist there, rename the engine tests here to say 'plumbing' and drop the two stub-only tests.
- **Correction:** (no) (1) The fast worker tests fake AeroSandbox with a FakeOpti that 'returns' a given optimum (test_solvers_opti_glide.py:160 ff.), so a fast test cannot make the worker find V_md; the closed-form worker tests asked for already exist in the aero tier (see evidence). (2) The literal 10.529 m/s is wrong for the stated constants: sqrt(2*1.5*9.80665/(1.225*0.28)) = 9.26134 and * (0.05/0.03)^0.25 = 10.5229 m/s (5.8e-4 off, outside the stated rel 1e-4); the comment of test_minimum_drag_speed_engine.py:25 has the same 9.2666 * 1.13622 = 10.529 (its assert uses the expression, so it is unaffected). CL_md = 0.7746, E_max = 12.910, CL_mp = 1.3416 are right. (3) The fallback 'drop the two stub-only tests' is a deletion and is not proposed here; renaming them as plumbing/stub checks is enough.

## P2-F07 · low · missing_edge_case · do together with P2-F01

- **Test file:** `aero_kernel/tests/test_butterfly_approach.py` · existing test `test_an_approach_speed_at_or_below_the_landing_stall_speed_has_the_largest_mix_zero` (line 253)
- **Production:** `aero_kernel/formulas/butterfly_approach.py:91`
- **Gap:** At V_app exactly equal to the landing stall speed the formula must take the 'no glide' path (empty gamma_curve); with '<=' instead of '<' it reads eleven glides at the stall speed and still returns s_max = 0.
- **Evidence:** out = await run(CrowStub(), v_app=v_stall_landing()); assert out["s_max"] == 0.0
- **Verified:** CONFIRMED_BY_READING (READING). The test asserts one value: `out = await run(CrowStub(), v_app=v_stall_landing())` / `assert out["s_max"] == 0.0`. With `speed <= v_app` in _crossing (butterfly_approach.py:91) sample 0 is skipped, sample 1 closes with share (v_app - speeds[0]) / (speeds[1] - speeds[0]) = 0, so s_max is still 0.0 but found[1] == 1, the early return is not taken and eleven glides are read. The only test of the empty glide curve uses 0.9 V_S0 (`assert stub.glide_speeds == []`, line 337), where both comparisons agree.
- **Verifier's note:** The boundary is reachable: an approach-speed margin of exactly 1.0 gives V_app == V_S0(0).
- **Test to write:** Same test: also assert out['gamma_curve'].x == () and stub.glide_speeds == [].

## P2-F08 · low · missing_edge_case · do together with P2-F05

- **Test file:** `aero_kernel/tests/test_stall_break.py` · existing test `test_a_half_step_sweep_that_agrees_within_one_step_is_silent` (line 148)
- **Production:** `aero_kernel/formulas/stall_break.py:136`
- **Gap:** The resolution tolerance is bracketed only by shifts of 0.2 and 0.4 deg: comparing against 0.375 deg instead of 0.25 deg passes (the constant itself is asserted, its use is not).
- **Evidence:** stub.sweep_answer = lambda alphas: lift_curve_at((ALPHA_S + 0.2, CL_MAX), True, alphas) ... assert context.warnings == ()
- **Verified:** CONFIRMED_BY_READING (READING). The silent case shifts the finer sweep by 0.2 deg (`stub.sweep_answer = lambda alphas: lift_curve_at((ALPHA_S + 0.2, CL_MAX), True, alphas)` ... `assert context.warnings == ()`), the warning case by 0.4 deg; the comparison at stall_break.py:136 is `if abs(refined - published) > RESOLUTION_TOLERANCE_DEG:`. Any threshold between 0.2 and 0.4 (e.g. 0.375) satisfies both; `assert RESOLUTION_TOLERANCE_DEG == ALPHA_STEP_DEG == 0.25` pins the constant, not its use.
- **Test to write:** Fast: parametrise the shift over (0.24, False) and (0.26, True) for 'warning emitted'; the stub's crossing moves by exactly the shift (slope 0.2/deg on both sweeps).

## P2-F09 · low · weak_assertion · do together with P2-F05

- **Test file:** `aero_kernel/tests/test_stall_break.py` · existing test `test_a_sample_exactly_on_the_level_is_the_crossing` (line 64)
- **Production:** `aero_kernel/solvers/stall_math.py:81-83`
- **Gap:** Two edges of first_crossing_below are not discriminated: '<= level' vs '< level' gives the same 11.0 on the test's series, and the fallback share 1.0 for a non-falling bracket (start sample already at or below the level) is never executed with an assert.
- **Evidence:** assert close(first_crossing_below([10.0, 11.0, 12.0], [1.0, 0.9, 0.8], 10.0, 0.9), 11.0, 1e-12)
- **Verified:** CONFIRMED_BY_READING (READING). `assert close(first_crossing_below([10.0, 11.0, 12.0], [1.0, 0.9, 0.8], 10.0, 0.9), 11.0, 1e-12)`: with `<` instead of `<=` (stall_math.py:81) the scan stops at 12 deg with before = 0.9, share = (0.9 - 0.9) / 0.1 = 0 and returns 11.0 as well. The fallback `share = ... if before > after else 1.0` (line 83) needs a start sample already at or below the level; none of the six helper tests has one (all start at C_L 1.0 above the level 0.9).
- **Test to write:** Fast: first_crossing_below([10, 11, 12], [1.0, 0.9, 0.95], 10.0, 0.9) == 11.0 (the on-level sample is last below; '<' would return None), and first_crossing_below([10, 11], [0.8, 0.85], 10.0, 0.9) == 11.0 (start already below the level: the next sample is the crossing, share 1.0), or decide that this case is an error and test that.

## P2-F10 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_butterfly_approach.py` · existing test `test_the_forwarded_caveats_are_the_reference_solves_and_the_worst_case_of_the_sweep` (line 372)
- **Production:** `aero_kernel/formulas/butterfly_approach.py:129`
- **Gap:** The worst-case fit-range warning must carry the lowest mean confidence per device; taking the highest passes, because only 'flaps' and 'min_confidence' are asserted.
- **Evidence:** assert flaps == {"F": 60.0, "A": -40.0}; assert fit.detail["min_confidence"] == pytest.approx(0.4)
- **Verified:** CONFIRMED_BY_READING (READING). The test reads two keys of the worst-case warning: `assert flaps == {"F": 60.0, "A": -40.0}` and `assert fit.detail["min_confidence"] == pytest.approx(0.4)`. detail['devices'] (butterfly_approach.py:125-129 and 136-139, `confidence[key] = min(float(mean), confidence.get(key, float(mean)))`) is never read by a test; min_confidence comes from the separate `lowest` list, so min -> max in line 129 changes only 'devices'.
- **Verifier's note:** Kept: the per-device confidence is the 'where and how much' of the warning the caller sees (#1342). Same test function as P2-F01, so it is one edit.
- **Test to write:** Same test: assert fit.detail['devices'] == [{'wing': 'Main', 'device': 'F', 'mean_confidence': pytest.approx(0.4)}] (Noisy gives 1 - flap/100, lowest at the 60 deg flap).

## P2-F11 · low · over_mocked

- **Test file:** `aero_kernel/tests/test_hinge_moment_engine.py` · existing test `test_each_role_is_one_adapter_call_at_the_lift_of_the_operating_point` (line 101)
- **Production:** `aero_kernel/formulas/control_surface_hinge_moments.py:60`
- **Gap:** The air state handed to the hinge adapter (it drives the Reynolds warnings the notice refers to) is not recorded by StubAvl.hinge_moments, so a wrong density or viscosity passes. The per-surface numbers of the engine tests are the stub's 1e-3*sign*delta: they prove the union and the pass-through, not q S c Chinge or the sign convention (adapter tests outside P2).
- **Evidence:** self.hinge_calls.append({"airplane": airplane, "cl": cl, "role": role, "delta": delta_deg, "speed": speed_ms})
- **Verified:** CONFIRMED_BY_READING (READING). The stub drops the air state: np_builders.py:132 `self.hinge_calls.append({"airplane": airplane, "cl": cl, "role": role, "delta": delta_deg, "speed": speed_ms})` while production passes `air=air_state(x)` (control_surface_hinge_moments.py:60); the test asserts cl and speed only (`assert all(c["speed"] == 20.0 for c in avl.hinge_calls)`). grep finds no assert on air or density in test_hinge_moment_engine.py or test_hinge_moment_graph.py.
- **Verifier's note:** Kept: the air state decides the Reynolds warnings of the surfaces that the hinge_moment_inviscid_estimate notice points the caller to. The second half of the claim (q S c Chinge and the sign live in adapter tests outside P2) is a statement about tier layout, not a gap.
- **Test to write:** np_builders.StubAvl.hinge_moments: record 'air'; in the test assert every call has air.density == 1.225 and the stub atmosphere's viscosity and speed of sound.

## P2-F12 · low · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_stall_speed_engine.py` · existing test `test_the_inverted_application_solves_at_minus_one_g` (line 176)
- **Production:** `aero_kernel/formulas/stall_speed.py:161-187`
- **Gap:** Static-scan check: alpha_range_past_inverted_stall, optimum_at_first_cl_trough, approach_speed_positive and air_density_positive ARE tested on both sides, as imported functions (not string literals). What is missing is the engine side: no test makes the inverted application, or butterfly with v_app <= 0, or spanwise-loads with rho <= 0, end in postcondition_violated / precondition_violated, so the application scoping ['inverted'] of the two postconditions is unpinned.
- **Evidence:** assert only.status is QuantityStatus.OK; assert only.value == INVERTED_TROUGH[1]; assert opti.calls[0][3] == -1.0
- **Verified:** CONFIRMED_BY_READING (READING). The four checks are called as functions on both sides (test_stall_speed_checks.py:124-142, test_butterfly_approach.py:262-268, test_spanwise_loads.py:103-113). Through the engine, the inverted application has one test and it is the good case: `assert only.status is QuantityStatus.OK` / `assert only.value == INVERTED_TROUGH[1]`. The engine refusals that exist name other checks: `assert quantity.error.detail == {"precondition": "crow_aileron_not_negative"}` (test_butterfly_approach.py:284), `{"precondition": "flight_speed_positive"}` (test_spanwise_loads.py:175), `{"postcondition": "cl_max_at_stall_reynolds_number"}` and optimum_at_first_cl_peak for stall-speed.
- **Verifier's note:** Kept: a boundary sample passed off as C_L,min is an error the caller must get (ADR 0020), and only the canon's application list makes the engine run these two checks.
- **Test to write:** Fast, test_stall_speed_engine.py: StubOpti(answer=StallSolution(v_s=sqrt(2*1.5*9.80665/(1.225*0.28*0.7)), cl_max=-0.7, alpha_s=-15.0, polar=<cl falling monotonically to the first sample at -15 deg>)) requested as 'inverted-max-lift-coefficient': status ERROR, code postcondition_violated, detail postcondition in {'alpha_range_past_inverted_stall', 'optimum_at_first_cl_trough'}; and the same answer requested as 'stall-speed' must NOT report an inverted postcondition.
- **Correction:** (unclear) The polar is described, not given, and the stub answer must pass the other postconditions of stall-speed (lift balance, C_L at alpha_S) so that one of the two inverted checks is the one reported; the implementer has to build that polar and may need to accept either of the two ids, as the recommendation already allows. The second assert (the same answer as 'stall-speed' reports no inverted postcondition) is the one that pins the scoping.

## P2-F16 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_aileron_deflection_required_engine.py` · existing test `test_the_approach_application_uses_the_approach_speed` (line 235)
- **Production:** `aero_kernel/formulas/aileron_deflection_required.py:232`
- **Gap:** The approach application is pinned only by 'the speed is not V_cruise': a wrong approach speed or the clean airplane instead of the landing configuration passes.
- **Evidence:** speeds = {call[4] for call in opti.roll_calls}; assert len(speeds) == 1; assert V_CRUISE not in speeds
- **Verified:** CONFIRMED_BY_READING (READING). The whole check of the approach application is `speeds = {call[4] for call in opti.roll_calls}` / `assert len(speeds) == 1` / `assert V_CRUISE not in speeds`: any single speed other than the cruise speed passes, and the airplane of the roll calls (call[0]) is not looked at.
- **Verifier's note:** Kept: the required aileron deflection at approach is a caller value that depends directly on this speed.
- **Test to write:** Fast: assert the one speed equals v_app(plane()) = 1.3*sqrt(2*0.15*9.80665/(1.225*0.16*1.19)) (rel 1e-12, helper in test_roll_rate_engine.py), and with flap_and_aileron() and flap-deflection-landing = 30 that every roll call's airplane has deflections {'flap': 30.0, 'aileron': 0.0}.
- **Correction:** (unclear) The speed half is ready: the helper v_app(plane()) exists in test_roll_rate_engine.py:63 with MASS 0.15, S_ref 0.16, C_L,max 1.19, factor 1.3 (= 4.617 m/s), and roll_calls records the speed at index 4. The landing-configuration half ({'flap': 30.0, 'aileron': 0.0} on every roll call) assumes the approach application binds the landing airplane; I did not verify that binding in the canon, the implementer must.

## Not part of this package's work

| Finding | State | Reason |
|---|---|---|
| P2-F13 | dropped | Dropped: the three conventions named in the claim are already pinned by aero tests; a stub is the right tool for the formula level. |
| P2-F14 | dropped | Dropped: the goldens are honestly labelled and the same file has independent checks (residual and finite difference, lift against a one-point sweep). |
| P2-F15 | dropped | Dropped: the aero test's job is one producer per input through the public compute, and it does that; nothing is at risk. |
