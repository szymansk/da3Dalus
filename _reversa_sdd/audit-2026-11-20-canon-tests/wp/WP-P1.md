# WP-P1 — Closed-form formulas: preconditions on both sides

Self-contained brief for one implementer subagent. Base commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

Every finding below was checked by an independent verifier on 2026-11-21 (`../rework/`). The line **Verified** says how. Where **Correction** appears, it overrides the text under **Test to write**.

- **Production code under test:** aero_kernel/formulas/ (parabolic polar, sink rate, spiral parameter, maneuvering speed)
- **Requirement sources:** canon entries, canon_model.json preconditions
- **Test files you may change:** `aero_kernel/tests/test_formulas_end_to_end.py`, `aero_kernel/tests/test_maneuvering_speed_engine.py`, `aero_kernel/tests/test_parabolic_closed_forms.py`, `aero_kernel/tests/test_parabolic_polar_fit.py`, `aero_kernel/tests/test_spiral_parameter.py`, `aero_kernel/tests/test_vertical_tail_volume.py`
- **Findings to work on:** 13 (1 high, 7 medium, 5 low)

## P1-F02 · high · missing_edge_case

- **Test file:** `aero_kernel/tests/test_parabolic_closed_forms.py` · existing test `test_sink_rate_precondition_refuses_a_lift_coefficient_at_or_below_zero` (line 217)
- **Production:** `aero_kernel/formulas/sink_rate.py:29`
- **Gap:** lift_coefficient_positive can reject every lift coefficient and no test fails: sink-rate has no 'held' case for C_L and is never requested through the engine in any tier, so a sink rate that is never computed would go unnoticed.
- **Evidence:** `assert lift_coefficient_positive(x).state == "violated"` for cl in [0.0, -0.2]; the held test exists only for drag_coefficient_positive (line 240).
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived: 627 + 56 fast tests green. `sink-rate` occurs in no test file besides test_parabolic_closed_forms.py (and formula_builders.py); the only assert on this check is `assert lift_coefficient_positive(x).state == "violated"`. Unmutated, evaluate() returns sink-rate ok = 2.0736946702938845 m/s for the stub parabola at 10 m/s, so the mutation removes a caller-visible value.
- **Acceptance mutation:** `git apply rework/patches/WP-P1/P1-F02.patch` (from the audit folder; aero_kernel/formulas/sink_rate.py:29  `if cl > 0.0:` -> `if False:`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast: (a) lift_coefficient_positive held for C_L = 0.5 and for 1e-12; (b) engine test: evaluate(shipped_build, m 1.5 kg, altitude 0, flight-speed 10 m/s, StubOpti parabola C_D0 0.03, k 0.05) requesting sink-rate, lift-coefficient, drag-coefficient-parabolic: assert sink-rate OK, unit m/s, value == V * (0.03 + 0.05 C_L^2)/C_L with C_L = m g/(0.5 rho V^2 S_ref) to 1e-9; (c) a negative load-factor (-1) must give error.code 'precondition_violated' with detail.precondition 'lift_coefficient_positive'.

## P1-F01 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_parabolic_closed_forms.py` · existing test `test_minimum_drag_speed_precondition_refuses_an_undefined_parabola` (line 153)
- **Production:** `aero_kernel/formulas/minimum_drag_speed_closed_form.py:24`
- **Gap:** The precondition parabola_defined of minimum-drag-speed-closed-form can be violated for every input (the probe quantity would never be produced) and the fast tier stays green: there is no 'held' case and no fast engine run of minimum-drag-speed-probe.
- **Evidence:** The only assert on the check: `assert v_md_parabola_defined(x).state == "violated"` (four violated cases, no held case).
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived: 627 + 56 fast tests green. No fast test asserts a held state and none requests minimum-drag-speed-probe through the engine (grep: only test_parabolic_polar_fit_fleet.py, aero, requests it). The only assert on the check is `assert v_md_parabola_defined(x).state == "violated"`. Unmutated, evaluate() with the stub parabola returns minimum-drag-speed-probe ok = 4.402051477464504 m/s, so the mutation turns a caller-visible value into an error.
- **Verifier's note:** Aero candidates fail at `assert all(q.status is QuantityStatus.OK for q in result.quantities), result` in the fleet file's run().
- **Acceptance mutation:** `git apply rework/patches/WP-P1/P1-F01.patch` (from the audit folder; aero_kernel/formulas/minimum_drag_speed_closed_form.py:24  `if all(value > 0.0 for value in values.values()):` -> `if False:`). Today every fast test stays green; after your change at least one fast test must fail under it. The aero tier catches it (aero_kernel/tests/test_parabolic_polar_fit_fleet.py::test_the_fit_and_its_probes_against_the_goldens[FleetMember.BRYAN]); the new test belongs in the fast tier.
- **Test to write:** Fast, test_parabolic_closed_forms.py: (a) v_md_parabola_defined(x).state == 'held' for W/S 30 N/m^2, rho 1.225, C_D0 0.03, k 0.05; (b) through evaluate() on the shipped build with StubOpti (stub parabola C_D0 0.03, k 0.05, like test_parabolic_polar_fit.run) request minimum-drag-speed-probe and assert status OK and value == sqrt(2 (m g/S_ref) / (rho sqrt(0.03/0.05))) to 1e-9; (c) with a falling polar (k < 0) assert error.code == 'upstream_failed' or 'precondition_violated' explicitly.

## P1-F03 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_parabolic_closed_forms.py` · existing test `test_max_lift_to_drag_precondition_refuses_an_undefined_parabola` (line 111)
- **Production:** `aero_kernel/formulas/max_lift_to_drag_parabolic.py:24`
- **Gap:** The aspect ratio can be dropped from parabola_defined of max-lift-to-drag-parabolic; with AR = 0 the formula then returns E_max,probe = 0.0 as a value (observed), a substitute instead of the declared error.
- **Evidence:** Parametrisation `[(0.8, 8.0, 0.0), (0.8, 8.0, -0.01), (0.0, 8.0, 0.03)]` has no case with ar <= 0 and none with e < 0.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived: 627 + 56 fast tests green. Observed at the check: (e 0.8, AR 0.0, C_D0 0.03) and (0.8, -8.0, 0.03) are 'violated' unmutated and 'held' mutated; the formula then returns {'e_max_probe': 0.0} for AR = 0 and raises ValueError (math domain error) for AR = -8. The parametrisation `[(0.8, 8.0, 0.0), (0.8, 8.0, -0.01), (0.0, 8.0, 0.03)]` has no AR <= 0 case.
- **Acceptance mutation:** `git apply rework/patches/WP-P1/P1-F03.patch` (from the audit folder; aero_kernel/formulas/max_lift_to_drag_parabolic.py:24  `if cd0 > 0.0 and e_osw > 0.0 and ar > 0.0:` -> `if cd0 > 0.0 and e_osw > 0.0:`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, same test: add (e 0.8, AR 0.0, C_D0 0.03), (0.8, -8.0, 0.03) and (-0.3, 8.0, 0.03) -> 'violated'; add a held case (0.8, 8.0, 0.03) and (1e-12, 1e-12, 1e-12).

## P1-F04 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_parabolic_polar_fit.py` · existing test `test_a_nonphysical_fit_stops_the_chain_at_the_induced_drag_factor` (line 340)
- **Production:** `aero_kernel/formulas/max_lift_to_drag_parabolic.py:24`
- **Gap:** For a negative fitted e the probe may fail with an internal ValueError (sqrt of a negative number) instead of precondition_violated, and induced-drag-factor may fail with any error: the chain test accepts every non-OK status.
- **Evidence:** `assert by_slug["induced-drag-factor"].status is QuantityStatus.ERROR` and `assert by_slug["max-lift-to-drag-probe"].status is not QuantityStatus.OK`
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived: 627 + 56 fast tests green. In the scenario of the cited chain test the probe error changes from (unsupported_configuration, 'precondition_violated', detail {'precondition': 'parabola_defined'}) to (internal, 'internal', 'Internal error (ValueError) while computing `max-lift-to-drag-probe`.'); the test only asserts `assert by_slug["max-lift-to-drag-probe"].status is not QuantityStatus.OK`.
- **Verifier's note:** The unit case (-0.3, 8.0, 0.03) recommended in P1-F03 kills the same mutation; the chain assertion of this finding is still the only one that pins the error code the caller gets.
- **Acceptance mutation:** `git apply rework/patches/WP-P1/P1-F04.patch` (from the audit folder; aero_kernel/formulas/max_lift_to_drag_parabolic.py:24  `e_osw > 0.0` -> `e_osw != 0.0`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, same test: assert induced-drag-factor.error.code == 'precondition_violated', category UNSUPPORTED_CONFIGURATION and detail['precondition'] == 'oswald_factor_positive'; assert max-lift-to-drag-probe.error.code == 'precondition_violated' with detail['precondition'] == 'parabola_defined' (it binds e, AR and C_D0 directly, not k).

## P1-F05 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_parabolic_closed_forms.py` · existing test `test_minimum_drag_speed_precondition_refuses_an_undefined_parabola` (line 153)
- **Production:** `aero_kernel/formulas/minimum_drag_speed_closed_form.py:24`
- **Gap:** The exact boundary k = 0 (division by zero in sqrt(C_D0/k)) and negative W/S, rho or C_D0 are not refused by any test: both relaxed checks pass the suite.
- **Evidence:** Cases: `(0.0, 1.225, 0.03, 0.05), (30.0, 0.0, 0.03, 0.05), (30.0, 1.225, 0.0, 0.05), (30.0, 1.225, 0.03, -0.05)`: k only negative, the other three only zero.
- **Verified:** CONFIRMED (NEW_MUTATION). One mutation that relaxes both parts of the claim (k = 0 held; negative W/S, rho, C_D0 held) survived: 627 + 56 fast tests green. Observed at the check: (30, 1.225, 0.03, 0.0), (-30, ...), (30, -1.225, ...), (30, 1.225, -0.03, 0.05) are 'violated' unmutated and 'held' mutated; the formula then raises ZeroDivisionError for k = 0 and ValueError for a single negative, and returns 7.951879096324973 for W/S and rho both negative. Tested cases: `(0.0, 1.225, 0.03, 0.05), (30.0, 0.0, 0.03, 0.05), (30.0, 1.225, 0.0, 0.05), (30.0, 1.225, 0.03, -0.05)`.
- **Acceptance mutation:** `git apply rework/patches/WP-P1/P1-F05.patch` (from the audit folder; aero_kernel/formulas/minimum_drag_speed_closed_form.py:24  `if all(value > 0.0 for value in values.values()):` -> `if values["k"] >= 0.0 and all(v != 0.0 for n, v in values.items() if n != "k"):`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, same parametrisation: add (30, 1.225, 0.03, 0.0), (-30, 1.225, 0.03, 0.05), (30, -1.225, 0.03, 0.05), (30, 1.225, -0.03, 0.05) -> 'violated' (P1-M04 covers the negatives).

## P1-F07 · medium · untested_error_path

- **Test file:** `aero_kernel/tests/test_spiral_parameter.py` · existing test `test_a_lift_coefficient_that_is_not_positive_is_invalid_input` (line 122)
- **Production:** `aero_kernel/formulas/spiral_parameter.py:20`
- **Gap:** The guard against a non-positive lift coefficient can be removed for the V_mp value: every parametrised case (m = 0, v_md = inf, g = -1) fails at V_md first; a NaN C_L is not tested either, and only the category is asserted.
- **Evidence:** `@pytest.mark.parametrize("override", [{"m": 0.0}, {"v_md": math.inf}, {"g": -1.0}])` ... `assert raised.value.category is ErrorCategory.INVALID_INPUT`
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived: 627 + 56 fast tests green. Observed at the formula: {'v_mp': inf} raises FormulaError invalid_input unmutated and ZeroDivisionError mutated; {'v_mp': nan} raises FormulaError unmutated and returns {'b_spiral_md': 3.069916842142834, 'b_spiral_mp': nan} mutated. The parametrisation `[{"m": 0.0}, {"v_md": math.inf}, {"g": -1.0}]` fails at V_md first in every case.
- **Acceptance mutation:** `git apply rework/patches/WP-P1/P1-F07.patch` (from the audit folder; aero_kernel/formulas/spiral_parameter.py:20  `if math.isnan(cl) or cl <= 0.0:` -> `if speed == "V_md" and (math.isnan(cl) or cl <= 0.0):`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, same test: add {'v_mp': math.inf} (C_L,mp = 0 while C_L,md stays positive) and {'v_mp': math.nan}; assert code == 'invalid_input', parameter == 'm' and that the message names 'V_mp'.

## P1-F08 · medium · untested_warning

- **Test file:** `aero_kernel/tests/test_maneuvering_speed_engine.py` · existing test `test_the_regime_warnings_of_the_optimiser_arrive_on_the_manoeuvring_speed` (line 66)
- **Production:** `aero_kernel/formulas/maneuvering_speed.py:37`
- **Gap:** The call warn_flap_validity(...) in maneuvering-speed can be deleted without a failing fast test: a manoeuvring speed computed with a flap deflection outside the method's validity would carry no caveat.
- **Evidence:** Only `("reynolds_bubble_sensitive", "maneuvering-speed", {"re": 6e4}) in [(w.code, w.origin, w.detail) for w in quantity.warnings]` is asserted; no flap-validity code.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived: 627 + 56 fast tests green. Calling the formula function directly with an airplane whose flap carries deflection_deg 45 gives warnings ['flap_deflection_beyond_validity'] unmutated and [] mutated. Through the engine no difference can be produced: the formula's only application binds `"airplane": "calc:airplane"` (canon_model.json) and engine.py:281 sets `self.airplane_at_rest = devices_at_rest(aircraft.airplane)`; with the same 45 deg in the document evaluate() returns warnings ['default_target_used', 'geometry_deflection_ignored'] with and without the mutation.
- **Verifier's note:** The claim's consequence ('a manoeuvring speed computed with a flap deflection outside the method's validity would carry no caveat') does not hold for the kernel's caller at 72c4b5c6, because the manoeuvring speed is never computed with a deflected flap. Whether the call is then unreachable code is a question for the maintainer, not answered here.
- **Acceptance mutation:** `git apply rework/patches/WP-P1/P1-F08.patch` (from the audit folder; aero_kernel/formulas/maneuvering_speed.py:37  `warn_flap_validity(ctx, airplane_of(x), stall.solution.diagnostics)` -> (line removed)). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_maneuvering_speed_engine.py: reuse the flapped aircraft and the stub diagnostics of the stall-speed flap-validity test (test_stall_speed_engine.py / test_device_confidence.py) and assert the same warning code with origin 'maneuvering-speed' on the quantity.
- **Correction:** (no) The recommended test asserts the warning 'with origin maneuvering-speed on the quantity' through the engine with the flapped aircraft of the stall-speed test. That cannot pass: maneuvering-speed has no configured-airplane application, so the flap is at rest when the formula runs (tried: flap-deflection-landing 45 and a document deflection of 45 both give no flap warning on maneuvering-speed). Only a direct call of maneuvering_speed(x, ctx) with a deflected airplane kills the mutation.

## P1-F12 · medium · misleading_name

- **Test file:** `aero_kernel/tests/test_formulas_end_to_end.py` · existing test `test_a_missing_altitude_fails_density_and_pressure_but_not_weight` (line 105)
- **Production:** `aero_kernel/formulas/air_density_isa.py:27`
- **Gap:** The test does not test a missing altitude: altitude has the canon default 0 m (provenance shows it), and the density fails only because the stub table is empty (KeyError -> `internal`). The real rule (default taken and declared) is unpinned, and any failure of the density formula would satisfy the test.
- **Evidence:** `assert quantities["air-density"].status is QuantityStatus.ERROR` / `assert quantities["dynamic-pressure"].status is QuantityStatus.ERROR`; observed error: ('internal', 'internal', 'Internal error (KeyError) while computing `air-density`.'), defaults_used [('altitude', 0.0), ('gravity', 9.80665)]
- **Verified:** CONFIRMED_BY_READING (READING). Ran the test's scenario in the copy: with StubAtmosphere({}) the stub was asked [0.0], provenance.defaults_used holds DefaultUsed(slug='altitude', value=0.0, unit='m', ...), and air-density is ('internal', 'internal', 'Internal error (KeyError) while computing `air-density`.'); dynamic-pressure is 'upstream_failed'. The test asserts only `assert quantities["air-density"].status is QuantityStatus.ERROR`. So the altitude is not missing, it is defaulted, and the error is the empty stub table.
- **Verifier's note:** No other fast test in the package's files asserts the altitude default: test_formulas_end_to_end.py:86 has `[d.slug for d in result.provenance.defaults_used] == ["gravity"]` with an altitude given. The default mechanism itself is tested generically in test_engine_defaults.py.
- **Test to write:** Fast: replace by 'a missing altitude takes the default 0 m and declares it': StubAtmosphere({0.0: 1.225}), no altitude in values; assert air-density OK == 1.225, stub.asked == [0.0], 'altitude' in provenance.defaults_used with value 0.0, dynamic-pressure == 0.5*1.225*15^2 = 137.8125 Pa. Keep a separate adapter-failure test that asserts the error category and code.

## P1-F06 · low · missing_edge_case · do together with P1-F05

- **Test file:** `aero_kernel/tests/test_parabolic_closed_forms.py` · existing test `test_sink_rate_precondition_refuses_a_drag_coefficient_at_or_below_zero` (line 229)
- **Production:** `aero_kernel/formulas/sink_rate.py:47`
- **Gap:** The four positivity preconditions of the parabolic closed forms (oswald_factor_positive, both parabola_defined, lift/drag_coefficient_positive) may treat NaN as held; drag_positive and dihedral_effect_stabilising test NaN, these do not. Through the engine a NaN cannot arrive (finite-output guard), so this is the checks' own contract only.
- **Evidence:** `@pytest.mark.parametrize("cd", [0.0, -0.01])` and `[(0.0, 8.0), (-0.3, 8.0), (0.8, 0.0), (0.8, -1.0)]`: no math.nan.
- **Verified:** CONFIRMED_BY_READING (READING). The five checks compare with `> 0.0` (e.g. sink_rate.py:47 `if cd > 0.0:`), so NaN is 'violated' today, and no parametrisation in test_parabolic_closed_forms.py contains math.nan: `@pytest.mark.parametrize("cd", [0.0, -0.01])`, `@pytest.mark.parametrize("cl", [0.0, -0.2])`. test_lift_to_drag_ratio.py:45 does have `(math.nan, "violated")` for drag_positive.
- **Verifier's note:** Same test file and the same parametrisations that P1-F03 and P1-F05 extend.
- **Test to write:** Fast: add math.nan to each violated parametrisation of the five checks (also P1-M08), as test_lift_to_drag_ratio.py does for drag_positive.

## P1-F10 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_parabolic_polar_fit.py` · existing test `test_every_fit_declares_its_residual` (line 135)
- **Production:** `aero_kernel/formulas/parabolic_polar_fit.py:169`
- **Gap:** The residual notice's max_relative (and max_abs, v_min_ms, v_max_ms) can be wrong without a failing test; the scatter test accepts C_D0 within 10 % and an RMS anywhere in 0.0003..0.0006.
- **Evidence:** `assert detail_of(warning, "rms") < 1e-12` (no other residual key) and `assert 0.0003 < rms < 0.0006` / `assert close(result["cd0"], CD0 + 0.0005, 0.1)`
- **Verified:** CONFIRMED_BY_READING (READING). parabolic_polar_fit.py:162-170 builds the notice detail with v_min_ms, v_max_ms, max_abs and `"max_relative": max(abs(r) / cd for r, cd in _residuals(polar.cl, polar.cd, fit))`. No test reads these keys from the warning (grep max_relative|v_min_ms|v_max_ms over the tests finds only fit.max_abs on fit_parabola directly, test_parabolic_polar_fit.py:96). The asserts are `assert detail_of(warning, "rms") < 1e-12` and `assert 0.0003 < rms < 0.0006` / `assert close(result["cd0"], CD0 + 0.0005, 0.1)`.
- **Verifier's note:** The detail of the polar_fit_residual notice reaches the caller with every fitted quantity.
- **Test to write:** Fast: feed polar_of over levels with C_L^2 = (1, 2, 3) and C_D = (1, 3, 2) through a StubOpti.level_answer and assert detail rms == sqrt(0.5), max_abs == 1.0, max_relative == max(0.5/1, 1/3, 0.5/2) = 0.5, v_min_ms == v_max_ms == 10.0, each to 1e-12.
- **Correction:** (unclear) Arithmetic recomputed: least-squares line through (1,1), (2,3), (3,2) is 1 + 0.5 x, residuals (-0.5, 1, -0.5), so rms = sqrt(0.5), max_abs = 1.0, max_relative = max(0.5/1, 1/3, 0.5/2) = 0.5; correct, and min() would give 0.25. Unclear is whether a StubOpti.level_answer may return three points when the formula asked for 48 levels and what polar_of puts into v_ms; the implementer has to check both.

## P1-F13 · low · over_mocked

- **Test file:** `aero_kernel/tests/test_vertical_tail_volume.py` · existing test `test_a_v_tail_counts_its_fin_share_sin_squared_of_the_panel_angle` (line 48)
- **Production:** `aero_kernel/formulas/vertical_tail_volume.py:34`
- **Gap:** The asserted sin^2 fin share is computed by the test fake StubGeometry -> asb_fakes.stand_in_fin_area, not by production code; the production projection (GEO adapter) could be wrong, or the formula could ask the wrong adapter method, and this test would still describe the fake.
- **Evidence:** `context = context_with(StubAtmosphere({}), geometry=StubGeometry())` ... `assert close(found["v_v"], 2.0 * (panel + extension) * 0.5 * arm / (S_REF * B_REF), 1e-12)`
- **Verified:** CONFIRMED_BY_READING (READING). The value comes from the fake: `context = context_with(StubAtmosphere({}), geometry=StubGeometry())` and formula_builders.py:246 `return stand_in_fin_area((airplane.wings or {})[key])`; the production formula only multiplies and divides. The sub-claim 'the formula could ask the wrong adapter method' is refuted for the suite: the supplementary mutation is killed by test_vertical_tail_volume.py::test_the_fin_area_is_asked_of_the_geometry_adapter_for_the_one_vertical_surface (`assert set(run.geometry.fin_keys) == {"fin"}`) and five more tests, although the cited V-tail test itself stays green under it (sin^2 = cos^2 at 45 deg).
- **Verifier's note:** Verdict by reading; `killed` and `killed_by` describe only the supplementary wrong-adapter-method mutation. Severity changed from medium to low.
- **Acceptance mutation:** `git apply rework/patches/WP-P1/P1-F13.patch` (from the audit folder; supplementary: aero_kernel/formulas/vertical_tail_volume.py:34  `ctx.solvers.geometry.fin_area(airplane, key)` -> `ctx.solvers.geometry.horizontal_tail_area(airplane, key)`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast: give StubGeometry a fixed fin_area (e.g. 0.02 m^2) and assert v_v == 0.02*0.4/(0.28*1.4) = 0.0204082 and fin_keys == ['vee'] (plumbing, honestly named). Aero: assert the real GeometryAdapter.fin_area of this V-tail equals 2*(0.09*0.2828427 + 0.12*0.0707107)*0.5 = 0.0339411 m^2 (hand: 45 deg panel, sin^2 = 1/2) to 1e-9; same for horizontal_tail_area with cos^2.

## P1-F15 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_vertical_tail_volume.py` · existing test `test_without_a_vertical_tail_the_volume_does_not_apply` (line 66)
- **Production:** `aero_kernel/engine.py`
- **Gap:** Four 'does not apply' tests accept any non-OK status, so an internal error instead of not_applicable / condition_not_met would pass (also test_tail_arms.py:154, test_spiral_parameter.py:92, test_parabolic_polar_fit.py:340).
- **Evidence:** `assert quantity.status is not QuantityStatus.OK`
- **Verified:** CONFIRMED_BY_READING (READING). test_vertical_tail_volume.py:70 `assert quantity.status is not QuantityStatus.OK`, test_spiral_parameter.py:96 and test_tail_arms.py:156 the same. Run in the copy, all three are status not_applicable with reason code condition_not_met ('The aircraft does not satisfy `has_vertical_tail`.'), which the asserts do not pin. The fourth site, test_parabolic_polar_fit.py:340, is an error case (precondition_violated), not a 'does not apply' case.
- **Verifier's note:** Status and reason reach the caller. The fourth site is the same gap as P1-F04.
- **Test to write:** In each: assert status is QuantityStatus.NOT_APPLICABLE and reason.code == 'condition_not_met', as test_horizontal_tail_volume.py:61 and test_turn_sideslip.py:108 already do.
- **Correction:** (unclear) Correct as written for three sites (NOT_APPLICABLE, reason.code 'condition_not_met' observed). Wrong for test_parabolic_polar_fit.py: that quantity is ERROR with code 'precondition_violated'; use the assertion of P1-F04 there.

## P1-F16 · low · mirror_or_tautology

- **Test file:** `aero_kernel/tests/test_spiral_parameter.py` · existing test `test_the_formula_is_the_closed_form_for_given_speeds` (line 116)
- **Production:** `aero_kernel/formulas/spiral_parameter.py:28`
- **Gap:** The expected B is produced by a test helper that repeats the production expression term by term; a wrong formula copied into both would pass. Only Gamma_eq = 6.4 deg is independent. The same pattern: test_lift_coefficient_required.py:105 (aero) recomputes C_L from the result's own weight, q and S_ref.
- **Evidence:** `def spiral(arm, speed): cl = MASS * GRAVITY / (0.5 * RHO * speed**2 * S_REF); return arm * GAMMA_EQ / (B_REF * cl)` ... `assert close(found["b_spiral_md"], spiral(0.4, 12.0), 1e-9)`
- **Verified:** CONFIRMED_BY_READING (READING). The helper repeats the production expression: `cl = MASS * GRAVITY / (0.5 * RHO * speed**2 * S_REF)` / `return arm * GAMMA_EQ / (B_REF * cl)` against production `arm * dihedral_deg / (span * cl)` with `weight / (pressure_area * number(x, "v_md") ** 2)`; every expected value in the file goes through it. test_lift_coefficient_required.py:105 is `assert close(quantities["lift-coefficient"].value, weight / (q * s_ref), 1e-12)` with weight, q and s_ref taken from the same result.
- **Verifier's note:** A caller-visible value with no literal anywhere in the fast tier; the fix is two numbers.
- **Test to write:** Fast: assert literals. m 1.5 kg, g 9.80665, rho 1.225, S 0.28 m^2, b 1.4 m, arm 0.4 m, Gamma_eq 6.4 deg: at 12 m/s q S = 0.5*1.225*144*0.28 = 24.696 N, C_L = 14.709975/24.696 = 0.595642, B_md = 0.4*6.4/(1.4*0.595642) = 3.069917; at 9 m/s q S = 13.8915 N, C_L = 1.058919, B_mp = 1.726828; tolerance 1e-6.

## Not part of this package's work

| Finding | State | Reason |
|---|---|---|
| P1-F11 | production_defect | #1435 |
| P1-F17 | dropped | The caller cannot supply an int: AircraftInput.values is `Annotated[float, Field(strict=True)]` (schema.py:744), and an int or bool passing number() would compute the same value. No risk to a result. |
| P1-F18 | dropped | Cosmetic: the set equality on the line above the literal already pins the same fact, and the name has no effect on any result. |
