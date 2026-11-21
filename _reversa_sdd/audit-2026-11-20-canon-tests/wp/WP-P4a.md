# WP-P4a — Cache key, engine provenance, rule bounds

Self-contained brief for one implementer subagent. Base commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

Every finding below was checked by an independent verifier on 2026-11-21 (`../rework/`). The line **Verified** says how. Where **Correction** appears, it overrides the text under **Test to write**.

- **Production code under test:** aero_kernel/engine.py, cache.py, rules.py
- **Requirement sources:** ARCHITECTURE §8.4, §8.13, §10 (Q31)
- **Test files you may change:** `aero_kernel/tests/test_cache_dedup.py`, `aero_kernel/tests/test_cache_world_tools.py`, `aero_kernel/tests/test_engine_cache.py`, `aero_kernel/tests/test_engine_defaults.py`
- **Findings to work on:** 7 (3 high, 3 medium, 1 low)

## P4-F01 · high · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_engine_cache.py` · no test exists
- **Production:** `aero_kernel/engine.py:568`
- **Gap:** The engine can drop the world assignment from the node cache key without any test failing. With a cache, all worlds of a node whose worlds share a tool then share one entry: the interval collapses to the first world's value (observed under the mutation: {'unc=alpha': 10.0, 'unc=beta': 10.0, 'unc=gamma': 10.0} instead of 10/20/30) and is served as such on later calls.
- **Evidence:** engine.py:565-568 `node_key = cache_key(formula=node.id.formula, application=node.id.application, world=key, ...)`. The only tests of the world in the key call cache_key() themselves (test_cache_key.py `{"world": "neutral-point=avl"}`, test_engine_worlds.py::test_the_cache_key_is_per_assignment `cache_key(formula="calc:unc", ..., world=key, ...)`); test_engine_cache.py::test_a_new_tool_version_expires_only_the_world_of_that_tool uses worlds with different tools (ATM / AVL), whose keys differ by tool version anyway.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survives all 934 fast tests. Own reproduction on the test_engine_worlds fixture with one DedupedCache(MemoryCache(64)), quantities np-q and join-q: original gives np-q {'unc=alpha': 10.0, 'unc=beta': 20.0, 'unc=gamma': 30.0} and join-q 18/28/38 on both calls; mutated gives np-q {'unc=alpha': 10.0, 'unc=beta': 10.0, 'unc=gamma': 10.0} and join-q 18/18/18, on the first call already and from_cache True on the second. The only world-in-key test builds the key itself: test_engine_worlds.py `cache_key(formula="calc:unc", ..., world=key, ...)`.
- **Verifier's note:** Reaches the shipped canon: neutral-point has worlds textbook and pappas, both tool APP, so through the app's CachedKernel they would share one entry. No aero test computes neutral-point through a cache (test_cached_kernel_fleet.py and test_aero_model_real.py request stall-speed only), hence no aero candidate.
- **Acceptance mutation:** `git apply rework/patches/WP-P4a/P4-F01.patch` (from the audit folder; aero_kernel/engine.py:568  `world=key,` -> `world=None,`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast tier, aero_kernel/tests/test_engine_cache.py (or test_engine_worlds.py). Build the fixture of test_engine_worlds.py (formula `unc`, tool APP, worlds alpha/beta/gamma returning 10.0/20.0/30.0, `down` adding 1.0, `side` 7.0, `join` a+b) and call evaluate() twice with ONE DedupedCache(MemoryCache(max_entries=64)) for quantities ('np-q', 'join-q'). Expect on both calls np-q interval.worlds == {'unc=alpha': 10.0, 'unc=beta': 20.0, 'unc=gamma': 30.0} and join-q == {'unc=alpha': 18.0, 'unc=beta': 28.0, 'unc=gamma': 38.0} (10+1+7 etc.), exact equality; first call from_cache False, second True; `unc` called exactly 3 times in total.

## P4-F02 · high · untested_error_path

- **Test file:** `aero_kernel/tests/test_engine_cache.py` · existing test `test_a_node_open_when_the_budget_expired_is_not_stored` (line 252)
- **Production:** `aero_kernel/engine.py:588-595`
- **Gap:** If the engine stops releasing a cache claim when a node run is cancelled or the time budget expires, every later call on the same CachedKernel that needs that key waits forever (observed under the mutation: the second call still hangs after 3 s, after a timed-out call and after a cancelled one). No test notices.
- **Evidence:** engine.py:594-595 `finally:\n    lease.release(stored)`. The test helper builds a new deduplicating cache per call: test_engine_cache.py:137 `cache=None if store is None else DedupedCache(store),` so `again = by_slug(await run(build, store, "double-weight"))["double-weight"]` never meets the leaked in-flight future. test_cached_kernel.py has no cancelled or timed-out call.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survives all 934 fast tests. Own reproduction with ONE DedupedCache on the test_engine_cache fixture (slow `double`, 0.2 s): after a call with time_budget_s=0.05 (error code timeout) the next identical call hangs beyond 3 s under the mutation and returns ok 39.24 on the original; the same after a cancelled task. The existing test never meets the leaked claim because its helper builds a new dedup layer per call: test_engine_cache.py:137 `cache=None if store is None else DedupedCache(store),`.
- **Verifier's note:** No aero test cancels or times out a call on a shared cache.
- **Acceptance mutation:** `git apply rework/patches/WP-P4a/P4-F02.patch` (from the audit folder; aero_kernel/engine.py:588-595  `try: ... finally: lease.release(stored)` -> release on the two normal returns and in `except Exception:` only). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast tier, aero_kernel/tests/test_cached_kernel.py. (a) One CachedKernel(max_entries=16); stub `weight` awaits an asyncio.Event; first call with ComputeRequest(quantities=('weight',), time_budget_s=0.05) -> error.code == 'timeout'; set the event; second call without budget inside asyncio.timeout(5) -> status ok, value == 2.0 * 9.81, from_cache False, stub called twice. (b) Same kernel type: start kernel.compute as a task, wait until the stub has started (an Event set by the stub), task.cancel(); `with pytest.raises(asyncio.CancelledError): await task`; then a second call inside asyncio.timeout(5) -> ok. Use events, not sleeps.

## P4-F03 · high · missing_edge_case

- **Test file:** `aero_kernel/tests/test_engine_cache.py` · existing test `test_a_polar_output_comes_back_as_an_equal_fresh_polar` (line 303)
- **Production:** `aero_kernel/engine.py:193-197`
- **Gap:** A polar that a node reads can be left out of that node's cache key (replaced by a constant) without any test failing: a reader of a changed polar would then be served the value computed from the old polar.
- **Evidence:** engine.py:195-196 `if isinstance(value, AirplaneGeometry | Polar | Components):\n    return spell_non_finite(value.model_dump(mode="json"))`. The only cached test with a polar reader never changes the polar: `assert polar == A_POLAR` / `assert polar is not A_POLAR`. The same mutation for Components is killed by test_airplane_components.py::test_a_changed_component_changes_the_cached_value (P4-M08); a changed geometry by test_a_non_finite_number_in_an_unread_geometry_field_does_not_break_the_key.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survives all 934 fast tests. Own reproduction on the engine_builders canon (polar-twin returns A_POLAR at mass 2.0 and a polar with cl + 0.1 at mass 3.0, polar-reader returns polar.cl[0]) with one MemoryCache: original second call gives polar-read-q 0.2, from_cache False, reader called twice; mutated gives 0.1, from_cache True, reader called once. The only cached polar-reader test never changes the polar: `assert polar == A_POLAR`.
- **Verifier's note:** In the shipped canon the only polar is polar-stall (produced by stall-speed, read by stall-break). No aero test requests a stall-break quantity twice through a cache with a changed polar, hence no aero candidate.
- **Acceptance mutation:** `git apply rework/patches/WP-P4a/P4-F03.patch` (from the audit folder; aero_kernel/engine.py:195  `isinstance(value, AirplaneGeometry | Polar | Components)` -> a Polar returns the constant "polar"; geometry and components unchanged). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast tier, aero_kernel/tests/test_engine_cache.py, fixture canon of engine_builders (polar-twin -> polar-q, polar-reader -> polar-read-q). Stub polar-twin returns A_POLAR when aircraft-mass == 2.0 and a second polar with one changed lift coefficient (e.g. cl + 0.1 at one alpha) when aircraft-mass == 3.0; stub polar-reader returns {'r': polar.cl[0]} (or any number read from the polar). One RecordingCache; call 1 with mass 2.0, call 2 with mass 3.0, request 'polar-read-q'. Expect call 2: from_cache False, reader called twice, value equals the number read from the second polar exactly.

## P4-F04 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_engine_cache.py` · existing test `test_a_hit_declares_the_thresholds_its_node_read` (line 292)
- **Production:** `aero_kernel/engine.py:617-620`
- **Gap:** A cache hit may stop recording the tool versions and solver settings in the provenance: a fully cached call then reports tool_versions == {} although its values were computed with AVL / AeroSandbox. Cached and uncached provenance differ and no test fails.
- **Evidence:** The only miss-versus-hit comparison of the provenance is `assert second.provenance.rules_used == first.provenance.rules_used`. test_engine_world_tools.py asserts `provenance.tool_versions == {"avl-binary": "9.9"}` on uncached calls only.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survives all 934 fast tests. Own reproduction with two_tool_build(), StubAtmosphere({}, {'aerosandbox': '1.2.3'}) and VersionedAvl('1.0') on one RecordingCache: the cached second call reports tool_versions {} and solver_settings {} under the mutation, and {'aerosandbox': '1.2.3', 'avl-binary': '1.0'} / {'avl_nspan': 7} on the original. The only fast miss-versus-hit comparison of the provenance is `assert second.provenance.rules_used == first.provenance.rules_used`.
- **Verifier's note:** The aero tier already has the assert the fast tier lacks: test_cached_kernel_fleet.py `assert second.provenance == first.provenance` (real AeroSandbox version on the first call).
- **Acceptance mutation:** `git apply rework/patches/WP-P4a/P4-F04.patch` (from the audit folder; aero_kernel/engine.py:616-619  `_hit`: removed `self.tool_versions.update(self.solvers.tool_versions_of(tool))` and `self.solver_settings.update(self.solvers.settings_of(tool))`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast tier, aero_kernel/tests/test_engine_cache.py, reuse two_tool_build() with StubAtmosphere({}, {'aerosandbox': '1.2.3'}) and VersionedAvl('1.0'): two calls for 'np-q' on one RecordingCache; expect second.from_cache True and second.provenance.model_dump_json() == first.provenance.model_dump_json(), with first.provenance.tool_versions == {'aerosandbox': '1.2.3', 'avl-binary': '1.0'} and solver_settings == {'avl_nspan': 7}.

## P4-F05 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_engine_defaults.py` · no test exists
- **Production:** `aero_kernel/engine.py:525-528`
- **Gap:** On a cache hit the engine may skip taking the node's defaults: the second, cached call then reports provenance.defaults_used == () and logs no 'default used' line, although Q31 demands both 'also on a second, cached call'.
- **Evidence:** engine.py:525 `# taken on a hit too: the defaults are part of the provenance and logged (ch. 8.11)` followed by `default_warnings = self._take_defaults(defaults)`. No test file combines a default with a cache: `grep defaults_used` finds nothing in test_engine_cache.py, test_cached_kernel*.py or test_cache_world_tools.py, and test_engine_defaults.py never passes `cache=`.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survives all 934 fast tests. Own reproduction on the engine_builders canon with one DedupedCache, quantities density-q and margin-q: on the cached second call the mutation gives provenance.defaults_used == () and no 'default used' log line; the original gives both defaults and both lines again. The `default_target_used` notice survives the mutation (it is stored in the entry). ARCHITECTURE Q31: `one INFO line for gravity and one INFO line for the target, each with call_id, also on a second, cached call`. test_engine_defaults.py::go never passes `cache=`.
- **Verifier's note:** Aero candidate fails only if the BRYAN stall-speed call takes a default (gravity is not in its values, so it should); it is the same test as for P4-F04.
- **Acceptance mutation:** `git apply rework/patches/WP-P4a/P4-F05.patch` (from the audit folder; aero_kernel/engine.py:524-528  `default_warnings = self._take_defaults(defaults)` moved behind the claim and skipped when `lease.entry is not None`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast tier, aero_kernel/tests/test_engine_defaults.py, fixture canon of engine_builders. With one DedupedCache(MemoryCache(max_entries=16)) call evaluate() twice for ('density-q', 'margin-q') inside caplog.at_level(INFO, logger='aero_kernel'). Expect for BOTH calls: provenance.defaults_used == (DENSITY, MARGIN); exactly two 'default used: ...' INFO lines per call with the texts 'default used: air-density = 1.225 kg/m^3 (us standard atmosphere)' and 'default used: margin-target = 1.3 1 (test margin)', each with a call_id; margin-q carries exactly one default_target_used notice; on the second call both quantities have from_cache True.

## P4-F06 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_cache_dedup.py` · existing test `test_a_cancelled_waiter_does_not_cancel_the_run` (line 51)
- **Production:** `aero_kernel/cache.py:302`
- **Gap:** Without asyncio.shield a cancelled waiter cancels the shared in-flight future, so every other waiter of that key gets a CancelledError nobody asked for (observed under the mutation with two waiters). The test passes with and without the shield.
- **Evidence:** The test has a single waiter and checks only the store afterwards: `waiter.cancel()` ... `lease.release(entry(5.0))` / `served = (await cache.claim(KEY)).entry` / `assert served.outputs == {"v": 5.0}`.
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survives all 934 fast tests, including test_a_cancelled_waiter_does_not_cancel_the_run. Own reproduction with two waiters a and b on one key: after a.cancel() and lease.release(entry(5.0)), b raises CancelledError under the mutation and returns outputs {'v': 5.0} on the original. The test has one waiter and looks only at the store afterwards: `served = (await cache.claim(KEY)).entry` / `assert served.outputs == {"v": 5.0}`.
- **Verifier's note:** No aero test cancels a waiter.
- **Acceptance mutation:** `git apply rework/patches/WP-P4a/P4-F06.patch` (from the audit folder; aero_kernel/cache.py:302  `text = await asyncio.shield(running)` -> `text = await running`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast tier, aero_kernel/tests/test_cache_dedup.py: claim KEY; create two waiter tasks a and b; `await asyncio.sleep(0)`; a.cancel(); `await asyncio.gather(a, return_exceptions=True)`; lease.release(entry(5.0)); expect `(await b).entry.outputs == {'v': 5.0}` (b not cancelled) and a.cancelled() is True.

## P4-F14 · low · mirror_or_tautology · do together with P4-F04

- **Test file:** `aero_kernel/tests/test_cache_world_tools.py` · existing test `test_an_overridden_rule_parameter_misses_the_cache_in_the_avl_world` (line 208)
- **Production:** `aero_kernel/engine.py:562-574`
- **Gap:** The file tests a key that its own helper assembles 'as the facade will build it' instead of the key the engine builds. The engine may drop the solver settings from its key and every test stays green (the build digest still protects real constants, so the practical risk is low, but the declared guard is unpinned).
- **Evidence:** test_cache_world_tools.py:31-48 `def node_key(...)`: `return cache_key(formula="calc:rate", ..., tool_versions=solvers.tool_versions_of(tool), solver_settings=solvers.settings_of(tool), rule_overrides={})` duplicates engine._claim.
- **Verified:** CONFIRMED_BY_READING (READING). test_cache_world_tools.py:31-32 builds the key itself: `def node_key(solvers: Solvers, world: str, **inputs: float) -> str:` / `"""The key of the roll-rate-like node in ``world``, built as the facade will build it."""` and calls `cache_key(... solver_settings=solvers.settings_of(tool), rule_overrides={})`; the engine's own assembly is engine.py:565-574 (`solver_settings=settings,`). The tests that go through evaluate() with a cache never vary a setting: the only settings stub is test_engine_cache.py:362-363 `def settings(self)` / `return {"avl_nspan": 7}`.
- **Verifier's note:** The reviewer's mutation (`solver_settings={}`) was not re-run (severity low in the input). AvlAdapter.settings() returns module constants and config.yaml values; whether the build digest covers config.yaml was not checked.
- **Test to write:** Fast tier, aero_kernel/tests/test_engine_cache.py, reuse two_tool_build() and VersionedAvl: give VersionedAvl a settings value passed in the constructor (avl_nspan 7 versus 8); three calls on one RecordingCache (7, 7, 8) -> from_cache (False, True, False) and the AVL world called twice, the ATM world once.

## Not part of this package's work

| Finding | State | Reason |
|---|---|---|
| P4-F07 | waiting_for_decision | maintainer decision open (README section 6); do not write its test |
| P4-F08 | waiting_for_decision | maintainer decision open (README section 6); do not write its test |
| P4-F11 | refuted | killed by `aero_kernel/tests/test_aileron_deflection_required_engine.py::test_a_target_above_the_aerobuildup_maximum_is_an_error_with_the_avl_value` |
| P4-F15 | dropped | Drop: the default decides speed only, never a value, and the app does not use it (app/services/canon_service.py `_new_kernel` passes max_workers=KERNEL_WORKERS and max_concurrency=KERNEL_WORKERS, 'every setting passed explicitly'). The clai |
| P4-F16 | dropped | Drop: the docstring itself says 'Routing is a guess: a miss costs a build, never a value'; the cost is bounded by max_workers spawns per runtime. No other finding of this package touches test_runtime_routing.py. |
| P4-F19 | dropped | Drop: kill and cleanup are asserted where they are implemented (test_solvers_process.py); runtime.run_process delegates to that helper (runtime.py:519 'see solvers.process.run_process'). What remains is the wording of two test names. |
