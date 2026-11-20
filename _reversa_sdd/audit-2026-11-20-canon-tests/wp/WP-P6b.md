# WP-P6b — AVL: Referenzgrößen, Leitwerks-Stationen, Rumpfkörper

Self-contained brief for one implementer subagent. Frozen review state: commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

- **Production code under test:** aero_kernel/solvers/avl*.py, solver_bodies.py
- **Requirement sources:** ARCHITECTURE §8.8, §8.10
- **Test files you may change:** `aero_kernel/tests/test_avl_contour.py`, `aero_kernel/tests/test_avl_hinge_mesh.py`, `aero_kernel/tests/test_avl_mesh_split.py`, `aero_kernel/tests/test_avl_writer.py`, `aero_kernel/tests/test_avl_writer_roll.py`, `aero_kernel/tests/test_solver_bodies.py`, `aero_kernel/tests/test_solvers_avl.py`, `aero_kernel/tests/test_solvers_avl_lateral.py`, `aero_kernel/tests/test_solvers_avl_loads.py`, `aero_kernel/tests/test_solvers_avl_roll.py`, `aero_kernel/tests/test_solvers_avl_roll_real.py`
- **Findings:** 16 (3 high, 7 medium, 6 low)

A finding marked **DECISION** needs the maintainer's answer first: do not write its test, list it in your report as open.

## P6b-F01 · high · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_solvers_avl.py` · existing test `test_avl_gets_the_declared_and_the_refined_mesh_and_the_requested_cl` (line 87)
- **Production:** `aero_kernel/solvers/avl.py:538`
- **Gap:** The adapter can hand the wrong reference to the writer (Cref = span, or Bref = mean chord) and every fast test passes. The hinge moment is q*S_ref*c_ref*Chinge 'with the S_ref, c_ref the AVL file carries', and Clp / p'b/2V and the VM normalisation use the file's Bref, so the fast tier would ship moments wrong by b/c and roll rates wrong by c/b.
- **Evidence:** assert seen["n_chord"] == 20 / assert "a c 0.62" in seen["commands"] / assert "af0.dat" in seen["files"]  -- no adapter test reads the '#Sref    Cref    Bref' line of seen["geometry"]; mutated lines: c_ref=reference.b_ref (M01), b_ref=reference.c_mac (M07).
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P6b-M01:** in `aero_kernel/solvers/avl.py` line 539: _execute_collecting: c_ref=reference.c_mac -> c_ref=reference.b_ref (the span written as Cref). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_solvers_avl_hinge.py (it already monkeypatches main_wing_properties to MainWingProperties(s_ref=0.16, c_mac=0.2, b_ref=0.8)): after `await hinge()` read seen(fake)['geometry'], take the line after '#Sref    Cref    Bref' and assert it equals '0.16 0.2 0.8' (three distinct values, so any swap fails). Add the same assert to test_solvers_avl_roll.py::test_roll_file_and_commands_reach_avl and test_solvers_avl_lateral.py::test_one_run_at_the_lift_coefficient_with_the_moment_reference_at_the_cg with the references of their airplanes computed once by hand (rectangular wing: S = 2*0.4*chord, c = chord, b = 0.8).

## P6b-F03 · high · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_avl_hinge_mesh.py` · existing test `test_a_wing_without_a_control_in_the_role_is_not_split` (line 130)
- **Production:** `aero_kernel/solvers/avl_hinge.py:265`
- **Gap:** On a horizontal tail or fin of the hinge-moment mesh the stations are unchecked: the device ends need not be stations (a part-span elevator or rudder then controls the wrong strips or, with one bounding section lacking the CONTROL, none: AVL drives a strip only if both sections declare it), the tail need not take the wing's stations, and slivers next to a break need not be dropped.
- **Evidence:** names = [s.name for s in mesh.surfaces]
    assert "Tail right" in names
    assert "Tail right front" not in names  -- the only asserts on a tail of the hinge mesh are names and control signs; every tail/fin device of hinge_builders spans the whole surface.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P6b-M02:** in `aero_kernel/solvers/avl_hinge.py` line 270: _with_breaks: return sorted({*kept, *inner}) -> return sorted(kept) (device ends no longer added as stations on tail/fin). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_avl_hinge_mesh.py: the conventional() airplane (wing half span 0.4 m, n_wing 12, strip 0.033333 m) with the tail replaced by wing_document('Tail', 'horizontal_tail', [(0.6, 0.0, 0.0, 0.1), (0.6, 0.07, 0.0, 0.1), (0.6, 0.15, 0.0, 0.1)], {1: device('elevator', 'elevator', 0.6)}), role 'elevator'. Expected y of 'Tail right aft': the wing's stations inside the tail span 0.033333, 0.066667, 0.1, 0.133333 (0.133333 < 0.15 - 0.3*0.033333 = 0.14 stays), the break 0.07 added and 0.066667 dropped because |0.066667 - 0.07| = 0.0033 < 0.01: [0.0, 0.033333, 0.07, 0.1, 0.133333, 0.15] to 1e-6; the control c01 on exactly [0.07, 0.1, 0.133333, 0.15] with x_hinge 0. (The unmutated code returns these values.) Add the same for a rudder that starts at the second rib of a three-rib fin.

## P6b-F05 · high · missing_edge_case

- **Test file:** `aero_kernel/tests/test_solver_bodies.py` · existing test `test_the_stations_are_the_union_with_exact_duplicates_collapsed` (line 93)
- **Production:** `aero_kernel/solver_bodies.py:204`
- **Gap:** The section of a body at an inserted station can ignore the taper (half-width taken from the lower neighbour instead of interpolated) without a failure: every parent and canopy of the tests has constant a, b, n and centre along x. A real fuselage tapers, so the merged body's width at every canopy station, its area for the AVL body radius and its wetted area would be wrong.
- **Evidence:** assert [s.xyz[0] for s in found.x_secs] == [0.0, 0.3, 0.5, 0.6, 1.0]  -- the only assert on inserted stations is their x; fuselage_box() is [section(0.0, 0.05, 0.04), section(0.5, 0.05, 0.04), section(1.0, 0.05, 0.04)].
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P6b-M09:** in `aero_kernel/solver_bodies.py` line 204: _lerp: a=mix(low.a, high.a) -> a=low.a. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_solver_bodies.py: parent body([section(0.0, 0.02, 0.02, z=0.0), section(1.0, 0.06, 0.04, z=0.02)]) and a narrow canopy far above it, body([section(0.25, 0.01, 0.01, z=0.2), section(0.75, 0.01, 0.01, z=0.2)], 'canopy', 'Rumpf'). The canopy is narrower than the parent, so the merged half-width is the interpolated parent's: at x = 0.25 a = 0.02 + 0.25*0.04 = 0.03 and the bottom z - b = 0.005 - 0.025 = -0.02; at x = 0.75 a = 0.05, bottom 0.015 - 0.035 = -0.02. Assert station.a (rel 1e-6) and station.xyz[2] - station.b (abs 1e-9) at both inserted stations (the unmutated code returns exactly these). A second case with n = 2 at one parent section and n = 4 at the next pins the interpolation of the exponents through the area of the parent-only half.

## P6b-F02 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_solvers_avl.py` · existing test `test_avl_gets_the_declared_and_the_refined_mesh_and_the_requested_cl` (line 87)
- **Production:** `aero_kernel/solvers/avl.py:713`
- **Gap:** The refinement check of the neutral point can run the 'refined' case on the declared 24 spanwise strips (only the chordwise count doubled) without a failure, so avl_mesh_not_converged would no longer measure what ARCHITECTURE 8.8 defines ('the same mesh refined by avl_refine_factor (both counts)').
- **Evidence:** seen = json.loads((fake / "seen.json").read_text())  # the last run: the refined one
    assert seen["n_chord"] == 20
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P6b-M20:** in `aero_kernel/solvers/avl.py` line 713: neutral_point: refined = mesh_surfaces(airplane, N_SPAN * REFINE_FACTOR, ...) -> N_SPAN (refined run on the declared spanwise mesh). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_solvers_avl.py: in the same test count the SECTION lines of the first SURFACE block of seen['geometry'] (the main wing of airplane_with(*CONVENTIONAL)) and assert 49 (48 strips + 1) for the refined run; record the declared run too (let the fake append to a list) and assert 25. Same for the roll in test_solvers_avl_roll.py::test_the_wing_reaches_avl_as_a_front_and_an_aft_surface: 49 SECTION lines on 'Main front' in the last run.

## P6b-F04 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_solvers_avl_lateral.py` · existing test `test_a_deflected_flap_is_held_by_the_flap_control_and_declared` (line 154)
- **Production:** `aero_kernel/solvers/avl.py:982`
- **Gap:** The lateral run can stop splitting the flapped wing at the hinge (Drela's rule 3) without a failure; the flap's control derivative then carries the O(1/N_chord) hinge discretisation error the split exists to remove (4.5 to 7.5 % measured for the roll).
- **Evidence:** assert f"a c 0.6\nd1 d1 {FLAP}\nx\nst\n" in seen["commands"]
    assert "CONTROL" in seen["geometry"].splitlines()
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P6b-M06:** in `aero_kernel/solvers/avl.py` line 982: lateral_derivatives: 'if flaps:' split_at_hinge -> 'if False:' (flapped wing not split at the hinge). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, same test: from seen['geometry'] collect the names after each 'SURFACE' line and the counts after '#Nchordwise  Cspace' and assert ['Main front', 'Main aft'] and ['12   1', '8   1']; assert every CONTROL line has x_hinge 0.0 (hinge at the aft piece's leading edge).

## P6b-F06 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_solver_bodies.py` · existing test `test_the_refit_keeps_the_area_of_the_envelope_with_its_notch` (line 132)
- **Production:** `aero_kernel/solver_bodies.py:360`
- **Gap:** The refit can assign the upper half's exponent to the lower half and vice versa (the merged body upside down: the canopy's bulge underneath) and all tests pass, because only the sum of both halves is compared.
- **Evidence:** assert math.isclose(area(station), _union_area(parts), rel_tol=5e-5)
    assert station.n != station.n_lower
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P6b-M08:** in `aero_kernel/solver_bodies.py` line 360: _refit: n=n_upper, n_lower=n_lower -> n=n_lower, n_lower=n_upper. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, same test: split the independent grid at the middle of the envelope z_mid = (0.07 - 0.04)/2 = 0.015 and assert 2*a*b*quadrant_area_fraction(station.n) equals the grid area above z_mid and 2*a*b*quadrant_area_fraction(station.n_lower) the one below, each rel 1e-4. For the rectangle case of test_a_canopy_floating_above_the_parent_has_its_gap_filled the two halves are computable by hand (total height 0.13, middle at z = 0.025: below 0.065*0.10 = 0.0065 m^2, above 0.015*0.10 + 0.01*0.06 + 0.04*0.06 = 0.0045 m^2).

## P6b-F08 · medium · golden_without_independent_check

- **Test file:** `aero_kernel/tests/test_avl_writer_roll.py` · existing test `test_clean_mesh_and_file_unchanged` (line 47)
- **Production:** `aero_kernel/solvers/avl_writer.py:274`
- **Gap:** The order and meaning of the numbers of a SECTION line (Xle Yle Zle Chord Ainc) are pinned only by byte snapshots that the writer itself produced; a snapshot regenerated after a writer change would accept swapped fields. No fast test asserts a section line with meaning.
- **Evidence:** expected = (SNAPSHOTS / f"{member.name.lower()}_clean.avl").read_text()
    assert written(member, roll=False) == expected  -- swapping chord and twist in the SECTION line fails these seven snapshot tests and nothing else.
- **Status:** READ_ONLY
- **Acceptance mutation P6b-M05:** in `aero_kernel/solvers/avl_writer.py` line 274: SECTION line: '{chord} {twist}' -> '{twist} {chord}'. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_avl_writer.py: one MeshSurface with a single hand-made MeshSection(x=0.01, y=0.2, z=0.03, chord=0.15, twist=1.5, airfoil=0) twice; assert the line after '#Xle    Yle    Zle     Chord   Ainc  Nspanwise  Sspace' equals '0.01 0.2 0.03 0.15 1.5   1   1' (five distinct values; metres and degrees).

## P6b-F09 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_avl_contour.py` · existing test `test_the_count_is_fixed_whatever_the_input` (line 18)
- **Production:** `aero_kernel/solvers/avl_contour.py:46`
- **Gap:** The contour can be resampled at uniform instead of cosine-spaced x and all tests pass; ARCHITECTURE 8.8 specifies 80 cosine-spaced points per side (resolution of the leading edge, from which AVL takes the camber slope).
- **Evidence:** assert len(repanel(ellipse(n), 80)) == 159  /  assert contour[79][0] == 0.0  -- no assert on any interior x.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P6b-M10:** in `aero_kernel/solvers/avl_contour.py` line 46: repanel: cosine stations 0.5*(1-cos(pi k/(n-1))) -> uniform k/(n-1). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_avl_contour.py: contour = repanel(ellipse(50), 5); the upper side's x must be [1.0, 0.853553, 0.5, 0.146447, 0.0] = 0.5*(1 - cos(pi*k/4)) for k = 4..0 (abs 1e-6), and the lower side the same ascending.

## P6b-F10 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_solvers_avl_loads.py` · existing test `test_the_rows_of_the_first_surface_come_back_in_metres_per_dynamic_pressure` (line 56)
- **Production:** `aero_kernel/solvers/avl.py:795`
- **Gap:** The adapter can hand Sref where the reader expects Bref (and the reverse): station positions, shear and bending moment come back scaled wrongly and the fast tier is green, because the adapter test asserts only the strip columns and y_station[0] == 0.
- **Evidence:** assert found.y_strip == (0.0146, 0.0437, 0.0729)
    assert found.c_cl == (0.1392, 0.1391, 0.1389)
    assert found.y_station[0] == 0.0
    assert found.warnings == ()
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P6b-M19:** in `aero_kernel/solvers/avl.py` line 795: spanwise_loads: parse_loads_output(..., reference.b_ref, reference.s_ref) -> (..., reference.s_ref, reference.b_ref). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, same test (CONVENTIONAL airplane of np_builders: S_ref 0.28 m^2, b_ref 1.4 m as in test_avl_writer.py): assert found.y_station == (0.0, 0.0208*0.7, 0.7), found.shear[0] == approx(0.298353*0.28, rel 1e-9) and found.moment[0] == approx(0.0669065*0.28*1.4, rel 1e-9), the hand values test_avl_writer_loads.py already derives.

## P6b-F11 · medium · untested_error_path · DECISION

- **Test file:** `aero_kernel/tests/test_solvers_avl_loads.py` · existing test `test_the_rows_of_the_first_surface_come_back_in_metres_per_dynamic_pressure` (line 56)
- **Production:** `aero_kernel/solvers/avl_writer.py:548`
- **Gap:** A truncated strip-force or shear table is returned as a shorter curve instead of an error: the reader stops at the first row it cannot parse and nothing compares the row count with the mesh (24 strips, 26 shear rows). The passing fast test proves it: its fixture has 3 strips and 3 shear rows.
- **Evidence:** STRIPS: '# Chordwise = 10   # Spanwise = 24' followed by three rows; found.y_strip == (0.0146, 0.0437, 0.0729) is accepted by spanwise_loads().
- **Status:** READ_ONLY
- **Test to write:** Fast, test_solvers_avl_loads.py: the requirement first needs a decision (count rows against '# Spanwise = N' of the FS header, or against N_SPAN). Then: configure(fake, STRIPS, SHEAR_MOMENT) with a full 24-row table generated in the test and the same table cut after row 10 -> pytest.raises(RuntimeError, match='did not complete'); likewise a VM table whose row count is not strips + 2.

## P6b-F07 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_avl_mesh_split.py` · existing test `test_stations_off_the_device_take_the_cut_of_the_nearest_controlled_station` (line 64)
- **Production:** `aero_kernel/solvers/avl_mesh.py:412`
- **Gap:** Stations outboard of a device can take the cut of the first controlled station of the wing instead of the nearest one; the front/aft cut then jumps at the outboard device end. The production docstring calls the cut 'continuous and otherwise immaterial', so the effect on a result is small.
- **Evidence:** root = front.sections[0]
    assert math.isclose(root.chord_range[1], 0.7)  -- device on the outer panel only, so nearest == first controlled.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P6b-M04:** in `aero_kernel/solvers/avl_mesh.py` line 412: split_at_hinge.split_of: min(controlled, key=nearest)[1] -> controlled[0][1]. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_avl_mesh_split.py: wing ribs y = 0, 0.2, 0.4, 0.6 with aileron(0.7, 0.8) on rib 1 (y 0.2..0.4), drive_roll, split; assert front.sections[-1].chord_range[1] == 0.8 (tip takes the outboard end's hinge) and front.sections[0].chord_range[1] == 0.7.

## P6b-F12 · low · over_mocked

- **Test file:** `aero_kernel/tests/test_avl_writer.py` · existing test `test_the_output_is_read_by_its_first_hit_of_each_key` (line 86)
- **Production:** `aero_kernel/solvers/avl_writer.py:427`
- **Gap:** The readers of the neutral point, the hinge table and the lateral block, and all five fake executables, are fed lines the test author wrote to fit the regular expressions; only the loads files are stated to be recorded AVL 3.40 output. A change of AVL's real layout (e.g. 'Neutral point  Xnp =', a control name longer than its column, '*******' overflow fields) is noticed only in the aero tier.
- **Evidence:** out = " Sref = 0.28000  Cref = 0.2\n CLtot =   0.50000\n Xnp = 0.131\n Clb Cnr / Clr Cnb = 1\n Xnp = 9.9\n"
- **Status:** READ_ONLY
- **Test to write:** Fast: record once, with the real binary, the complete stdout of one neutral-point run, one steady-roll run, one hinge run and one lateral run of aileron_trainer (or CONVENTIONAL) into aero_kernel/tests/fixtures/avl_outputs/*.txt, and parse them in the fast tier against the numbers read off the file by eye (Xnp, CLtot, p'b/2V, Clp, Cld01, each Chinge row, six derivatives). Add one recorded output with a Fortran '*******' field and one cut in the middle of the stability block -> None.

## P6b-F13 · low · redundant

- **Test file:** `aero_kernel/tests/test_avl_hinge_mesh.py` · existing test `test_a_device_without_a_name_is_keyed_like_the_geometry_format_derives_it` (line 339)
- **Production:** `aero_kernel/solvers/avl_hinge.py:139`
- **Gap:** The test repeats the second half of test_a_device_name_falls_back_to_its_label_and_then_its_role (line 90) with the same input and the same expected keys; test_the_role_sets_are_those_of_the_conditions_and_the_roll_rule (line 323) partly compares constants with the expression that defines them.
- **Evidence:** bare = device(None, "elevator", 0.6)
    assert list(controls_by_key(mesh_of(conventional(tail={0: bare}), "elevator"))) == ["Tail.elevator_right", "Tail.elevator_left"]
- **Status:** READ_ONLY
- **Test to write:** Merge the duplicate into test_a_device_name_falls_back_to_its_label_and_then_its_role; in the role-set test keep the literal assert COMMAND_SIGNS['aileron'] == (-1, 1) and add the literals for elevator (1, 1), rudder (1, -1), flap (1, 1).

## P6b-F14 · low · coverage_only

- **Test file:** `aero_kernel/tests/test_solvers_avl.py` · existing test `test_the_module_states_its_sources` (line 193)
- **Production:** `aero_kernel/solvers/avl.py:121`
- **Gap:** The test compares a module constant with its own literal and says nothing about CLAF as written; the rule CLAF = 1 + 0.77 t/c is checked only in the aero tier of another package (test_neutral_point_fleet.py::test_claf_follows_the_thickness_rule_of_the_airfoil), and contour_worker has no fast test. test_the_run_limit_is_far_above_the_measured_refined_run likewise compares a constant with a bound.
- **Evidence:** assert avl_module.CLAF_PER_THICKNESS == 0.77
- **Status:** READ_ONLY
- **Test to write:** Fast, test_solvers_avl.py: call contour_worker with one InlineAirfoil lens of 12 % thickness (the ellipse() of test_avl_contour.py) if AeroSandbox imports in the fast tier, else inject max_thickness; assert claf == approx(1 + 0.77*0.12, rel 2e-3) and len(coordinates) == 159. Rename or drop the constant-equals-literal test.

## P6b-F15 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_solvers_avl_roll.py` · existing test `test_more_than_fifty_chordwise_vortices_on_one_surface_are_refused` (line 279)
- **Production:** `aero_kernel/solvers/avl.py:499`
- **Gap:** The array limits are tested well above (51, and monkeypatched small limits) but never at the boundary: a mesh with exactly 50 chordwise vortices, 500 strips, 6000 vortices or 100 surfaces could be refused (> turned into >=) without a failure.
- **Evidence:** monkeypatch.setattr("aero_kernel.solvers.avl.SPLIT_N_CHORD", (51, 8))
    ...
    assert raised.value.detail["n_chord"] == 51
- **Status:** READ_ONLY
- **Test to write:** Fast, test_solvers_avl_roll.py: SPLIT_N_CHORD = (50, 8) with configure(fake, {'50': 0.05}) -> a value (p_hat 0.05) and avl_refinement_unchecked for the refined 100; AVL_MAX_STRIPS monkeypatched to 96 (the declared mesh has exactly 96 strips) -> no error, 95 -> avl_array_limit.

## P6b-F16 · low · golden_without_independent_check

- **Test file:** `aero_kernel/tests/test_solvers_avl_roll_real.py` · existing test `test_the_aircraft_without_an_independent_reference_have_regression_values` (line 73)
- **Production:** `aero_kernel/solvers/avl.py:819`
- **Gap:** Three fleet roll rates (BELEMNITOS 0.27042, WIESEL 0.25762, RV7 0.22094) and the flapped RV-7 value 0.21929 are the kernel's own output at abs 1e-4; the file says so. They detect change, not error. BRYAN and JAGUAR carry the validation (independent script, 1 %).
- **Evidence:** assert math.isclose(found.p_hat, REGRESSION[member], abs_tol=1e-4)
- **Status:** READ_ONLY
- **Test to write:** Aero: extend scripts/sim_export/crrcsim/avl_roll_reference.py to RV7 (the one fleet member with flaps) and compare at rel 1 % like BRYAN and JAGUAR, clean and with the 30 deg flap; keep the other two as declared regression.
