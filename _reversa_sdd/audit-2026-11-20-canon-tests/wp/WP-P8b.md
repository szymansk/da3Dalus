# WP-P8b — App-Anbindung: Fehlerhülle und Eingabeprüfung über den Endpunkt

Self-contained brief for one implementer subagent. Frozen review state: commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

- **Production code under test:** app/services/canon_service.py, app/api/…/canon
- **Requirement sources:** ADR 0019, ADR 0020
- **Test files you may change:** `app/tests/test_canon_aeroplane_input.py`, `app/tests/test_canon_endpoint.py`, `app/tests/test_canon_service.py`, `app/tests/test_canon_stall_speed_integration.py`
- **Findings:** 7 (0 high, 4 medium, 3 low)

A finding marked **DECISION** needs the maintainer's answer first: do not write its test, list it in your report as open.

## P8-F07 · medium · missing_edge_case

- **Test file:** `app/tests/test_canon_service.py` · existing test `test_a_skipped_long_run_asks_for_confirmation` (line 239)
- **Production:** `app/services/canon_service.py:228`
- **Gap:** needs_confirmation is documented as the quantities skipped because they take minutes; the reason-code filter can be removed and every skipped quantity (e.g. depends_on_skipped) is listed, with no test failing.
- **Evidence:** use_kernel(monkeypatch, StubKernel(skipped_long_run("neutral-point"), ok("a", 1.0)))
    ...
    assert response.needs_confirmation == ["neutral-point"]
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P8-M04:** in `app/services/canon_service.py` line 232: _needs_confirmation: dropped 'q.reason is not None and q.reason.code is ReasonCode.LONG_RUN_NOT_INCLUDED' (any skipped quantity is listed). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast tier, test_canon_service.py: stub returns skipped_long_run('neutral-point'), a QuantityResult(slug='static-margin-measured', status=SKIPPED, reason=Reason(code=ReasonCode.DEPENDS_ON_SKIPPED, message='m')) and a NOT_APPLICABLE one; assert needs_confirmation == ['neutral-point']. If the maintainer wants dependents listed too, the test states that instead; today either behaviour passes.

## P8-F08 · medium · untested_error_path

- **Test file:** `app/tests/test_canon_endpoint.py` · no test exists
- **Production:** `app/main.py:279`
- **Gap:** ADR 0019 requires one error envelope. An exception from the kernel that is not a ServiceException (the service test proves it propagates) leaves POST /canon/compute as Starlette's plain-text 500; no endpoint test covers the path, so neither the missing envelope nor a later leak of the exception text would be noticed.
- **Evidence:** Measured in the copy with KERNEL.compute raising LookupError and TestClient(raise_server_exceptions=False): '500 text/plain; charset=utf-8 Internal Server Error'. app/main.py registers handlers for ServiceException, IntegrityError and RequestValidationError only.
- **Status:** READ_ONLY
- **Test to write:** Fast tier, test_canon_endpoint.py with TestClient(application, raise_server_exceptions=False): monkeypatch canon_service.KERNEL to a facade whose compute raises RuntimeError('boom /private/var/x'); POST {'aircraft': {'fleet': 'bryan'}, 'quantities': ['stall-speed']}; assert status 500, response.json()['error']['code'] == 'internal_error', and '/private' not in response.text. The test fails today: it documents a production gap, to be fixed in production.

## P8-F09 · medium · over_mocked

- **Test file:** `app/tests/test_canon_endpoint.py` · existing test `test_a_quantity_is_computed` (line 304)
- **Production:** `app/services/canon_service.py:262`
- **Gap:** Every fast endpoint and service test replaces the whole kernel, so the kernel's own input validation and per-quantity errors never pass through the endpoint outside the aero tier: Q8 (mass <= 0 -> invalid_input with input_path) and an unknown quantity are unpinned at the API. Invalid input also has two shapes (422 envelope with details.input_errors as dicts for a parse failure, 200 with body.input_errors as KernelError for inadmissible values) and no test states the split.
- **Evidence:** monkeypatch.setattr(canon_service, "KERNEL", Facade())   # use_kernel(); stub_kernel returns one OK quantity for any input
- **Status:** READ_ONLY
- **Test to write:** Fast tier, test_canon_endpoint.py with the real kernel and 'fresh': true (validation and graph resolution run before any solver; checked: compute(aircraft_input(BRYAN, {'aircraft-mass': -1.0}), ...) returns input_errors [('non_positive_value', invalid_input, 'values.aircraft-mass')] and no quantities): (1) POST fleet bryan, values {'aircraft-mass': -1.0}, quantities ['wing-loading'] -> 200, quantities == [], input_errors[0] has code 'non_positive_value', category 'invalid_input', input_path 'values.aircraft-mass', message and hint non-empty; (2) quantities ['no-such-quantity'] -> 200, status 'error', error.code 'unknown_quantity', unit null, value null.

## P8-F13 · medium · misleading_name · DECISION

- **Test file:** `app/tests/test_canon_stall_speed_integration.py` · existing test `test_stall_speed_closes_in_reynolds_number` (line 108)
- **Production:** `app/services/assumption_compute_service.py`
- **Gap:** The docstring declares the test 'expected to fail' as the measurement for gh-1142, yet it has no xfail and is slow + requires_aerosandbox, so it runs only nightly. Either the nightly run is permanently red or the docstring is wrong; it tests the legacy app computation, not the canon kernel its file name suggests, and labels G = 9.81 as the canon's gravity (canon default 9.80665).
- **Evidence:** "This test is therefore expected to fail, and **its failure message is the measurement gh-1142 asks for**" ... assert spread <= TOLERANCE
- **Status:** UNKNOWN
- **Test to write:** Do not remove or weaken it. Run it once through the lock and record the outcome in gh-1142. Add the kernel-side counterpart in the aero tier: for BRYAN, take stall-speed and max-lift-coefficient from compute(), re-run sweep_lift at exactly that speed and assert max C_L of the first peak equals max-lift-coefficient within 1e-3 (the kernel's stall solve is the fixed point the canon precondition demands).

## P8-F10 · low · weak_assertion

- **Test file:** `app/tests/test_canon_endpoint.py` · existing test `test_an_aircraft_reference_that_is_not_one_of_the_two_is_rejected` (line 296)
- **Production:** `app/schemas/canon.py:66`
- **Gap:** The three malformed aircraft references assert the status code only; a response outside the error envelope would pass.
- **Evidence:** assert response.status_code == 422
- **Status:** READ_ONLY
- **Test to write:** Same test: add assert response.json()['error']['code'] == 'validation_error' and that error['details'] names the 'aircraft' location.

## P8-F11 · low · weak_assertion

- **Test file:** `app/tests/test_canon_aeroplane_input.py` · existing test `test_spars_are_given_in_metres` (line 138)
- **Production:** `app/services/wing_service.py:64`
- **Gap:** The seam's own unit test pins width, height and start. Leaving spare_length or spare_origin in millimetres is noticed only by a wing-endpoint test of the shared helper; if the seam stopped using that helper for those fields, nothing in the canon tests would fail.
- **Evidence:** assert spar.spare_support_dimension_width == pytest.approx(0.004)
        assert spar.spare_support_dimension_height == pytest.approx(0.006)
        assert spar.spare_start == pytest.approx(0.010)
        assert spar.spare_vector == (0.0, 1.0, 0.0)
- **Status:** READ_ONLY
- **Acceptance mutation P8-M10:** in `app/services/wing_service.py` line 64: _convert_spare_to_meters: spare_length left in mm. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Same test: store spare_length=250.0 and spare_origin=[30.0, 10.0, 2.0] (mm) on the row and assert spar.spare_length == approx(0.250) and spar.spare_origin == approx((0.030, 0.010, 0.002)).

## P8-F12 · low · weak_assertion

- **Test file:** `app/tests/test_canon_service.py` · existing test `test_a_caller_that_leaves_does_not_break_the_kernel_loop` (line 378)
- **Production:** `app/services/canon_service.py:129`
- **Gap:** The guard that skips settling a cancelled caller's future can be removed; the test still passes because it only checks that a later compute works.
- **Evidence:** assert (await canon_service._KERNEL_LOOP.run(slow())).quantities == ()
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P8-M15:** in `app/services/canon_service.py` line 129: _settle: removed 'if done.cancelled(): return'. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Same test: install loop.set_exception_handler on the kernel loop (or use caplog on the 'asyncio' logger) and assert no 'Exception in callback' / InvalidStateError record was emitted after the cancelled caller's kernel task finished.
