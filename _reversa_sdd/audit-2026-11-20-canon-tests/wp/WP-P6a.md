# WP-P6a — Opti adapter: fakes that record objective and constraints

Self-contained brief for one implementer subagent. Base commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

Every finding below was checked by an independent verifier on 2026-11-21 (`../rework/`). The line **Verified** says how. Where **Correction** appears, it overrides the text under **Test to write**.

- **Production code under test:** aero_kernel/solvers/opti.py, regime.py, asb_airplane.py
- **Requirement sources:** ARCHITECTURE §8.8, ADR 0020, ADR 0028
- **Test files you may change:** `aero_kernel/tests/test_solvers_flap_devices.py`, `aero_kernel/tests/test_solvers_opti.py`, `aero_kernel/tests/test_solvers_opti_glide.py`, `aero_kernel/tests/test_solvers_opti_level.py`, `aero_kernel/tests/test_solvers_opti_level_point.py`, `aero_kernel/tests/test_solvers_opti_real.py`, `aero_kernel/tests/test_solvers_opti_roll.py`, `aero_kernel/tests/test_solvers_opti_sweep.py`
- **Findings to work on:** 16 (3 high, 7 medium, 6 low)

## P6a-F01 · high · untested_warning

- **Test file:** `aero_kernel/tests/test_solvers_opti_level.py` · existing test `test_the_regime_warnings_are_those_of_the_slowest_and_the_fastest_point` (line 209)
- **Production:** `aero_kernel/solvers/opti.py:2299`
- **Gap:** level_polar could check the regime at the slowest point only: a Mach or Re-above-band warning of the fastest point (up to the `error` mach_beyond_validity) would be dropped and no test fails.
- **Evidence:** monkeypatch.setattr(opti_module, "level_polar_worker", canned(polar_at((18.0, 12.0, 6.0)))) ... assert result.warnings == (*slow, drag_notice())  -- the fastest point (18 m/s) has no warning, so its check is never observed.
- **Verified:** CONFIRMED (MUTATION_RERUN). All 1448 fast tests stay green under the mutation. The only test of the two-point check uses a fastest point without any warning: `monkeypatch.setattr(opti_module, "level_polar_worker", canned(polar_at((18.0, 12.0, 6.0))))` ... `assert result.warnings == (*slow, drag_notice())`.
- **Verifier's note:** No aero test asserts a regime warning of the fastest level-polar point (parabolic-polar fleet test only looks for polar_fit_* codes).
- **Acceptance mutation:** `git apply rework/patches/WP-P6a/P6a-F01.patch` (from the audit folder; aero_kernel/solvers/opti.py:2299  `for speed in (min(polar.v_ms), max(polar.v_ms)):` -> `for speed in (min(polar.v_ms),):`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_solvers_opti_level.py: canned polar with v_ms (120.0, 12.0, 6.0) on airplane() (chords 0.2 / 0.1 m, AIR a = 340.294 m/s). Expected codes in order: ['reynolds_bubble_sensitive' (slowest point, 6 m/s: MAC 0.1556 m, nu = 1.7894e-5 / 1.225 = 1.4607e-5 m^2/s, Re 6.4e4), 'reynolds_above_band' (fastest point: Re = 120 * 0.1556 / 1.4607e-5 = 1.28e6 > 1e6), 'mach_above_limit' (120 / 340.294 = 0.353 > 0.3), 'induced_drag_viscous_factor_removed']. Assert the mach warning's detail['mach'] == 120.0 / 340.294 (rel 1e-12).

## P6a-F02 · high · untested_error_path

- **Test file:** `aero_kernel/tests/test_solvers_opti_sweep.py` · existing test `test_a_deflected_control_surface_is_refused` (line 74)
- **Production:** `aero_kernel/solvers/opti.py:2397`
- **Gap:** sweep could accept a deflected flap (flaps_supported=True) and return the polar of the flapped airplane without any caveat, although ch. 8.8 says sweep refuses a flap because it returns no warnings.
- **Evidence:** deflected = airplane(device=("aileron", 4.0)) ... assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION  -- only an aileron is tried.
- **Verified:** CONFIRMED (MUTATION_RERUN). All 1448 fast tests stay green under the mutation. The only refusal test of sweep tries an aileron: `deflected = airplane(device=("aileron", 4.0))`; no fast test passes a deflected flap to OptiAdapter.sweep.
- **Acceptance mutation:** `git apply rework/patches/WP-P6a/P6a-F02.patch` (from the audit folder; aero_kernel/solvers/opti.py:2397  sweep: `refuse_deflected_devices(airplane, "AeroBuildup", flaps_supported=False)` -> `flaps_supported=True`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_solvers_opti_sweep.py: airplane(device=('flap', 10.0), hinge=0.75); await OptiAdapter(InProcessRuntime()).sweep(plane, AIR, 10.0, (14.0, 14.5, 15.0)) must raise FormulaError with category UNSUPPORTED_CONFIGURATION, 'flap-1' in the message, and the canned worker must not have been called.

## P6a-F03 · high · untested_warning

- **Test file:** `aero_kernel/tests/test_solvers_opti_glide.py` · no test exists
- **Production:** `aero_kernel/solvers/opti.py:2238`
- **Gap:** best_glide could drop the flap caveats (hinge_line_averaged, control_surface_fit_range_unknown) of a flapped configuration: an undeclared model substitution (ADR 0020). The same declaration is untested for min_sink (opti.py:2442) and level_flight_point (opti.py:2367).
- **Evidence:** No test of test_solvers_opti_glide.py, test_solvers_opti_min_sink.py or test_solvers_opti_level_point.py passes a deflected flap; the only flap asserts are in the stall, evaluate, zero-lift, level-polar and roll files.
- **Verified:** CONFIRMED (MUTATION_RERUN). All 1448 fast tests stay green under the mutation. grep 'flap' finds nothing in test_solvers_opti_glide.py, test_solvers_opti_min_sink.py and test_solvers_opti_level_point.py. A second run with the same change at min_sink (opti.py:2442) and level_flight_point (opti.py:2367) also stayed green (patch P6a-F03b.patch).
- **Verifier's note:** Three entry points, one root cause; the implementer needs one test per entry point (extra patch patches/WP-P6a/P6a-F03b.patch covers the other two).
- **Acceptance mutation:** `git apply rework/patches/WP-P6a/P6a-F03.patch` (from the audit folder; aero_kernel/solvers/opti.py:2238  best_glide: `warnings = _flap_warnings(flaps)` -> `warnings = []`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, one test per entry point (best_glide, min_sink, level_flight_point) with a canned worker: airplane(device=('flap', 10.0), hinge=0.75) at 18 m/s (no regime warning). Expected warnings exactly: (control_surface_fit_range_unknown with detail == {'flaps': [{'wing': 'Main', 'device': 'flap-1', 'deflection_deg': 10.0}]}, induced_drag_viscous_factor_removed). With rel_chord_root 0.74 / rel_chord_tip 0.76 additionally hinge_line_averaged first, detail used == 0.75.

## P6a-F04 · medium · over_mocked

- **Test file:** `aero_kernel/tests/test_solvers_opti.py` · existing test `test_an_interior_optimum_is_accepted` (line 352)
- **Production:** `aero_kernel/solvers/opti.py:645`
- **Gap:** In the fast tier the stall problem is not pinned as an optimisation at all: the objective can be any expression (minimise lift instead of V) and the lift constraint can ask for 2 n m g; the same shared _solve constraint is unpinned for best glide and minimum sink. Only the aero tier (lift balance 1e-6, closed-form parabola with real IPOPT) notices.
- **Evidence:** class FakeOpti: ... def subject_to(self, _: object) -> None: return None / def minimize(self, _: object) -> None: return None ... assert (outcome.value.v_s, outcome.value.alpha_s) == (8.0, 15.75)  -- the asserted numbers are the fake solver's own return.
- **Verified:** CONFIRMED (MUTATION_RERUN). All 1448 fast tests stay green under the mutation. The fast fakes discard the constraint: test_solvers_opti.py `def subject_to(self, _: object) -> None: return None`, and the glide fake's `def __eq__(self, other: object) -> bool:  # ... builds a constraint / return True`.
- **Verifier's note:** Input severity was medium; raised by the rule, to be lowered again if an aero candidate fails.
- **Acceptance mutation:** `git apply rework/patches/WP-P6a/P6a-F04.patch` (from the audit folder; aero_kernel/solvers/opti.py:645  `opti.subject_to(aero["L"] == problem.lift)` -> `opti.subject_to(aero["L"] == 2.0 * problem.lift)`). Today every fast test stays green; after your change at least one fast test must fail under it. The aero tier catches it (aero_kernel/tests/test_solvers_opti_real.py::test_the_lift_balance_holds_at_the_optimum); the new test belongs in the fast tier.
- **Test to write:** Fast, test_solvers_opti.py: reuse the recording Expr / FakeOpti of test_solvers_opti_glide.install_optimum but record subject_to as well (make Expr.__eq__ return a ('eq', name, other) record). For stall_worker with mass 1.5 kg, g 9.81, n 1: assert the minimised expression is the speed variable itself (name 'speed') and the one constraint is ('eq', 'L', 1.5 * 9.81 = 14.715); for n = -1 the constraint value is -14.715. Do the same constraint assert in the glide and min-sink worker tests. (P6a-M01b: objective replaced by aero['L'] also survived.)

## P6a-F05 · medium · over_mocked

- **Test file:** `aero_kernel/tests/test_solvers_opti_roll.py` · existing test `test_the_worker_rotates_about_the_stability_axis` (line 363)
- **Production:** `aero_kernel/solvers/opti.py:1274`
- **Gap:** In the fast tier the steady roll has no equilibrium conditions: the rolling-moment constraint can be removed and the lift constraint can lose g without a failing test. The aero residual test pins both.
- **Evidence:** def subject_to(self, _: object) -> None: return None ... assert (outcome.value.p_rad_s, outcome.value.alpha_deg) == (2.0, 4.0)
- **Verified:** CONFIRMED (MUTATION_RERUN). All 1448 fast tests stay green under the mutation. The roll fake discards every constraint: test_solvers_opti_roll.py `def subject_to(self, _: object) -> None: return None`, and its AeroBuildup returns `{"L": 0.0, "Cl": cl, "Cn": cn}` as plain floats.
- **Verifier's note:** Input severity was medium; raised by the rule, to be lowered again if an aero candidate fails.
- **Acceptance mutation:** `git apply rework/patches/WP-P6a/P6a-F05.patch` (from the audit folder; aero_kernel/solvers/opti.py:1275  removed `opti.subject_to(stability_rolling_moment(aero["Cl"], aero["Cn"], alpha, asb.numpy) == 0)`). Today every fast test stays green; after your change at least one fast test must fail under it. The aero tier catches it (aero_kernel/tests/test_solvers_opti_roll_real.py::test_a_positive_command_rolls_right_and_the_solution_is_an_equilibrium); the new test belongs in the fast tier.
- **Test to write:** Fast, test_solvers_opti_roll.py: let Boundary record subject_to arguments and let the fake AeroBuildup return recording expressions for L, Cl, Cn (as in the glide fake). Assert exactly two constraints: L == 0.15 * 9.81 = 1.4715 N, and (Cl*cos(alpha) + Cn*sin(alpha)) == 0 built from the model's Cl and Cn and the alpha variable. (P6a-M05: constraint L == m survived too.)

## P6a-F06 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_solvers_opti_roll.py` · existing test `test_steady_roll_end_to_end_with_stub` (line 66)
- **Production:** `aero_kernel/solvers/opti.py:2504`
- **Gap:** steady_roll could key its job with the clean airplane's model key (roll 0): inside a CachedKernel worker the roll problem would then be solved through the cached function of the airplane without the aileron deflection and return a roll rate near zero. No fast test notices; the aero tier would (three calls on one runtime in the RV-7 test).
- **Evidence:** assert (request.v_ms, request.delta_deg) == (SPEED, 20.0) / assert request.airplane == plane  -- request.model_key is not asserted.
- **Verified:** CONFIRMED (MUTATION_RERUN). All 1448 fast tests stay green under the mutation. test_steady_roll_end_to_end_with_stub asserts `assert (request.v_ms, request.delta_deg) == (SPEED, 20.0)` and `assert request.airplane == plane`, never request.model_key; grep 'model_key' finds nothing in test_solvers_opti_roll.py. On the unmutated copy the request's key equals adapter._model_key(plane, 20.0) (sha256:310fb3...) and differs from the roll-0 key (sha256:448347...).
- **Verifier's note:** test_solvers_opti_roll_real.py does not reach it: its roll() helper opens a new SolverRuntime per call, so the worker cache is empty. The candidates fail only if the roll job is routed to the worker slot that holds the clean (or other-deflection) function; the parent's routing prefers that slot for an equal key. Input severity was medium; raised by the rule, to be lowered again if an aero candidate fails.
- **Acceptance mutation:** `git apply rework/patches/WP-P6a/P6a-F06.patch` (from the audit folder; aero_kernel/solvers/opti.py:2504  steady_roll: `model_key=self._model_key(airplane, delta_a_deg),` -> `model_key=self._model_key(airplane, 0.0),`). Today every fast test stays green; after your change at least one fast test must fail under it. The aero tier catches it (aero_kernel/tests/test_roll_rate_fleet.py::test_roll_rate_goldens_per_world[FleetMember.BRYAN]); the new test belongs in the fast tier.
- **Test to write:** Fast, test_solvers_opti_roll.py: after steady_roll(plane, MASS, GRAVITY, AIR, SPEED, 20.0) assert request.model_key == model_key(plane, roll_deg=20.0, model_size=opti_module.NEURALFOIL_MODEL_SIZE, tool_versions=adapter.tool_versions()) and that it differs from the key with roll_deg=0.0 (as test_solvers_opti_zero_lift does for the clean key).

## P6a-F07 · medium · untested_error_path

- **Test file:** `aero_kernel/tests/test_solvers_opti_roll.py` · no test exists
- **Production:** `aero_kernel/solvers/opti.py:2482`
- **Gap:** steady_roll could omit require_available: without AeroSandbox the caller would get a worker ImportError (internal) instead of tool_unavailable. Every other entry point has this test; steady_roll and level_flight_point do not.
- **Evidence:** test_solvers_opti_roll.py has no test that patches OptiAdapter.requirements; grep 'TOOL_UNAVAILABLE' finds none in test_solvers_opti_roll*.py or test_solvers_opti_level_point.py.
- **Verified:** CONFIRMED (MUTATION_RERUN). All 1448 fast tests stay green under the mutation. grep 'TOOL_UNAVAILABLE|requirements' finds nothing in test_solvers_opti_roll.py, test_solvers_opti_roll_flaps.py and test_solvers_opti_level_point.py. Only the steady_roll half is a gap of its own: level_flight_point has no require_available of its own, it calls `request, flaps = self._request(airplane, mass_kg, gravity, 1.0, air, upright_only=True)` and _request (opti.py:2157) holds the check that the stall, glide and min-sink tool_unavailable tests already kill.
- **Verifier's note:** No aero test can reach it (AeroSandbox is installed there).
- **Acceptance mutation:** `git apply rework/patches/WP-P6a/P6a-F07.patch` (from the audit folder; aero_kernel/solvers/opti.py:2482  steady_roll: removed `self.require_available()`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast: monkeypatch.setattr(OptiAdapter, 'requirements', {'no-such-distribution': 'no_such_xyz'}); steady_roll(rolling_airplane(), 0.15, 9.81, AIR, 10.0, 20.0) and level_flight_point(airplane(), 0.5, 9.80665, AIR, 18.0, 1.0) must each raise FormulaError with category TOOL_UNAVAILABLE.

## P6a-F08 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_solvers_opti_level_point.py` · existing test `test_an_inadmissible_load_factor_is_refused_before_any_solve` (line 128)
- **Production:** `aero_kernel/solvers/opti.py:2350`
- **Gap:** level_flight_point could refuse n_load = 0 (the vertical dive of dive-speed, ch. 8.8 #1414): the admissible boundary is tested on the worker only, not on the adapter.
- **Evidence:** @pytest.mark.parametrize("n_load", [-0.5, math.nan, math.inf])  -- no admissible n_load = 0 through OptiAdapter.level_flight_point.
- **Verified:** CONFIRMED (MUTATION_RERUN). All 1448 fast tests stay green under the mutation. The adapter test tries inadmissible values only: `@pytest.mark.parametrize("n_load", [-0.5, math.nan, math.inf])`; n_load = 0 is exercised on the worker (`level_point_worker(point_request(18.0, 0.0))`), and every fast dive-speed test replaces level_flight_point by a stub (powered_builders.py:54).
- **Verifier's note:** The aero candidate asserts error.code == 'outside_propeller_table'; under the mutation the dive's first point is refused as invalid_input instead.
- **Acceptance mutation:** `git apply rework/patches/WP-P6a/P6a-F08.patch` (from the audit folder; aero_kernel/solvers/opti.py:2350  level_flight_point: `n_load >= 0.0` -> `n_load > 0.0`). Today every fast test stays green; after your change at least one fast test must fail under it. The aero tier catches it (aero_kernel/tests/test_powered_performance_aero.py::test_the_dive_speed_is_the_declared_table_failure_on_the_avistar); the new test belongs in the fast tier.
- **Test to write:** Fast, test_solvers_opti_level_point.py: with a canned level_point_worker, level_flight_point(airplane(), MASS, GRAVITY, AIR, 18.0, 0.0) returns the canned point and the worker's request has n_load == 0.0.

## P6a-F09 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_solvers_opti_real.py` · existing test `test_inverted_flight_finds_the_negative_lift_coefficient` (line 117)
- **Production:** `aero_kernel/solvers/opti.py:547`
- **Gap:** The inverted stall is pinned by signs only: the alpha window of the inverted branch can be replaced by the upright one (fast probe survived) and neither the lift balance nor 'first trough from alpha = 0' is asserted for n < 0 in any tier of this package.
- **Evidence:** assert solution.cl_max < 0.0 / assert solution.alpha_s < 0.0 / assert solution.v_s > 0.0 / assert polar.alpha_deg[0] < solution.alpha_s < polar.alpha_deg[-1]
- **Verified:** CONFIRMED (MUTATION_RERUN). All 1448 fast tests stay green under the mutation. The mutation is observable: for n < 0 the window of alpha becomes (-15, trough + 0.25) instead of (trough - 0.25, 25), which changes the bounds given to opti.variable and what _reject_active_bound accepts. The fast stall fake drops them (`def variable(self, **_: object) -> Variable:`) and the aero test asserts signs only: `assert solution.cl_max < 0.0` / `assert solution.alpha_s < 0.0` / `assert solution.v_s > 0.0`.
- **Verifier's note:** The aero candidate is the only aero test that reaches the inverted branch; it fails only if NACA 2412's C_L falls below the first trough between -15 deg and the trough (then the optimum moves to the bound and is refused). I could not decide that by reading; a pass there does not refute the finding.
- **Acceptance mutation:** `git apply rework/patches/WP-P6a/P6a-F09.patch` (from the audit folder; aero_kernel/solvers/opti.py:547  inverted window `low, high = alpha_peak - peak_margin_deg, ALPHA_MAX_DEG` -> `low, high = ALPHA_MIN_DEG, alpha_peak + peak_margin_deg`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Aero, test_solvers_opti_real.py, trainer at n = -1: (a) V_S == sqrt(2 * 1.5 * 9.81 / (rho * 0.28 * |cl_max|)) rel 1e-6; (b) first_extremum over the polar scanned from alpha = 0 downwards (maximum=False) lies within ALPHA_STEP_DEG of alpha_s. Fast, test_solvers_opti.py: record opti.variable kwargs in the stall fake and assert for n = -1 with lift_curve(INVERTED_TROUGH, upright=False) the alpha bounds (-10.0 - 0.25, 25.0), for n = +1 (-15.0, 15.75 + 0.25), and the V bounds (1.0, 0.6 * 340.294).

## P6a-F10 · medium · over_mocked

- **Test file:** `aero_kernel/tests/test_solvers_opti.py` · existing test `test_an_interior_optimum_is_accepted` (line 352)
- **Production:** `aero_kernel/solvers/opti.py:696`
- **Gap:** The published stall polar could be swept at the bracketing speed instead of V_S (wrong Reynolds number, so cl_max read from it is not the C_L at the stall): the fast sweep fake ignores its arguments. The aero tier catches it only indirectly through the 1e-6 lift balance.
- **Evidence:** def sweep(*_: object) -> Polar: return polar  ... monkeypatch.setattr(opti_module, "sweep_polar", sweep)
- **Verified:** CONFIRMED (MUTATION_RERUN). All 1448 fast tests stay green under the mutation. The fast fake ignores what the published polar is swept at: test_solvers_opti.py `def sweep(*_: object) -> Polar: return polar` installed for both sweep_polar and sweep_lift, while production reads the result from that polar: `cl_max = polar.cl[polar.alpha_deg.index(optimum.alpha)]`.
- **Verifier's note:** Input severity was medium; raised by the rule, to be lowered again if an aero candidate fails. The difference between V_bracket and V_S is one Reynolds refinement, so the aero kill is likely but not certain at rel 1e-6 / 1e-4.
- **Acceptance mutation:** `git apply rework/patches/WP-P6a/P6a-F10.patch` (from the audit folder; aero_kernel/solvers/opti.py:696  stall_worker: published polar swept at `problem.v_bracket` instead of `optimum.speed`). Today every fast test stays green; after your change at least one fast test must fail under it. The aero tier catches it (aero_kernel/tests/test_solvers_opti_real.py::test_the_lift_balance_holds_at_the_optimum); the new test belongs in the fast tier.
- **Test to write:** Fast, test_solvers_opti.py: let the sweep_polar fake record its arguments; with install_solution(monkeypatch, 8.0, 15.75) assert it was called once with velocity 8.0 (the optimum, not the bracketing speed sqrt(2 * 14.715 / (1.225 * 0.28 * 1.19)) = 8.49 m/s), with 15.75 among the angles and K_E_D0 as viscous factor. Aero: assert solution.polar.conditions.v_ms == solution.v_s.

## P6a-F13 · low · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_solvers_opti.py` · existing test `test_an_inadmissible_input_is_invalid_input` (line 84)
- **Production:** `aero_kernel/solvers/opti.py:2202`
- **Gap:** The stall adapter could refuse a negative load factor (inverted stall becomes invalid_input) without a fast test failing; the aero inverted test would catch it.
- **Evidence:** [(0.0, 9.81, 1.0), (-1.0, 9.81, 1.0), (1.5, 0.0, 1.0), (1.5, 9.81, 0.0), (1.5, 9.81, math.nan)]  -- no admissible n_load < 0 case.
- **Verified:** CONFIRMED_BY_READING (READING). Every fast call of OptiAdapter.stall passes n_load 1.0 except the refusal list `[(0.0, 9.81, 1.0), (-1.0, 9.81, 1.0), (1.5, 0.0, 1.0), (1.5, 9.81, 0.0), (1.5, 9.81, math.nan)]`, where -1.0 is the mass. On the unmutated copy adapter.stall(airplane(), 1.5, 9.81, -1.0, AIR) with a canned worker returns the solution; no fast test says so.
- **Verifier's note:** Keep: an inverted stall refused as invalid_input is an error that reaches the caller instead of a value; one fast test of five lines.
- **Test to write:** Fast: with a canned stall_worker, adapter.stall(airplane(), 1.5, 9.81, -1.0, AIR) returns the canned solution and the request has n_load == -1.0.

## P6a-F14 · low · untested_error_path · do together with P6a-F07

- **Test file:** `aero_kernel/tests/test_solvers_opti_roll.py` · no test exists
- **Production:** `aero_kernel/solvers/opti.py:2494`
- **Gap:** The guard 'a non-zero aileron command needs a device acting as aileron' (ValueError) can be removed unnoticed.
- **Evidence:** No test calls steady_roll with a non-zero command on an airplane without a roll device.
- **Verified:** CONFIRMED_BY_READING (READING). opti.py:2494 `if abs(delta_a_deg) > 0.0 and not driven:` / `msg = "a non-zero aileron command needs a device acting as aileron"`. grep 'ValueError' finds nothing in test_solvers_opti_roll.py or test_solvers_opti_roll_flaps.py; the two matches of 'device acting as aileron' are the AVL adapter's (test_solvers_avl_roll.py:247, test_solvers_avl_roll_real.py:88).
- **Verifier's note:** Same file and the same kind of adapter-level refusal test as P6a-F07.
- **Test to write:** Fast: steady_roll(wing_geometry((0.0, 0.2, 0.4), 1, {'name': 'E', 'role': 'elevator'}), 0.15, 9.81, AIR, 10.0, 20.0) raises ValueError matching 'needs a device acting as aileron' and the worker is not called.

## P6a-F15 · low · weak_assertion · do together with P6a-F05

- **Test file:** `aero_kernel/tests/test_solvers_opti_roll.py` · existing test `test_the_worker_records_min_confidence_and_max_effective_alpha_over_all_sections` (line 489)
- **Production:** `aero_kernel/solvers/opti.py:1103`
- **Gap:** That the recording run of the roll diagnostics is made at the solved body rates (p cos alpha, p sin alpha) is asserted nowhere; a run at zero roll rate would report the confidence of another flow state. The probe was killed only because the fake reads op_point.p.
- **Evidence:** assert boundary.numeric_runs == 3  # two for the start of the roll rate, one recording pass  -- the operating point of the third run is not inspected.
- **Verified:** CONFIRMED_BY_READING (READING). The recording run is built with `p=p_body, r=r_body` (opti.py:1107-1108); the test ends with `assert boundary.numeric_runs == 3  # two for the start of the roll rate, one recording pass` and never looks at that operating point. test_the_worker_rotates_about_the_stability_axis checks p and r of the symbolic point only (`first = next(op for op in boundary.operating_points if isinstance(op["alpha"], Variable))`). The fake reads `op_point.p`, so dropping the keywords crashes, but p=0.0, r=0.0 would pass.
- **Verifier's note:** Same fake (Boundary) and file as P6a-F05.
- **Test to write:** Fast: in that test take the last recorded operating point with a float alpha and assert alpha == 4.0, velocity == 10.0, p == 2.0 * cos(4 deg) = 1.995128, r == 2.0 * sin(4 deg) = 0.139513 (rel 1e-9).

## P6a-F16 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_solvers_flap_devices.py` · no test exists
- **Production:** `aero_kernel/solvers/asb_airplane.py:108`
- **Gap:** A flap deflection beyond its stop must be applied as given (stops are never read); no conversion test has a flap with positive_deflection_deg below its deflection_deg, so a clamp added in the conversion would pass this package.
- **Evidence:** def flap(role: str = "flap", root: float | None = 0.8, tip: float | None = 0.8, **extra: Any)  -- no stop is ever given.
- **Verified:** CONFIRMED_BY_READING (READING). test_solvers_flap_devices.py builds every flap without a stop (`def flap(role: str = "flap", root: float | None = 0.8, tip: float | None = 0.8, **extra: Any)`), and the one conversion fixture with stops stays inside them (test_solvers_asb_airplane.py: `"positive_deflection_deg": 25.0` with `"deflection_deg": 12.0`). grep finds no read of positive_deflection_deg / negative_deflection_deg in aero_kernel/solvers/. The rule itself is pinned one layer above only: test_devices.py `configured = with_flaps_at(model, 55.0)  # beyond the stop of 30 deg: applied exactly`.
- **Verifier's note:** Keep: 'deflections are parameters, stops are never read' is a maintainer decision, and a clamp in the conversion would change every flapped value the caller gets without a warning (ADR 0020). One test of three lines.
- **Test to write:** Fast, test_solvers_flap_devices.py: geometry(flap(deflection_deg=40.0, positive_deflection_deg=25.0, negative_deflection_deg=10.0)); airfoils(converted(model))[2] == ('deflected', 'naca2412', 40.0, 0.8) and flap_segments(model)[0].deflection_deg == 40.0.

## P6a-F17 · low · weak_assertion · do together with P6a-F04

- **Test file:** `aero_kernel/tests/test_solvers_opti.py` · existing test `test_a_regime_warning_names_the_wing_that_is_out_of_band` (line 193)
- **Production:** `aero_kernel/solvers/opti.py:2076`
- **Gap:** The assert on the bubble-sensitive warnings is sliced by the length of the actual list, so it passes for zero, one or two such warnings.
- **Evidence:** assert [w.detail["wing"] for w in sensitive] == ["Main", "Tail"][: len(sensitive)]
- **Verified:** CONFIRMED_BY_READING (READING). `assert [w.detail["wing"] for w in sensitive] == ["Main", "Tail"][: len(sensitive)]` passes for an empty list, for ['Main'] and for ['Main', 'Tail'] (not for ['Tail'] alone). On the unmutated copy the warnings of that call are exactly [('reynolds_outside_band', 'Tail')].
- **Verifier's note:** Same file as P6a-F04 (test_solvers_opti.py).
- **Test to write:** State the expectation: at 8 m/s the stand-in MAC of Main (chords 0.2 / 0.1 m, 0.1556 m) gives Re 8.5e4 (no warning) and the tail is outside the band, so assert sensitive == [] and [w.code for w in stall.warnings] == ['reynolds_outside_band'] (plus the tail's device warning if a device is added).

## P6a-F18 · low · weak_assertion · do together with P6a-F05

- **Test file:** `aero_kernel/tests/test_solvers_opti_roll.py` · existing test `test_the_start_value_of_alpha_carries_the_weight_on_the_rising_branch` (line 388)
- **Production:** `aero_kernel/solvers/opti.py:1155`
- **Gap:** The hand value of the start alpha is accepted within a whole sweep step (0.25 deg) although the interpolation on the linear stub is exact: an error of about 10 % in the needed C_L (reference area, density) stays inside the tolerance.
- **Evidence:** assert math.isclose(alpha_init, expected, abs_tol=0.25)
- **Verified:** CONFIRMED_BY_READING (READING). `assert math.isclose(alpha_init, expected, abs_tol=0.25)`. On the unmutated copy alpha_init = -11.85495626822157 and the test's expected = -11.854956268221574: the stub is exact to 4e-15, so the tolerance of a whole sweep step is not needed.
- **Verifier's note:** Same file as P6a-F05; a one-token change.
- **Test to write:** Same test with abs_tol=1e-9: expected = 15.75 - (1.19 - 0.15 * 9.81 / (0.5 * 1.225 * 100 * 0.28)) / 0.04 = -11.8547 deg.

## Not part of this package's work

| Finding | State | Reason |
|---|---|---|
| P6a-F11 | refuted | The cited test is a pass-through check (`assert (airplane.s_ref, airplane.b_ref, airplane.c_ref) == (properties.s_ref, properties.b_ref, properties.c_mac)`), but the gap does not exist: aero_kernel/te |
| P6a-F12 | dropped | Drop: a device station at exactly Re 3e4 is a measure-zero case without consequence for flyability; the same comparison is already pinned for the surface. It costs four lines if someone edits the file anyway. |
| P6a-F19 | dropped | Drop: no value, error or warning is at stake; the aero tier runs sequentially, where a 2 s margin on a 3 s build has held. Revisit only if the test is seen to flake. |
| P6a-F20 | dropped | Drop: the closed form in the test is independent of AeroSandbox and the atmosphere is compared against it at 5e-4; literals would add a third copy of the same numbers. |
