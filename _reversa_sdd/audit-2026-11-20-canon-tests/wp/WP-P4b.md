# WP-P4b — Test-Isolation und zeitabhängige Tests

Self-contained brief for one implementer subagent. Frozen review state: commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

- **Production code under test:** aero_kernel/tests/test_engine.py, test_runtime*.py, test_engine_timing.py
- **Requirement sources:** ARCHITECTURE §8.10, §8.14
- **Test files you may change:** `aero_kernel/tests/test_engine.py`, `aero_kernel/tests/test_engine_timing.py`, `aero_kernel/tests/test_runtime.py`, `aero_kernel/tests/test_runtime_routing.py`
- **Findings:** 5 (0 high, 3 medium, 2 low)

A finding marked **DECISION** needs the maintainer's answer first: do not write its test, list it in your report as open.

## P4-F09 · medium · brittle

- **Test file:** `aero_kernel/tests/test_engine.py` · existing test `test_every_debug_line_of_a_node_carries_formula_and_application` (line 949)
- **Production:** `aero_kernel/engine.py:390`
- **Gap:** The test fails whenever the root logger is at DEBUG. It depends on global state, not on test order: app/main.py calls setup_logging() at import (logging.basicConfig(level=DEBUG)), and app/tests/conftest.py imports app.main during collection, so any session that also collects app/tests fails it. It filters caplog.records by level only, so DEBUG records of other aero_kernel loggers (registry 'registered formula ...', validate, graph) are counted as node lines. Reproduction: `poetry run pytest aero_kernel/tests/test_engine.py -k 'test_every_debug_line_of_a_node_carries_formula_and_application or test_one_info_line_per_call_and_debug_per_node_all_with_the_same_call_id' --log-level=DEBUG -p no:cacheprovider` (2 failed), or the same -k with `app/tests/conftest.py aero_kernel/tests/test_engine.py` as targets; alone: 2 passed. All other 755 fast tests of this package pass with --log-level=DEBUG.
- **Evidence:** `with caplog.at_level(logging.DEBUG, logger="aero_kernel.engine"):` ... `node_lines = [r for r in caplog.records if r.levelno == logging.DEBUG]` / `assert [r.getMessage().split(":")[0] for r in node_lines] == ["node started", "node finished"]`. Failure seen: `At index 0 diff: 'registered formula calc' != 'node started'`, 69 extra items.
- **Status:** READ_ONLY
- **Test to write:** Keep the assertion, make the selection explicit: filter `r.name == 'aero_kernel.engine'` and the two node messages (r.getMessage().startswith(('node started', 'node finished'))) before comparing; then the test states its requirement independently of the root level. Verify with both commands above.

## P4-F10 · medium · brittle

- **Test file:** `aero_kernel/tests/test_engine.py` · existing test `test_one_info_line_per_call_and_debug_per_node_all_with_the_same_call_id` (line 1078)
- **Production:** `aero_kernel/engine.py:1502`
- **Gap:** Same cause as P4-F09: with the root logger at DEBUG, records of aero_kernel.validate / registry / graph (which carry no call_id) enter caplog.records and the set of call ids has two members. Reproduction command in P4-F09.
- **Evidence:** `ids = {getattr(r, "call_id", None) for r in caplog.records}` / `assert len(ids) == 1`. Failure seen: `assert 2 == 1  +  where 2 = len({'8483fa68', None})`.
- **Status:** READ_ONLY
- **Test to write:** Restrict the records to `r.name == 'aero_kernel.engine'` before building the set of call ids (the requirement of ch. 8.14 is about the lines of one call of the engine); keep `len(ids) == 1` and the INFO-line assertion.

## P4-F17 · medium · brittle

- **Test file:** `aero_kernel/tests/test_runtime.py` · existing test `test_the_loop_stays_responsive_during_pool_work` (line 295)
- **Production:** `aero_kernel/runtime.py:441-508`
- **Gap:** The concurrency tests build their interleavings with fixed sleeps and some assert wall-clock bounds, so they can fail on a loaded machine (coverage, parallel suites) without a defect. Hard wall-clock asserts: test_runtime.py::TestRunCpu::test_the_loop_stays_responsive_during_pool_work, ::TestPoolLifetime::test_the_loop_stays_free_while_aclose_waits_for_a_worker, ::TestPoolLifetime::test_aclose_of_an_idle_owned_pool_keeps_the_loop_free (all `worst_delay < 0.05`); ::TestCancellationAndBudget::test_cancel_propagates_and_frees_the_slot (`asyncio.timeout(1.0)` around a job that needs a second worker to be spawned; the architecture puts a spawn at about a second); ::TestConcurrencyLimit::test_a_subprocess_takes_no_worker_gate_slot (overlap `> 0.15`). Sleep-positioned interleavings: ::TestConcurrencyLimit::test_at_most_max_concurrency_calls_run_at_once, ::test_subprocesses_share_the_limit, ::test_pool_work_and_subprocesses_count_together, ::TestRunCpu::test_a_worker_raising_formula_error_neither_breaks_the_pool_nor_its_siblings, ::TestPoolLifetime::test_close_refuses_a_call_waiting_for_a_slot_and_creates_no_pool, ::test_close_turns_queued_pool_calls_into_closed_errors_not_cancellation, ::test_a_real_cancellation_of_a_queued_call_still_raises_cancelled_error, ::test_close_refuses_a_process_call_waiting_for_a_slot, ::test_the_worker_gate_is_released_on_every_path, ::test_a_caller_cancelling_a_queued_call_while_close_runs_still_sees_cancellation, ::test_aclose_waits_for_running_calls_and_their_callers_get_results, ::test_aclose_also_waits_for_a_worker_whose_caller_was_cancelled, ::test_aclose_waits_for_a_running_subprocess_call, ::test_a_call_after_close_began_does_not_wait_for_a_slot, ::test_the_gate_follows_the_given_worker_count_not_the_concurrency_limit; test_runtime_routing.py::test_a_job_without_a_key_takes_any_idle_worker, ::test_a_key_whose_worker_is_busy_is_built_again_elsewhere_not_waited_for, ::test_the_worker_is_reused_after_a_cancelled_call, ::test_a_cancelled_call_keeps_its_worker_from_new_jobs_until_it_ends, ::test_a_worker_that_dies_after_its_caller_left_is_logged_once. All passed in this review (one plain full run of the package: 757 passed).
- **Evidence:** `await shared_runtime.run_cpu(workers.nap, 0.6)` ... `assert worst_delay < 0.05`; `await asyncio.sleep(0.3)` / `running.cancel()` / `async with asyncio.timeout(1.0): assert await runtime.run_cpu(workers.square, 3) == 9`.
- **Status:** READ_ONLY
- **Test to write:** No new requirement; replace positions in time by events where the test owns both sides: a worker function that signals 'started' through a multiprocessing Event or a file (as RENDEZVOUS_SCRIPT already does for subprocesses) instead of `await asyncio.sleep(0.2)` before cancel/close; warm the second worker before test_cancel_propagates_and_frees_the_slot measures 1 s. Keep the 50 ms bound of Q16 (it is the requirement) but take the median of several ticks or run the probe once with a warmed pool and a retry-free generous CI margin decided by the maintainer.

## P4-F18 · low · brittle

- **Test file:** `aero_kernel/tests/test_engine_timing.py` · existing test `test_a_quantity_open_when_the_budget_expired_has_no_timing` (line 104)
- **Production:** `aero_kernel/engine.py:1557-1564`
- **Gap:** The budget leaves the first node 5 ms of slack: the stub sleeps 0.03 s and the budget is 0.035 s, in which validation, graph and the first node must finish; on a slow run `weight` is still open and the assertion on its timing fails. test_engine_cache.py::test_a_node_open_when_the_budget_expired_is_not_stored (sleep 0.2 s against a budget of 0.05 s, asserting that weight finished in time) has the same shape with a wider margin.
- **Evidence:** `quantities = await run("weight", "double-weight", budget=WEIGHT_S + DOUBLE_S / 4)` with WEIGHT_S = 0.03, DOUBLE_S = 0.02, then `assert quantities["weight"].timing is not None`.
- **Status:** READ_ONLY
- **Test to write:** Same assertions with an event instead of a margin: let the `double` stub wait on an asyncio.Event that is never set and give the request a budget of 0.5 s; `weight` returns at once, so the result does not depend on the machine.

## P4-F20 · low · brittle

- **Test file:** `aero_kernel/tests/test_runtime_routing.py` · existing test `test_a_job_without_a_key_takes_any_idle_worker` (line 53)
- **Production:** `aero_kernel/runtime.py:287`
- **Gap:** Two routing tests rely on the default max_concurrency (os.cpu_count()) being at least 2: with one CPU the second job waits for the busy holder and the assertion fails. Shown by probe P4-M06 (default concurrency 1), which failed exactly this test. Also affected: test_a_key_whose_worker_is_busy_is_built_again_elsewhere_not_waited_for (line 62).
- **Evidence:** `async with SolverRuntime(max_workers=2, max_models_per_worker=1) as runtime:` (no max_concurrency) ... `assert await pid(runtime, None) != holder`.
- **Status:** READ_ONLY
- **Acceptance mutation P4-M06:** in `aero_kernel/runtime.py` line 287: `self.max_concurrency = max_concurrency or os.cpu_count() or 1` -> `max_concurrency or 1`. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Pass max_concurrency=2 explicitly in both tests; the default itself is then pinned by the test recommended in P4-F15.
