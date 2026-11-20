# WP-P1 — Geschlossene Formeln: Vorbedingungen beidseitig

Self-contained brief for one implementer subagent. Frozen review state: commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

- **Production code under test:** aero_kernel/formulas/ (parabolische Polare, Sinkrate, Spiralparameter, Manövergeschwindigkeit)
- **Requirement sources:** Kanon-Einträge, canon_model.json preconditions
- **Test files you may change:** `aero_kernel/tests/test_formulas.py`, `aero_kernel/tests/test_formulas_end_to_end.py`, `aero_kernel/tests/test_lift_coefficient_required.py`, `aero_kernel/tests/test_maneuvering_speed_engine.py`, `aero_kernel/tests/test_parabolic_closed_forms.py`, `aero_kernel/tests/test_parabolic_polar_fit.py`, `aero_kernel/tests/test_spiral_parameter.py`, `aero_kernel/tests/test_vertical_tail_volume.py`
- **Findings:** 16 (2 high, 8 medium, 6 low)

A finding marked **DECISION** needs the maintainer's answer first: do not write its test, list it in your report as open.

## P1-F01 · high · missing_edge_case

- **Test file:** `aero_kernel/tests/test_parabolic_closed_forms.py` · existing test `test_minimum_drag_speed_precondition_refuses_an_undefined_parabola` (line 153)
- **Production:** `aero_kernel/formulas/minimum_drag_speed_closed_form.py:24`
- **Gap:** The precondition parabola_defined of minimum-drag-speed-closed-form can be violated for every input (the probe quantity would never be produced) and the fast tier stays green: there is no 'held' case and no fast engine run of minimum-drag-speed-probe.
- **Evidence:** The only assert on the check: `assert v_md_parabola_defined(x).state == "violated"` (four violated cases, no held case).
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P1-M05:** in `aero_kernel/formulas/minimum_drag_speed_closed_form.py` line 24: `if all(value > 0.0 ...):` -> `if False:` (always violated). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_parabolic_closed_forms.py: (a) v_md_parabola_defined(x).state == 'held' for W/S 30 N/m^2, rho 1.225, C_D0 0.03, k 0.05; (b) through evaluate() on the shipped build with StubOpti (stub parabola C_D0 0.03, k 0.05, like test_parabolic_polar_fit.run) request minimum-drag-speed-probe and assert status OK and value == sqrt(2 (m g/S_ref) / (rho sqrt(0.03/0.05))) to 1e-9; (c) with a falling polar (k < 0) assert error.code == 'upstream_failed' or 'precondition_violated' explicitly.

## P1-F02 · high · missing_edge_case

- **Test file:** `aero_kernel/tests/test_parabolic_closed_forms.py` · existing test `test_sink_rate_precondition_refuses_a_lift_coefficient_at_or_below_zero` (line 217)
- **Production:** `aero_kernel/formulas/sink_rate.py:29`
- **Gap:** lift_coefficient_positive can reject every lift coefficient and no test fails: sink-rate has no 'held' case for C_L and is never requested through the engine in any tier, so a sink rate that is never computed would go unnoticed.
- **Evidence:** `assert lift_coefficient_positive(x).state == "violated"` for cl in [0.0, -0.2]; the held test exists only for drag_coefficient_positive (line 240).
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P1-M06:** in `aero_kernel/formulas/sink_rate.py` line 29: lift_coefficient_positive: `if cl > 0.0:` -> `if False:` (always violated). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast: (a) lift_coefficient_positive held for C_L = 0.5 and for 1e-12; (b) engine test: evaluate(shipped_build, m 1.5 kg, altitude 0, flight-speed 10 m/s, StubOpti parabola C_D0 0.03, k 0.05) requesting sink-rate, lift-coefficient, drag-coefficient-parabolic: assert sink-rate OK, unit m/s, value == V * (0.03 + 0.05 C_L^2)/C_L with C_L = m g/(0.5 rho V^2 S_ref) to 1e-9; (c) a negative load-factor (-1) must give error.code 'precondition_violated' with detail.precondition 'lift_coefficient_positive'.

## P1-F03 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_parabolic_closed_forms.py` · existing test `test_max_lift_to_drag_precondition_refuses_an_undefined_parabola` (line 111)
- **Production:** `aero_kernel/formulas/max_lift_to_drag_parabolic.py:24`
- **Gap:** The aspect ratio can be dropped from parabola_defined of max-lift-to-drag-parabolic; with AR = 0 the formula then returns E_max,probe = 0.0 as a value (observed), a substitute instead of the declared error.
- **Evidence:** Parametrisation `[(0.8, 8.0, 0.0), (0.8, 8.0, -0.01), (0.0, 8.0, 0.03)]` has no case with ar <= 0 and none with e < 0.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P1-M01:** in `aero_kernel/formulas/max_lift_to_drag_parabolic.py` line 24: `if cd0 > 0.0 and e_osw > 0.0 and ar > 0.0:` -> `if cd0 > 0.0 and e_osw > 0.0:`. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, same test: add (e 0.8, AR 0.0, C_D0 0.03), (0.8, -8.0, 0.03) and (-0.3, 8.0, 0.03) -> 'violated'; add a held case (0.8, 8.0, 0.03) and (1e-12, 1e-12, 1e-12).

## P1-F04 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_parabolic_polar_fit.py` · existing test `test_a_nonphysical_fit_stops_the_chain_at_the_induced_drag_factor` (line 340)
- **Production:** `aero_kernel/formulas/max_lift_to_drag_parabolic.py:24`
- **Gap:** For a negative fitted e the probe may fail with an internal ValueError (sqrt of a negative number) instead of precondition_violated, and induced-drag-factor may fail with any error: the chain test accepts every non-OK status.
- **Evidence:** `assert by_slug["induced-drag-factor"].status is QuantityStatus.ERROR` and `assert by_slug["max-lift-to-drag-probe"].status is not QuantityStatus.OK`
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P1-M02:** in `aero_kernel/formulas/max_lift_to_drag_parabolic.py` line 24: `e_osw > 0.0` -> `e_osw != 0.0` (negative e held). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, same test: assert induced-drag-factor.error.code == 'precondition_violated', category UNSUPPORTED_CONFIGURATION and detail['precondition'] == 'oswald_factor_positive'; assert max-lift-to-drag-probe.error.code == 'precondition_violated' with detail['precondition'] == 'parabola_defined' (it binds e, AR and C_D0 directly, not k).

## P1-F05 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_parabolic_closed_forms.py` · existing test `test_minimum_drag_speed_precondition_refuses_an_undefined_parabola` (line 153)
- **Production:** `aero_kernel/formulas/minimum_drag_speed_closed_form.py:24`
- **Gap:** The exact boundary k = 0 (division by zero in sqrt(C_D0/k)) and negative W/S, rho or C_D0 are not refused by any test: both relaxed checks pass the suite.
- **Evidence:** Cases: `(0.0, 1.225, 0.03, 0.05), (30.0, 0.0, 0.03, 0.05), (30.0, 1.225, 0.0, 0.05), (30.0, 1.225, 0.03, -0.05)`: k only negative, the other three only zero.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P1-M03:** in `aero_kernel/formulas/minimum_drag_speed_closed_form.py` line 24: all four `> 0.0` -> k checked with `>= 0.0`. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, same parametrisation: add (30, 1.225, 0.03, 0.0), (-30, 1.225, 0.03, 0.05), (30, -1.225, 0.03, 0.05), (30, 1.225, -0.03, 0.05) -> 'violated' (P1-M04 covers the negatives).

## P1-F07 · medium · untested_error_path

- **Test file:** `aero_kernel/tests/test_spiral_parameter.py` · existing test `test_a_lift_coefficient_that_is_not_positive_is_invalid_input` (line 122)
- **Production:** `aero_kernel/formulas/spiral_parameter.py:20`
- **Gap:** The guard against a non-positive lift coefficient can be removed for the V_mp value: every parametrised case (m = 0, v_md = inf, g = -1) fails at V_md first; a NaN C_L is not tested either, and only the category is asserted.
- **Evidence:** `@pytest.mark.parametrize("override", [{"m": 0.0}, {"v_md": math.inf}, {"g": -1.0}])` ... `assert raised.value.category is ErrorCategory.INVALID_INPUT`
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P1-M10:** in `aero_kernel/formulas/spiral_parameter.py` line 20: guard applied only when speed == "V_md". Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, same test: add {'v_mp': math.inf} (C_L,mp = 0 while C_L,md stays positive) and {'v_mp': math.nan}; assert code == 'invalid_input', parameter == 'm' and that the message names 'V_mp'.

## P1-F08 · medium · untested_warning

- **Test file:** `aero_kernel/tests/test_maneuvering_speed_engine.py` · existing test `test_the_regime_warnings_of_the_optimiser_arrive_on_the_manoeuvring_speed` (line 66)
- **Production:** `aero_kernel/formulas/maneuvering_speed.py:37`
- **Gap:** The call warn_flap_validity(...) in maneuvering-speed can be deleted without a failing fast test: a manoeuvring speed computed with a flap deflection outside the method's validity would carry no caveat.
- **Evidence:** Only `("reynolds_bubble_sensitive", "maneuvering-speed", {"re": 6e4}) in [(w.code, w.origin, w.detail) for w in quantity.warnings]` is asserted; no flap-validity code.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P1-M13:** in `aero_kernel/formulas/maneuvering_speed.py` line 37: removed `warn_flap_validity(ctx, airplane_of(x), stall.solution.diagnostics)`. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_maneuvering_speed_engine.py: reuse the flapped aircraft and the stub diagnostics of the stall-speed flap-validity test (test_stall_speed_engine.py / test_device_confidence.py) and assert the same warning code with origin 'maneuvering-speed' on the quantity.

## P1-F11 · medium · untested_error_path · DECISION

- **Test file:** `aero_kernel/tests/test_lift_coefficient_required.py` · no test exists
- **Production:** `aero_kernel/formulas/lift_coefficient_required.py:26`
- **Gap:** flight-speed = 0 is admissible input (dynamic-pressure is OK with 0.0 Pa), and lift-coefficient then ends as category `internal` (ZeroDivisionError) instead of a declared FormulaError; no test pins what the caller gets. Observed by running evaluate() in the review copy.
- **Evidence:** Production: `return {"cl_req": lift_n / (number(x, "q") * number(x, "s_ref"))}`; observed result: `lift-coefficient error ('internal', 'internal', 'Internal error (ZeroDivisionError) while computing `lift-coefficient`.')`
- **Status:** READ_ONLY
- **Test to write:** Fast, test_lift_coefficient_required.py: evaluate with aircraft-mass 1.5 kg, altitude 0, flight-speed 0.0 requesting lift-coefficient; assert status ERROR and error.category is INVALID_INPUT (or whichever declared category the maintainer chooses), never INTERNAL, and value None. The decision (precondition `dynamic_pressure_positive` in the canon vs. validation) belongs to the canon.

## P1-F12 · medium · misleading_name

- **Test file:** `aero_kernel/tests/test_formulas_end_to_end.py` · existing test `test_a_missing_altitude_fails_density_and_pressure_but_not_weight` (line 105)
- **Production:** `aero_kernel/formulas/air_density_isa.py:27`
- **Gap:** The test does not test a missing altitude: altitude has the canon default 0 m (provenance shows it), and the density fails only because the stub table is empty (KeyError -> `internal`). The real rule (default taken and declared) is unpinned, and any failure of the density formula would satisfy the test.
- **Evidence:** `assert quantities["air-density"].status is QuantityStatus.ERROR` / `assert quantities["dynamic-pressure"].status is QuantityStatus.ERROR`; observed error: ('internal', 'internal', 'Internal error (KeyError) while computing `air-density`.'), defaults_used [('altitude', 0.0), ('gravity', 9.80665)]
- **Status:** READ_ONLY
- **Test to write:** Fast: replace by 'a missing altitude takes the default 0 m and declares it': StubAtmosphere({0.0: 1.225}), no altitude in values; assert air-density OK == 1.225, stub.asked == [0.0], 'altitude' in provenance.defaults_used with value 0.0, dynamic-pressure == 0.5*1.225*15^2 = 137.8125 Pa. Keep a separate adapter-failure test that asserts the error category and code.

## P1-F13 · medium · over_mocked

- **Test file:** `aero_kernel/tests/test_vertical_tail_volume.py` · existing test `test_a_v_tail_counts_its_fin_share_sin_squared_of_the_panel_angle` (line 48)
- **Production:** `aero_kernel/formulas/vertical_tail_volume.py:34`
- **Gap:** The asserted sin^2 fin share is computed by the test fake StubGeometry -> asb_fakes.stand_in_fin_area, not by production code; the production projection (GEO adapter) could be wrong, or the formula could ask the wrong adapter method, and this test would still describe the fake.
- **Evidence:** `context = context_with(StubAtmosphere({}), geometry=StubGeometry())` ... `assert close(found["v_v"], 2.0 * (panel + extension) * 0.5 * arm / (S_REF * B_REF), 1e-12)`
- **Status:** READ_ONLY
- **Test to write:** Fast: give StubGeometry a fixed fin_area (e.g. 0.02 m^2) and assert v_v == 0.02*0.4/(0.28*1.4) = 0.0204082 and fin_keys == ['vee'] (plumbing, honestly named). Aero: assert the real GeometryAdapter.fin_area of this V-tail equals 2*(0.09*0.2828427 + 0.12*0.0707107)*0.5 = 0.0339411 m^2 (hand: 45 deg panel, sin^2 = 1/2) to 1e-9; same for horizontal_tail_area with cos^2.

## P1-F06 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_parabolic_closed_forms.py` · existing test `test_sink_rate_precondition_refuses_a_drag_coefficient_at_or_below_zero` (line 229)
- **Production:** `aero_kernel/formulas/sink_rate.py:47`
- **Gap:** The four positivity preconditions of the parabolic closed forms (oswald_factor_positive, both parabola_defined, lift/drag_coefficient_positive) may treat NaN as held; drag_positive and dihedral_effect_stabilising test NaN, these do not. Through the engine a NaN cannot arrive (finite-output guard), so this is the checks' own contract only.
- **Evidence:** `@pytest.mark.parametrize("cd", [0.0, -0.01])` and `[(0.0, 8.0), (-0.3, 8.0), (0.8, 0.0), (0.8, -1.0)]`: no math.nan.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P1-M07:** in `aero_kernel/formulas/sink_rate.py` line 47: drag_coefficient_positive: `if cd > 0.0:` -> `if not cd <= 0.0:` (NaN held). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast: add math.nan to each violated parametrisation of the five checks (also P1-M08), as test_lift_to_drag_ratio.py does for drag_positive.

## P1-F10 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_parabolic_polar_fit.py` · existing test `test_every_fit_declares_its_residual` (line 135)
- **Production:** `aero_kernel/formulas/parabolic_polar_fit.py:169`
- **Gap:** The residual notice's max_relative (and max_abs, v_min_ms, v_max_ms) can be wrong without a failing test; the scatter test accepts C_D0 within 10 % and an RMS anywhere in 0.0003..0.0006.
- **Evidence:** `assert detail_of(warning, "rms") < 1e-12` (no other residual key) and `assert 0.0003 < rms < 0.0006` / `assert close(result["cd0"], CD0 + 0.0005, 0.1)`
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P1-M15:** in `aero_kernel/formulas/parabolic_polar_fit.py` line 169: `"max_relative": max(...)` -> `min(...)`. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast: feed polar_of over levels with C_L^2 = (1, 2, 3) and C_D = (1, 3, 2) through a StubOpti.level_answer and assert detail rms == sqrt(0.5), max_abs == 1.0, max_relative == max(0.5/1, 1/3, 0.5/2) = 0.5, v_min_ms == v_max_ms == 10.0, each to 1e-12.

## P1-F15 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_vertical_tail_volume.py` · existing test `test_without_a_vertical_tail_the_volume_does_not_apply` (line 66)
- **Production:** `aero_kernel/engine.py`
- **Gap:** Four 'does not apply' tests accept any non-OK status, so an internal error instead of not_applicable / condition_not_met would pass (also test_tail_arms.py:154, test_spiral_parameter.py:92, test_parabolic_polar_fit.py:340).
- **Evidence:** `assert quantity.status is not QuantityStatus.OK`
- **Status:** READ_ONLY
- **Test to write:** In each: assert status is QuantityStatus.NOT_APPLICABLE and reason.code == 'condition_not_met', as test_horizontal_tail_volume.py:61 and test_turn_sideslip.py:108 already do.

## P1-F16 · low · mirror_or_tautology

- **Test file:** `aero_kernel/tests/test_spiral_parameter.py` · existing test `test_the_formula_is_the_closed_form_for_given_speeds` (line 116)
- **Production:** `aero_kernel/formulas/spiral_parameter.py:28`
- **Gap:** The expected B is produced by a test helper that repeats the production expression term by term; a wrong formula copied into both would pass. Only Gamma_eq = 6.4 deg is independent. The same pattern: test_lift_coefficient_required.py:105 (aero) recomputes C_L from the result's own weight, q and S_ref.
- **Evidence:** `def spiral(arm, speed): cl = MASS * GRAVITY / (0.5 * RHO * speed**2 * S_REF); return arm * GAMMA_EQ / (B_REF * cl)` ... `assert close(found["b_spiral_md"], spiral(0.4, 12.0), 1e-9)`
- **Status:** READ_ONLY
- **Test to write:** Fast: assert literals. m 1.5 kg, g 9.80665, rho 1.225, S 0.28 m^2, b 1.4 m, arm 0.4 m, Gamma_eq 6.4 deg: at 12 m/s q S = 0.5*1.225*144*0.28 = 24.696 N, C_L = 14.709975/24.696 = 0.595642, B_md = 0.4*6.4/(1.4*0.595642) = 3.069917; at 9 m/s q S = 13.8915 N, C_L = 1.058919, B_mp = 1.726828; tolerance 1e-6.

## P1-F17 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_formulas.py` · existing test `test_number_rejects_an_absent_or_non_numeric_parameter` (line 98)
- **Production:** `aero_kernel/formulas/values.py:31`
- **Gap:** number() may accept an int (or bool) although the contract is a float; only None is tested as the rejected value.
- **Evidence:** `with pytest.raises(TypeError, match="'a'"): number({"a": None}, "a")`
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P1-M16:** in `aero_kernel/formulas/values.py` line 31: `isinstance(value, float)` -> `isinstance(value, (int, float))`. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast: number({'a': 2}, 'a'), number({'a': True}, 'a') and number({'a': '2.5'}, 'a') raise TypeError naming 'a'; number({}, 'a') raises KeyError.

## P1-F18 · low · misleading_name

- **Test file:** `aero_kernel/tests/test_formulas.py` · existing test `test_the_default_registry_holds_exactly_these_three_and_is_frozen` (line 81)
- **Production:** `aero_kernel/registry.py`
- **Gap:** The name speaks of three formulas while IMPLEMENTED lists dozens, and the sibling test hard-codes the canon size (64); both must be edited with every new formula, so they pin a hand-kept list rather than a requirement.
- **Evidence:** `assert DEFAULT_REGISTRY.slugs() == IMPLEMENTED` and `assert len(build.report.not_implemented) == 64 - len(IMPLEMENTED)`
- **Status:** READ_ONLY
- **Test to write:** Rename to test_the_default_registry_holds_exactly_the_implemented_formulas_and_is_frozen; derive the total from len(declared) instead of the literal 64.
