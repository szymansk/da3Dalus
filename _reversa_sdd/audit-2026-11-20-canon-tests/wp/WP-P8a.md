# WP-P8a — Reference fleet: relations, fast chain, golden recorder

Self-contained brief for one implementer subagent. Base commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

Every finding below was checked by an independent verifier on 2026-11-21 (`../rework/`). The line **Verified** says how. Where **Correction** appears, it overrides the text under **Test to write**.

- **Production code under test:** aero_kernel/tests/test_*_fleet.py, aero_kernel/reference/
- **Requirement sources:** aero_kernel/CLAUDE.md 'regression, not validation', ARCHITECTURE §10
- **Test files you may change:** `aero_kernel/tests/test_mvp_chain_fleet.py`, `aero_kernel/tests/test_plan_batch_fleet.py`, `aero_kernel/tests/test_reference_fleet.py`, `aero_kernel/tests/test_stall_speed_fleet.py`
- **Findings to work on:** 8 (1 high, 4 medium, 3 low)

## P8-F05 · high · weak_assertion

- **Test file:** `aero_kernel/tests/test_reference_fleet.py` · existing test `test_the_masses_are_the_recorded_ones` (line 279)
- **Production:** `aero_kernel/reference_fleet.py:206`
- **Gap:** The masses of the two validation aircraft, the only ones with a published source, are not pinned: AVISTAR_ELITE changed from 3.70 kg (gross) to 3.07 kg (empty) passes every fast test that uses the fleet.
- **Evidence:** assert FleetMember.RV7.mass_kg == 0.500  # ... last mass asserted; PLAN_BATCH_MASS_KG covers the 28 plan models; no line for AVISTAR_ELITE / ULTRA_STICK_120
- **Verified:** CONFIRMED (MUTATION_RERUN). Mutation survived: 966 passed, 707 deselected (baseline identical). With it fleet_values(FleetMember.AVISTAR_ELITE) is {'aircraft-mass': 3.07} and app.services.canon_service.list_fleet serves `mass_kg=member.mass_kg`. The last pinned mass is `assert FleetMember.RV7.mass_kg == 0.500  # approx., maintainer 2026-10-25`; PLAN_BATCH_MASS_KG has no AVISTAR_ELITE / ULTRA_STICK_120 key and test_canon_service pins only `fleet["bryan"].mass_kg`.
- **Verifier's note:** CONFIRMED means: the fast tier does not notice. The aero candidate is expected to fail by a hand estimate, not by a run: the test's bounds are for W = 36.29 N (`assert 9.09 <= roc <= 10.4`); at 3.07 kg the lower bound alone scales to 9.09 x 3.70 / 3.07 = 10.96 m/s. The other Avistar aero tests assert relations and wide brackets and probably stay green.
- **Acceptance mutation:** `git apply rework/patches/WP-P8a/P8-F05.patch` (from the audit folder; aero_kernel/reference_fleet.py:206  `3.70,  # gross weight, AIAA 2020-0780 Table 1` -> `3.07,  # gross weight, AIAA 2020-0780 Table 1`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast tier, test_reference_fleet.py: assert FleetMember.AVISTAR_ELITE.mass_kg == 3.70 (gross weight, AIAA 2020-0780 Table 1: 3.07 kg empty + 0.63 kg battery) and FleetMember.ULTRA_STICK_120.mass_kg == 8.95 (19.72 lbf x 0.45359 = 8.945 kg, FASER Table 2, NTRS 20060022541), and that each copy's total_mass_kg, if present, equals it.

## P8-F01 · medium · golden_without_independent_check

- **Test file:** `aero_kernel/tests/test_plan_batch_fleet.py` · existing test `test_the_chain_of_the_plan_batch_is_the_regression_golden` (line 1225)
- **Production:** `aero_kernel/reference/README.md:432`
- **Gap:** The 28 plan models are checked only against 812 cells copied from the kernel's own output (637 values, 97 not_applicable, 78 errors) at rel 2e-3. A defect present when the goldens were recorded, or introduced and re-recorded, passes: no relation between the values is asserted for these aircraft.
- **Evidence:** for slug, golden in GOLDEN[member].items():
        check(by_slug[slug], golden)   # check(): assert close(quantity.value, golden) with REL = 2e-3
- **Verified:** CONFIRMED_BY_READING (READING). The only assertion on the 28 plan models is the comparison with the recorded cell: `for slug, golden in GOLDEN[member].items():\n        check(by_slug[slug], golden)` with `REL = 2e-3`; no other test of test_plan_batch_fleet.py touches a value. Counted by importing GOLDEN in the copy: 28 members x 29 slugs = 812 cells, 637 values, 97 not_applicable, 78 errors, exactly as claimed.
- **Verifier's note:** Relations do exist for the six MVP aircraft in test_mvp_chain_fleet.py (spiral signs for BRYAN/JAGUAR/RV7, CHEKKER sideslip from its gain); none for the plan batch. No mutation: the claim is about what the goldens can prove, the code under them is reached by aero tests only.
- **Test to write:** Aero tier, same file, reusing the one compute per member: for every member whose values are floats assert (a) stall-speed < minimum-sink-speed < minimum-drag-speed; (b) stall-speed == sqrt(2 m g / (rho S_ref C_L,max)) with m = member.mass_kg, g = 9.80665, rho = 1.225 kg/m^3, S_ref = member.asb_reference[0], rel 2e-3; (c) per world sign(spiral-criterion-x) == -sign(spiral-doubling-time-x) for x in md, mp, app; (d) neutral-point worlds lie between the main wing's quarter-chord MAC x and the tail's quarter-chord MAC x for members of WITH_PITCH_TAIL. (a)-(c) hold for all recorded goldens today (checked by importing GOLDEN), so nothing is weakened.
- **Correction:** (unclear) (a), (b), (c) recomputed on the recorded goldens: all three hold for every member with float values (b with g 9.80665, rho 1.225, S_ref = asb_reference[0], within 2e-3; AERONCA_CHAMP has no stall value and must be skipped). (c) is not an identity: sign(t) = -sign(E) * sign(C_l,beta C_n,p - C_n,beta C_l,p) (lateral_stability._spiral_time), so it holds only while that denominator is positive; say so in the test. (d) was not checked here (needs the quarter-chord MAC positions of wing and tail) and is not shown to hold today.

## P8-F02 · medium · golden_without_independent_check

- **Test file:** `aero_kernel/tests/test_plan_batch_fleet.py` · existing test `test_the_chain_of_the_plan_batch_is_the_regression_golden` (line 1225)
- **Production:** `aero_kernel/tests/test_plan_batch_fleet.py:43`
- **Gap:** An error of category internal is an accepted golden: MINI_FUNTANA's 13 lateral quantities are pinned as Failed('internal') (bug #1373), AERONCA_CHAMP's stall as not_converged. The suite is green while the defect exists, and a new internal error can be recorded the same way without anyone deciding it.
- **Evidence:** # AVL's lateral run gives no derivatives: recorded as the kernel answers it, bug #1373
    FleetMember.MINI_FUNTANA: {  ... "dihedral-effect-md": Failed("internal"), ...
- **Verified:** CONFIRMED_BY_READING (READING). Root errors (code != upstream_failed) in GOLDEN, counted by import: MINI_FUNTANA internal x13, AERONCA_CHAMP not_converged x2, VOODOO unsupported_layout x1, WINDFREAK unsupported_layout x1. Quote: `# AVL's lateral run gives no derivatives: recorded as the kernel answers it, bug #1373\n    FleetMember.MINI_FUNTANA: {`; check() accepts any code: `assert quantity.error.code == golden.code`.
- **Verifier's note:** The pinned internal error is itself bug #1373 (a production defect with a ticket); this finding is only about the missing gate.
- **Test to write:** Fast-tier (solver-free, data only) test in test_reference_fleet_helpers.py or an unmarked function: collect every Failed(code) in GOLDEN whose code is not upstream_failed and assert the set of (member, code) equals an explicit register {(MINI_FUNTANA, 'internal'): '#1373', (AERONCA_CHAMP, 'not_converged'): <issue>, (VOODOO, 'unsupported_layout'): <issue>, (WINDFREAK, 'unsupported_layout'): <issue>}; a new root error then needs a named issue to be recorded. Keep the existing golden test unchanged.
- **Correction:** (unclear) The register of the recommendation is exactly today's set of (member, code) pairs, so the test is green today and fails on a new root error. It cannot be written as given: three of the four entries carry `<issue>` placeholders (AERONCA_CHAMP not_converged, VOODOO / WINDFREAK unsupported_layout) whose issue numbers the implementer must find or the maintainer must name. Importing GOLDEN from the aero-marked module in an unmarked test works (done here in the fast environment).

## P8-F06 · medium · golden_without_independent_check

- **Test file:** `aero_kernel/tests/test_stall_speed_fleet.py` · no test exists
- **Production:** `aero_kernel/reference/avistar_elite/MEASUREMENTS.md:3`
- **Gap:** No fleet test compares a kernel value with a measurement. Counted over the 17 fleet files: about 26 pure regression tests, about 40 relation/contract tests, 3 cross-checks against the CRRCSim prototype (same AeroSandbox), 0 flight-test or published values. The published Avistar Elite and FASER data are in the repository and unused.
- **Evidence:** MEASUREMENTS.md: "Nothing here is used by a test: the kernel marks no value as validated (A11), and the published values are coarse."
- **Verified:** CONFIRMED_BY_READING (READING). Both measurement files say it themselves: avistar_elite/MEASUREMENTS.md `Nothing here is used by a test: the kernel marks no value as validated (A11), and the published values are coarse.`; ultra_stick_120/MEASUREMENTS.md `Nothing here is used by a test: the kernel marks no value as\nvalidated (A11).` A grep of all test_*_fleet.py, test_*_aero.py and test_*_real.py for measured / published / FASER / wind tunnel finds no assertion against a published aircraft value (only the published motor and propeller data as inputs, and two BRYAN prototype cross-checks).
- **Verifier's note:** The files state the absence as intended ('the kernel marks no value as validated (A11)'): a bracket test touches that decision, the maintainer should confirm. The reviewer's counts (26 / 40 / 3) were not recounted; the zero is what was verified.
- **Test to write:** Aero tier, new test_validation_fleet.py, declared as a coarse bracket and not as validation of the method: stall-speed of AVISTAR_ELITE at 3.70 kg, sea level ISA, flaps 0, lies in [10.0, 13.0] m/s (published: mush at approximately 12 m/s at 3.70 kg and a stall break at approximately 14 m/s at 3.95 kg; the kernel gave 11.4 m/s on 2026-11-14); at 3.95 kg the value is larger by sqrt(3.95/3.70) = 1.033 within 1e-3 if C_L,max is unchanged, else within 2 %. Add the FASER values once MEASUREMENTS exist for ULTRA_STICK_120.

## P8-F18 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_plan_batch_fleet.py` · no test exists
- **Production:** `aero_kernel/reference_fleet.py:302`
- **Gap:** Layout coverage of the fleet is narrower than its size suggests: 31 of 36 are conventional; the 2 flying wings pin unsupported_layout instead of a value; 4 of the 5 flapped aircraft (ALBATROS_4, GEE_BEE_R3, P39, SPIRIT_100) get no flap deflection, so their approach chain is recorded as upstream_failed; no aircraft has flaperons, elevons, a canard, two wings or twin booms. Defects in those branches (D9/D10 flaperon rules, Q35) are invisible to the fleet.
- **Evidence:** FLAP_DEFLECTIONS_DEG = {FleetMember.RV7: {"flap-deflection-takeoff": 15.0, "flap-deflection-landing": 30.0},}   # device roles in the 36 documents: elevator 33, rudder 27, aileron 25, flap 5, ruddervator 1, stabilator 1
- **Verified:** CONFIRMED_BY_READING (READING). Counted from the 36 documents: surface types (horizontal_tail, main_wing, vertical_tail) 31, (main_wing, v_tail) 3, (main_wing, vertical_tail) 1, (main_wing, vertical_tail, winglet) 1; device roles elevator 33, rudder 27, aileron 25, flap 5, ruddervator 1, stabilator 1, no flaperon or elevon, no canard, one main wing each. Flapped: RV7, ALBATROS_4, GEE_BEE_R3, P39, SPIRIT_100, and `FLAP_DEFLECTIONS_DEG = {\n    FleetMember.RV7: {"flap-deflection-takeoff": 15.0, "flap-deflection-landing": 30.0},\n}`; the four others record five cells each as Failed('upstream_failed', (('airplane-landing', 'missing_input'),)). VOODOO and WINDFREAK record neutral-point as Failed('unsupported_layout').
- **Verifier's note:** The comment above FLAP_DEFLECTIONS_DEG is wrong for the plan batch: `The other\n# aircraft have no flap, so they take none.` while four of them have flaps. Flaperon and elevon rules are tested in the fast tier on synthetic geometry (test_graph_conditions.py, test_devices.py, test_roll_rate_engine.py), so 'invisible to the fleet' is not 'untested'. Twin booms were not checked.
- **Test to write:** Aero tier: (1) pass flap-deflection-takeoff 15 / landing 30 deg as caller values to the four flapped plan models in a second compute and record stall-speed-landing < stall-speed plus the approach chain; (2) a synthetic flaperon variant of BRYAN (role 'flaperon' on its aileron device): roll-rate-approach is ok, butterfly-max-mix is not_applicable with reason condition_not_met (Q35); (3) for VOODOO/WINDFREAK assert the hint of unsupported_layout names the missing tail, and keep them as the tripwire for the tailless neutral point.
- **Correction:** (unclear) (1) can be written as given. (2) is incomplete: `FLAP_ROLES = frozenset({"flap", "flaperon"})` (aero_kernel/devices.py), so a flaperon BRYAN has a flap and its approach point needs flap-deflection-landing; without it roll-rate-approach is upstream_failed, not ok. The butterfly part fits the code (`CROW_FLAP_ROLES = frozenset({"flap"})`, a flaperon is neither). (3) fits the code: the hint is `a tailless wing, a canard and a tandem wing are not covered yet` with detail surface_types.

## P8-F03 · low · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_mvp_chain_fleet.py` · no test exists
- **Production:** `aero_kernel/reference/README.md:432`
- **Gap:** Goldens are re-recorded by hand-pasting numbers into the test files; there is no recorder, no update flag and no generated old/new report. The six MVP files keep manual '#1358: was ...' comments, the plan batch keeps none, and the seven AVL snapshots in reference/snapshots have no regeneration script. A regeneration can bless a regression with nothing but the PR diff of ~800 floats as the gate.
- **Evidence:** FleetMember.BRYAN: { "vertical-tail-volume": (0.055889564925848935, 0.05583702833957879, 0.055117972548860625,),  # #1358: was (...)
- **Verified:** CONFIRMED_BY_READING (READING). No recorder exists: grep for record_golden / update_golden / --update / regenerate over aero_kernel and scripts finds only the importer's own goldens (aero_kernel/tests/importer_golden.py, test_importer_write.py) and unrelated scripts; nothing writes aero_kernel/reference/snapshots (7 .avl files, read by test_avl_writer_roll.py: `expected = (SNAPSHOTS / f"{member.name.lower()}_clean.avl").read_text()`). Hand comments: `),  # #1358: was (0.055889564925848935, 0.05583702833957879, 0.05512381302882941)`; test_plan_batch_fleet.py has 0 such comments.
- **Verifier's note:** Severity change medium -> low. One detail of the claim is off: the '#1358: was' comments are in eight fleet files, not six (mvp_chain 101, roll_rate 17, tail_arms 15, stall_speed 11, neutral_point 8, minimum_drag 6, minimum_sink 6, stall_break 6).
- **Test to write:** Add scripts/canon_checks/reference_fleet/record_goldens.py (aero tier, run through the lock) that computes the fleet and writes a JSON golden file plus a report listing, per aircraft and slug, old value, new value and relative change, and status changes (ok -> error and back) first. Fast test: the committed report's header names the commit and tool versions of the committed goldens, and every relative change above 1e-3 in the report is listed in an 'accepted' section with an issue number; the fleet tests read the JSON instead of literals.
- **Correction:** (unclear) The recommendation is a tool plus a format change (JSON goldens, a committed report with an 'accepted' section), not a test; report format, where the JSON lives and how the aero lock is used are open design questions an implementer cannot settle alone.

## P8-F04 · low · wrong_tier

- **Test file:** `aero_kernel/tests/test_mvp_chain_fleet.py` · no test exists
- **Production:** `.github/workflows/test.yml:144`
- **Gap:** The end-to-end chain on fleet geometry exists only in the aero tier. PR CI runs -m "... and not aero"; aero runs with the ci-full label or nightly. A broken binding between formulas on real geometry (a wrong applicability fact, a renamed input in the lateral chain) merges green and is found the next night.
- **Evidence:** pytestmark = [pytest.mark.aero]   # test_mvp_chain_fleet.py:25, same in every test_*_fleet.py of the chain
- **Verified:** CONFIRMED_BY_READING (READING). Tier statement true: `pytestmark = [pytest.mark.aero]` (test_mvp_chain_fleet.py:25, test_plan_batch_fleet.py:22; every other test_*_fleet.py of the chain likewise) and CI `-m "not slow and not e2e and not requires_cadquery and not requires_aerosandbox and not requires_avl and not aero"` (.github/workflows/test.yml:144). The claim's example is not true, though: a wrong applicability fact (aero_kernel/graph.py:941 `has_no_aileron=not has_aileron` -> `has_no_aileron=True`) is killed in the fast tier by aero_kernel/tests/test_graph_conditions.py::test_has_no_aileron_is_the_complement_of_has_aileron[aileron-False] (`E       assert True is False`).
- **Verifier's note:** Severity change medium -> low. Probe mutation run on test_graph_conditions.py, test_graph.py, test_turn_sideslip.py, test_rudder_roll_authority.py, test_drela_tail_rules.py, test_lateral_static_stability.py, test_evaluation_evaluator.py, test_evaluation_rules.py (baseline 243 passed); killed, so no patch saved. What remains uncovered in the fast tier is only the combination 'whole chain x real fleet document'.
- **Test to write:** Fast tier, new aero_kernel/tests/test_mvp_chain_fast.py: BRYAN, CHEKKER (rudder only), BELEMNITOS (V-tail), RV-7 (flaps) and VOODOO (tailless) through evaluate(shipped_build(), aircraft_input(member), request(*SLUGS of test_mvp_chain_fleet + CORE_SLUGS of test_plan_batch_fleet), solvers=solvers_with(<fakes of formula_builders/asb_fakes>)). Assert per quantity the status (ok / not_applicable / the declared error code), the world keys {neutral-point=textbook, pappas, avl}, tool and application set, and for the pure-arithmetic nodes the hand value from the fake inputs (e.g. approach-speed = 1.3 x fake V_S; horizontal-tail-volume = S_h l_H / (S c) from the stand-in areas).
- **Correction:** (unclear) Implementable in principle (the per-formula fast tests already drive evaluate(shipped_build(), ..., solvers=solvers_with(<fakes>))), but the list of fakes for 29 slugs, the expected status per aircraft and the 'hand values from the fake inputs' are left to the implementer; much of it would repeat test_lateral_static_stability.py, test_turn_sideslip.py and test_graph_conditions.py.

## P8-F17 · low · wrong_tier · do together with P8-F02

- **Test file:** `aero_kernel/tests/test_plan_batch_fleet.py` · existing test `test_every_member_of_the_batch_has_its_golden` (line 1218)
- **Production:** `aero_kernel/tests/test_plan_batch_fleet.py:22`
- **Gap:** Two solver-free data tests inherit the module's aero marker and never run in PR CI: the completeness of the plan-batch goldens and the roll-device partition of the fleet.
- **Evidence:** pytestmark = [pytest.mark.aero]  ...  def test_every_member_of_the_batch_has_its_golden() -> None:
    assert set(GOLDEN) == set(PLAN_BATCH)
- **Verified:** CONFIRMED_BY_READING (READING). Both are plain data tests under the module marker: `pytestmark = [pytest.mark.aero]` ... `def test_every_member_of_the_batch_has_its_golden() -> None:\n    assert set(GOLDEN) == set(PLAN_BATCH)\n    assert all(tuple(golden) == SLUGS for golden in GOLDEN.values())` and test_mvp_chain_fleet.py:693 `def test_the_fleet_has_members_with_and_without_a_roll_device() -> None:\n    assert FleetMember.CHEKKER in RUDDER_ONLY`. Neither awaits a compute.
- **Verifier's note:** Costs nothing when done together with the fast data test of P8-F02 (same GOLDEN import, same target file).
- **Test to write:** Move both assertions (and test_the_fleet_has_members_with_and_without_a_roll_device of test_mvp_chain_fleet.py:693) into the unmarked test_reference_fleet_helpers.py, importing GOLDEN / RUDDER_ONLY from the aero modules (pure data, no solver import at module level besides aero_kernel.compute).

## Not part of this package's work

| Finding | State | Reason |
|---|---|---|
| P8-F14 | dropped | A wrong closed form is caught by the fast hand-value test, so nothing reaches a caller through this test's weakness. |
| P8-F15 | dropped | Drop: an AeroSandbox or NeuralFoil upgrade is already named in the same aero run by the four fleet files that pin the literal, and a changed value fails the goldens anyway. Only the AVL binary version is pinned nowhere; that would be the pa |
| P8-F16 | dropped | Drop: the consequence is a false alarm on a platform or AVL-build change, no wrong value reaches a caller. If it is fixed, fix it with P8-F01 (same test, same quantities); the doubling time needs the same treatment because it is proportiona |
