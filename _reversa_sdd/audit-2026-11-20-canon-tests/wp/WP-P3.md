# WP-P3 — Antrieb, Leistung, Flugzeit, Holm

Self-contained brief for one implementer subagent. Frozen review state: commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

- **Production code under test:** aero_kernel/formulas/powered_flight.py, endurance_*.py, motor_propeller_*.py, spar_capacity.py
- **Requirement sources:** Kanon-Einträge der Formeln, ARCHITECTURE §8.12
- **Test files you may change:** `aero_kernel/tests/test_endurance_and_range.py`, `aero_kernel/tests/test_endurance_and_range_optimum.py`, `aero_kernel/tests/test_motor_propeller_part_load.py`, `aero_kernel/tests/test_motor_propeller_part_load_aero.py`, `aero_kernel/tests/test_powered_flight.py`, `aero_kernel/tests/test_powered_performance.py`, `aero_kernel/tests/test_powered_scan_start.py`, `aero_kernel/tests/test_powertrain_chain.py`, `aero_kernel/tests/test_powertrain_edges.py`, `aero_kernel/tests/test_powertrain_reference.py`, `aero_kernel/tests/test_spar_capacity.py`
- **Findings:** 18 (3 high, 6 medium, 9 low)

A finding marked **DECISION** needs the maintainer's answer first: do not write its test, list it in your report as open.

## P3-F01 · high · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_endurance_and_range_optimum.py` · no test exists
- **Production:** `aero_kernel/formulas/endurance_and_range_optimum.py:116`
- **Gap:** The canon constraint r_T(V) <= 1 of the optimum can be dropped: max-endurance/max-range are then returned at a speed the drive train cannot hold, instead of no_level_flight_speed or a declared full_throttle bound.
- **Evidence:** Production `return speed if speed.point.r_t <= 1.0 else _FULL_THROTTLE` replaced by `return speed`: 298 passed. No test in the file mentions `full_throttle` as a bound (only `full_throttle_thrust`, `propeller_table`, `stall_speed`, `level_flight_solution`, `mach_limit`).
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P3-M04:** in `aero_kernel/formulas/endurance_and_range_optimum.py` line 116: `return speed if speed.point.r_t <= 1.0 else _FULL_THROTTLE` -> `return speed` (r_T <= 1 constraint dropped). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_endurance_and_range_optimum.py, two tests with endurance_builders. (1) SpeedOpti(a=0.06, b=0.0), stall-speed 19.0 m/s: D = 0.06 V^2 = 21.7 N at 19 m/s exceeds the full-throttle thrust at every speed from there on, expect FormulaError code no_level_flight_speed (verified on unmutated code; the mutant returns t_max = 280.8 s). (2) SpeedOpti(a=0.0, b=9000.0), stall-speed 6.0: expect an optimum_at_domain_bound warning with detail.bound == 'full_throttle' (edge about 43.3 m/s) and no postcondition_violated warning (verified; the mutant reports propeller_table and a violated postcondition).

## P3-F02 · high · untested_error_path

- **Test file:** `aero_kernel/tests/test_endurance_and_range.py` · existing test `test_a_drive_train_that_draws_no_power_gives_no_flight_time` (line 197)
- **Production:** `aero_kernel/formulas/motor_propeller_part_load.py:300`
- **Gap:** A negative battery power (reachable with a table whose C_P is negative at the part-load point) would give a negative flight time and range instead of non_positive_battery_power.
- **Evidence:** `energy_over_power(74.0, 0.0, 10.0)` is the only call in a raises block; the stubbed formula test also uses `p_bat=0.0`. Guard `if not p_bat_w > 0.0:` replaced by `if p_bat_w == 0.0:`: 298 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P3-M03:** in `aero_kernel/formulas/motor_propeller_part_load.py` line 300: `if not p_bat_w > 0.0:` -> `if p_bat_w == 0.0:` (negative power accepted). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_endurance_and_range.py: parametrize p_bat over [0.0, -1e-9, -60.0] and expect FormulaError code non_positive_battery_power with detail p_bat_w equal to the input; keep the positive case 3600*74/60 = 4440 s.

## P3-F03 · high · missing_edge_case

- **Test file:** `aero_kernel/tests/test_spar_capacity.py` · existing test `test_normal_mode_origin_is_an_offset_from_the_segment_root` (line 377)
- **Production:** `aero_kernel/spar_capacity.py:239-242`
- **Gap:** The axis origin of a partial-extent spar (root rib of ITS segment; offset in normal mode, absolute in standard mode) is unproven: a spar in an outboard segment could be placed from y = 0 and reported present/absent at the wrong stations. (Module is unreachable until gh-1429, so no user value is wrong today.)
- **Evidence:** `wing_ = two_rib_wing(fields, tip=(0.0, 0.5, 0.0), tip_chord=0.2)` - every fixture with spare_start/spare_length has its segment root at xyz_le y = 0.0, so `root.xyz_le[1] + offset` equals `offset`. Mutation `return root.xyz_le[1] + offset, slope` -> `return offset, slope`: all spar tests pass. test_standard_mode_origin_is_an_absolute_point (line 538) uses the same root, so the two tests assert identical numbers (0.24 absent, 0.26 present) for the two rules.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P3-M07:** in `aero_kernel/spar_capacity.py` line 241: `return root.xyz_le[1] + offset, slope` -> `return offset, slope` (origin not relative to the segment root). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_spar_capacity.py. (1) wing([spar(section=RECTANGULAR, material='test')], [spar(section=RECTANGULAR, material='test', spare_start=0.1, spare_length=0.2)]) (ribs at y = 0, 0.5, 1.0): y 0.55 -> NoSparAtStation, 0.6, 0.65, 0.8 -> BendingCapacity, 0.85 -> NoSparAtStation (verified on unmutated code). (2) Same two-segment wing, second-segment spar with spare_vector [0,1,0], spare_origin [0,0.2,0], spare_start 0.05: mode 'normal' present from y = 0.5+0.2+0.05 = 0.75; mode 'standard' present from y = 0.2+0.05 = 0.25, i.e. over the whole segment from 0.5.

## P3-F04 · medium · untested_error_path · DECISION

- **Test file:** `aero_kernel/tests/test_endurance_and_range_optimum.py` · no test exists
- **Production:** `aero_kernel/formulas/endurance_and_range_optimum.py:134-140`
- **Gap:** A stall speed of 0 (or negative) never leaves the scan loop (`v *= self._ratio`), so compute() would hang instead of failing; the entry has no stall_speed_usable precondition although the six powered entries have one.
- **Evidence:** canon_model.json: formulas['endurance-and-range-optimum'].preconditions == []. Reproduction (not a mutation): endurance_and_range_optimum(bound(SLUG, {'stall-speed': 0.0}), context_of(SLUG, SpeedOpti(min_speed=1.0))) did not return and was killed by SIGALRM after 15 s. No test passes a stall speed <= 0 to this formula.
- **Status:** READ_ONLY
- **Test to write:** After the canon decides the rule (precondition stall_speed_usable on this entry, or a guard in _Domain.scan): fast test in test_endurance_and_range_optimum.py that v_s in [0.0, -3.0] ends as a declared error within the test timeout (precondition state 'violated', or FormulaError), mirroring test_a_stall_speed_that_is_not_positive_finite_and_inside_the_scan_violates_it.

## P3-F05 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_powered_flight.py` · existing test `test_the_sustained_load_factor_is_the_closed_form_one` (line 300)
- **Production:** `aero_kernel/formulas/powered_flight.py:716`
- **Gap:** The declared limit of a sustained turn (thrust vs wing, ADR 0020 notice) can be the verdict at n_lim instead of the one the bisection met: a thrust-limited turn would be declared wing-limited.
- **Evidence:** `assert got.limit == expected[1]` at 20 m/s, n_lim 6, where the wing stops both at n_lim and at the answer; the formula tests accept either: `assert declared in (['thrust'], ['wing'])`. Mutation `high, stop = middle, found` -> `high = middle`: 298 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P3-M14:** in `aero_kernel/formulas/powered_flight.py` line 716: `high, stop = middle, found` -> `high = middle` (limit label from the verdict at n_lim). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_powered_flight.py: got = await pf.sustained_load_factor(flight(), 28.0, 10.0); expect got.limit == 'thrust' and got.n == pb.sustained_n(28.0, 3.4, 10.0)[0] = 4.34764 (rel 1e-5). At n = 10 the wing stops the turn (C_L = 10*33.34/240.1 = 1.39 > 1.2) while the thrust binds first at n = 4.35, so the two labels differ (verified on unmutated code).

## P3-F06 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_powered_flight.py` · no test exists
- **Production:** `aero_kernel/formulas/powered_flight.py:580`
- **Gap:** The golden-section refinement may evaluate speeds below the scan start when the best scan point is the start itself; on airframes whose sweep has no lift peak there (gh-1419) the formula would end as not_converged again.
- **Evidence:** `low = max(speeds[best] - step, start)` -> `low = speeds[best] - step`: 298 passed. test_a_sweep_without_a_peak_below_the_scan_start_does_not_end_the_formula asserts `min(v for v, _ in opti.evaluations) >= start - 1e-9`, but none of its six optima sits on the first scan point.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P3-M09:** in `aero_kernel/formulas/powered_flight.py` line 580: `low = max(speeds[best] - step, start)` -> `low = speeds[best] - step`. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_powered_flight.py: record the arguments of f(v) = -v, call pf.maximise_over_speed(f, flight(), 9.5); expect min(recorded) >= 9.5 and 9.5 <= optimum.v < 9.51 (unmutated code gives 9.50005 and a minimum of 9.5).

## P3-F07 · medium · untested_warning

- **Test file:** `aero_kernel/tests/test_powered_performance.py` · existing test `test_the_best_rate_of_climb_vertical_is_declared_too` (line 192)
- **Production:** `aero_kernel/formulas/best_rate_of_climb.py:62`
- **Gap:** best-rate-of-climb can stop declaring that its optimum lies on the vertical bound or on the stall corner (powered_limit_declared) without any test failing; the test named 'is declared too' asserts no declaration.
- **Evidence:** The whole body of asserts: `assert abs(got["v_y"] - v_expected) <= 0.06` / `assert close(got["roc_max"], roc_expected, 1e-3)`. Replacing `await finish_climb(flight, optimum, gamma)` by a bare `flight.answer(...)`: 298 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P3-M06:** in `aero_kernel/formulas/best_rate_of_climb.py` line 62: `await finish_climb(flight, optimum, gamma)` -> `await flight.answer(optimum.v, 0.0 if gamma >= 0.5 * math.pi else math.cos(gamma))` (no bound declaration). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_powered_performance.py: in the mass 0.8 kg test add `assert 'gamma_90_deg' in pb.limits(ctx)` (keep ctx). Add a best-rate case on the stall corner (PolarOpti with a high cd0 or a heavy mass so that the optimum is the first valued scan point) and assert 'wing' in pb.limits(ctx) with detail cos_gamma and cl present.

## P3-F08 · medium · untested_warning

- **Test file:** `aero_kernel/tests/test_powertrain_chain.py` · existing test `test_the_static_thrust_to_weight_is_the_hand_thrust_over_the_weight` (line 307)
- **Production:** `aero_kernel/formulas/static_thrust_to_weight.py:49`
- **Gap:** static-thrust-to-weight can drop its route notice (which route ran, R_m is the winding only, nominal voltage; Q-PT-6 / ADR 0020) unnoticed.
- **Evidence:** Asserts of the test: `close(got["t0_w"], t_static / (3.4 * G), 1e-6)`, `close(got["t0_w"], 32.9713 / (3.4 * G), 1e-5)`, `set(ctx.embedded_requests) == set(formula.embeds)`; no assert on ctx.warnings. Removing `declare_route(ctx)`: 298 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P3-M05:** in `aero_kernel/formulas/static_thrust_to_weight.py` line 49: removed `declare_route(ctx)` (route notice). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, same test: `assert [w.code for w in ctx.warnings] == ['powertrain_route_winding_resistance']` and `ctx.warnings[0].detail == {'route': 'B'}`; in test_the_chain_through_the_engine_gives_the_independent_values assert the code is among got['static-thrust-to-weight'].warnings.

## P3-F09 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_powertrain_chain.py` · no test exists
- **Production:** `aero_kernel/formulas/motor_propeller_equilibrium.py:193`
- **Gap:** With two torque-balance crossings inside the table the full-throttle speed is meant to be the highest one; taking the lowest would lower every thrust-dependent quantity and pass.
- **Evidence:** `for low, high in reversed(covered_pairs(points)):` -> without reversed(): 298 passed. Every table fixture (APC 13x8E, small_table flat C_P) has a single sign change.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P3-M02:** in `aero_kernel/formulas/motor_propeller_equilibrium.py` line 193: `reversed(covered_pairs(points))` -> `covered_pairs(points)` (lowest instead of highest crossing). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_powertrain_edges.py: a three-block table (1000, 2000, 3000 rpm, J to 3.0) whose C_P makes the residual Q_m - Q_p positive at 1000, negative at 2000 only through a C_P spike there, and the motor (K_v high enough that the free-run speed is above 3000 rpm) crossing again between 2000 and 3000 after a positive point inserted at 2500 rpm; compute both roots with a plain bisection of (I-I_0)/K_v' - C_P rho n^2 D^5/(2 pi) and expect the upper one (rel 1e-6). If the maintainer does not want the rule, delete reversed() and the docstring sentence instead.

## P1-F09 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_powertrain_chain.py` · existing test `test_a_propeller_that_does_not_turn_has_no_advance_ratio` (line 123)
- **Production:** `aero_kernel/formulas/advance_ratio_from_speed.py:31`
- **Gap:** Only n_prop <= 0 is tested; the diameter is not. A check on n_prop alone passes the suite (D_prop = 0 then divides by zero), and today's product check lets two negative factors through: advance_ratio(5, -150, -0.3) returns 0.111.
- **Evidence:** `@pytest.mark.parametrize("n_prop", [0.0, -3.0])` ... `advance_ratio(5.0, n_prop, 0.3302)`
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P1-M14:** in `aero_kernel/formulas/advance_ratio_from_speed.py` line 31: `if not swept > 0.0:` -> `if not n_prop > 0.0:` (diameter unchecked). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast: advance_ratio(5.0, 150.0, 0.0) and (5.0, 150.0, -0.33) raise FormulaError non_positive_value; decide and pin (5.0, -150.0, -0.33) (docstring says both > 0); NaN for each argument raises. Also give the formula its own hand value written as a number: 10/(150*0.3302) = 0.2018978.

## P3-F10 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_motor_propeller_part_load.py` · no test exists
- **Production:** `aero_kernel/formulas/motor_propeller_part_load.py:84`
- **Gap:** With two thrust = drag crossings the part-load speed is meant to be the lowest; the highest would pass.
- **Evidence:** `for low, high in covered_pairs(points):` -> `reversed(covered_pairs(points))`: 298 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P3-M10:** in `aero_kernel/formulas/motor_propeller_part_load.py` line 84: `for low, high in covered_pairs(points):` -> `reversed(covered_pairs(points))` (highest instead of lowest crossing). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_powertrain_coverage_edge.py: flat-J table with C_T per block 0.1, 0.02, 0.1 at 1200, 2400, 3600 rpm at V = 0; thrust(n) = C_T(n) rho n^2 D^4 then crosses a drag between its local maximum and minimum three times; take the lowest root from a 1 rpm scan of that expression and expect solve_part_load_speed to return it (rel 1e-6).

## P3-F11 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_powered_performance.py` · existing test `test_a_drive_train_that_cannot_hold_level_flight_is_a_declared_failure` (line 77)
- **Production:** `aero_kernel/formulas/max_level_speed.py:100-101`
- **Gap:** max-level-speed's no_feasible_speed message is meant to say whether the wing or the thrust stopped every speed; the reason can be lost (message 'no speed was evaluated').
- **Evidence:** `assert caught.value.code == "no_feasible_speed"` only. Removing `reasons.add(Unflyable.THRUST)`: 298 passed. (The message tests in test_powered_flight.py target maximise_over_speed, a different loop.)
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P3-M11:** in `aero_kernel/formulas/max_level_speed.py` line 100: `reasons.add(Unflyable.THRUST)` -> `pass`. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, same test: add `assert 'thrust at full throttle is below' in caught.value.message` and `assert 'wing cannot carry' not in caught.value.message` (PolarOpti(cd0=2.0), 3.4 kg: every flyable speed has D > T).

## P3-F12 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_powertrain_edges.py` · existing test `test_exactly_on_the_last_block_the_top_block_alone_decides` (line 42)
- **Production:** `aero_kernel/formulas/propeller_table_lookup.py:119-122`
- **Gap:** Exactly on an inner rpm block the neighbour block's J range must not be checked; with the branch removed such a point fails as outside_propeller_table although the block covers it.
- **Evidence:** The test covers `last["rpm"] / 60` only. Deleting the branch `if (rpm <= low.rpm): return _in_block(low, j)`: 298 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P3-M15:** in `aero_kernel/formulas/propeller_table_lookup.py` line 119: removed the branch `if (rpm <= low.rpm): return _in_block(low, j)` (exactly on an inner block). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_powertrain_edges.py with narrow_second_block() of test_powertrain_coverage_edge (blocks 1200/2400/3600 rpm, J ranges 0.8/0.2/0.8, C_T 0.1, C_P 0.04): table_lookup(components, 0.5, 2400.0/60) must raise outside_propeller_table (J beyond its own block), while table_lookup(components, 0.5, 1200.0/60) returns c_t == 0.1 and c_p == 0.04 although the 2400 rpm neighbour ends at J = 0.2.

## P3-F13 · low · misleading_name

- **Test file:** `aero_kernel/tests/test_powered_scan_start.py` · existing test `test_a_climb_that_can_be_vertical_starts_at_the_floor_and_declares_it` (line 108)
- **Production:** `aero_kernel/formulas/powered_flight.py:242-251`
- **Gap:** The file's stated numbers are stale, so the test does not exercise the case its name states: the static thrust of the fixture is 32.97 N, below the weight 33.34 N, not 60 N.
- **Evidence:** `opti = pb.PolarOpti()  # 3.4 kg: T_0 = 60 N > W = 33.3 N, no lower stall bound from the angle`; module docstring: 'a static thrust of 60 N'. Reviewer ran pb.thrust(0.0) = 32.9713 N (the hand value of test_powertrain_chain). The floor is reached because (1 - 0.9889^2)^0.25 = 0.386 < 0.5. Same staleness: test_powered_flight.py line 274 `# T = 8.8 N, D = 11.7 N` (actual 12.18 N and 12.76 N, a 0.6 N margin) and line 99 'start = 0.80 V_S' (actual 0.953).
- **Status:** READ_ONLY
- **Test to write:** Correct the comments to the real numbers and add to this file a T_0 > W case at the unit level: airplane = PoweredFlight(pb.bound_inputs('best-angle-of-climb', mass=0.8), ...); airplane.climb_scan_start() == 0.5 * pb.stall_speed(0.8) (W = 7.85 N < 32.97 N), plus a T_0/W = 0.42 case (mass 8.0) expecting 0.9526 * pb.stall_speed(8.0) written as a number.

## P3-F14 · low · mirror_or_tautology

- **Test file:** `aero_kernel/tests/test_powered_performance.py` · existing test `test_the_fastest_sustained_turn_matches_the_closed_form_scan` (line 242)
- **Production:** `aero_kernel/formulas/max_sustained_turn_rate.py:42-44`
- **Gap:** The turn kinematics have no hand-computed value: the test re-types the production expression, so a wrong relation typed twice would pass (kernel rule: every formula against a hand-computed value).
- **Evidence:** Test helper: `return pb.G * math.sqrt(n * n - 1.0) / v` and `return -(v * v / (pb.G * math.sqrt(n * n - 1.0)))`; production: `return g * math.sqrt(n * n - 1.0) / v`.
- **Status:** READ_ONLY
- **Test to write:** Fast, test_powered_performance.py: turn_rate(9.80665, 20.0, 2.0) == 0.849281 rad/s (9.80665 * 1.7320508 / 20), i.e. 48.660 deg/s, and turn_radius(9.80665, 20.0, 2.0) == 23.549 m (400 / (9.80665 * 1.7320508)), rel 1e-5; cross-check omega = V / r.

## P3-F15 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_endurance_and_range.py` · no test exists
- **Production:** `aero_kernel/formulas/endurance_and_range.py:45-49`
- **Gap:** A zero or negative battery capacity gives a flight time of 0 or below without any error or warning from the three endurance formulas.
- **Evidence:** canon_model.json: quantities['battery-capacity'] has unit 'Wh' and positive: null; production `t_est = energy_over_power(e_bat, at_mp.point.p_bat, v_mp)` multiplies without a check. No test in the package passes e_bat <= 0.
- **Status:** READ_ONLY
- **Test to write:** Decide the rule in the canon first (positive: true on battery-capacity, checked at the input like battery-specific-energy). Then fast, test_powertrain_edges.py style: AircraftInput with values {'battery-capacity': 0.0} and request('endurance-estimate') gives input_errors == [('non_positive_value', 'values.battery-capacity')]; same for -74.0.

## P3-F16 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_motor_propeller_part_load_aero.py` · existing test `test_the_avistar_cruises_on_a_battery_power_the_drive_train_can_deliver` (line 32)
- **Production:** `aero_kernel/formulas/motor_propeller_part_load.py:166`
- **Gap:** The only real-solver test of the part-load formula accepts any positive battery power.
- **Evidence:** `assert power > 0.0`, `assert abs(current - power / 14.8) <= 1e-9 * power`, `assert 0.0 < got["thrust-demand-ratio"].value < 1.0`.
- **Status:** READ_ONLY
- **Test to write:** Aero tier, same test: bound the power by hand from the drag the fast tier already records for this aircraft (2.21 N at 18 m/s, AVISTAR_DRAG_N): shaft power >= D V = 39.8 W, so P_bat > 39.8 W; and P_bat < D V / 0.3 = 133 W as a generous lower efficiency bound stated in the docstring.

## P3-F17 · low · coverage_only

- **Test file:** `aero_kernel/tests/test_powertrain_reference.py` · existing test `test_a_set_maps_onto_the_components_contract` (line 46)
- **Production:** `aero_kernel/tests/components_builders.py:25`
- **Gap:** A set whose fields were mapped to wrong values would pass: only presence is asserted.
- **Evidence:** `assert components.motor is not None` / `assert components.motor.kv_rpm_per_volt > 0` / `assert components.battery is not None` / `assert components.propeller is not None`.
- **Status:** READ_ONLY
- **Test to write:** Fast: for each set compare components.motor.kv_rpm_per_volt, rm_ohm, io_no_load_a and battery capacity/cells with DATA['motors'][id]['fields'] / DATA['batteries'][id]['fields'] by equality.
