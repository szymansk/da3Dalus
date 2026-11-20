# WP-P5 — Validierung, Geometrie, Geräte

Self-contained brief for one implementer subagent. Frozen review state: commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

- **Production code under test:** aero_kernel/validate.py, devices.py, fuselage_contour.py, solver_bodies.py
- **Requirement sources:** ARCHITECTURE §8.11, §8.1, §8.2, rules.yaml
- **Test files you may change:** `aero_kernel/tests/test_body_axis.py`, `aero_kernel/tests/test_config.py`, `aero_kernel/tests/test_devices.py`, `aero_kernel/tests/test_dihedral.py`, `aero_kernel/tests/test_fuselage_contour.py`, `aero_kernel/tests/test_schema.py`, `aero_kernel/tests/test_surface_chain.py`, `aero_kernel/tests/test_surface_properties.py`, `aero_kernel/tests/test_validate.py`, `aero_kernel/tests/test_validate_rules.py`
- **Findings:** 19 (1 high, 9 medium, 9 low)

A finding marked **DECISION** needs the maintainer's answer first: do not write its test, list it in your report as open.

## P5-F01 · high · missing_edge_case

- **Test file:** `aero_kernel/tests/test_validate.py` · existing test `TestConflictingMass::test_differing_masses_warn_with_both_values` (line 672)
- **Production:** `aero_kernel/validate.py:886`
- **Gap:** The conflicting_mass notice can disappear for every what-if at a mass above the geometry's total_mass_kg without a test failing: all tests pass a mass below the stored one.
- **Evidence:** document["airplane"]["total_mass_kg"] = 2.0 (values aircraft-mass 1.5); test_the_comparison_is_exact: total_mass_kg = math.nextafter(1.5, 2.0); test_engine_defaults.py: go(..., geometry_mass_kg=3.0) with mass 2.0. Mutation 'if passed == stored' -> 'if passed >= stored' passed 1421 tests.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P5-M20:** in `aero_kernel/validate.py` line 886: _mass_warnings: 'if passed == stored' -> 'if passed >= stored' (no warning when the passed mass is above the geometry's). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_validate.py TestConflictingMass: the minimal document with values aircraft-mass = 2.5 kg and airplane.total_mass_kg = 2.0 kg. Expect exactly one warning, code conflicting_mass, severity notice, origin aircraft-mass, detail == {"aircraft_mass_kg": 2.5, "geometry_total_mass_kg": 2.0}, errors == (). Add the mirror of the exact-comparison test with total_mass_kg = math.nextafter(1.5, 1.0).

## P4-F12 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_validate_rules.py` · existing test `test_a_bad_override_is_an_input_error` (line 104)
- **Production:** `aero_kernel/rules.py:178`
- **Gap:** An override of exactly 0 for a 'positive' rule parameter can be accepted (<= 0 changed to < 0) without a failing test; a zero threshold (for example k_e_d0 = 0 or a zero tolerance) would then reach the solvers.
- **Evidence:** The parametrisation has only `("no-such-rule.x", "unknown_rule_parameter")`, `(f"{RULE}.no_such", "unknown_rule_parameter")`, `(f"{RULE}.max_inclination", "non_finite_number")`; rules.py:178 `elif entry.positive and overrides[key] <= 0:` has no test.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P4-M14:** in `aero_kernel/rules.py` line 178: rule_override_errors: `entry.positive and overrides[key] <= 0` -> `< 0` (an override of exactly 0 is accepted). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast tier, aero_kernel/tests/test_validate_rules.py, on the shipped model (or a fixture rule with `positive: true`): rule_override_errors({'<rule>.<positive parameter>': v}, MODEL) for v in (0.0, -1.0) -> exactly one error with code 'non_positive_value' and input_path 'rule_overrides.<key>'; for v = 1e-9 -> ().

## P4-F13 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_validate_rules.py` · existing test `test_a_bad_override_is_an_input_error` (line 104)
- **Production:** `aero_kernel/rules.py:184`
- **Gap:** The at_most bound of a rule parameter has no test at all: the boundary can move (> to >=) so that the admissible maximum itself is refused (k_e_d0 = 1.0, which the canon text calls admissible: 'at most 1 (1 removes nothing)'), and the whole branch could be removed.
- **Evidence:** rules.py:184 `elif entry.at_most is not None and overrides[key] > entry.at_most:`; no test in the suite produces 'value_above_maximum' through rule_override_errors (the code appears in test files only for supplied quantities).
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P4-M10:** in `aero_kernel/rules.py` line 184: rule_override_errors: `overrides[key] > entry.at_most` -> `>=` (the admissible maximum itself is refused). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast tier, aero_kernel/tests/test_validate_rules.py, shipped model, the rule whose parameter k_e_d0 has `at_most: 1.0` and `positive: true`: override 1.0 -> no error; override 1.0000001 -> one error, code 'value_above_maximum', input_path 'rule_overrides.<rule>.k_e_d0', message containing '<= 1.0'.

## P5-F02 · medium · untested_error_path

- **Test file:** `aero_kernel/tests/test_validate.py` · no test exists
- **Production:** `aero_kernel/validate.py:1110`
- **Gap:** A NaN or infinite airplane.xyz_ref, which the ASB and AVL conversions read as the moment reference point, can stop being reported.
- **Evidence:** errors = _non_finite(airplane, "airplane", skip=frozenset({"wings", "fuselages"})) -- adding "xyz_ref" to the skip set passed 1239 tests; the only root-level non-finite test is total_mass_kg (test_a_non_finite_mass_is_an_error_and_no_warning).
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P5-M13:** in `aero_kernel/validate.py` line 1110: skip set of the root walk extended by "xyz_ref" (a non-finite reference point no longer reported). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_validate.py TestNonFinite, parametrised over index 0..2 and nan/inf/-inf: document["airplane"]["xyz_ref"] = [0.0, 0.0, 0.0] with one element replaced. Expect codes == ["non_finite_number"], paths == [f"airplane.xyz_ref[{i}]"], detail == {"value": str(bad)}.

## P5-F03 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_fuselage_contour.py` · existing test `TestContourDefect::test_a_figure_eight_is_refused` (line 80)
- **Production:** `aero_kernel/fuselage_contour.py:91`
- **Gap:** A contour whose vertex lies on a non-adjacent segment (touching without crossing) can be accepted; the rule says 'cross or touch other than at a shared vertex'.
- **Evidence:** FIGURE_EIGHT and the closing-segment case are proper crossings; replacing the collinear branch of _segments_meet ('return (d1 == 0 and _on_segment(c, d, a)) or ...') by 'return False' passed 1239 tests.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P5-M06:** in `aero_kernel/fuselage_contour.py` line 91: _segments_meet: the collinear/touching branch 'return (d1 == 0 and _on_segment(...)) or ...' -> 'return False'. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_fuselage_contour.py: contour [(0.0, 0.0), (0.04, 0.0), (0.04, 0.04), (0.02, 0.0), (0.0, 0.04)] in metres, MIN_POINTS 3. Point 3 lies on segment 0. Shoelace: 2A = 0 + 0.0016 - 0.0008 + 0.0008 + 0 = 0.0016, A = +0.0008 m^2, so orientation cannot refuse it. Expect defect is not None, 'crosses itself' in defect.message, defect.point == 2. Same contour once through validate_aircraft: code invalid_fuselage_contour at ...x_secs[i].contour[2].

## P5-F04 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_devices.py` · no test exists
- **Production:** `aero_kernel/devices.py:167`
- **Gap:** flap_deflections() can return deflected ailerons, elevators and rudders as flaps; flap_validity and butterfly_approach read it, so a flap-validity warning or the largest flap angle would be taken from a device that is no flap.
- **Evidence:** 'and device.role in FLAP_ROLES' removed from flap_deflections: 1495 passed (package files plus test_butterfly_approach.py, test_stall_speed_engine.py, test_roll_rate_engine.py, test_solvers_avl_flap.py, test_solvers_flap_devices.py, test_solvers_opti_roll_flaps.py, test_formulas.py, test_reference_fleet_helpers.py). test_devices.py does not import flap_deflections.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P5-M08:** in `aero_kernel/devices.py` line 167: flap_deflections: 'and device.role in FLAP_ROLES' removed. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_devices.py: main wing 'Main' with sections y = 0, 0.2, 0.4, 0.6, 0.8 m carrying {role flap, name 'F', deflection_deg 20.0}, {role flaperon, no name, deflection_deg -5.0}, {role aileron, name 'A', deflection_deg 3.0}, {role flap, name 'G', deflection_deg 0.0}, none. Expect flap_deflections(...) == [("Main", "F", 20.0), ("Main", "device 1", -5.0)]: only flap roles, a flap at rest left out, the unnamed one labelled by its section index.

## P5-F05 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_body_axis.py` · existing test `test_aerobuildup_gets_the_merged_bodies_straightened_after_the_merge` (line 108)
- **Production:** `aero_kernel/body_axis.py:137`
- **Gap:** aerobuildup_bodies() can ignore opt_body_axis_tolerance (1e-9 m): a body off its line by rounding noise would be moved and declared with fuselage_axis_straightened, although ch. 8.2 says it is unchanged and not declared.
- **Evidence:** expected, straightening = straight_axis(merged, config().opt_body_axis_tolerance.value) -- the merged body's shift is far above the tolerance; 'result = _straightened(bodies, 0.0)' passed 1304 tests (package files, test_solver_bodies.py, test_solvers_asb_airplane.py).
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P5-M23:** in `aero_kernel/body_axis.py` line 137: aerobuildup_bodies: '_straightened(bodies, config().opt_body_axis_tolerance.value)' -> '_straightened(bodies, 0.0)'. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_body_axis.py: an airplane with one body whose centres are (x, z) = (0, 0), (0.5, 1e-10), (1.0, 0) m (largest distance to the least-squares line 2e-10 / 3 = 6.7e-11 m < 1e-9 m). Expect aerobuildup_bodies(plane).straightenings == () and .bodies == solver_bodies(plane); and validate_aircraft on the same input has no warning fuselage_axis_straightened.

## P5-F06 · medium · missing_requirement_test · DECISION

- **Test file:** `aero_kernel/tests/test_validate_rules.py` · existing test `test_every_code_a_rule_names_is_a_code_the_kernel_reports` (line 177)
- **Production:** `aero_kernel/validate.py:765`
- **Gap:** A validation code can exist without a canon rule: non_positive_exponent is reported by validate.py but listed by no rule (positive-lengths states the exponent in its criterion and lists only non_positive_length). The trace test checks rule -> code only, and by a text search that any quoted occurrence in any source satisfies.
- **Evidence:** missing = [(rule_id, code) for ... for code in rule.codes if f'"{code}"' not in sources]; computed here: codes built in validate.py / body_attachment.py that no rule names = ['non_positive_exponent', 'not_an_input', 'unknown_quantity'].
- **Status:** READ_ONLY
- **Test to write:** Fast, test_validate_rules.py: collect the codes of every finding validate_aircraft can build (the code literals passed to _finding / KernelError in validate.py and the AttachmentCode literal) and assert each is in the union of rule.codes of the rules with applies_to.quantity in {airplane, components}; today it fails for non_positive_exponent, which is the canon finding to settle (add the code to positive-lengths or give the exponent its own rule). unknown_quantity and not_an_input belong to validate_values and are exempt by name.

## P5-F07 · medium · misleading_name

- **Test file:** `aero_kernel/tests/test_surface_properties.py` · existing test `test_a_single_panel_tail_has_the_hand_values` (line 52)
- **Production:** `aero_kernel/solvers/asb_airplane.py (surface_properties)`
- **Gap:** All seven tests of this file pin the test stand-in, not the kernel: the production surface_properties (AeroSandbox adapter) could return wrong area, span, MAC or x_LE,MAC and this file stays green. Production is pinned in the aero tier only.
- **Evidence:** from aero_kernel.tests.planform_stand_in import stand_in_surface_properties as surface_properties
- **Status:** READ_ONLY
- **Test to write:** Rename the file to test_planform_stand_in.py and drop the alias so the dashboard does not count it for production. Keep the same hand case in the aero tier against the real adapter: half panel y 0..0.2 m, chord 0.10 -> 0.05 m, x_le 0.50 -> 0.52 m, mirrored: area 2 * 0.2 * 0.075 = 0.03 m^2, span 0.4 m, AR 0.16 / 0.03, c_MAC = (2/3)(0.01 + 0.005 + 0.0025) / 0.15 = 0.077778 m (rel 1e-9; x_LE,MAC follows ASB's quarter-chord definition and is compared with ASB, not with the stand-in's 0.508889 m).

## P5-F08 · medium · missing_requirement_test · DECISION

- **Test file:** `aero_kernel/tests/test_validate.py` · no test exists
- **Production:** `aero_kernel/validate.py:643`
- **Gap:** The stated requirement 'flaperons XOR ailerons + flaps' has neither a rule nor a test: a wing carrying a flaperon, a flap and an aileron validates with no error and no warning, and no test says whether that is intended.
- **Evidence:** Checked by running validate_aircraft on a main wing with devices flaperon, flap, aileron (rel_chord_root 0.75): errors == [], warnings == []. test_devices.py pins only CROW_FLAP_ROLES == {'flap'} and CROW_AILERON_ROLES == {'aileron', 'elevon'}.
- **Status:** READ_ONLY
- **Test to write:** A maintainer decision first (rule or declared non-rule). Then fast, test_validate.py: main wing with sections y = 0, 0.2, 0.4, 0.6 m carrying roles flaperon, flap, aileron, none. Either assert the decided code at airplane.wings["Main wing"] or, if mixed layouts are admissible, assert errors == () and warnings == () under a test name that states it.

## P5-F09 · low · coverage_only

- **Test file:** `aero_kernel/tests/test_validate.py` · existing test `TestCanopyMerge::test_an_invalid_input_gets_no_merge_declaration` (line 1182)
- **Production:** `aero_kernel/validate.py:1122`
- **Gap:** This test passes whether or not the 'only for an admissible input' guard exists: an unknown parent is never merged anyway. The guard itself is pinned by the spinner and the axis variant.
- **Evidence:** result = _result(_with_canopy(_document(), attached_to="Fuselage")); assert "canopy_merged_into_fuselage" not in _codes_of_warnings(result) -- with 'if not errors:' replaced by 'if True:' only TestSpinner::test_an_invalid_spinner_gets_no_merge_declaration and TestFuselageAxisStraightened::test_an_invalid_input_gets_no_straightening_declaration fail.
- **Status:** READ_ONLY
- **Acceptance mutation P5-M04:** in `aero_kernel/validate.py` line 1122: 'if not errors:' -> 'if True:' (merge and axis declared for an inadmissible input). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_validate.py TestCanopyMerge: the document of _with_canopy(_document()) (a canopy that would merge) with the main wing's second chord set to -0.1 m. Expect codes of errors == ["non_positive_length"] and no warning with a code starting with 'canopy_'.

## P5-F10 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_validate.py` · existing test `TestBodyAttachment::test_a_canopy_reaching_behind_its_parent_is_refused_at_the_section` (line 1119)
- **Production:** `aero_kernel/validate.py:811`
- **Gap:** A finding can carry the hint of another rule: no geometry test asserts a hint, so an agent would be told the wrong remedy.
- **Evidence:** assert _codes(errors) == ["canopy_outside_parent"]; assert _paths(errors) == [f"{CANOPY}.x_secs[1].xyz[0]"]; assert "0.6" in errors[0].message -- with _ATTACHMENT_HINTS["invalid_body_attachment"] used for every attachment code, 1239 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P5-M15:** in `aero_kernel/validate.py` line 811: _ATTACHMENT_HINTS[defect.code] -> _ATTACHMENT_HINTS["invalid_body_attachment"] (wrong hint on the range and spinner findings). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_validate.py: for canopy_outside_parent assert 'within the x range' in error.hint, for spinner_not_adjoining_parent 'back plate' in error.hint, for invalid_body_attachment 'attached_to' in error.hint; one parametrised test over a document per validation code asserting error.hint names the field or the remedy (chord: '> 0').

## P5-F11 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_validate.py` · existing test `TestWingSections::test_one_section_is_rejected` (line 141)
- **Production:** `aero_kernel/validate.py:592`
- **Gap:** too_few_sections can lose its detail (the section count) unnoticed.
- **Evidence:** assert _paths(errors) == ['airplane.wings["Main wing"].x_secs']; assert _codes(errors) == ["too_few_sections"] -- dropping 'float(count)' from the finding passed 1239 tests.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P5-M19:** in `aero_kernel/validate.py` line 592: _too_few_sections: the detail value 'float(count)' dropped. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast: in test_one_section_is_rejected add assert errors[0].detail == {"value": 1.0}; in test_no_section_is_rejected assert the code and detail == {"value": 0.0}.

## P5-F12 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_validate.py` · existing test `TestInlineAirfoil::test_fewer_than_three_points_are_rejected` (line 638)
- **Production:** `aero_kernel/validate.py:410`
- **Gap:** The airfoil point minimum can become a literal 3 instead of the overridable canon parameter airfoil-resolvable.min_contour_points (maintainer rule: no threshold as a literal).
- **Evidence:** minimum_points = int(rules.value("airfoil-resolvable", "min_contour_points")) replaced by 'minimum_points = 3': 1239 passed. The same holds by reading for one-main-wing.required_main_wings.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P5-M24:** in `aero_kernel/validate.py` line 410: airfoil point minimum: rules.value("airfoil-resolvable", "min_contour_points") -> literal 3. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_validate.py: inline airfoil coordinates [[1.0, 0.0], [1.0, 0.0]] with rule_overrides {"airfoil-resolvable.min_contour_points": 2.0}. Without the override the code is invalid_airfoil_contour; with it the count rule passes, both ends lie at the largest x and the thickness is 0, so expect codes == ["non_positive_thickness"].

## P5-F13 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_dihedral.py` · existing test `test_a_root_off_the_centreline_weights_only_the_wing_that_exists` (line 65)
- **Production:** `aero_kernel/dihedral.py:61`
- **Gap:** A weighting that starts at the centreline instead of the root rib would pass: the test asserts a range, not the value.
- **Evidence:** assert 0.0 < found < math.degrees(math.atan2(0.07, 0.4)) -- hand value: chord 0.2, W1 = 0.2 (0.6^2 - 0.1^2) / 2 = 0.035, W2 = 0.2 (1.0^2 - 0.6^2) / 2 = 0.064, Gamma_2 = atan2(0.07, 0.4) = 9.92625 deg, Gamma_eq = 9.92625 * 0.064 / 0.099 = 6.41697 deg; weighting from y = 0 gives W1 = 0.036 and 6.35280 deg, also inside the range.
- **Status:** READ_ONLY
- **Test to write:** Fast: assert close(found, math.degrees(math.atan2(0.07, 0.4)) * 0.064 / 0.099, 1e-12) (6.41697 deg).

## P5-F14 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_surface_chain.py` · existing test `test_a_wing_chain_that_folds_back_names_y` (line 62)
- **Production:** `aero_kernel/surface_chain.py:115`
- **Gap:** The fold-back tests do not assert the code of rule sections-monotone-in-y, and the admissible boundary (two sections at one y, e.g. a vertical winglet panel) is stated only indirectly through test_dihedral.py.
- **Evidence:** with pytest.raises(FormulaError, match="fold back in y"): oriented_chain(wing, 1) -- '<' -> '<=' in the fold-back test is killed only by test_dihedral.py::test_a_wing_without_a_span_has_no_weighting_and_is_refused.
- **Status:** READ_ONLY
- **Acceptance mutation P5-M05:** in `aero_kernel/surface_chain.py` line 115: fold-back test 'along(outer) < along(inner)' -> '<='. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_surface_chain.py: assert raised.value.code == "unsupported_configuration" in both fold-back tests; add a chain (y, z) = (0, 0), (0.5, 0), (0.5, 0.1) with axis 1 and expect three points with y == [0.0, 0.5, 0.5], no error.

## P5-F15 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_schema.py` · existing test `TestKernelWarning::test_rejects_empty_text` (line 43)
- **Production:** `aero_kernel/schema.py:146`
- **Gap:** 24 refusals in test_schema.py (5 in test_errors.py) are asserted as 'some ValidationError', so a refusal for another reason keeps them green.
- **Evidence:** with pytest.raises(ValidationError):
- **Status:** READ_ONLY
- **Test to write:** Add match= with the field or message to each bare pytest.raises(ValidationError), e.g. match="at least 1 character" for the empty-text cases and match="finite" for the non-finite ones.

## P5-F16 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_validate.py` · existing test `TestFuselageSectionEquivalent::test_every_substituted_section_warns` (line 739)
- **Production:** `aero_kernel/validate.py:950`
- **Gap:** Several validate tests assert a count or a path without the code: two warnings of any code satisfy this one; test_no_section_is_rejected, test_non_finite_tuple_element_gets_an_index and the read-set tests assert the path only.
- **Evidence:** assert len(_result(document).warnings) == 2
- **Status:** READ_ONLY
- **Test to write:** Assert [w.code for w in warnings] == ["fuselage_section_equivalent"] * 2 and the two section paths in detail; add _codes(...) next to every bare _paths(...) assert.

## P5-F17 · low · untested_error_path

- **Test file:** `aero_kernel/tests/test_config.py` · no test exists
- **Production:** `aero_kernel/config.py:31`
- **Gap:** config() for a model without a configuration (RuntimeError) has no test.
- **Evidence:** if found is None: msg = "the canon model states no kernel configuration (config.yaml)"; raise RuntimeError(msg)
- **Status:** READ_ONLY
- **Test to write:** Fast, test_config.py: monkeypatch aero_kernel.build.shipped_build to return a build whose model.namespaces['calc'].config is None (the canon written by write_canon(tmp_path) without config.yaml) and expect RuntimeError matching 'config.yaml'.
