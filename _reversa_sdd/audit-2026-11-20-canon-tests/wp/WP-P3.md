# WP-P3 — Powertrain, performance, endurance, spar

Self-contained brief for one implementer subagent. Base commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

Every finding below was checked by an independent verifier on 2026-11-21 (`../rework/`). The line **Verified** says how. Where **Correction** appears, it overrides the text under **Test to write**.

- **Production code under test:** aero_kernel/formulas/powered_flight.py, endurance_*.py, motor_propeller_*.py, spar_capacity.py
- **Requirement sources:** canon entries of the formulas, ARCHITECTURE §8.12
- **Test files you may change:** `aero_kernel/tests/test_endurance_and_range.py`, `aero_kernel/tests/test_endurance_and_range_optimum.py`, `aero_kernel/tests/test_motor_propeller_part_load.py`, `aero_kernel/tests/test_motor_propeller_part_load_aero.py`, `aero_kernel/tests/test_powered_flight.py`, `aero_kernel/tests/test_powered_performance.py`, `aero_kernel/tests/test_powertrain_chain.py`, `aero_kernel/tests/test_powertrain_edges.py`, `aero_kernel/tests/test_spar_capacity.py`
- **Findings to work on:** 14 (4 high, 6 medium, 4 low)

## P3-F01 · high · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_endurance_and_range_optimum.py` · no test exists
- **Production:** `aero_kernel/formulas/endurance_and_range_optimum.py:116`
- **Gap:** The canon constraint r_T(V) <= 1 of the optimum can be dropped: max-endurance/max-range are then returned at a speed the drive train cannot hold, instead of no_level_flight_speed or a declared full_throttle bound.
- **Evidence:** Production `return speed if speed.point.r_t <= 1.0 else _FULL_THROTTLE` replaced by `return speed`: 298 passed. No test in the file mentions `full_throttle` as a bound (only `full_throttle_thrust`, `propeller_table`, `stall_speed`, `level_flight_solution`, `mach_limit`).
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived 1081 fast tests. Witness SpeedOpti(a=0.06, b=0.0), stall-speed 19.0: original raises FormulaError no_level_flight_speed, mutant returns {'t_max': 280.78, 'r_max': 5334.9}. Witness SpeedOpti(a=0.0, b=9000.0), stall-speed 6.0: original warns optimum_at_domain_bound with bound 'full_throttle' and r_max 24756.9, mutant warns bound 'propeller_table' plus postcondition_violated and r_max 27203.1. In test_endurance_and_range_optimum.py the only bound asserts are `assert all(w.detail["bound"] == "propeller_table" for w in bounds)` and `... == "full_throttle_thrust" ...`.
- **Verifier's note:** No aero test is expected to fail: on the Avistar the optimum is interior and the brute-force cross-check in test_endurance_and_range_aero.py does not look at the upper domain end.
- **Acceptance mutation:** `git apply rework/patches/WP-P3/P3-F01.patch` (from the audit folder; aero_kernel/formulas/endurance_and_range_optimum.py:116  `return speed if speed.point.r_t <= 1.0 else _FULL_THROTTLE` -> `return speed`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_endurance_and_range_optimum.py, two tests with endurance_builders. (1) SpeedOpti(a=0.06, b=0.0), stall-speed 19.0 m/s: D = 0.06 V^2 = 21.7 N at 19 m/s exceeds the full-throttle thrust at every speed from there on, expect FormulaError code no_level_flight_speed (verified on unmutated code; the mutant returns t_max = 280.8 s). (2) SpeedOpti(a=0.0, b=9000.0), stall-speed 6.0: expect an optimum_at_domain_bound warning with detail.bound == 'full_throttle' (edge about 43.3 m/s) and no postcondition_violated warning (verified; the mutant reports propeller_table and a violated postcondition).

## P3-F02 · high · untested_error_path

- **Test file:** `aero_kernel/tests/test_endurance_and_range.py` · existing test `test_a_drive_train_that_draws_no_power_gives_no_flight_time` (line 197)
- **Production:** `aero_kernel/formulas/motor_propeller_part_load.py:300`
- **Gap:** A negative battery power (reachable with a table whose C_P is negative at the part-load point) would give a negative flight time and range instead of non_positive_battery_power.
- **Evidence:** `energy_over_power(74.0, 0.0, 10.0)` is the only call in a raises block; the stubbed formula test also uses `p_bat=0.0`. Guard `if not p_bat_w > 0.0:` replaced by `if p_bat_w == 0.0:`: 298 passed.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived 1081 fast tests. energy_over_power(74.0, -60.0, 10.0): original raises non_positive_battery_power, mutant returns -4440.0 s; for -1e-9 the mutant returns -2.66e14 s. The only raising calls use zero: `energy_over_power(74.0, 0.0, 10.0)`. Reachability checked: part_load() on a four-block table with C_P = (0.04, -0.04, -0.04, 0.04) at 1000/3000/6000/9000 rpm returns p_bat = -17.08 W (r_t 0.114) at 5 m/s; the table validation in validate.py does not check the sign of cp.
- **Acceptance mutation:** `git apply rework/patches/WP-P3/P3-F02.patch` (from the audit folder; aero_kernel/formulas/motor_propeller_part_load.py:300  `if not p_bat_w > 0.0:` -> `if p_bat_w == 0.0:`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_endurance_and_range.py: parametrize p_bat over [0.0, -1e-9, -60.0] and expect FormulaError code non_positive_battery_power with detail p_bat_w equal to the input; keep the positive case 3600*74/60 = 4440 s.

## P3-F07 · high · untested_warning

- **Test file:** `aero_kernel/tests/test_powered_performance.py` · existing test `test_the_best_rate_of_climb_vertical_is_declared_too` (line 192)
- **Production:** `aero_kernel/formulas/best_rate_of_climb.py:62`
- **Gap:** best-rate-of-climb can stop declaring that its optimum lies on the vertical bound or on the stall corner (powered_limit_declared) without any test failing; the test named 'is declared too' asserts no declaration.
- **Evidence:** The whole body of asserts: `assert abs(got["v_y"] - v_expected) <= 0.06` / `assert close(got["roc_max"], roc_expected, 1e-3)`. Replacing `await finish_climb(flight, optimum, gamma)` by a bare `flight.answer(...)`: 298 passed.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived 1081 fast tests. best_rate_of_climb at mass 0.8: original declares ['scan_floor', 'gamma_90_deg'], mutant only ['scan_floor']; at mass 6.0 with PolarOpti(cd0=0.3): original declares 'wing' (detail keys cl, cos_gamma, gamma_deg, lowest_evaluated_level_flight_speed_ms, v_ms), mutant declares nothing. Values v_y and roc_max are identical. The test named '..._vertical_is_declared_too' ends with `assert abs(got["v_y"] - v_expected) <= 0.06` / `assert close(got["roc_max"], roc_expected, 1e-3)` and never reads ctx.warnings.
- **Verifier's note:** The aero test test_the_best_rate_of_climb_lies_between_the_hand_bounds asserts the notice is absent (interior optimum), so it would not fail.
- **Acceptance mutation:** `git apply rework/patches/WP-P3/P3-F07.patch` (from the audit folder; aero_kernel/formulas/best_rate_of_climb.py:62  `await finish_climb(flight, optimum, gamma)` -> `await flight.answer(optimum.v, 0.0 if gamma >= 0.5 * math.pi else math.cos(gamma))`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_powered_performance.py: in the mass 0.8 kg test add `assert 'gamma_90_deg' in pb.limits(ctx)` (keep ctx). Add a best-rate case on the stall corner (PolarOpti with a high cd0 or a heavy mass so that the optimum is the first valued scan point) and assert 'wing' in pb.limits(ctx) with detail cos_gamma and cl present.

## P3-F08 · high · untested_warning

- **Test file:** `aero_kernel/tests/test_powertrain_chain.py` · existing test `test_the_static_thrust_to_weight_is_the_hand_thrust_over_the_weight` (line 307)
- **Production:** `aero_kernel/formulas/static_thrust_to_weight.py:49`
- **Gap:** static-thrust-to-weight can drop its route notice (which route ran, R_m is the winding only, nominal voltage; Q-PT-6 / ADR 0020) unnoticed.
- **Evidence:** Asserts of the test: `close(got["t0_w"], t_static / (3.4 * G), 1e-6)`, `close(got["t0_w"], 32.9713 / (3.4 * G), 1e-5)`, `set(ctx.embedded_requests) == set(formula.embeds)`; no assert on ctx.warnings. Removing `declare_route(ctx)`: 298 passed.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived 1081 fast tests. static_thrust_to_weight on the test fixture: original ctx.warnings == [('powertrain_route_winding_resistance', {'route': 'B'})], mutant []; t0_w = 0.988864 in both. The test's asserts are `assert close(got["t0_w"], t_static / (3.4 * G), 1e-6)`, the hand value and `assert set(ctx.embedded_requests) == set(formula.embeds)`; the route-notice asserts elsewhere (test_powertrain_chain.py:227, test_motor_propeller_part_load.py:146, test_powered_performance.py:64/112, endurance tests) belong to other formulas.
- **Acceptance mutation:** `git apply rework/patches/WP-P3/P3-F08.patch` (from the audit folder; aero_kernel/formulas/static_thrust_to_weight.py:49  removed `declare_route(ctx)`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, same test: `assert [w.code for w in ctx.warnings] == ['powertrain_route_winding_resistance']` and `ctx.warnings[0].detail == {'route': 'B'}`; in test_the_chain_through_the_engine_gives_the_independent_values assert the code is among got['static-thrust-to-weight'].warnings.

## P3-F03 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_spar_capacity.py` · existing test `test_normal_mode_origin_is_an_offset_from_the_segment_root` (line 377)
- **Production:** `aero_kernel/spar_capacity.py:239-242`
- **Gap:** The axis origin of a partial-extent spar (root rib of ITS segment; offset in normal mode, absolute in standard mode) is unproven: a spar in an outboard segment could be placed from y = 0 and reported present/absent at the wrong stations. (Module is unreachable until gh-1429, so no user value is wrong today.)
- **Evidence:** `wing_ = two_rib_wing(fields, tip=(0.0, 0.5, 0.0), tip_chord=0.2)` - every fixture with spare_start/spare_length has its segment root at xyz_le y = 0.0, so `root.xyz_le[1] + offset` equals `offset`. Mutation `return root.xyz_le[1] + offset, slope` -> `return offset, slope`: all spar tests pass. test_standard_mode_origin_is_an_absolute_point (line 538) uses the same root, so the two tests assert identical numbers (0.24 absent, 0.26 present) for the two rules.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived 1081 fast tests (incl. test_spar_capacity.py and test_spar_validation.py). Witness wing([spar(...)], [spar(..., spare_start=0.1, spare_length=0.2)]): original gives NoSparAtStation at y 0.55 and 0.85, BendingCapacity at 0.6/0.65/0.8; the mutant gives NoSparAtStation at all five. Normal-mode witness with spare_origin [0,0.2,0], spare_start 0.05 in the second segment: original absent at 0.74, present at 0.76; mutant present from 0.51. Both cited tests use `wing_ = two_rib_wing(fields, tip=(0.0, 0.5, 0.0), tip_chord=0.2)` and assert the same pair 0.24/0.26.
- **Acceptance mutation:** `git apply rework/patches/WP-P3/P3-F03.patch` (from the audit folder; aero_kernel/spar_capacity.py:241  `return root.xyz_le[1] + offset, slope` -> `return offset, slope`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_spar_capacity.py. (1) wing([spar(section=RECTANGULAR, material='test')], [spar(section=RECTANGULAR, material='test', spare_start=0.1, spare_length=0.2)]) (ribs at y = 0, 0.5, 1.0): y 0.55 -> NoSparAtStation, 0.6, 0.65, 0.8 -> BendingCapacity, 0.85 -> NoSparAtStation (verified on unmutated code). (2) Same two-segment wing, second-segment spar with spare_vector [0,1,0], spare_origin [0,0.2,0], spare_start 0.05: mode 'normal' present from y = 0.5+0.2+0.05 = 0.75; mode 'standard' present from y = 0.2+0.05 = 0.25, i.e. over the whole segment from 0.5.

## P3-F05 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_powered_flight.py` · existing test `test_the_sustained_load_factor_is_the_closed_form_one` (line 300)
- **Production:** `aero_kernel/formulas/powered_flight.py:716`
- **Gap:** The declared limit of a sustained turn (thrust vs wing, ADR 0020 notice) can be the verdict at n_lim instead of the one the bisection met: a thrust-limited turn would be declared wing-limited.
- **Evidence:** `assert got.limit == expected[1]` at 20 m/s, n_lim 6, where the wing stops both at n_lim and at the answer; the formula tests accept either: `assert declared in (['thrust'], ['wing'])`. Mutation `high, stop = middle, found` -> `high = middle`: 298 passed.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived 1081 fast tests. pf.sustained_load_factor(flight(), 28.0, 10.0): original TurnLimit(n=4.34764, limit='thrust'), mutant limit='wing' with the same n. At formula level max_sustained_turn_rate with the default fixture (n_lim 6) declares ['thrust'] on the original and ['wing'] on the mutant; the test accepts both: `assert declared == [limit_expected] or {*declared, limit_expected} == {"thrust", "wing"}`.
- **Verifier's note:** The aero turn test only asserts that a powered_limit_declared notice exists, so it would not fail.
- **Acceptance mutation:** `git apply rework/patches/WP-P3/P3-F05.patch` (from the audit folder; aero_kernel/formulas/powered_flight.py:716  `high, stop = middle, found` -> `high = middle`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_powered_flight.py: got = await pf.sustained_load_factor(flight(), 28.0, 10.0); expect got.limit == 'thrust' and got.n == pb.sustained_n(28.0, 3.4, 10.0)[0] = 4.34764 (rel 1e-5). At n = 10 the wing stops the turn (C_L = 10*33.34/240.1 = 1.39 > 1.2) while the thrust binds first at n = 4.35, so the two labels differ (verified on unmutated code).

## P3-F06 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_powered_flight.py` · no test exists
- **Production:** `aero_kernel/formulas/powered_flight.py:580`
- **Gap:** The golden-section refinement may evaluate speeds below the scan start when the best scan point is the start itself; on airframes whose sweep has no lift peak there (gh-1419) the formula would end as not_converged again.
- **Evidence:** `low = max(speeds[best] - step, start)` -> `low = speeds[best] - step`: 298 passed. test_a_sweep_without_a_peak_below_the_scan_start_does_not_end_the_formula asserts `min(v for v, _ in opti.evaluations) >= start - 1e-9`, but none of its six optima sits on the first scan point.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived 1081 fast tests. pf.maximise_over_speed(f(v) = -v, flight(), 9.5): original optimum v = 9.50005 with lowest evaluated speed 9.5; mutant optimum v = 7.50006 with lowest evaluated speed 7.50006, i.e. 2 m/s below the scan start. The existing guard `assert min(v for v, _ in opti.evaluations) >= start - 1e-9` runs only on cases whose optimum is not the first scan point.
- **Verifier's note:** Aero candidates are uncertain: they fail only if the best scan point is the start itself and the sweep has no lift peak below it (RV7 vertical climb at the floor is the likelier one).
- **Acceptance mutation:** `git apply rework/patches/WP-P3/P3-F06.patch` (from the audit folder; aero_kernel/formulas/powered_flight.py:580  `low = max(speeds[best] - step, start)` -> `low = speeds[best] - step`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_powered_flight.py: record the arguments of f(v) = -v, call pf.maximise_over_speed(f, flight(), 9.5); expect min(recorded) >= 9.5 and 9.5 <= optimum.v < 9.51 (unmutated code gives 9.50005 and a minimum of 9.5).

## P3-F09 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_powertrain_chain.py` · no test exists
- **Production:** `aero_kernel/formulas/motor_propeller_equilibrium.py:193`
- **Gap:** With two torque-balance crossings inside the table the full-throttle speed is meant to be the highest one; taking the lowest would lower every thrust-dependent quantity and pass.
- **Evidence:** `for low, high in reversed(covered_pairs(points)):` -> without reversed(): 298 passed. Every table fixture (APC 13x8E, small_table flat C_P) has a single sign change.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived 1081 fast tests. Not equivalent: a four-block table (1000/2000/2500/3000 rpm, flat over J to 3.0, C_P = 10.379, 5.502, 0.930, 1.431) with K_v 300, I_0 1.2, R_m 0.082, 14.8 V, V = 0 has grid residuals +2.21, -1.56, +1.24, -0.91 Nm; equilibrium() returns 2807.39 rpm on the original (highest crossing) and 1492.04 rpm on the mutant.
- **Verifier's note:** No aero test reaches a second crossing: the APC 13x8E table has one sign change.
- **Acceptance mutation:** `git apply rework/patches/WP-P3/P3-F09.patch` (from the audit folder; aero_kernel/formulas/motor_propeller_equilibrium.py:193  `for low, high in reversed(covered_pairs(points)):` -> `for low, high in covered_pairs(points):`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_powertrain_edges.py: a three-block table (1000, 2000, 3000 rpm, J to 3.0) whose C_P makes the residual Q_m - Q_p positive at 1000, negative at 2000 only through a C_P spike there, and the motor (K_v high enough that the free-run speed is above 3000 rpm) crossing again between 2000 and 3000 after a positive point inserted at 2500 rpm; compute both roots with a plain bisection of (I-I_0)/K_v' - C_P rho n^2 D^5/(2 pi) and expect the upper one (rel 1e-6). If the maintainer does not want the rule, delete reversed() and the docstring sentence instead.
- **Correction:** (unclear) The idea works, but the text is hard to follow (a 'three-block table' with a point 'inserted at 2500 rpm' is four blocks). A verified construction: blocks 1000/2000/2500/3000 rpm, J 0..3.0, C_P per block = 0.5x, 1.5x, 0.5x, 1.5x of the C_P that zeroes the residual at that block, K_v 300 rpm/V (free-run 4440 rpm); expect about 2807.39 rpm from an independent bisection between 2500 and 3000 rpm.

## P3-F10 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_motor_propeller_part_load.py` · no test exists
- **Production:** `aero_kernel/formulas/motor_propeller_part_load.py:84`
- **Gap:** With two thrust = drag crossings the part-load speed is meant to be the lowest; the highest would pass.
- **Evidence:** `for low, high in covered_pairs(points):` -> `reversed(covered_pairs(points))`: 298 passed.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived 1081 fast tests. Not equivalent: four blocks 1200/2400/3600/4800 rpm, flat over J, C_T = 0.05, 0.1, 0.02, 0.1, V = 0, drag = 100 rho D^4 (thrust at the blocks 0.291, 2.330, 1.049, 9.320 N against 1.456 N): solve_part_load_speed returns 2051.97 rpm on the original (lowest crossing) and 3695.43 rpm on the mutant.
- **Verifier's note:** Input severity was low; a mutation was run because the original probe existed.
- **Acceptance mutation:** `git apply rework/patches/WP-P3/P3-F10.patch` (from the audit folder; aero_kernel/formulas/motor_propeller_part_load.py:84  `for low, high in covered_pairs(points):` -> `for low, high in reversed(covered_pairs(points)):`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_powertrain_coverage_edge.py: flat-J table with C_T per block 0.1, 0.02, 0.1 at 1200, 2400, 3600 rpm at V = 0; thrust(n) = C_T(n) rho n^2 D^4 then crosses a drag between its local maximum and minimum three times; take the lowest root from a 1 rpm scan of that expression and expect solve_part_load_speed to return it (rel 1e-6).
- **Correction:** (no) The recommended three-block table (C_T 0.1, 0.02, 0.1 at 1200/2400/3600 rpm) does not kill the mutant: only one neighbouring pair has the required sign change (low > 0 >= high), so original and mutant return the same speed for every drag tried (33..300 rho D^4: 2407.46 .. 3456.19 rpm in both; below that outside_propeller_table in both). Use four blocks, e.g. C_T 0.05, 0.1, 0.02, 0.1 at 1200/2400/3600/4800 rpm with drag 100 rho D^4: expected lowest root 2051.97 rpm.

## P3-F12 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_powertrain_edges.py` · existing test `test_exactly_on_the_last_block_the_top_block_alone_decides` (line 42)
- **Production:** `aero_kernel/formulas/propeller_table_lookup.py:119-122`
- **Gap:** Exactly on an inner rpm block the neighbour block's J range must not be checked; with the branch removed such a point fails as outside_propeller_table although the block covers it.
- **Evidence:** The test covers `last["rpm"] / 60` only. Deleting the branch `if (rpm <= low.rpm): return _in_block(low, j)`: 298 passed.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived 1081 fast tests. Not equivalent: blocks 1200/2400/3600 rpm with J ranges 0.8/0.8/0.2, table_lookup(components, 0.5, 2400.0/60) returns Coefficients(c_t=0.1, c_p=0.04) on the original and raises outside_propeller_table ('outside the table at 3600 rpm (J from 0 to 0.2)') on the mutant. The cited test covers `last["rpm"] / 60` only.
- **Verifier's note:** Input severity was low; a mutation was run because the original probe existed.
- **Acceptance mutation:** `git apply rework/patches/WP-P3/P3-F12.patch` (from the audit folder; aero_kernel/formulas/propeller_table_lookup.py:119-122  removed `if (rpm <= low.rpm): return _in_block(low, j)`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_powertrain_edges.py with narrow_second_block() of test_powertrain_coverage_edge (blocks 1200/2400/3600 rpm, J ranges 0.8/0.2/0.8, C_T 0.1, C_P 0.04): table_lookup(components, 0.5, 2400.0/60) must raise outside_propeller_table (J beyond its own block), while table_lookup(components, 0.5, 1200.0/60) returns c_t == 0.1 and c_p == 0.04 although the 2400 rpm neighbour ends at J = 0.2.
- **Correction:** (no) As written it does not kill the mutant: with narrow_second_block() (J ranges 0.8/0.2/0.8) the call at 2400 rpm with J 0.5 raises in original and mutant (J is beyond its own block), and the call at 1200 rpm is the FIRST block, handled by the first-block branch, not the removed inner-block branch; I ran both and the results are identical. The narrow range must be on the UPPER neighbour of the inner block: J ranges 0.8/0.8/0.2 and lookup (0.5, 2400.0/60) == (0.1, 0.04).

## P1-F09 · low · missing_edge_case · do together with P3-F08

- **Test file:** `aero_kernel/tests/test_powertrain_chain.py` · existing test `test_a_propeller_that_does_not_turn_has_no_advance_ratio` (line 123)
- **Production:** `aero_kernel/formulas/advance_ratio_from_speed.py:31`
- **Gap:** Only n_prop <= 0 is tested; the diameter is not. A check on n_prop alone passes the suite (D_prop = 0 then divides by zero), and today's product check lets two negative factors through: advance_ratio(5, -150, -0.3) returns 0.111.
- **Evidence:** `@pytest.mark.parametrize("n_prop", [0.0, -3.0])` ... `advance_ratio(5.0, n_prop, 0.3302)`
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived 1081 fast tests. Not equivalent: advance_ratio(5.0, 150.0, 0.0) raises non_positive_value on the original and ZeroDivisionError on the mutant; (5.0, 150.0, -0.33) raises on the original and returns -0.10101 on the mutant. The only raising test is `@pytest.mark.parametrize("n_prop", [0.0, -3.0])` with `advance_ratio(5.0, n_prop, 0.3302)`. The second half of the claim also holds on unmutated code: advance_ratio(5, -150, -0.3) returns 0.1111.
- **Verifier's note:** Input severity was low; a mutation was run anyway because the original probe existed. Same test file as P3-F08 (test_powertrain_chain.py).
- **Acceptance mutation:** `git apply rework/patches/WP-P3/P1-F09.patch` (from the audit folder; aero_kernel/formulas/advance_ratio_from_speed.py:31  `if not swept > 0.0:` -> `if not n_prop > 0.0:`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast: advance_ratio(5.0, 150.0, 0.0) and (5.0, 150.0, -0.33) raise FormulaError non_positive_value; decide and pin (5.0, -150.0, -0.33) (docstring says both > 0); NaN for each argument raises. Also give the formula its own hand value written as a number: 10/(150*0.3302) = 0.2018978.
- **Correction:** (unclear) The D_prop = 0 and D_prop < 0 cases kill the mutant, and 10/(150*0.3302) = 0.2018978 is right (recomputed: 0.20189784). But 'NaN for each argument raises' is false today for v = NaN (the original returns nan, no error), and (5, -150, -0.33) returns 0.10101 today: both need a production decision, not only a test.

## P3-F11 · low · weak_assertion · do together with P3-F07

- **Test file:** `aero_kernel/tests/test_powered_performance.py` · existing test `test_a_drive_train_that_cannot_hold_level_flight_is_a_declared_failure` (line 77)
- **Production:** `aero_kernel/formulas/max_level_speed.py:100-101`
- **Gap:** max-level-speed's no_feasible_speed message is meant to say whether the wing or the thrust stopped every speed; the reason can be lost (message 'no speed was evaluated').
- **Evidence:** `assert caught.value.code == "no_feasible_speed"` only. Removing `reasons.add(Unflyable.THRUST)`: 298 passed. (The message tests in test_powered_flight.py target maximise_over_speed, a different loop.)
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived 1081 fast tests. max_level_speed with PolarOpti(cd0=2.0), 3.4 kg: original message '... (9.52513 to 150 m/s): the propeller table ends and the thrust at full throttle is below what the state needs', mutant '...: the propeller table ends'. The test asserts only `assert caught.value.code == "no_feasible_speed"`. The reviewer's wording of the mutant message ('no speed was evaluated') is not what this fixture produces, but the thrust reason is lost as claimed.
- **Verifier's note:** Input severity was low; a mutation was run because the original probe existed. Same test file as P3-F07 (test_powered_performance.py).
- **Acceptance mutation:** `git apply rework/patches/WP-P3/P3-F11.patch` (from the audit folder; aero_kernel/formulas/max_level_speed.py:100  `reasons.add(Unflyable.THRUST)` -> `pass`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, same test: add `assert 'thrust at full throttle is below' in caught.value.message` and `assert 'wing cannot carry' not in caught.value.message` (PolarOpti(cd0=2.0), 3.4 kg: every flyable speed has D > T).

## P3-F14 · low · mirror_or_tautology

- **Test file:** `aero_kernel/tests/test_powered_performance.py` · existing test `test_the_fastest_sustained_turn_matches_the_closed_form_scan` (line 242)
- **Production:** `aero_kernel/formulas/max_sustained_turn_rate.py:42-44`
- **Gap:** The turn kinematics have no hand-computed value: the test re-types the production expression, so a wrong relation typed twice would pass (kernel rule: every formula against a hand-computed value).
- **Evidence:** Test helper: `return pb.G * math.sqrt(n * n - 1.0) / v` and `return -(v * v / (pb.G * math.sqrt(n * n - 1.0)))`; production: `return g * math.sqrt(n * n - 1.0) / v`.
- **Verified:** CONFIRMED_BY_READING (READING). The test helper re-types the production expression: test `def rate(v, n): return pb.G * math.sqrt(n * n - 1.0) / v` against production `return g * math.sqrt(n * n - 1.0) / v` (max_sustained_turn_rate.py turn_rate). grep finds no fast test that calls turn_rate or turn_radius with a number; the formula tests compare against turn_scan(rate, ...) built on that helper.
- **Verifier's note:** Keep: omega_max and r_min reach the caller and have no number written by hand anywhere in the fast tier.
- **Test to write:** Fast, test_powered_performance.py: turn_rate(9.80665, 20.0, 2.0) == 0.849281 rad/s (9.80665 * 1.7320508 / 20), i.e. 48.660 deg/s, and turn_radius(9.80665, 20.0, 2.0) == 23.549 m (400 / (9.80665 * 1.7320508)), rel 1e-5; cross-check omega = V / r.

## P3-F16 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_motor_propeller_part_load_aero.py` · existing test `test_the_avistar_cruises_on_a_battery_power_the_drive_train_can_deliver` (line 32)
- **Production:** `aero_kernel/formulas/motor_propeller_part_load.py:166`
- **Gap:** The only real-solver test of the part-load formula accepts any positive battery power.
- **Evidence:** `assert power > 0.0`, `assert abs(current - power / 14.8) <= 1e-9 * power`, `assert 0.0 < got["thrust-demand-ratio"].value < 1.0`.
- **Verified:** CONFIRMED_BY_READING (READING). The aero test's value asserts are `assert power > 0.0  # the drive train draws power to hold level flight`, `assert abs(current - power / 14.8) <= 1e-9 * power  # U_bat = 4 x 3.7 V` and `assert 0.0 < got["thrust-demand-ratio"].value < 1.0`; the module docstring says 'The assertions are physical consistency and plausibility, not a validation'. Any positive battery power passes.
- **Verifier's note:** Keep: it is the only real-solver check of battery-power; the lower bound P_bat > D V is physics and costs one line.
- **Test to write:** Aero tier, same test: bound the power by hand from the drag the fast tier already records for this aircraft (2.21 N at 18 m/s, AVISTAR_DRAG_N): shaft power >= D V = 39.8 W, so P_bat > 39.8 W; and P_bat < D V / 0.3 = 133 W as a generous lower efficiency bound stated in the docstring.
- **Correction:** (unclear) D V = 2.21 * 18 = 39.8 W and 39.8 / 0.3 = 132.6 W recomputed. But AVISTAR_DRAG_N has no 18.0 m/s key (17.75: 2.2065 N, 22.0: 2.3661 N), so 2.21 N is an interpolation to be stated as such, and whether the real P_bat lies below 133 W could not be checked without running the aero test.

## Not part of this package's work

| Finding | State | Reason |
|---|---|---|
| P3-F04 | production_defect | latent: not reachable through the API (stall-speed is no input, its producer never returns 0); maintainer decides whether to add the precondition stall_speed_usable |
| P3-F13 | dropped | Drop reason: the assertions are right for the production rule ('close to or above the weight'), and the truly vertical floor case (T_0 > W, mass 0.8) is asserted in test_powered_performance.py::test_a_thrust_above_the_weight_climbs_vertical |
| P3-F15 | dropped | Drop reason: E_bat is derived from three inputs that are each checked > 0 at the input and cannot be overridden through values, so a non-positive capacity cannot reach the three endurance formulas. |
| P3-F17 | dropped | Drop reason: the mapping is `fields` handed unchanged to Components.model_validate in a test builder; there is no production mapping that could be wrong, and the values of each part are pinned by hand in test_airplane_components.py (HAND ta |
