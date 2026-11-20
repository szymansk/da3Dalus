# WP-P8a — Referenzflotte: Relationen, schnelle Kette, Golden-Recorder

Self-contained brief for one implementer subagent. Frozen review state: commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

- **Production code under test:** aero_kernel/tests/test_*_fleet.py, aero_kernel/reference/
- **Requirement sources:** aero_kernel/CLAUDE.md „regression, not validation“, ARCHITECTURE §10
- **Test files you may change:** `aero_kernel/tests/test_mvp_chain_fleet.py`, `aero_kernel/tests/test_parabolic_polar_fit_fleet.py`, `aero_kernel/tests/test_plan_batch_fleet.py`, `aero_kernel/tests/test_reference_fleet.py`, `aero_kernel/tests/test_stall_speed_fleet.py`
- **Findings:** 11 (0 high, 7 medium, 4 low)

A finding marked **DECISION** needs the maintainer's answer first: do not write its test, list it in your report as open.

## P8-F01 · medium · golden_without_independent_check

- **Test file:** `aero_kernel/tests/test_plan_batch_fleet.py` · existing test `test_the_chain_of_the_plan_batch_is_the_regression_golden` (line 1225)
- **Production:** `aero_kernel/reference/README.md:432`
- **Gap:** The 28 plan models are checked only against 812 cells copied from the kernel's own output (637 values, 97 not_applicable, 78 errors) at rel 2e-3. A defect present when the goldens were recorded, or introduced and re-recorded, passes: no relation between the values is asserted for these aircraft.
- **Evidence:** for slug, golden in GOLDEN[member].items():
        check(by_slug[slug], golden)   # check(): assert close(quantity.value, golden) with REL = 2e-3
- **Status:** READ_ONLY
- **Test to write:** Aero tier, same file, reusing the one compute per member: for every member whose values are floats assert (a) stall-speed < minimum-sink-speed < minimum-drag-speed; (b) stall-speed == sqrt(2 m g / (rho S_ref C_L,max)) with m = member.mass_kg, g = 9.80665, rho = 1.225 kg/m^3, S_ref = member.asb_reference[0], rel 2e-3; (c) per world sign(spiral-criterion-x) == -sign(spiral-doubling-time-x) for x in md, mp, app; (d) neutral-point worlds lie between the main wing's quarter-chord MAC x and the tail's quarter-chord MAC x for members of WITH_PITCH_TAIL. (a)-(c) hold for all recorded goldens today (checked by importing GOLDEN), so nothing is weakened.

## P8-F02 · medium · golden_without_independent_check

- **Test file:** `aero_kernel/tests/test_plan_batch_fleet.py` · existing test `test_the_chain_of_the_plan_batch_is_the_regression_golden` (line 1225)
- **Production:** `aero_kernel/tests/test_plan_batch_fleet.py:43`
- **Gap:** An error of category internal is an accepted golden: MINI_FUNTANA's 13 lateral quantities are pinned as Failed('internal') (bug #1373), AERONCA_CHAMP's stall as not_converged. The suite is green while the defect exists, and a new internal error can be recorded the same way without anyone deciding it.
- **Evidence:** # AVL's lateral run gives no derivatives: recorded as the kernel answers it, bug #1373
    FleetMember.MINI_FUNTANA: {  ... "dihedral-effect-md": Failed("internal"), ...
- **Status:** READ_ONLY
- **Test to write:** Fast-tier (solver-free, data only) test in test_reference_fleet_helpers.py or an unmarked function: collect every Failed(code) in GOLDEN whose code is not upstream_failed and assert the set of (member, code) equals an explicit register {(MINI_FUNTANA, 'internal'): '#1373', (AERONCA_CHAMP, 'not_converged'): <issue>, (VOODOO, 'unsupported_layout'): <issue>, (WINDFREAK, 'unsupported_layout'): <issue>}; a new root error then needs a named issue to be recorded. Keep the existing golden test unchanged.

## P8-F03 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_mvp_chain_fleet.py` · no test exists
- **Production:** `aero_kernel/reference/README.md:432`
- **Gap:** Goldens are re-recorded by hand-pasting numbers into the test files; there is no recorder, no update flag and no generated old/new report. The six MVP files keep manual '#1358: was ...' comments, the plan batch keeps none, and the seven AVL snapshots in reference/snapshots have no regeneration script. A regeneration can bless a regression with nothing but the PR diff of ~800 floats as the gate.
- **Evidence:** FleetMember.BRYAN: { "vertical-tail-volume": (0.055889564925848935, 0.05583702833957879, 0.055117972548860625,),  # #1358: was (...)
- **Status:** READ_ONLY
- **Test to write:** Add scripts/canon_checks/reference_fleet/record_goldens.py (aero tier, run through the lock) that computes the fleet and writes a JSON golden file plus a report listing, per aircraft and slug, old value, new value and relative change, and status changes (ok -> error and back) first. Fast test: the committed report's header names the commit and tool versions of the committed goldens, and every relative change above 1e-3 in the report is listed in an 'accepted' section with an issue number; the fleet tests read the JSON instead of literals.

## P8-F04 · medium · wrong_tier

- **Test file:** `aero_kernel/tests/test_mvp_chain_fleet.py` · no test exists
- **Production:** `.github/workflows/test.yml:144`
- **Gap:** The end-to-end chain on fleet geometry exists only in the aero tier. PR CI runs -m "... and not aero"; aero runs with the ci-full label or nightly. A broken binding between formulas on real geometry (a wrong applicability fact, a renamed input in the lateral chain) merges green and is found the next night.
- **Evidence:** pytestmark = [pytest.mark.aero]   # test_mvp_chain_fleet.py:25, same in every test_*_fleet.py of the chain
- **Status:** READ_ONLY
- **Test to write:** Fast tier, new aero_kernel/tests/test_mvp_chain_fast.py: BRYAN, CHEKKER (rudder only), BELEMNITOS (V-tail), RV-7 (flaps) and VOODOO (tailless) through evaluate(shipped_build(), aircraft_input(member), request(*SLUGS of test_mvp_chain_fleet + CORE_SLUGS of test_plan_batch_fleet), solvers=solvers_with(<fakes of formula_builders/asb_fakes>)). Assert per quantity the status (ok / not_applicable / the declared error code), the world keys {neutral-point=textbook, pappas, avl}, tool and application set, and for the pure-arithmetic nodes the hand value from the fake inputs (e.g. approach-speed = 1.3 x fake V_S; horizontal-tail-volume = S_h l_H / (S c) from the stand-in areas).

## P8-F05 · medium · weak_assertion

- **Test file:** `aero_kernel/tests/test_reference_fleet.py` · existing test `test_the_masses_are_the_recorded_ones` (line 279)
- **Production:** `aero_kernel/reference_fleet.py:206`
- **Gap:** The masses of the two validation aircraft, the only ones with a published source, are not pinned: AVISTAR_ELITE changed from 3.70 kg (gross) to 3.07 kg (empty) passes every fast test that uses the fleet.
- **Evidence:** assert FleetMember.RV7.mass_kg == 0.500  # ... last mass asserted; PLAN_BATCH_MASS_KG covers the 28 plan models; no line for AVISTAR_ELITE / ULTRA_STICK_120
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P8-M17:** in `aero_kernel/reference_fleet.py` line 206: FleetMember.AVISTAR_ELITE mass 3.70 -> 3.07 kg. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast tier, test_reference_fleet.py: assert FleetMember.AVISTAR_ELITE.mass_kg == 3.70 (gross weight, AIAA 2020-0780 Table 1: 3.07 kg empty + 0.63 kg battery) and FleetMember.ULTRA_STICK_120.mass_kg == 8.95 (19.72 lbf x 0.45359 = 8.945 kg, FASER Table 2, NTRS 20060022541), and that each copy's total_mass_kg, if present, equals it.

## P8-F06 · medium · golden_without_independent_check

- **Test file:** `aero_kernel/tests/test_stall_speed_fleet.py` · no test exists
- **Production:** `aero_kernel/reference/avistar_elite/MEASUREMENTS.md:3`
- **Gap:** No fleet test compares a kernel value with a measurement. Counted over the 17 fleet files: about 26 pure regression tests, about 40 relation/contract tests, 3 cross-checks against the CRRCSim prototype (same AeroSandbox), 0 flight-test or published values. The published Avistar Elite and FASER data are in the repository and unused.
- **Evidence:** MEASUREMENTS.md: "Nothing here is used by a test: the kernel marks no value as validated (A11), and the published values are coarse."
- **Status:** READ_ONLY
- **Test to write:** Aero tier, new test_validation_fleet.py, declared as a coarse bracket and not as validation of the method: stall-speed of AVISTAR_ELITE at 3.70 kg, sea level ISA, flaps 0, lies in [10.0, 13.0] m/s (published: mush at approximately 12 m/s at 3.70 kg and a stall break at approximately 14 m/s at 3.95 kg; the kernel gave 11.4 m/s on 2026-11-14); at 3.95 kg the value is larger by sqrt(3.95/3.70) = 1.033 within 1e-3 if C_L,max is unchanged, else within 2 %. Add the FASER values once MEASUREMENTS exist for ULTRA_STICK_120.

## P8-F18 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_plan_batch_fleet.py` · no test exists
- **Production:** `aero_kernel/reference_fleet.py:302`
- **Gap:** Layout coverage of the fleet is narrower than its size suggests: 31 of 36 are conventional; the 2 flying wings pin unsupported_layout instead of a value; 4 of the 5 flapped aircraft (ALBATROS_4, GEE_BEE_R3, P39, SPIRIT_100) get no flap deflection, so their approach chain is recorded as upstream_failed; no aircraft has flaperons, elevons, a canard, two wings or twin booms. Defects in those branches (D9/D10 flaperon rules, Q35) are invisible to the fleet.
- **Evidence:** FLAP_DEFLECTIONS_DEG = {FleetMember.RV7: {"flap-deflection-takeoff": 15.0, "flap-deflection-landing": 30.0},}   # device roles in the 36 documents: elevator 33, rudder 27, aileron 25, flap 5, ruddervator 1, stabilator 1
- **Status:** READ_ONLY
- **Test to write:** Aero tier: (1) pass flap-deflection-takeoff 15 / landing 30 deg as caller values to the four flapped plan models in a second compute and record stall-speed-landing < stall-speed plus the approach chain; (2) a synthetic flaperon variant of BRYAN (role 'flaperon' on its aileron device): roll-rate-approach is ok, butterfly-max-mix is not_applicable with reason condition_not_met (Q35); (3) for VOODOO/WINDFREAK assert the hint of unsupported_layout names the missing tail, and keep them as the tripwire for the tailless neutral point.

## P8-F14 · low · mirror_or_tautology

- **Test file:** `aero_kernel/tests/test_parabolic_polar_fit_fleet.py` · existing test `test_the_closed_forms_are_consistent_with_the_fit` (line 85)
- **Production:** `aero_kernel/formulas/`
- **Gap:** The expected value is the production expression recomputed from the production outputs at 1e-12; a wrong closed form shared by test and code passes.
- **Evidence:** assert close(found["max-lift-to-drag-probe"], 1.0 / (2.0 * math.sqrt(cd0 * k)), 1e-12)
- **Status:** READ_ONLY
- **Test to write:** Replace the expectation's source, not the test: sample the fitted parabola C_D = C_D0 + k C_L^2 on a fine C_L grid (0.05..1.5, 1e-4 steps), take max(C_L / C_D) numerically and assert it equals max-lift-to-drag-probe within 1e-6; likewise oswald-efficiency == 1 / (pi k AR) with AR = b_ref^2 / S_ref from member.asb_reference.

## P8-F15 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_stall_speed_fleet.py` · existing test `test_bryan_regression_goldens_with_the_xlarge_model` (line 96)
- **Production:** `aero_kernel/tests/test_stall_speed_fleet.py:96`
- **Gap:** The stall goldens are 'pinned to their tools' by comparing provenance with whatever is installed, so an AeroSandbox upgrade is not named by this assert; the chain, plan-batch, neutral-point, tail-arm and roll files pin no version at all.
- **Evidence:** assert result.provenance.tool_versions == {"aerosandbox": importlib.metadata.version("aerosandbox"), "neuralfoil": importlib.metadata.version("neuralfoil")}
- **Status:** READ_ONLY
- **Test to write:** One shared constant GOLDEN_TOOL_VERSIONS = {'aerosandbox': '4.2.9', 'neuralfoil': '0.3.2', 'avl-binary': <installed pin>} in tests/reference_fleet.py and one helper asserting result.provenance.tool_versions against the subset that ran; call it in every *_fleet golden test.

## P8-F16 · low · brittle

- **Test file:** `aero_kernel/tests/test_plan_batch_fleet.py` · existing test `test_the_chain_of_the_plan_batch_is_the_regression_golden` (line 1225)
- **Production:** `aero_kernel/tests/test_plan_batch_fleet.py:25`
- **Gap:** A relative tolerance of 2e-3 is applied to differences of AVL derivatives printed to six decimals: A6M2_ZERO's spiral-criterion-md is -3.74e-05 in the Pappas world, so the allowed deviation is 7.5e-08, below one unit of the last printed digit of its inputs. A harmless last-digit change (platform, AVL build) fails the test, and the doubling time derived from it (199.6 s) moves by percent.
- **Evidence:** "spiral-criterion-md": (-0.00016501468900000007, -3.743801099999984e-05, -8.759905000000007e-05,),  ...  REL = 2e-3
- **Status:** READ_ONLY
- **Test to write:** Keep the tolerance for well-conditioned quantities; for spiral-criterion-* and spiral-doubling-time-* derive the tolerance from the print resolution: recompute the criterion from the recorded six-decimal derivatives of the same compute and assert equality to 1e-12, and compare against the golden with abs tolerance 2e-6 (two print units of a product of derivatives of order 0.1). State the reason next to the constant.

## P8-F17 · low · wrong_tier

- **Test file:** `aero_kernel/tests/test_plan_batch_fleet.py` · existing test `test_every_member_of_the_batch_has_its_golden` (line 1218)
- **Production:** `aero_kernel/tests/test_plan_batch_fleet.py:22`
- **Gap:** Two solver-free data tests inherit the module's aero marker and never run in PR CI: the completeness of the plan-batch goldens and the roll-device partition of the fleet.
- **Evidence:** pytestmark = [pytest.mark.aero]  ...  def test_every_member_of_the_batch_has_its_golden() -> None:
    assert set(GOLDEN) == set(PLAN_BATCH)
- **Status:** READ_ONLY
- **Test to write:** Move both assertions (and test_the_fleet_has_members_with_and_without_a_roll_device of test_mvp_chain_fleet.py:693) into the unmarked test_reference_fleet_helpers.py, importing GOLDEN / RUDDER_ONLY from the aero modules (pure data, no solver import at module level besides aero_kernel.compute).
