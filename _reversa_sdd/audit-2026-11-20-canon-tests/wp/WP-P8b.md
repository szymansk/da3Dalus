# WP-P8b — App layer: error envelope and input checks through the endpoint

Self-contained brief for one implementer subagent. Base commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

Every finding below was checked by an independent verifier on 2026-11-21 (`../rework/`). The line **Verified** says how. Where **Correction** appears, it overrides the text under **Test to write**.

- **Production code under test:** app/services/canon_service.py, app/api/…/canon
- **Requirement sources:** ADR 0019, ADR 0020
- **Test files you may change:** `app/tests/test_canon_aeroplane_input.py`, `app/tests/test_canon_endpoint.py`, `app/tests/test_canon_service.py`, `app/tests/test_canon_stall_speed_integration.py`
- **Findings to work on:** 6 (1 high, 1 medium, 4 low)

## P8-F09 · high · over_mocked

- **Test file:** `app/tests/test_canon_endpoint.py` · existing test `test_a_quantity_is_computed` (line 304)
- **Production:** `app/services/canon_service.py:262`
- **Gap:** Every fast endpoint and service test replaces the whole kernel, so the kernel's own input validation and per-quantity errors never pass through the endpoint outside the aero tier: Q8 (mass <= 0 -> invalid_input with input_path) and an unknown quantity are unpinned at the API. Invalid input also has two shapes (422 envelope with details.input_errors as dicts for a parse failure, 200 with body.input_errors as KernelError for inadmissible values) and no test states the split.
- **Evidence:** monkeypatch.setattr(canon_service, "KERNEL", Facade())   # use_kernel(); stub_kernel returns one OK quantity for any input
- **Verified:** CONFIRMED (NEW_MUTATION). Baseline 108 passed; mutated 108 passed. The app layer silently dropping a non-positive caller value hides the kernel's Q8 error from the API: real kernel through POST /canon/compute (fresh, no solver) with values {'aircraft-mass': -1.0} answers today 200 with input_errors[0] = {code 'non_positive_value', category 'invalid_input', input_path 'values.aircraft-mass'} and quantities []; under the mutation input_errors == [] and the fleet mass is used. Every fast test that reaches the kernel replaces it (`monkeypatch.setattr(canon_service, "KERNEL", Facade())`, `monkeypatch.setattr(canon_service, "compute", stub_kernel)`); the only caller value in a fast test is positive (`values={"aircraft-mass": 0.7}`).
- **Verifier's note:** Severity raised from medium by the common rule. The mutation is an app-layer regression (undeclared fallback, ADR 0020); the kernel's own validation is covered by kernel tests and is not what is unpinned. The service-level pass-through of input_errors is pinned with a stub (test_input_errors_of_the_kernel_are_passed_through); the JSON shape at the endpoint is not. The aero endpoint tests send no inadmissible value.
- **Acceptance mutation:** `git apply rework/patches/WP-P8b/P8-F09.patch` (from the audit folder; app/services/canon_service.py:194  `return aircraft_input(member, request.values)` -> `return aircraft_input(member, {k: v for k, v in request.values.items() if v > 0})`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast tier, test_canon_endpoint.py with the real kernel and 'fresh': true (validation and graph resolution run before any solver; checked: compute(aircraft_input(BRYAN, {'aircraft-mass': -1.0}), ...) returns input_errors [('non_positive_value', invalid_input, 'values.aircraft-mass')] and no quantities): (1) POST fleet bryan, values {'aircraft-mass': -1.0}, quantities ['wing-loading'] -> 200, quantities == [], input_errors[0] has code 'non_positive_value', category 'invalid_input', input_path 'values.aircraft-mass', message and hint non-empty; (2) quantities ['no-such-quantity'] -> 200, status 'error', error.code 'unknown_quantity', unit null, value null.

## P8-F07 · medium · missing_edge_case

- **Test file:** `app/tests/test_canon_service.py` · existing test `test_a_skipped_long_run_asks_for_confirmation` (line 239)
- **Production:** `app/services/canon_service.py:228`
- **Gap:** needs_confirmation is documented as the quantities skipped because they take minutes; the reason-code filter can be removed and every skipped quantity (e.g. depends_on_skipped) is listed, with no test failing.
- **Evidence:** use_kernel(monkeypatch, StubKernel(skipped_long_run("neutral-point"), ok("a", 1.0)))
    ...
    assert response.needs_confirmation == ["neutral-point"]
- **Verified:** CONFIRMED (MUTATION_RERUN). Baseline 108 passed; mutated 108 passed. Direct call of compute_canon with a stub returning neutral-point (long_run_not_included) and static-margin-measured (depends_on_skipped): original needs_confirmation == ['neutral-point'], mutated ['neutral-point', 'static-margin-measured']. The only assertion on a non-empty list is `assert response.needs_confirmation == ["neutral-point"]` with a stub that holds no other skipped quantity. The kernel does produce the other reason (aero_kernel/graph.py:349 `code = ReasonCode.DEPENDS_ON_SKIPPED`).
- **Verifier's note:** No aero test reaches a skipped quantity through the endpoint (app/tests/test_canon_endpoint_aero.py asserts no needs_confirmation).
- **Acceptance mutation:** `git apply rework/patches/WP-P8b/P8-F07.patch` (from the audit folder; app/services/canon_service.py:231-233  `if q.status is QuantityStatus.SKIPPED and q.reason is not None and q.reason.code is ReasonCode.LONG_RUN_NOT_INCLUDED` -> `if q.status is QuantityStatus.SKIPPED`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast tier, test_canon_service.py: stub returns skipped_long_run('neutral-point'), a QuantityResult(slug='static-margin-measured', status=SKIPPED, reason=Reason(code=ReasonCode.DEPENDS_ON_SKIPPED, message='m')) and a NOT_APPLICABLE one; assert needs_confirmation == ['neutral-point']. If the maintainer wants dependents listed too, the test states that instead; today either behaviour passes.

## P8-F10 · low · weak_assertion · do together with P8-F09

- **Test file:** `app/tests/test_canon_endpoint.py` · existing test `test_an_aircraft_reference_that_is_not_one_of_the_two_is_rejected` (line 296)
- **Production:** `app/schemas/canon.py:66`
- **Gap:** The three malformed aircraft references assert the status code only; a response outside the error envelope would pass.
- **Evidence:** assert response.status_code == 422
- **Verified:** CONFIRMED_BY_READING (READING). app/tests/test_canon_endpoint.py:296-300: the only assertion of the three parametrised cases is `assert response.status_code == 422`. Measured today: all three answer error.code 'validation_error' with details[0].loc ['body','aircraft',...], so the envelope is in place and only unasserted here.
- **Test to write:** Same test: add assert response.json()['error']['code'] == 'validation_error' and that error['details'] names the 'aircraft' location.

## P8-F11 · low · weak_assertion

- **Test file:** `app/tests/test_canon_aeroplane_input.py` · existing test `test_spars_are_given_in_metres` (line 138)
- **Production:** `app/services/wing_service.py:64`
- **Gap:** The seam's own unit test pins width, height and start. Leaving spare_length or spare_origin in millimetres is noticed only by a wing-endpoint test of the shared helper; if the seam stopped using that helper for those fields, nothing in the canon tests would fail.
- **Evidence:** assert spar.spare_support_dimension_width == pytest.approx(0.004)
        assert spar.spare_support_dimension_height == pytest.approx(0.006)
        assert spar.spare_start == pytest.approx(0.010)
        assert spar.spare_vector == (0.0, 1.0, 0.0)
- **Verified:** CONFIRMED_BY_READING (READING). test_spars_are_given_in_metres stores no spare_length and no spare_origin and asserts only `spar.spare_support_dimension_width`, `..._height`, `spar.spare_start` and `spar.spare_vector`. No canon or spar-section test carries a non-zero spare_origin or any spare_length (grep: only `"spare_origin": [0, 0, 0]`). Additionally re-ran P8-M10: the five canon/spar files stay green (108 passed) with spare_length left in mm.
- **Verifier's note:** keep: spare_length and spare_origin reach the kernel's spar capacity (aero_kernel/spar_capacity.py:239-247), where a millimetre value read as metres changes the spar extent. The mutation was run although severity is low, because it was cheap; the verdict rests on reading.
- **Acceptance mutation:** `git apply rework/patches/WP-P8b/P8-F11.patch` (from the audit folder; app/services/wing_service.py:64-66  `"spare_length": spare.spare_length * _MM_TO_M if spare.spare_length is not None else None` -> `"spare_length": spare.spare_length`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Same test: store spare_length=250.0 and spare_origin=[30.0, 10.0, 2.0] (mm) on the row and assert spar.spare_length == approx(0.250) and spar.spare_origin == approx((0.030, 0.010, 0.002)).

## P8-F12 · low · weak_assertion · do together with P8-F07

- **Test file:** `app/tests/test_canon_service.py` · existing test `test_a_caller_that_leaves_does_not_break_the_kernel_loop` (line 378)
- **Production:** `app/services/canon_service.py:129`
- **Gap:** The guard that skips settling a cancelled caller's future can be removed; the test still passes because it only checks that a later compute works.
- **Evidence:** assert (await canon_service._KERNEL_LOOP.run(slow())).quantities == ()
- **Verified:** CONFIRMED_BY_READING (READING). The test's only assertion is `assert (await canon_service._KERNEL_LOOP.run(slow())).quantities == ()`. Re-ran P8-M15: 41 passed. Observable difference: with the guard removed the 'asyncio' logger gets one record 'Exception in callback _KernelLoop.run.<locals>.start.<locals>...' with InvalidStateError; original: no record. The later compute works in both.
- **Verifier's note:** Not an equivalent mutant (log record differs). Mutation run although severity is low; verdict rests on reading plus this run.
- **Acceptance mutation:** `git apply rework/patches/WP-P8b/P8-F12.patch` (from the audit folder; app/services/canon_service.py:129-130  `if done.cancelled(): return` -> (removed)). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Same test: install loop.set_exception_handler on the kernel loop (or use caplog on the 'asyncio' logger) and assert no 'Exception in callback' / InvalidStateError record was emitted after the cancelled caller's kernel task finished.

## P8-F13 · low · misleading_name

- **Test file:** `app/tests/test_canon_stall_speed_integration.py` · existing test `test_stall_speed_closes_in_reynolds_number` (line 108)
- **Production:** `app/services/assumption_compute_service.py`
- **Gap:** The docstring declares the test 'expected to fail' as the measurement for gh-1142, yet it has no xfail and is slow + requires_aerosandbox, so it runs only nightly. Either the nightly run is permanently red or the docstring is wrong; it tests the legacy app computation, not the canon kernel its file name suggests, and labels G = 9.81 as the canon's gravity (canon default 9.80665).
- **Evidence:** "This test is therefore expected to fail, and **its failure message is the measurement gh-1142 asks for**" ... assert spread <= TOLERANCE
- **Verified:** CONFIRMED_BY_READING (READING). Each stated fact holds: docstring `This test is therefore expected to fail, and **its failure message is the measurement gh-1142 asks for**`; decorators are only `@pytest.mark.slow` and `@pytest.mark.requires_aerosandbox`, no xfail anywhere in the file; it imports `from app.services.assumption_compute_service import _coarse_alpha_sweep, _fine_sweep_cl_max` and nothing from aero_kernel; `#: Approved canon quantity ``gravity`` (m/s^2).` / `G = 9.81` while aero_kernel/canon/canon_model.json namespaces.calc.defaults.gravity.value is 9.80665. Only the nightly tier runs it (.github/workflows/test.yml: fast and full exclude `slow`).
- **Verifier's note:** The open half of the finding (does the test fail or pass when run) is NOT settled. Obstacle: it is a slow + requires_aerosandbox test, which this verification must not run, and CI gives no answer: the scheduled nightly run on exactly 72c4b5c6 (run 44721669112, 2026-11-20) ends in both Python jobs with `Process completed with exit code 124` (the 3000 s timeout) at about 22 % inside aero_kernel/tests, and its log contains no app/tests line at all; the five nightly runs before it also failed. So the nightly is red for another reason and this test is currently never executed anywhere, which means the gh-1142 measurement its docstring promises is not being produced. Severity lowered from medium by the common rule. keep: the hygiene part is cosmetic, but the recommended kernel-side fixed-point check would protect stall-speed, a value the caller sees; what happens to the existing test stays the maintainer's decision (blocked_by_decision).
- **Test to write:** Do not remove or weaken it. Run it once through the lock and record the outcome in gh-1142. Add the kernel-side counterpart in the aero tier: for BRYAN, take stall-speed and max-lift-coefficient from compute(), re-run sweep_lift at exactly that speed and assert max C_L of the first peak equals max-lift-coefficient within 1e-3 (the kernel's stall solve is the fixed point the canon precondition demands).
- **Correction:** (unclear) The kernel-side counterpart needs the aero tier and could not be tried here; sweep_lift exists (aero_kernel/solvers/aerobuildup.py:97), but whether 'max C_L of the first peak' agrees with max-lift-coefficient within 1e-3 is unverified. 'Record the outcome in gh-1142' is not a test.

## Not part of this package's work

| Finding | State | Reason |
|---|---|---|
| P8-F08 | production_defect | #1434 |
