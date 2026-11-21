# WP-P5 — Validation, geometry, devices

Self-contained brief for one implementer subagent. Base commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

Every finding below was checked by an independent verifier on 2026-11-21 (`../rework/`). The line **Verified** says how. Where **Correction** appears, it overrides the text under **Test to write**.

- **Production code under test:** aero_kernel/validate.py, devices.py, fuselage_contour.py, solver_bodies.py
- **Requirement sources:** ARCHITECTURE §8.11, §8.1, §8.2, rules.yaml
- **Test files you may change:** `aero_kernel/tests/test_body_axis.py`, `aero_kernel/tests/test_devices.py`, `aero_kernel/tests/test_dihedral.py`, `aero_kernel/tests/test_fuselage_contour.py`, `aero_kernel/tests/test_surface_chain.py`, `aero_kernel/tests/test_surface_properties.py`, `aero_kernel/tests/test_validate.py`
- **Findings to work on:** 13 (2 high, 6 medium, 5 low)

## P5-F01 · high · missing_edge_case

- **Test file:** `aero_kernel/tests/test_validate.py` · existing test `TestConflictingMass::test_differing_masses_warn_with_both_values` (line 672)
- **Production:** `aero_kernel/validate.py:886`
- **Gap:** The conflicting_mass notice can disappear for every what-if at a mass above the geometry's total_mass_kg without a test failing: all tests pass a mass below the stored one.
- **Evidence:** document["airplane"]["total_mass_kg"] = 2.0 (values aircraft-mass 1.5); test_the_comparison_is_exact: total_mass_kg = math.nextafter(1.5, 2.0); test_engine_defaults.py: go(..., geometry_mass_kg=3.0) with mass 2.0. Mutation 'if passed == stored' -> 'if passed >= stored' passed 1421 tests.
- **Verified:** CONFIRMED (MUTATION_RERUN). 586 passed under the mutation. Observed on the minimal document with aircraft-mass 2.5 and total_mass_kg 2.0: original returns one warning ('conflicting_mass', 'notice', 'aircraft-mass', {'aircraft_mass_kg': 2.5, 'geometry_total_mass_kg': 2.0}); mutant returns []. Every test that expects the notice passes a mass below the stored one: `document["airplane"]["total_mass_kg"] = 2.0` against values aircraft-mass 1.5.
- **Verifier's note:** The only aero test naming conflicting_mass (test_stall_speed_fleet.py::test_belemnitos_regression_goldens) asserts its absence, so it cannot fail under this mutation.
- **Acceptance mutation:** `git apply rework/patches/WP-P5/P5-F01.patch` (from the audit folder; aero_kernel/validate.py:886  `if passed == stored:` -> `if passed >= stored:`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_validate.py TestConflictingMass: the minimal document with values aircraft-mass = 2.5 kg and airplane.total_mass_kg = 2.0 kg. Expect exactly one warning, code conflicting_mass, severity notice, origin aircraft-mass, detail == {"aircraft_mass_kg": 2.5, "geometry_total_mass_kg": 2.0}, errors == (). Add the mirror of the exact-comparison test with total_mass_kg = math.nextafter(1.5, 1.0).

## P5-F02 · high · untested_error_path

- **Test file:** `aero_kernel/tests/test_validate.py` · no test exists
- **Production:** `aero_kernel/validate.py:1110`
- **Gap:** A NaN or infinite airplane.xyz_ref, which the ASB and AVL conversions read as the moment reference point, can stop being reported.
- **Evidence:** errors = _non_finite(airplane, "airplane", skip=frozenset({"wings", "fuselages"})) -- adding "xyz_ref" to the skip set passed 1239 tests; the only root-level non-finite test is total_mass_kg (test_a_non_finite_mass_is_an_error_and_no_warning).
- **Verified:** CONFIRMED (MUTATION_RERUN). 919 and 154 passed under the mutation. Observed: for xyz_ref with nan/inf/-inf at index 0..2 the original reports ('non_finite_number', 'airplane.xyz_ref[i]', {'value': 'nan'|'inf'|'-inf'}); the mutant reports no error for all nine cases. No fast test sets a non-finite `xyz_ref`.
- **Verifier's note:** Severity raised from medium to high by the common rule (missing error at the caller). test_engine.py run together with app/tests/test_canon_aeroplane_input.py has two log-capture failures already in the baseline (test_every_debug_line_of_a_node_carries_formula_and_application, test_one_info_line_per_call_and_debug_per_node_all_with_the_same_call_id); run on their own they are green, so the two groups were run separately.
- **Acceptance mutation:** `git apply rework/patches/WP-P5/P5-F02.patch` (from the audit folder; aero_kernel/validate.py:1110  `skip=frozenset({"wings", "fuselages"})` -> `skip=frozenset({"wings", "fuselages", "xyz_ref"})`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_validate.py TestNonFinite, parametrised over index 0..2 and nan/inf/-inf: document["airplane"]["xyz_ref"] = [0.0, 0.0, 0.0] with one element replaced. Expect codes == ["non_finite_number"], paths == [f"airplane.xyz_ref[{i}]"], detail == {"value": str(bad)}.

## P5-F03 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_fuselage_contour.py` · existing test `TestContourDefect::test_a_figure_eight_is_refused` (line 80)
- **Production:** `aero_kernel/fuselage_contour.py:91`
- **Gap:** A contour whose vertex lies on a non-adjacent segment (touching without crossing) can be accepted; the rule says 'cross or touch other than at a shared vertex'.
- **Evidence:** FIGURE_EIGHT and the closing-segment case are proper crossings; replacing the collinear branch of _segments_meet ('return (d1 == 0 and _on_segment(c, d, a)) or ...') by 'return False' passed 1239 tests.
- **Verified:** CONFIRMED (MUTATION_RERUN). 854 passed under the mutation. Observed with the contour [(0,0),(0.04,0),(0.04,0.04),(0.02,0),(0,0.04)]: original `_crossing` returns (0, 2) and validate_aircraft reports invalid_fuselage_contour at `airplane.fuselages["Body"].x_secs[1].contour[2]` ('crosses itself: segment 0 (point 0 to 1) meets segment 2 (point 2 to 3)'); the mutant returns None and no such error.
- **Acceptance mutation:** `git apply rework/patches/WP-P5/P5-F03.patch` (from the audit folder; aero_kernel/fuselage_contour.py:91  `return ((d1 == 0 and _on_segment(c, d, a)) or (d2 == 0 and _on_segment(c, d, b)) or (d3 == 0 and _on_segment(a, b, c)) or (d4 == 0 and _on_segment(a, b, d)))` -> `return False`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_fuselage_contour.py: contour [(0.0, 0.0), (0.04, 0.0), (0.04, 0.04), (0.02, 0.0), (0.0, 0.04)] in metres, MIN_POINTS 3. Point 3 lies on segment 0. Shoelace: 2A = 0 + 0.0016 - 0.0008 + 0.0008 + 0 = 0.0016, A = +0.0008 m^2, so orientation cannot refuse it. Expect defect is not None, 'crosses itself' in defect.message, defect.point == 2. Same contour once through validate_aircraft: code invalid_fuselage_contour at ...x_secs[i].contour[2].

## P5-F04 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_devices.py` · no test exists
- **Production:** `aero_kernel/devices.py:167`
- **Gap:** flap_deflections() can return deflected ailerons, elevators and rudders as flaps; flap_validity and butterfly_approach read it, so a flap-validity warning or the largest flap angle would be taken from a device that is no flap.
- **Evidence:** 'and device.role in FLAP_ROLES' removed from flap_deflections: 1495 passed (package files plus test_butterfly_approach.py, test_stall_speed_engine.py, test_roll_rate_engine.py, test_solvers_avl_flap.py, test_solvers_flap_devices.py, test_solvers_opti_roll_flaps.py, test_formulas.py, test_reference_fleet_helpers.py). test_devices.py does not import flap_deflections.
- **Verified:** CONFIRMED (MUTATION_RERUN). 547 passed under the mutation, including test_device_confidence.py, test_engine_checks.py and test_config_butterfly.py, which the reviewer did not run. Observed on the recommended wing: original flap_deflections returns [('Main', 'F', 20.0), ('Main', 'device 1', -5.0)]; mutant returns additionally ('Main', 'A', 3.0). No fast test imports the production function: test_stall_speed_engine.py defines its own `def flap_deflections(airplane: AirplaneGeometry) -> list[float | None]:`.
- **Verifier's note:** The aero test test_butterfly_approach_fleet.py uses crow flap 45 deg and aileron 15 deg up; the flap stays the largest angle with or without the role filter, so it is not expected to fail.
- **Acceptance mutation:** `git apply rework/patches/WP-P5/P5-F04.patch` (from the audit folder; aero_kernel/devices.py:167  `and device.role in FLAP_ROLES` -> (line removed)). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_devices.py: main wing 'Main' with sections y = 0, 0.2, 0.4, 0.6, 0.8 m carrying {role flap, name 'F', deflection_deg 20.0}, {role flaperon, no name, deflection_deg -5.0}, {role aileron, name 'A', deflection_deg 3.0}, {role flap, name 'G', deflection_deg 0.0}, none. Expect flap_deflections(...) == [("Main", "F", 20.0), ("Main", "device 1", -5.0)]: only flap roles, a flap at rest left out, the unnamed one labelled by its section index.

## P5-F05 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_body_axis.py` · existing test `test_aerobuildup_gets_the_merged_bodies_straightened_after_the_merge` (line 108)
- **Production:** `aero_kernel/body_axis.py:137`
- **Gap:** aerobuildup_bodies() can ignore opt_body_axis_tolerance (1e-9 m): a body off its line by rounding noise would be moved and declared with fuselage_axis_straightened, although ch. 8.2 says it is unchanged and not declared.
- **Evidence:** expected, straightening = straight_axis(merged, config().opt_body_axis_tolerance.value) -- the merged body's shift is far above the tolerance; 'result = _straightened(bodies, 0.0)' passed 1304 tests (package files, test_solver_bodies.py, test_solvers_asb_airplane.py).
- **Verified:** CONFIRMED (MUTATION_RERUN). 527 passed under the mutation. Observed for one body with centres (0,0), (0.5,1e-10), (1.0,0): original aerobuildup_bodies has straightenings == () and bodies == solver_bodies(plane), validate_aircraft has no warning; mutant returns AxisStraightening(fuselage='Rumpf', sections=3, largest_shift=6.666666666666667e-11, section_index=1, x=0.5) and validate_aircraft warns ['fuselage_axis_straightened']. The tolerance is tested only on straight_axis directly (test_a_shift_within_the_tolerance_is_no_straightening).
- **Verifier's note:** The aero test test_solvers_asb_airplane_real.py calls aerobuildup_bodies on the fleet, but would fail only if a fleet body lay off its line by between 0 and 1e-9 m; not expected.
- **Acceptance mutation:** `git apply rework/patches/WP-P5/P5-F05.patch` (from the audit folder; aero_kernel/body_axis.py:137  `result = _straightened(bodies, config().opt_body_axis_tolerance.value)` -> `result = _straightened(bodies, 0.0)`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_body_axis.py: an airplane with one body whose centres are (x, z) = (0, 0), (0.5, 1e-10), (1.0, 0) m (largest distance to the least-squares line 2e-10 / 3 = 6.7e-11 m < 1e-9 m). Expect aerobuildup_bodies(plane).straightenings == () and .bodies == solver_bodies(plane); and validate_aircraft on the same input has no warning fuselage_axis_straightened.

## P5-F10 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_validate.py` · existing test `TestBodyAttachment::test_a_canopy_reaching_behind_its_parent_is_refused_at_the_section` (line 1119)
- **Production:** `aero_kernel/validate.py:811`
- **Gap:** A finding can carry the hint of another rule: no geometry test asserts a hint, so an agent would be told the wrong remedy.
- **Evidence:** assert _codes(errors) == ["canopy_outside_parent"]; assert _paths(errors) == [f"{CANOPY}.x_secs[1].xyz[0]"]; assert "0.6" in errors[0].message -- with _ATTACHMENT_HINTS["invalid_body_attachment"] used for every attachment code, 1239 passed.
- **Verified:** CONFIRMED_BY_READING (READING). test_validate.py has no assertion on `.hint` (grep for `.hint` in the file: no match); the cited test asserts only `_codes(errors) == ["canopy_outside_parent"]`, the path and `"0.6" in errors[0].message`. The hint is chosen per code at validate.py:811 `_ATTACHMENT_HINTS[defect.code]`.
- **Verifier's note:** Severity raised from low to medium by the common rule. No mutation run (input severity low).
- **Test to write:** Fast, test_validate.py: for canopy_outside_parent assert 'within the x range' in error.hint, for spinner_not_adjoining_parent 'back plate' in error.hint, for invalid_body_attachment 'attached_to' in error.hint; one parametrised test over a document per validation code asserting error.hint names the field or the remedy (chord: '> 0').

## P5-F12 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_validate.py` · existing test `TestInlineAirfoil::test_fewer_than_three_points_are_rejected` (line 638)
- **Production:** `aero_kernel/validate.py:410`
- **Gap:** The airfoil point minimum can become a literal 3 instead of the overridable canon parameter airfoil-resolvable.min_contour_points (maintainer rule: no threshold as a literal).
- **Evidence:** minimum_points = int(rules.value("airfoil-resolvable", "min_contour_points")) replaced by 'minimum_points = 3': 1239 passed. The same holds by reading for one-main-wing.required_main_wings.
- **Verified:** CONFIRMED_BY_READING (READING). validate.py:410 `minimum_points = int(rules.value("airfoil-resolvable", "min_contour_points"))`; the shipped parameter is adopted (value 3.0, status 'adopted'), so it can be overridden, but the only overrides of a point minimum in the fast tests are `{"fuselage-contour.min_contour_points": 2.0}` (test_validate.py:1049). one-main-wing.required_main_wings is overridden only in test_cache_key.py, which tests the key, not the validation.
- **Verifier's note:** Severity raised from low to medium by the common rule. No mutation run (input severity low).
- **Test to write:** Fast, test_validate.py: inline airfoil coordinates [[1.0, 0.0], [1.0, 0.0]] with rule_overrides {"airfoil-resolvable.min_contour_points": 2.0}. Without the override the code is invalid_airfoil_contour; with it the count rule passes, both ends lie at the largest x and the thickness is 0, so expect codes == ["non_positive_thickness"].

## P5-F13 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_dihedral.py` · existing test `test_a_root_off_the_centreline_weights_only_the_wing_that_exists` (line 65)
- **Production:** `aero_kernel/dihedral.py:61`
- **Gap:** A weighting that starts at the centreline instead of the root rib would pass: the test asserts a range, not the value.
- **Evidence:** assert 0.0 < found < math.degrees(math.atan2(0.07, 0.4)) -- hand value: chord 0.2, W1 = 0.2 (0.6^2 - 0.1^2) / 2 = 0.035, W2 = 0.2 (1.0^2 - 0.6^2) / 2 = 0.064, Gamma_2 = atan2(0.07, 0.4) = 9.92625 deg, Gamma_eq = 9.92625 * 0.064 / 0.099 = 6.41697 deg; weighting from y = 0 gives W1 = 0.036 and 6.35280 deg, also inside the range.
- **Verified:** CONFIRMED_BY_READING (READING). The only assertion is `assert 0.0 < found < math.degrees(math.atan2(0.07, 0.4))`. Recomputed: the kernel returns 6.41696679217888 deg, equal to atan2(0.07, 0.4) * 0.064 / 0.099; a weighting from the centreline (W1 = 0.2 * 0.6^2 / 2 = 0.036) gives 6.352797 deg, which also lies in (0, 9.926).
- **Verifier's note:** Severity raised from low to medium by the common rule; a mutation of _panel_weight would probably make it high.
- **Test to write:** Fast: assert close(found, math.degrees(math.atan2(0.07, 0.4)) * 0.064 / 0.099, 1e-12) (6.41697 deg).

## P5-F07 · low · misleading_name

- **Test file:** `aero_kernel/tests/test_surface_properties.py` · existing test `test_a_single_panel_tail_has_the_hand_values` (line 52)
- **Production:** `aero_kernel/solvers/asb_airplane.py (surface_properties)`
- **Gap:** All seven tests of this file pin the test stand-in, not the kernel: the production surface_properties (AeroSandbox adapter) could return wrong area, span, MAC or x_LE,MAC and this file stays green. Production is pinned in the aero tier only.
- **Evidence:** from aero_kernel.tests.planform_stand_in import stand_in_surface_properties as surface_properties
- **Verified:** CONFIRMED_BY_READING (READING). test_surface_properties.py:8 `from aero_kernel.tests.planform_stand_in import stand_in_surface_properties as surface_properties`; all seven tests of the file call this alias, never aero_kernel.solvers.asb_airplane.surface_properties (asb_airplane.py:394). One part of the claim is too strong: the production adapter is also exercised in the fast tier against a fake AeroSandbox (test_solvers_asb_airplane.py::test_the_surface_properties_are_asbs_with_the_ac_less_a_quarter_mac, `assert found.x_le_mac == FAKE_AC_X["Fin"] - 0.25 * chord`), so only the real planform numbers are aero-tier only (test_geometry_properties.py).
- **Verifier's note:** Severity lowered from medium to low. The stand-in itself is used by conftest.py and asb_fakes.py for many fast tests, so its own tests are worth keeping under an honest name.
- **Test to write:** Rename the file to test_planform_stand_in.py and drop the alias so the dashboard does not count it for production. Keep the same hand case in the aero tier against the real adapter: half panel y 0..0.2 m, chord 0.10 -> 0.05 m, x_le 0.50 -> 0.52 m, mirrored: area 2 * 0.2 * 0.075 = 0.03 m^2, span 0.4 m, AR 0.16 / 0.03, c_MAC = (2/3)(0.01 + 0.005 + 0.0025) / 0.15 = 0.077778 m (rel 1e-9; x_LE,MAC follows ASB's quarter-chord definition and is compared with ASB, not with the stand-in's 0.508889 m).

## P5-F09 · low · coverage_only · do together with P5-F01

- **Test file:** `aero_kernel/tests/test_validate.py` · existing test `TestCanopyMerge::test_an_invalid_input_gets_no_merge_declaration` (line 1182)
- **Production:** `aero_kernel/validate.py:1122`
- **Gap:** This test passes whether or not the 'only for an admissible input' guard exists: an unknown parent is never merged anyway. The guard itself is pinned by the spinner and the axis variant.
- **Evidence:** result = _result(_with_canopy(_document(), attached_to="Fuselage")); assert "canopy_merged_into_fuselage" not in _codes_of_warnings(result) -- with 'if not errors:' replaced by 'if True:' only TestSpinner::test_an_invalid_spinner_gets_no_merge_declaration and TestFuselageAxisStraightened::test_an_invalid_input_gets_no_straightening_declaration fail.
- **Verified:** CONFIRMED_BY_READING (READING). The test's input is inadmissible because of the attachment itself: `result = _result(_with_canopy(_document(), attached_to="Fuselage"))` - a canopy on a parent that does not exist has nothing to merge into, so `"canopy_merged_into_fuselage" not in ...` holds with or without the guard `if not errors:` (validate.py:1122). The guard is pinned by TestSpinner::test_an_invalid_spinner_gets_no_merge_declaration and TestFuselageAxisStraightened::test_an_invalid_input_gets_no_straightening_declaration (the latter asserts `result.errors != ()` on a body that would be straightened).
- **Verifier's note:** No mutation run (severity low); the reviewer's probe result was not re-executed.
- **Test to write:** Fast, test_validate.py TestCanopyMerge: the document of _with_canopy(_document()) (a canopy that would merge) with the main wing's second chord set to -0.1 m. Expect codes of errors == ["non_positive_length"] and no warning with a code starting with 'canopy_'.

## P5-F11 · low · weak_assertion · do together with P5-F16

- **Test file:** `aero_kernel/tests/test_validate.py` · existing test `TestWingSections::test_one_section_is_rejected` (line 141)
- **Production:** `aero_kernel/validate.py:592`
- **Gap:** too_few_sections can lose its detail (the section count) unnoticed.
- **Evidence:** assert _paths(errors) == ['airplane.wings["Main wing"].x_secs']; assert _codes(errors) == ["too_few_sections"] -- dropping 'float(count)' from the finding passed 1239 tests.
- **Verified:** CONFIRMED_BY_READING (READING). TestWingSections::test_one_section_is_rejected asserts only `assert _paths(errors) == ['airplane.wings["Main wing"].x_secs']` and `assert _codes(errors) == ["too_few_sections"]`; test_no_section_is_rejected only the path. The detail comes from `float(count),` in _too_few_sections (validate.py:592); no other fast test asserts the detail of too_few_sections.
- **Verifier's note:** Severity raised from low to medium by the common rule. Two extra assert lines in tests P5-F16 touches anyway.
- **Test to write:** Fast: in test_one_section_is_rejected add assert errors[0].detail == {"value": 1.0}; in test_no_section_is_rejected assert the code and detail == {"value": 0.0}.

## P5-F14 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_surface_chain.py` · existing test `test_a_wing_chain_that_folds_back_names_y` (line 62)
- **Production:** `aero_kernel/surface_chain.py:115`
- **Gap:** The fold-back tests do not assert the code of rule sections-monotone-in-y, and the admissible boundary (two sections at one y, e.g. a vertical winglet panel) is stated only indirectly through test_dihedral.py.
- **Evidence:** with pytest.raises(FormulaError, match="fold back in y"): oriented_chain(wing, 1) -- '<' -> '<=' in the fold-back test is killed only by test_dihedral.py::test_a_wing_without_a_span_has_no_weighting_and_is_refused.
- **Verified:** CONFIRMED_BY_READING (READING). test_a_wing_chain_that_folds_back_names_y is `with pytest.raises(FormulaError, match="fold back in y"):` with no assertion after it; the z variant asserts only `raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION`. The code is set in _unsupported (surface_chain.py:69 `"unsupported_configuration",`) and asserted by neither. test_surface_chain.py has no chain with two sections at one y.
- **Verifier's note:** Kept because the code reaches the caller and the test is two lines; no other finding in this test file to bundle with.
- **Test to write:** Fast, test_surface_chain.py: assert raised.value.code == "unsupported_configuration" in both fold-back tests; add a chain (y, z) = (0, 0), (0.5, 0), (0.5, 0.1) with axis 1 and expect three points with y == [0.0, 0.5, 0.5], no error.

## P5-F16 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_validate.py` · existing test `TestFuselageSectionEquivalent::test_every_substituted_section_warns` (line 739)
- **Production:** `aero_kernel/validate.py:950`
- **Gap:** Several validate tests assert a count or a path without the code: two warnings of any code satisfy this one; test_no_section_is_rejected, test_non_finite_tuple_element_gets_an_index and the read-set tests assert the path only.
- **Evidence:** assert len(_result(document).warnings) == 2
- **Verified:** CONFIRMED_BY_READING (READING). test_every_substituted_section_warns ends with `assert len(_result(document).warnings) == 2`; test_no_section_is_rejected is `assert _paths(_validate(document)) == ['airplane.wings["Main wing"].x_secs']`; test_non_finite_tuple_element_gets_an_index is `assert _paths(_validate(document)) == ['airplane.wings["Main wing"].x_secs[0].xyz_le[1]']`. The code and detail of fuselage_section_equivalent are asserted for one section by the test just above in the same class.
- **Verifier's note:** Kept as the carrier of P5-F11 (same file, same kind of added assert).
- **Test to write:** Assert [w.code for w in warnings] == ["fuselage_section_equivalent"] * 2 and the two section paths in detail; add _codes(...) next to every bare _paths(...) assert.

## Not part of this package's work

| Finding | State | Reason |
|---|---|---|
| P4-F12 | refuted | killed by `aero_kernel/tests/test_induced_drag.py::test_an_override_outside_the_range_is_refused[0.0-non_positive_value]` |
| P4-F13 | refuted | killed by `aero_kernel/tests/test_induced_drag.py::test_an_override_inside_the_range_is_accepted[1.0]` |
| P5-F06 | waiting_for_decision | maintainer decision open (README section 6); do not write its test |
| P5-F08 | production_defect | #1439 |
| P5-F15 | dropped | Drop: each of these tests changes one field of a builder that is otherwise valid (make_warning: 'Build a valid notice, with fields overridden'), so a refusal for another reason is hardly possible, and matching pydantic's wording ties the te |
| P5-F17 | dropped | Drop: no risk for the purpose of the software; the branch only words an import defect. Cheap to add if the implementer is in the file anyway, but no other finding of this package touches test_config.py. |
