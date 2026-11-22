# WP-P6b — AVL: reference quantities, tail stations, fuselage body

Self-contained brief for one implementer subagent. Base commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

Every finding below was checked by an independent verifier on 2026-11-21 (`../rework/`). The line **Verified** says how. Where **Correction** appears, it overrides the text under **Test to write**.

- **Production code under test:** aero_kernel/solvers/avl*.py, solver_bodies.py
- **Requirement sources:** ARCHITECTURE §8.8, §8.10
- **Test files you may change:** `aero_kernel/tests/test_avl_contour.py`, `aero_kernel/tests/test_avl_hinge_mesh.py`, `aero_kernel/tests/test_avl_mesh_split.py`, `aero_kernel/tests/test_avl_writer.py`, `aero_kernel/tests/test_avl_writer_roll.py`, `aero_kernel/tests/test_solver_bodies.py`, `aero_kernel/tests/test_solvers_avl.py`, `aero_kernel/tests/test_solvers_avl_lateral.py`, `aero_kernel/tests/test_solvers_avl_loads.py`, `aero_kernel/tests/test_solvers_avl_roll.py`
- **Findings to work on:** 14 (1 high, 8 medium, 5 low)

## P6b-F03 · high · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_avl_hinge_mesh.py` · existing test `test_a_wing_without_a_control_in_the_role_is_not_split` (line 130)
- **Production:** `aero_kernel/solvers/avl_hinge.py:265`
- **Gap:** On a horizontal tail or fin of the hinge-moment mesh the stations are unchecked: the device ends need not be stations (a part-span elevator or rudder then controls the wrong strips or, with one bounding section lacking the CONTROL, none: AVL drives a strip only if both sections declare it), the tail need not take the wing's stations, and slivers next to a break need not be dropped.
- **Evidence:** names = [s.name for s in mesh.surfaces]
    assert "Tail right" in names
    assert "Tail right front" not in names  -- the only asserts on a tail of the hinge mesh are names and control signs; every tail/fin device of hinge_builders spans the whole surface.
- **Verified:** CONFIRMED (MUTATION_RERUN). _with_breaks is used only by _tail_stations and _rest_stations (avl_hinge.py:361, 370); the main wing goes through sine_to_tip. Dropping the device ends as stations leaves all fast tests green. The only asserts on a tail of the hinge mesh are names and signs, e.g. `assert "Tail right" in names` (test_avl_hinge_mesh.py:133); hinge_builders.conventional() puts the elevator on rib 0 of a two-rib tail and the rudder on rib 0 of a two-rib fin, so no inner break exists.
- **Verifier's note:** Aero candidate is uncertain: it asserts signs and non-zero only, and it fails only if a fleet tail (RV7 has elevator and rudder) carries a part-span device whose strips lose the control completely. Possibly no aero test fails.
- **Acceptance mutation:** `git apply rework/patches/WP-P6b/P6b-F03.patch` (from the audit folder; aero_kernel/solvers/avl_hinge.py:270  `return sorted({*kept, *inner})` -> `return sorted(kept)`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_avl_hinge_mesh.py: the conventional() airplane (wing half span 0.4 m, n_wing 12, strip 0.033333 m) with the tail replaced by wing_document('Tail', 'horizontal_tail', [(0.6, 0.0, 0.0, 0.1), (0.6, 0.07, 0.0, 0.1), (0.6, 0.15, 0.0, 0.1)], {1: device('elevator', 'elevator', 0.6)}), role 'elevator'. Expected y of 'Tail right aft': the wing's stations inside the tail span 0.033333, 0.066667, 0.1, 0.133333 (0.133333 < 0.15 - 0.3*0.033333 = 0.14 stays), the break 0.07 added and 0.066667 dropped because |0.066667 - 0.07| = 0.0033 < 0.01: [0.0, 0.033333, 0.07, 0.1, 0.133333, 0.15] to 1e-6; the control c01 on exactly [0.07, 0.1, 0.133333, 0.15] with x_hinge 0. (The unmutated code returns these values.) Add the same for a rudder that starts at the second rib of a three-rib fin.
- **Correction:** hand values (underspecified): (All stated tail values are right; only the last sentence lacks values.) Add the same for a rudder: conventional() with the fin replaced by wing_document('Fin', 'vertical_tail', [(0.6, 0.0, 0.0, 0.12), (0.6, 0.0, 0.055, 0.11), (0.6, 0.0, 0.12, 0.1)], {1: device('rudder', 'rudder', 0.6)}, symmetric=False), role 'rudder'. Fin height 0.12 m at the wing strip 0.033333 m gives round(3.6) = 4 strips, stations z = 0, 0.03, 0.06, 0.09, 0.12; the break 0.055 is added and 0.06 dropped (|0.06 - 0.055| = 0.005 < 0.01), 0.03 stays (0.025): expected z of the aft piece [0.0, 0.03, 0.055, 0.09, 0.12] to 1e-6, the control on exactly [0.055, 0.09, 0.12]. The strip count 4 follows the code's rounding rule, which the architecture text does not state; confirm it with the maintainer or state it in the test's docstring.

## P6b-F01 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_solvers_avl.py` · existing test `test_avl_gets_the_declared_and_the_refined_mesh_and_the_requested_cl` (line 87)
- **Production:** `aero_kernel/solvers/avl.py:538`
- **Gap:** The adapter can hand the wrong reference to the writer (Cref = span, or Bref = mean chord) and every fast test passes. The hinge moment is q*S_ref*c_ref*Chinge 'with the S_ref, c_ref the AVL file carries', and Clp / p'b/2V and the VM normalisation use the file's Bref, so the fast tier would ship moments wrong by b/c and roll rates wrong by c/b.
- **Evidence:** assert seen["n_chord"] == 20 / assert "a c 0.62" in seen["commands"] / assert "af0.dat" in seen["files"]  -- no adapter test reads the '#Sref    Cref    Bref' line of seen["geometry"]; mutated lines: c_ref=reference.b_ref (M01), b_ref=reference.c_mac (M07).
- **Verified:** CONFIRMED (MUTATION_RERUN). The span written as Cref in every AVL file leaves all 1383 fast tests green. No adapter test reads the reference line; the only fast asserts on the file of a run are e.g. `assert lines[lines.index("#Xref    Yref    Zref") + 1] == "0.05 0.0 0.01"` (test_solvers_avl_roll.py:119). The writer-level snapshots (test_avl_writer_roll.py) call avl_geometry themselves with `c_ref=reference.c_mac` and so cannot see the adapter's argument.
- **Verifier's note:** Only Chinge depends on Cref among the values the kernel reads (Xnp is absolute, roll/lateral coefficients use Bref), so the aero tier notices through one test only; test_the_explicit_halves_sum_... runs both sides through the mutated writer and stays green. The reviewer's second mutant (b_ref=reference.c_mac, M07) was not re-run.
- **Acceptance mutation:** `git apply rework/patches/WP-P6b/P6b-F01.patch` (from the audit folder; aero_kernel/solvers/avl.py:539  `c_ref=reference.c_mac,` -> `c_ref=reference.b_ref,`). Today every fast test stays green; after your change at least one fast test must fail under it. The aero tier catches it (aero_kernel/tests/test_solvers_avl_hinge_real.py::test_a_flap_on_a_wing_of_high_aspect_ratio_agrees_with_thin_airfoil_theory); the new test belongs in the fast tier.
- **Test to write:** Fast, test_solvers_avl_hinge.py (it already monkeypatches main_wing_properties to MainWingProperties(s_ref=0.16, c_mac=0.2, b_ref=0.8)): after `await hinge()` read seen(fake)['geometry'], take the line after '#Sref    Cref    Bref' and assert it equals '0.16 0.2 0.8' (three distinct values, so any swap fails). Add the same assert to test_solvers_avl_roll.py::test_roll_file_and_commands_reach_avl and test_solvers_avl_lateral.py::test_one_run_at_the_lift_coefficient_with_the_moment_reference_at_the_cg with the references of their airplanes computed once by hand (rectangular wing: S = 2*0.4*chord, c = chord, b = 0.8).
- **Correction:** hand values (wrong): Add the assert to test_solvers_avl_roll.py::test_roll_file_and_commands_reach_avl with S = 0.16 m^2, c = 0.2 m, b = 0.8 m (rolling_airplane: half span 0.4 m, chord 0.2 m) and to test_solvers_avl_lateral.py::test_one_run_at_the_lift_coefficient_with_the_moment_reference_at_the_cg with S = 0.28 m^2, c = 0.2 m, b = 1.4 m (np_builders MAIN: half span 0.7 m, chord 0.2 m). In these two tests the reference is not monkeypatched to literals (the fast tier's stand-in returns 0.16000000000000003 and 0.27999999999999997), so split the line after '#Sref    Cref    Bref' into three floats and compare each with rel 1e-9 instead of comparing the string. Only test_solvers_avl_hinge.py may assert the exact string '0.16 0.2 0.8'.

## P6b-F02 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_solvers_avl.py` · existing test `test_avl_gets_the_declared_and_the_refined_mesh_and_the_requested_cl` (line 87)
- **Production:** `aero_kernel/solvers/avl.py:713`
- **Gap:** The refinement check of the neutral point can run the 'refined' case on the declared 24 spanwise strips (only the chordwise count doubled) without a failure, so avl_mesh_not_converged would no longer measure what ARCHITECTURE 8.8 defines ('the same mesh refined by avl_refine_factor (both counts)').
- **Evidence:** seen = json.loads((fake / "seen.json").read_text())  # the last run: the refined one
    assert seen["n_chord"] == 20
- **Verified:** CONFIRMED (MUTATION_RERUN). The refined neutral-point run on the declared 24 spanwise strips leaves all fast tests green. The only assert on the refined file is `assert seen["n_chord"] == 20` (test_solvers_avl.py:90); the fake keys its answer on the chordwise count. ARCHITECTURE.md:998: 'the same mesh refined by `avl_refine_factor` (both counts)'.
- **Verifier's note:** By the severity rule this could be argued high (a missing warning reaches the caller); kept medium because the value itself is right and the reviewer rated it medium.
- **Acceptance mutation:** `git apply rework/patches/WP-P6b/P6b-F02.patch` (from the audit folder; aero_kernel/solvers/avl.py:713  `refined = mesh_surfaces(airplane, N_SPAN * REFINE_FACTOR, number, join_tolerance_m=join)` -> `refined = mesh_surfaces(airplane, N_SPAN, number, join_tolerance_m=join)`). Today every fast test stays green; after your change at least one fast test must fail under it. The aero tier catches it (aero_kernel/tests/test_neutral_point_fleet.py::test_chekker_declares_the_avl_mesh_as_not_converged_and_wiesel_converges); the new test belongs in the fast tier.
- **Test to write:** Fast, test_solvers_avl.py: in the same test count the SECTION lines of the first SURFACE block of seen['geometry'] (the main wing of airplane_with(*CONVENTIONAL)) and assert 49 (48 strips + 1) for the refined run; record the declared run too (let the fake append to a list) and assert 25. Same for the roll in test_solvers_avl_roll.py::test_the_wing_reaches_avl_as_a_front_and_an_aft_surface: 49 SECTION lines on 'Main front' in the last run.

## P6b-F04 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_solvers_avl_lateral.py` · existing test `test_a_deflected_flap_is_held_by_the_flap_control_and_declared` (line 154)
- **Production:** `aero_kernel/solvers/avl.py:982`
- **Gap:** The lateral run can stop splitting the flapped wing at the hinge (Drela's rule 3) without a failure; the flap's control derivative then carries the O(1/N_chord) hinge discretisation error the split exists to remove (4.5 to 7.5 % measured for the roll).
- **Evidence:** assert f"a c 0.6\nd1 d1 {FLAP}\nx\nst\n" in seen["commands"]
    assert "CONTROL" in seen["geometry"].splitlines()
- **Verified:** CONFIRMED (MUTATION_RERUN). The lateral run with an unsplit flapped wing leaves all fast tests green. The flap test asserts `assert f"a c 0.6\nd1 d1 {FLAP}\nx\nst\n" in seen["commands"]` and `assert "CONTROL" in seen["geometry"].splitlines()` (test_solvers_avl_lateral.py:157-158); neither sees the surfaces.
- **Verifier's note:** Aero candidate: the RV7 chain golden holds the -app (landing flap) lateral slugs at REL 2e-3; whether the unsplit mesh moves them beyond that is expected but not certain. By the rule a changed value reaches the caller, so high is arguable; kept at the reviewer's medium because only the flapped configuration is touched.
- **Acceptance mutation:** `git apply rework/patches/WP-P6b/P6b-F04.patch` (from the audit folder; aero_kernel/solvers/avl.py:982  `if flaps:` -> `if False:` (lateral_derivatives no longer splits the flapped wing at the hinge)). Today every fast test stays green; after your change at least one fast test must fail under it. The aero tier catches it (aero_kernel/tests/test_mvp_chain_fleet.py::test_the_chain_per_world_is_the_regression_golden[FleetMember.RV7]); the new test belongs in the fast tier.
- **Test to write:** Fast, same test: from seen['geometry'] collect the names after each 'SURFACE' line and the counts after '#Nchordwise  Cspace' and assert ['Main front', 'Main aft'] and ['12   1', '8   1']; assert every CONTROL line has x_hinge 0.0 (hinge at the aft piece's leading edge).

## P6b-F05 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_solver_bodies.py` · existing test `test_the_stations_are_the_union_with_exact_duplicates_collapsed` (line 93)
- **Production:** `aero_kernel/solver_bodies.py:204`
- **Gap:** The section of a body at an inserted station can ignore the taper (half-width taken from the lower neighbour instead of interpolated) without a failure: every parent and canopy of the tests has constant a, b, n and centre along x. A real fuselage tapers, so the merged body's width at every canopy station, its area for the AVL body radius and its wetted area would be wrong.
- **Evidence:** assert [s.xyz[0] for s in found.x_secs] == [0.0, 0.3, 0.5, 0.6, 1.0]  -- the only assert on inserted stations is their x; fuselage_box() is [section(0.0, 0.05, 0.04), section(0.5, 0.05, 0.04), section(1.0, 0.05, 0.04)].
- **Verified:** CONFIRMED (MUTATION_RERUN). _lerp without interpolating the half-width leaves all fast tests green. Every parent of test_solver_bodies.py is prismatic: `return body([section(0.0, 0.05, 0.04), section(0.5, 0.05, 0.04), section(1.0, 0.05, 0.04)])`, and the only assert on inserted stations is `assert [s.xyz[0] for s in found.x_secs] == [0.0, 0.3, 0.5, 0.6, 1.0]`.
- **Verifier's note:** The same test should pin b, the centre and the exponents of _lerp too; the reviewer's probe covers a only.
- **Acceptance mutation:** `git apply rework/patches/WP-P6b/P6b-F05.patch` (from the audit folder; aero_kernel/solver_bodies.py:204  `a=mix(low.a, high.a),` -> `a=low.a,`). Today every fast test stays green; after your change at least one fast test must fail under it. The aero tier catches it (aero_kernel/tests/test_minimum_drag_speed_fleet.py::test_regression_goldens_with_the_xlarge_model[FleetMember.BRYAN]); the new test belongs in the fast tier.
- **Test to write:** Fast, test_solver_bodies.py: parent body([section(0.0, 0.02, 0.02, z=0.0), section(1.0, 0.06, 0.04, z=0.02)]) and a narrow canopy far above it, body([section(0.25, 0.01, 0.01, z=0.2), section(0.75, 0.01, 0.01, z=0.2)], 'canopy', 'Rumpf'). The canopy is narrower than the parent, so the merged half-width is the interpolated parent's: at x = 0.25 a = 0.02 + 0.25*0.04 = 0.03 and the bottom z - b = 0.005 - 0.025 = -0.02; at x = 0.75 a = 0.05, bottom 0.015 - 0.035 = -0.02. Assert station.a (rel 1e-6) and station.xyz[2] - station.b (abs 1e-9) at both inserted stations (the unmutated code returns exactly these). A second case with n = 2 at one parent section and n = 4 at the next pins the interpolation of the exponents through the area of the parent-only half.
- **Correction:** hand values (underspecified): (All stated values of the first case are right; only the second case lacks values.) Second case: state the sections and the expected area explicitly, e.g. parent sections with equal a, b, z and n = 2 at x = 0 and n = 4 at x = 1, canopy stations at x = 0.5; the interpolated parent exponent there is 3, its lower half (below the parent's centre) has the area 2 a b f(3) with f(3) = Gamma(4/3)^2 / Gamma(5/3) = 0.883319 (against 0.785398 for n = 2 taken from the lower neighbour). Compare the area of the merged outline below the parent's centre z with that value, not the refitted section's own lower half, because the refit puts the centre in the middle of the envelope.

## P6b-F06 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_solver_bodies.py` · existing test `test_the_refit_keeps_the_area_of_the_envelope_with_its_notch` (line 132)
- **Production:** `aero_kernel/solver_bodies.py:360`
- **Gap:** The refit can assign the upper half's exponent to the lower half and vice versa (the merged body upside down: the canopy's bulge underneath) and all tests pass, because only the sum of both halves is compared.
- **Evidence:** assert math.isclose(area(station), _union_area(parts), rel_tol=5e-5)
    assert station.n != station.n_lower
- **Verified:** CONFIRMED (MUTATION_RERUN). The swap leaves all fast tests green: `assert math.isclose(area(station), _union_area(parts), rel_tol=5e-5)` is symmetric in the two exponents and `assert station.n != station.n_lower` still holds. For a canopy merge alone the swap is invisible to every consumer (avl_body.section_area, asb_airplane.equivalent_exponent, outline_perimeter all sum both halves). I built an input where it is visible: a canopy starting at the parent's nose station plus a spinner joined there; _join_spinner refits the already merged section, and the AVL body radius at the joint changes from 0.056155 to 0.058568 m (area 0.009907 -> 0.010776 m^2).
- **Verifier's note:** The reviewer's impact ('the canopy's bulge underneath') overstates what a solver sees today: AVL takes an equal-area round body and AeroSandbox one equivalent exponent. No aero test reaches the differing case (no fleet aircraft has a canopy on the spinner joint).
- **Acceptance mutation:** `git apply rework/patches/WP-P6b/P6b-F06.patch` (from the audit folder; aero_kernel/solver_bodies.py:360-361  `n=n_upper, n_lower=n_lower,` -> `n=n_lower, n_lower=n_upper,`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, same test: split the independent grid at the middle of the envelope z_mid = (0.07 - 0.04)/2 = 0.015 and assert 2*a*b*quadrant_area_fraction(station.n) equals the grid area above z_mid and 2*a*b*quadrant_area_fraction(station.n_lower) the one below, each rel 1e-4. For the rectangle case of test_a_canopy_floating_above_the_parent_has_its_gap_filled the two halves are computable by hand (total height 0.13, middle at z = 0.025: below 0.065*0.10 = 0.0065 m^2, above 0.015*0.10 + 0.01*0.06 + 0.04*0.06 = 0.0045 m^2).

## P6b-F08 · medium · golden_without_independent_check

- **Test file:** `aero_kernel/tests/test_avl_writer_roll.py` · existing test `test_clean_mesh_and_file_unchanged` (line 47)
- **Production:** `aero_kernel/solvers/avl_writer.py:274`
- **Gap:** The order and meaning of the numbers of a SECTION line (Xle Yle Zle Chord Ainc) are pinned only by byte snapshots that the writer itself produced; a snapshot regenerated after a writer change would accept swapped fields. No fast test asserts a section line with meaning.
- **Evidence:** expected = (SNAPSHOTS / f"{member.name.lower()}_clean.avl").read_text()
    assert written(member, roll=False) == expected  -- swapping chord and twist in the SECTION line fails these seven snapshot tests and nothing else.
- **Verified:** CONFIRMED_BY_READING (MUTATION_RERUN). Re-ran the probe without -x: exactly 7 tests fail, all byte snapshots: `assert written(member, roll=False) == expected` with `expected = (SNAPSHOTS / f"{member.name.lower()}_clean.avl").read_text()`; 1376 others pass. No fast test asserts the content of a SECTION line (grep 'SECTION' in the writer and mesh tests finds only counts, e.g. `assert body.count("SECTION\n") == sum(len(s.sections) for s in surfaces)`). The claim as stated (pinned only by snapshots the writer produced) is true; the mutation itself is killed today.
- **Verifier's note:** killed = true refers to the snapshot tests; the verdict is about the finding's claim, which is not that the mutation survives.
- **Acceptance mutation:** `git apply rework/patches/WP-P6b/P6b-F08.patch` (from the audit folder; aero_kernel/solvers/avl_writer.py:274  `{section.chord!r} {section.twist!r}   {_STRIP}` -> `{section.twist!r} {section.chord!r}   {_STRIP}`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_avl_writer.py: one MeshSurface with a single hand-made MeshSection(x=0.01, y=0.2, z=0.03, chord=0.15, twist=1.5, airfoil=0) twice; assert the line after '#Xle    Yle    Zle     Chord   Ainc  Nspanwise  Sspace' equals '0.01 0.2 0.03 0.15 1.5   1   1' (five distinct values; metres and degrees).

## P6b-F09 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_avl_contour.py` · existing test `test_the_count_is_fixed_whatever_the_input` (line 18)
- **Production:** `aero_kernel/solvers/avl_contour.py:46`
- **Gap:** The contour can be resampled at uniform instead of cosine-spaced x and all tests pass; ARCHITECTURE 8.8 specifies 80 cosine-spaced points per side (resolution of the leading edge, from which AVL takes the camber slope).
- **Evidence:** assert len(repanel(ellipse(n), 80)) == 159  /  assert contour[79][0] == 0.0  -- no assert on any interior x.
- **Verified:** CONFIRMED (MUTATION_RERUN). Uniform instead of cosine stations leaves all fast tests green; test_avl_contour.py asserts count, end points and thickness only, e.g. `assert len(repanel(ellipse(n), 80)) == 159` and `assert contour[79][0] == 0.0`. ARCHITECTURE.md:990 requires '(80) cosine-spaced points per side'.
- **Verifier's note:** Aero candidate is weak: in a linear vortex lattice the neutral point and the roll are independent of camber; only quantities at a fixed C_L that depend on the angle of attack (lateral derivatives of a cambered-wing aircraft, REL 2e-3) can move. Possibly no aero test fails.
- **Acceptance mutation:** `git apply rework/patches/WP-P6b/P6b-F09.patch` (from the audit folder; aero_kernel/solvers/avl_contour.py:46  `stations = 0.5 * (1.0 - np.cos(np.pi * np.arange(points_per_side) / (points_per_side - 1)))` -> `stations = np.arange(points_per_side) / (points_per_side - 1)`). Today every fast test stays green; after your change at least one fast test must fail under it. The aero tier catches it (aero_kernel/tests/test_mvp_chain_fleet.py::test_the_chain_per_world_is_the_regression_golden[FleetMember.BRYAN]); the new test belongs in the fast tier.
- **Test to write:** Fast, test_avl_contour.py: contour = repanel(ellipse(50), 5); the upper side's x must be [1.0, 0.853553, 0.5, 0.146447, 0.0] = 0.5*(1 - cos(pi*k/4)) for k = 4..0 (abs 1e-6), and the lower side the same ascending.

## P6b-F10 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_solvers_avl_loads.py` · existing test `test_the_rows_of_the_first_surface_come_back_in_metres_per_dynamic_pressure` (line 56)
- **Production:** `aero_kernel/solvers/avl.py:795`
- **Gap:** The adapter can hand Sref where the reader expects Bref (and the reverse): station positions, shear and bending moment come back scaled wrongly and the fast tier is green, because the adapter test asserts only the strip columns and y_station[0] == 0.
- **Evidence:** assert found.y_strip == (0.0146, 0.0437, 0.0729)
    assert found.c_cl == (0.1392, 0.1391, 0.1389)
    assert found.y_station[0] == 0.0
    assert found.warnings == ()
- **Verified:** CONFIRMED (MUTATION_RERUN). Swapping Bref and Sref at the reader leaves all fast tests green. The adapter test asserts `assert found.y_station[0] == 0.0` and nothing else of the shear table. With the test's own fixture and airplane (S 0.28, b 1.4) the swap gives y_station (0.0, 0.002912, 0.14) instead of (0.0, 0.01456, 0.7) and shear[0] 0.417694 instead of 0.083539.
- **Verifier's note:** Severity raised from medium to high by the common rule. The reviewer's note that the swap changes the moment is wrong; the finding stands on y_station and shear.
- **Acceptance mutation:** `git apply rework/patches/WP-P6b/P6b-F10.patch` (from the audit folder; aero_kernel/solvers/avl.py:795  `parse_loads_output(stdout, strips, shear_moment, reference.b_ref, reference.s_ref)` -> `parse_loads_output(stdout, strips, shear_moment, reference.s_ref, reference.b_ref)`). Today every fast test stays green; after your change at least one fast test must fail under it. The aero tier catches it (aero_kernel/tests/test_spanwise_loads_real.py::test_the_load_of_the_half_wing_is_half_the_weight_and_the_curves_agree_with_each_other); the new test belongs in the fast tier.
- **Test to write:** Fast, same test (CONVENTIONAL airplane of np_builders: S_ref 0.28 m^2, b_ref 1.4 m as in test_avl_writer.py): assert found.y_station == (0.0, 0.0208*0.7, 0.7), found.shear[0] == approx(0.298353*0.28, rel 1e-9) and found.moment[0] == approx(0.0669065*0.28*1.4, rel 1e-9), the hand values test_avl_writer_loads.py already derives.

## P6b-F07 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_avl_mesh_split.py` · existing test `test_stations_off_the_device_take_the_cut_of_the_nearest_controlled_station` (line 64)
- **Production:** `aero_kernel/solvers/avl_mesh.py:412`
- **Gap:** Stations outboard of a device can take the cut of the first controlled station of the wing instead of the nearest one; the front/aft cut then jumps at the outboard device end. The production docstring calls the cut 'continuous and otherwise immaterial', so the effect on a result is small.
- **Evidence:** root = front.sections[0]
    assert math.isclose(root.chord_range[1], 0.7)  -- device on the outer panel only, so nearest == first controlled.
- **Verified:** CONFIRMED_BY_READING (READING). split_of returns `min(controlled, key=lambda c: abs(c[0] - section.y))[1]` (avl_mesh.py:412); the only test has the device on the outer panel (`plane = wing_geometry((0.0, 0.2, 0.4), 1, aileron(0.7, 0.8))`) and asserts the root only: `assert math.isclose(root.chord_range[1], 0.7)`, so nearest and first controlled station coincide. No test has a station outboard of a device.
- **Verifier's note:** keep: the cut sets the chordwise lattice of the driven wing, so it enters the roll rate and flap results (small effect); the test is one short case in an existing file.
- **Test to write:** Fast, test_avl_mesh_split.py: wing ribs y = 0, 0.2, 0.4, 0.6 with aileron(0.7, 0.8) on rib 1 (y 0.2..0.4), drive_roll, split; assert front.sections[-1].chord_range[1] == 0.8 (tip takes the outboard end's hinge) and front.sections[0].chord_range[1] == 0.7.

## P6b-F12 · low · over_mocked

- **Test file:** `aero_kernel/tests/test_avl_writer.py` · existing test `test_the_output_is_read_by_its_first_hit_of_each_key` (line 86)
- **Production:** `aero_kernel/solvers/avl_writer.py:427`
- **Gap:** The readers of the neutral point, the hinge table and the lateral block, and all five fake executables, are fed lines the test author wrote to fit the regular expressions; only the loads files are stated to be recorded AVL 3.40 output. A change of AVL's real layout (e.g. 'Neutral point  Xnp =', a control name longer than its column, '*******' overflow fields) is noticed only in the aero tier.
- **Evidence:** out = " Sref = 0.28000  Cref = 0.2\n CLtot =   0.50000\n Xnp = 0.131\n Clb Cnr / Clr Cnb = 1\n Xnp = 9.9\n"
- **Verified:** CONFIRMED_BY_READING (READING). The reader tests feed hand-written lines: `out = " Sref = 0.28000  Cref = 0.2\n CLtot =   0.50000\n Xnp = 0.131\n Clb Cnr / Clr Cnb = 1\n Xnp = 9.9\n"` (test_avl_writer.py:87), and the fakes print their own, e.g. `print(" Xnp = %r" % config["xnp"][str(n_chord)])`. Only the loads fixtures state their origin: '# Trimmed copies of the files AVL 3.40 wrote' (test_avl_writer_loads.py:7). aero_kernel/tests/fixtures holds no recorded AVL output.
- **Verifier's note:** keep: the readers turn AVL's text into every value and into the 'did not complete' errors the caller sees; a layout the regular expressions do not expect is exactly the case a fast test should hold.
- **Test to write:** Fast: record once, with the real binary, the complete stdout of one neutral-point run, one steady-roll run, one hinge run and one lateral run of aileron_trainer (or CONVENTIONAL) into aero_kernel/tests/fixtures/avl_outputs/*.txt, and parse them in the fast tier against the numbers read off the file by eye (Xnp, CLtot, p'b/2V, Clp, Cld01, each Chinge row, six derivatives). Add one recorded output with a Fortran '*******' field and one cut in the middle of the stability block -> None.
- **Correction:** (unclear) Needs one run of the real binary per reader to record the outputs (not possible in the fast tier itself) and a decision where the files live; the '*******' overflow case has to be produced or constructed by hand.

## P6b-F13 · low · redundant · do together with P6b-F03

- **Test file:** `aero_kernel/tests/test_avl_hinge_mesh.py` · existing test `test_a_device_without_a_name_is_keyed_like_the_geometry_format_derives_it` (line 339)
- **Production:** `aero_kernel/solvers/avl_hinge.py:139`
- **Gap:** The test repeats the second half of test_a_device_name_falls_back_to_its_label_and_then_its_role (line 90) with the same input and the same expected keys; test_the_role_sets_are_those_of_the_conditions_and_the_roll_rule (line 323) partly compares constants with the expression that defines them.
- **Evidence:** bare = device(None, "elevator", 0.6)
    assert list(controls_by_key(mesh_of(conventional(tail={0: bare}), "elevator"))) == ["Tail.elevator_right", "Tail.elevator_left"]
- **Verified:** CONFIRMED_BY_READING (READING). test_a_device_without_a_name_is_keyed_like_the_geometry_format_derives_it (test_avl_hinge_mesh.py:339) is `bare = device(None, "elevator", 0.6)` / `assert list(controls_by_key(mesh_of(conventional(tail={0: bare}), "elevator"))) == ["Tail.elevator_right", "Tail.elevator_left"]`, the same input and expectation as the second half of test_a_device_name_falls_back_to_its_label_and_then_its_role (line 90). In the role-set test `assert COMMAND_SIGNS["aileron"] == (round(roll_deflection(1, 1.0)), round(roll_deflection(-1, 1.0)))` repeats the defining expression of avl_hinge.py:71; the literal `(-1, 1)` follows it.
- **Verifier's note:** bundle: trivial and in the file F03 changes anyway; the added sign literals protect the sign of every hinge moment.
- **Test to write:** Merge the duplicate into test_a_device_name_falls_back_to_its_label_and_then_its_role; in the role-set test keep the literal assert COMMAND_SIGNS['aileron'] == (-1, 1) and add the literals for elevator (1, 1), rudder (1, -1), flap (1, 1).

## P6b-F14 · low · coverage_only · do together with P6b-F02

- **Test file:** `aero_kernel/tests/test_solvers_avl.py` · existing test `test_the_module_states_its_sources` (line 193)
- **Production:** `aero_kernel/solvers/avl.py:121`
- **Gap:** The test compares a module constant with its own literal and says nothing about CLAF as written; the rule CLAF = 1 + 0.77 t/c is checked only in the aero tier of another package (test_neutral_point_fleet.py::test_claf_follows_the_thickness_rule_of_the_airfoil), and contour_worker has no fast test. test_the_run_limit_is_far_above_the_measured_refined_run likewise compares a constant with a bound.
- **Evidence:** assert avl_module.CLAF_PER_THICKNESS == 0.77
- **Verified:** CONFIRMED_BY_READING (READING). `def test_the_module_states_its_sources() -> None:` / `assert avl_module.CLAF_PER_THICKNESS == 0.77` (test_solvers_avl.py:193) and `assert avl_module.AVL_MAX_RUN_S >= 4 * 15` (line 271) compare constants with literals. contour_worker is called only in test_neutral_point_fleet.py (lines 215, 243, 249), a module with `pytestmark = [pytest.mark.aero]`; the fast FakeAvl replaces _contours with a fixed `claf=1.0924`.
- **Verifier's note:** bundle: the fast-tier part is a rename/strengthening inside test_solvers_avl.py, which F02 edits; the CLAF rule itself is held by test_claf_follows_the_thickness_rule_of_the_airfoil.
- **Test to write:** Fast, test_solvers_avl.py: call contour_worker with one InlineAirfoil lens of 12 % thickness (the ellipse() of test_avl_contour.py) if AeroSandbox imports in the fast tier, else inject max_thickness; assert claf == approx(1 + 0.77*0.12, rel 2e-3) and len(coordinates) == 159. Rename or drop the constant-equals-literal test.
- **Correction:** (unclear) contour_worker calls load_aerosandbox() and asb.Airfoil(...).max_thickness() (avl.py:259-268), so the recommended fast test runs only where AeroSandbox imports; 'inject max_thickness' has no seam in the current code. The existing constant tests must stay unless replaced by a stronger one (no deletion).

## P6b-F15 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_solvers_avl_roll.py` · existing test `test_more_than_fifty_chordwise_vortices_on_one_surface_are_refused` (line 279)
- **Production:** `aero_kernel/solvers/avl.py:499`
- **Gap:** The array limits are tested well above (51, and monkeypatched small limits) but never at the boundary: a mesh with exactly 50 chordwise vortices, 500 strips, 6000 vortices or 100 surfaces could be refused (> turned into >=) without a failure.
- **Evidence:** monkeypatch.setattr("aero_kernel.solvers.avl.SPLIT_N_CHORD", (51, 8))
    ...
    assert raised.value.detail["n_chord"] == 51
- **Verified:** CONFIRMED_BY_READING (READING). The limits are `if widest > AVL_MAX_CHORD_VORTICES:` and `strips > AVL_MAX_STRIPS or vortices > AVL_MAX_VORTICES or surface_count > AVL_MAX_SURFACES` (avl.py:499, 514-516). Tests sit away from the boundary: `monkeypatch.setattr("aero_kernel.solvers.avl.SPLIT_N_CHORD", (51, 8))`, `(26, 8)` (refined 52), and `[("AVL_MAX_STRIPS", 10), ("AVL_MAX_VORTICES", 100), ("AVL_MAX_SURFACES", 3)]` against a mesh of 96 strips. No test runs a mesh exactly at a limit.
- **Verifier's note:** keep: turning > into >= would refuse a legal mesh with unsupported_configuration, an error that reaches the caller.
- **Test to write:** Fast, test_solvers_avl_roll.py: SPLIT_N_CHORD = (50, 8) with configure(fake, {'50': 0.05}) -> a value (p_hat 0.05) and avl_refinement_unchecked for the refined 100; AVL_MAX_STRIPS monkeypatched to 96 (the declared mesh has exactly 96 strips) -> no error, 95 -> avl_array_limit.

## Not part of this package's work

| Finding | State | Reason |
|---|---|---|
| P6b-F11 | production_defect | #1444 |
| P6b-F16 | dropped | drop from this package: the goldens are declared as regression by design and the same code path is validated on BRYAN and JAGUAR. The one uncovered case, the roll with a held flap, has no independent reference; that is worth a separate vali |
