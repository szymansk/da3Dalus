# WP-P7b — Evaluation (evaluator, rule table, Drela bands)

Self-contained brief for one implementer subagent. Base commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

Every finding below was checked by an independent verifier on 2026-11-21 (`../rework/`). The line **Verified** says how. Where **Correction** appears, it overrides the text under **Test to write**.

- **Production code under test:** aero_kernel/evaluation/, canon/model.py, registry.py
- **Requirement sources:** aero_kernel/CLAUDE.md 'Judgement lives in evaluation/', _reversa_sdd/calculations/evaluation/drela.yaml
- **Test files you may change:** `aero_kernel/tests/test_canon_rules_model.py`, `aero_kernel/tests/test_evaluation_evaluator.py`, `aero_kernel/tests/test_evaluation_rules.py`, `aero_kernel/tests/test_evaluation_text.py`
- **Findings to work on:** 12 (4 high, 5 medium, 3 low)

## P7b-F01 · high · untested_error_path

- **Test file:** `aero_kernel/tests/test_evaluation_evaluator.py` · no test exists
- **Production:** `aero_kernel/evaluation/evaluator.py:199`
- **Gap:** A quantity the kernel returned with status error or skipped can be reported as not_applicable ('The kernel found it not applicable: no reason given') instead of not_available, and no test fails. The consumer then reads a failed computation as 'the rule does not apply to this aircraft'.
- **Evidence:** if quantity.status is not QuantityStatus.OK: return _verdict(rule, RuleStatus.NOT_AVAILABLE, f"`{slug}` has no value (status {quantity.status.value}).")  -- no test builds a QuantityResult with status ERROR or SKIPPED; evaluation_builders.py offers only ok, spread, not_applicable, not_given.
- **Verified:** CONFIRMED (MUTATION_RERUN). A quantity with status error or skipped is then judged not_applicable and 244 fast tests stay green. evaluation_builders.py builds only `status=QuantityStatus.OK` and `status=QuantityStatus.NOT_APPLICABLE`; no evaluation test builds ERROR or SKIPPED. Unmutated code returns for both: "`static-margin-target` has no value (status error)." / "(status skipped)." with status not_available.
- **Verifier's note:** Aero tier read (test_mvp_chain_fleet.py, the only aero module that calls evaluate_rules): it asserts verdict.status and one level for values far from any band or level edge; none is expected to fail.
- **Acceptance mutation:** `git apply rework/patches/WP-P7b/P7b-F01.patch` (from the audit folder; aero_kernel/evaluation/evaluator.py:202  `RuleStatus.NOT_AVAILABLE,` (status-not-ok branch) -> `RuleStatus.NOT_APPLICABLE,`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_evaluation_evaluator.py. Add builders errored(slug) (QuantityResult status ERROR with a KernelError) and skipped(slug) (status SKIPPED with its Reason). For each: judge(result_of(x)) must have status RuleStatus.NOT_AVAILABLE, value None, severity None, and 'status error' resp. 'status skipped' in verdict.explanation; and caplog on logger aero_kernel.evaluation must stay empty.

## P7b-F03 · high · weak_assertion

- **Test file:** `aero_kernel/tests/test_evaluation_text.py` · existing test `test_the_unit_is_shown_unless_it_is_dimensionless` (line 51)
- **Production:** `aero_kernel/evaluation/evaluator.py:294`
- **Gap:** The verdict text of a one-sided band can state the band in the wrong direction ('≥ 15' for the limit ≤ 15 deg, '≤ 5' for B > 5) and no test fails. Turn sideslip and all three spiral rules of the shipped table have one-sided bands, and the text is the LLM-facing contract.
- **Evidence:** assert "= 20 deg lies above" in verdict.text   -- the band part of the sentence is not asserted; test_the_shipped_table_words_a_vertical_tail_volume_caution covers only a two-ended band.
- **Verified:** CONFIRMED (MUTATION_RERUN). The text of an upper-only band then reads 'lies above the band ≥ 15' and 244 fast tests stay green. The only test with a one-sided band in the text asserts `assert "= 20 deg lies above" in verdict.text` (test_evaluation_text.py:54), which stops before the band; the lower-only branch `≥ {band.min:g}` is asserted nowhere either.
- **Verifier's note:** Side observation, not part of the claim: _band_text ignores min_inclusive/max_inclusive. For the exclusive band min 5 (all three shipped spiral rules) the unmutated code writes '`static-margin-target` = 5 lies below the band ≥ 5', which contradicts itself. The second recommended assert would pin '≥ 5' for an exclusive bound; the maintainer may want '> 5' decided first. Aero tier read (test_mvp_chain_fleet.py, the only aero module that calls evaluate_rules): it asserts verdict.status and one level for values far from any band or level edge; none is expected to fail.
- **Acceptance mutation:** `git apply rework/patches/WP-P7b/P7b-F03.patch` (from the audit folder; aero_kernel/evaluation/evaluator.py:296  `return f"≤ {band.max:g}"` -> `return f"≥ {band.max:g}"`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_evaluation_text.py. With rule_of(unit='deg', band={'max': 15.0}, below=None) and value 20.0 deg assert the full text: 'Static margin (rule `static-margin`, Drela, Lab 11 Notes, Eq. (2)): `static-margin-target` = 20 deg lies above the band ≤ 15 — bad: Large trim changes with speed.' With rule_of(band={'min': 5.0, 'min_inclusive': False}, above=None) and value 4.0 assert '= 4 lies below the band ≥ 5 — bad: Negative: unstable.' in the text. (Probe M07 covers the lower-only branch.)

## P7b-F04 · high · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_evaluation_rules.py` · existing test `test_the_shipped_table_holds_drelas_bands` (line 121)
- **Production:** `aero_kernel/evaluation/rule_table.json`
- **Gap:** Three decided properties of the shipped rule table can change without a failing fast test: the band of the two circling rules over spiral-parameter-mp (5 -> 4), the severity of spiral-stability-circling-aileron below the band (caution -> bad, maintainer decision 2026-10-26), and the level edges of turn-sideslip (5 -> 6 deg).
- **Evidence:** assert table["spiral-stability"].band.min == 5.0   -- the rules spiral-stability-circling-aileron and spiral-stability-circling-rudder-only appear in no assert of the package; `levels` of the shipped table are asserted nowhere except sideslip.level == "within-typical-limit-range" for one value.
- **Verified:** CONFIRMED (MUTATION_RERUN). All three data changes applied together (reviewer probed only the severity), JSON regenerated, `--check` reports current, and 244 fast tests stay green. The two circling rules occur in no fast assert; the nearest is `assert table["spiral-stability"].band.min == 5.0` (test_evaluation_rules.py:137), a different rule, and no fast test reads `.levels` of the shipped table.
- **Verifier's note:** Aero tier read: test_mvp_chain_fleet.py asserts `verdicts["spiral-stability-circling-aileron"].status is RuleStatus.BELOW` for BELEMNITOS (golden B_mp about 0.73, below 4 as well) and `.level == "below-typical-limit"` for CHEKKER (golden sideslip about 2.8 deg, below 5 and 6); neither fails under this mutation, and no aero test asserts the severity.
- **Acceptance mutation:** `git apply rework/patches/WP-P7b/P7b-F04.patch` (from the audit folder; _reversa_sdd/calculations/evaluation/drela.yaml:114,131  both circling rules `band: {min: 5.0, min_inclusive: false}` -> `min: 4.0`; :121 `below_severity: caution` -> `below_severity: bad`; :171,174 turn-sideslip level edges `max: 5.0` / `min: 5.0` -> `6.0`; aero_kernel/evaluation/rule_table.json regenerated with `python -m aero_kernel.importer.rule_table`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_evaluation_rules.py, against load_rule_table(DRELA). For both circling rules: band.min == 5.0, band.min_inclusive is False, band.max is None, quantity.slug == 'spiral-parameter-mp' (Drela rule 9: B > 5 stable, B = 5 neutral). spiral-stability-circling-aileron: below_severity is Severity.CAUTION, 'maintainer 2026-10-26' in below_basis, when == ('has_vertical_tail', 'has_aileron'). spiral-stability-circling-rudder-only: below_severity is Severity.BAD, when_not == ('has_aileron',). Levels: turn-sideslip level_of(5.0) == 'below-typical-limit', level_of(5.0001) == 'within-typical-limit-range', level_of(15.0) == 'within-typical-limit-range', level_of(15.1) is None (Drela rule 11: 5...15 deg); spiral-stability level_of(3.0) == level_of(4.0) == 'manageable-for-experienced-pilot', level_of(4.5) is None (Drela: B = 3...4).

## P7b-F06 · high · missing_edge_case

- **Test file:** `aero_kernel/tests/test_evaluation_evaluator.py` · existing test `test_the_level_of_a_value_is_reported` (line 172)
- **Production:** `aero_kernel/evaluation/evaluator.py:257`
- **Gap:** An interval whose ends lie in two different levels can be reported with the level of its lower end (and that level's meaning in the text) without a failing test; the rule 'one level only if both ends share it' is unpinned.
- **Evidence:** verdict = judge(result_of(ok(SM, 0.03)), levels=[...]); assert verdict.level == "weak"   -- scalar only.
- **Verified:** CONFIRMED (MUTATION_RERUN). An interval whose ends lie in different levels is then reported with the level of its lower end, and 244 fast tests stay green. The only level test of the evaluator is scalar: `verdict = judge(result_of(ok(SM, 0.03)), levels=[...])` / `assert verdict.level == "weak"` (test_evaluation_evaluator.py:172-177).
- **Verifier's note:** The aero assert `verdicts["turn-sideslip"].level == "below-typical-limit"` (CHEKKER, an interval over three worlds, all about 2.8 deg) has both ends in one level and does not fail. Aero tier read (test_mvp_chain_fleet.py, the only aero module that calls evaluate_rules): it asserts verdict.status and one level for values far from any band or level edge; none is expected to fail.
- **Acceptance mutation:** `git apply rework/patches/WP-P7b/P7b-F06.patch` (from the audit folder; aero_kernel/evaluation/evaluator.py:257  `level = next(iter(levels)) if len(levels) == 1 else None` -> `level = rule.level_of(ends[0])`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_evaluation_evaluator.py, rule with levels weak [0.0, 0.05] and firm (0.05, 0.15]: spread(SM, 0.03, 0.10) -> verdict.level is None and 'Level' not in verdict.explanation; spread(SM, 0.06, 0.10) -> level == 'firm'; spread(SM, 0.2, 0.3) -> level is None.

## P7a-F06 · medium · untested_error_path

- **Test file:** `aero_kernel/tests/test_evaluation_rules.py` · existing test `test_the_shipped_json_is_current` (line 156)
- **Production:** `aero_kernel/importer/rule_table.py:81`
- **Gap:** 'python -m aero_kernel.importer.rule_table --check' (a CI gate) may exit 0 on a stale or missing rule_table.json; the writing branch is not executed by any test.
- **Evidence:** assert main([str(DRELA), "--check"]) == 0  -- the only call of main; mutation 'return 1' -> 'return 0' in the stale branch: 74 passed.
- **Verified:** CONFIRMED (MUTATION_RERUN). The stale branch can report success and all 244 fast tests stay green. The only call of main in any test is `assert main([str(DRELA), "--check"]) == 0` (test_evaluation_rules.py:157); grep finds no other caller, so neither the stale branch nor the writing branch (`target.write_text(fresh, encoding="utf-8")`) is executed by a test.
- **Verifier's note:** Aero tier read (test_mvp_chain_fleet.py, the only aero module that calls evaluate_rules): it asserts verdict.status and one level for values far from any band or level edge; none is expected to fail.
- **Acceptance mutation:** `git apply rework/patches/WP-P7b/P7a-F06.patch` (from the audit folder; aero_kernel/importer/rule_table.py:81  `return 1` (stale branch of --check) -> `return 0`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_evaluation_rules.py: monkeypatch aero_kernel.importer.rule_table.rules_module.__file__ (or Path resolution) to a tmp directory. (1) main([DRELA]) == 0 and tmp/rule_table.json == render_rule_table(load_rule_table(DRELA)). (2) main([DRELA, '--check']) == 0. (3) overwrite the file with '{}' -> main([DRELA, '--check']) == 1 and stdout contains 'rule_table.json is stale'. (4) delete it -> == 1.

## P7b-F02 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_evaluation_rules.py` · no test exists
- **Production:** `aero_kernel/evaluation/rules.py:28`
- **Gap:** The rule-table types can lose extra='forbid' and frozen without a failing test. A mistyped key in drela.yaml (e.g. `abov_severity: caution`, `min_inclusiv: false`) would then be dropped silently and the rule would judge with the default (bad, inclusive).
- **Evidence:** _FROZEN = ConfigDict(extra="forbid", frozen=True)  -> ConfigDict(): 157 passed. No test passes an unknown key to Band, Level, QuantityRef, Rule or RuleTable, and none assigns to a field.
- **Verified:** CONFIRMED (MUTATION_RERUN). With the mutation Band, Level, QuantityRef, Rule and RuleTable accept unknown keys and assignment, and 244 fast tests stay green. No test in the evaluation files passes an unknown key or assigns to a field; every `pytest.raises(ValidationError)` in test_evaluation_rules.py is about a known field.
- **Verifier's note:** Aero tier read (test_mvp_chain_fleet.py, the only aero module that calls evaluate_rules): it asserts verdict.status and one level for values far from any band or level edge; none is expected to fail.
- **Acceptance mutation:** `git apply rework/patches/WP-P7b/P7b-F02.patch` (from the audit folder; aero_kernel/evaluation/rules.py:28  `_FROZEN = ConfigDict(extra="forbid", frozen=True)` -> `_FROZEN = ConfigDict()`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_evaluation_rules.py. (a) pytest.raises(ValidationError, match='Extra inputs') for rule_of(abov_severity='caution'), rule_of(band={'min': 0.05, 'max': 0.15, 'min_inclusiv': False}), rule_of(quantity={'slug': 'x', 'plannd': '#1'}) and RuleTable.model_validate({'source': 's', 'rules': [rule_dict()], 'extra': 1}). (b) pytest.raises(ValidationError, match='frozen') for rule_of().band.min = 0.0 and rule_of().title = 'x'. Same two checks for RuleVerdict (probe M29).

## P7b-F05 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_evaluation_rules.py` · existing test `test_an_exclusive_end_is_outside` (line 37)
- **Production:** `aero_kernel/evaluation/rules.py:94`
- **Gap:** max_inclusive: false can be ignored (the upper edge counted inside) without a failing test; only the exclusive lower edge is tested.
- **Evidence:** band = Band(min=5.0, min_inclusive=False); assert band.position(5.0) is Position.BELOW   -- no counterpart with max_inclusive=False.
- **Verified:** CONFIRMED (MUTATION_RERUN). max_inclusive=False is then ignored and 244 fast tests stay green. The only exclusive-end test is `band = Band(min=5.0, min_inclusive=False)` (test_evaluation_rules.py:38); no test sets max_inclusive, and the shipped table uses it nowhere (only Level/Band defaults).
- **Verifier's note:** Aero tier read (test_mvp_chain_fleet.py, the only aero module that calls evaluate_rules): it asserts verdict.status and one level for values far from any band or level edge; none is expected to fail.
- **Acceptance mutation:** `git apply rework/patches/WP-P7b/P7b-F05.patch` (from the audit folder; aero_kernel/evaluation/rules.py:95  `value > self.max or (value == self.max and not self.max_inclusive)` -> `value > self.max`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_evaluation_rules.py: band = Band(max=15.0, max_inclusive=False); position(15.0) is Position.ABOVE, position(14.9) is Position.INSIDE; and Band(min=0.0, max=1.0, min_inclusive=False, max_inclusive=False): position(0.0) BELOW, position(1.0) ABOVE, position(0.5) INSIDE.

## P7b-F07 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_evaluation_evaluator.py` · no test exists
- **Production:** `aero_kernel/evaluation/evaluator.py:255`
- **Gap:** No evaluator test places a value or an interval end exactly on a band edge; the edge behaviour is pinned only one layer down in Band.position. A change in how the evaluator hands ends to the band (e.g. rounding the value as it does for the text, `:.4g`) would pass.
- **Evidence:** assert judge(result_of(spread(SM, -0.1, 0.0))).status is RuleStatus.BELOW   -- the nearest case; every interval in the file keeps both ends clear of 0.05 and 0.15.
- **Verified:** CONFIRMED (NEW_MUTATION). The reviewer's own example (rounding the ends to four digits as the text does) was applied; 244 fast tests stay green, and the mutated code judges 0.04999999 as inside. One sentence of the claim is too strong: test_the_shipped_table_judges_a_hand_made_result does place a value on an edge, `ok("spiral-parameter-md", 5.0)` with `assert verdicts["spiral-stability"].status is RuleStatus.BELOW  # B = 5 is neutral, not stable`; inclusive edges, interval ends on an edge and near-edge values remain unpinned at the evaluator.
- **Verifier's note:** Side observation: the text of spread(0.05, 0.1500001) reads '0.05…0.15 ... reaches outside the band 0.05…0.15', because the text rounds to four digits. Aero tier read (test_mvp_chain_fleet.py, the only aero module that calls evaluate_rules): it asserts verdict.status and one level for values far from any band or level edge; none is expected to fail.
- **Acceptance mutation:** `git apply rework/patches/WP-P7b/P7b-F07.patch` (from the audit folder; aero_kernel/evaluation/evaluator.py:255  `positions = {rule.band.position(end) for end in ends}` -> `positions = {rule.band.position(float(f"{end:.4g}")) for end in ends}`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_evaluation_evaluator.py, band 0.05..0.15 inclusive: ok(SM, 0.05) and ok(SM, 0.15) -> INSIDE, severity None; spread(SM, 0.05, 0.15) -> INSIDE; spread(SM, 0.05, 0.1500001) -> PARTLY with only the above meaning; ok(SM, 0.04999999) -> BELOW (shows no rounding to 4 digits before judging). With min_inclusive False: spread(SM, 0.05, 0.10) -> PARTLY.

## P7b-F09 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_canon_rules_model.py` · existing test `test_a_rule_names_exactly_one_existing_target` (line 58)
- **Production:** `aero_kernel/canon/model.py:1079`
- **Gap:** A canon validation rule may guard a derived or output quantity without a failing test, although _rule_target_problem requires an input or target quantity.
- **Evidence:** [{"quantity": "ghost"}, {"formula": "ghost"}, {}, {"quantity": "gravity", "formula": "weight-from-mass"}]   -- no case names an existing quantity of role derived/output.
- **Verified:** CONFIRMED (MUTATION_RERUN). A validation rule may then guard a derived or output quantity and 1274 fast canon, importer and registry tests stay green. The rejecting cases of the test are `{"quantity": "ghost"}, {"formula": "ghost"}, {}, {"quantity": "gravity", "formula": "weight-from-mass"}` (test_canon_rules_model.py:52-57); grep finds the message 'is not an input or target quantity' in no test.
- **Verifier's note:** Aero tier: no aero test builds a canon model with a rule on a non-input quantity.
- **Acceptance mutation:** `git apply rework/patches/WP-P7b/P7b-F09.patch` (from the audit folder; aero_kernel/canon/model.py:1079  `if found is not None and found.role in ("input", "target"):` -> `if found is not None:`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_canon_rules_model.py: with pytest.raises(ValidationError, match='weight is not an input or target quantity'): build(applies_to={'quantity': 'weight'}) (weight is role output in base_namespaces).

## P7b-F13 · low · missing_edge_case · do together with P7b-F05

- **Test file:** `aero_kernel/tests/test_evaluation_rules.py` · existing test `test_a_band_needs_a_bound_and_min_below_max` (line 43)
- **Production:** `aero_kernel/evaluation/rules.py:76`
- **Gap:** A band with min == max is accepted after `>=` -> `>` with all tests green.
- **Evidence:** with pytest.raises(ValidationError): Band(min=2.0, max=1.0)
- **Verified:** CONFIRMED_BY_READING (READING). Production: `if self.min is not None and self.max is not None and self.min >= self.max:` (rules.py:76). The test has only `Band()` and `Band(min=2.0, max=1.0)` inside `pytest.raises(ValidationError)`; equality is not tried.
- **Verifier's note:** Same test file and same unit (Band edges) as P7b-F05.
- **Test to write:** Fast, same test: pytest.raises(ValidationError, match='must be below max') for Band(min=1.0, max=1.0).

## P7b-F14 · low · untested_error_path · do together with P7b-F01

- **Test file:** `aero_kernel/tests/test_evaluation_evaluator.py` · existing test `test_a_condition_without_a_fact_yet_is_not_available` (line 156)
- **Production:** `aero_kernel/evaluation/evaluator.py:222`
- **Gap:** A pending term in when_not is no longer reported as not_available when the loop looks at `when` only; facts.holds() would then raise ValueError out of evaluate_rules.
- **Evidence:** verdict = judge(result_of(ok(SM, 0.1)), when=["has_horizontal_tail"])   -- only `when`.
- **Verified:** CONFIRMED_BY_READING (READING). Production loops over both lists: `for term in (*rule.when, *rule.when_not):` (evaluator.py:222); the test passes only `when=["has_horizontal_tail"]`. WhenFacts.holds raises `ValueError` 'the when-term has_horizontal_tail has no fact yet (#1187)' for a pending term (executed), so the claimed consequence is real.
- **Verifier's note:** Production has no pending term today (`PENDING_WHEN_TERMS: Mapping[str, str] = {}`, graph.py:857), so the path is reachable only through the fixture; cheap to add next to P7b-F01 in the same file.
- **Test to write:** Fast, same file with the pending_horizontal_tail fixture: judge(result_of(ok(SM, 0.1)), when_not=['has_horizontal_tail']).status is RuleStatus.NOT_AVAILABLE and '#1187' in the explanation.

## P7b-F18 · low · mirror_or_tautology · do together with P7b-F04

- **Test file:** `aero_kernel/tests/test_evaluation_rules.py` · existing test `test_the_json_rendering_is_stable` (line 160)
- **Production:** `aero_kernel/importer/rule_table.py`
- **Gap:** The test renders the same table twice and compares the results; it cannot fail for a deterministic function and says nothing about key order or content. test_every_not_yet_computable_rule_names_its_ticket asserts `planned == {}`, i.e. that no planned rule exists, which is not what its name says.
- **Evidence:** first = render_rule_table(table); second = render_rule_table(load_rule_table(DRELA)); assert first == second
- **Verified:** CONFIRMED_BY_READING (READING). The test is `first = render_rule_table(table)` / `second = render_rule_table(load_rule_table(DRELA))` / `assert first == second` / `assert first.endswith("}\n")`: the comparison renders the same YAML twice; only the last line (trailing newline) checks content, which the claim leaves out. test_every_not_yet_computable_rule_names_its_ticket ends with `assert planned == {}`.
- **Verifier's note:** Same test file as P7b-F04, whose asserts on the shipped table give this file the content checks it lacks.
- **Test to write:** Fast: replace by a test that renders a two-rule table built with keys in reversed order and asserts the text equals the rendering of the normally ordered table and json.loads(text)['rules'][0]['id'] is the first rule. Rename the planned test to test_no_shipped_rule_is_still_planned.

## Not part of this package's work

| Finding | State | Reason |
|---|---|---|
| P7b-F08 | production_defect | #1436 |
| P7b-F10 | dropped | Drop reason: canon authoring hygiene. A source listed twice is refused at canon build time in CI; I found no path by which the duplicate changes a value in flight, range, payload or cruise results (not traced further). Two lines if the main |
| P7b-F11 | dropped | Drop reason: the name promises more than the test shows, and the unpinned half (a repeated closure item) is canon authoring hygiene without an effect on a computed value that I could find. |
| P7b-F12 | dropped | Drop reason: if the comparison regressed to `>=`, a default at its bound would fail the canon build loudly in CI; nothing wrong would reach a computed value. |
| P7b-F15 | dropped | Drop reason: the cap only bounds the length of an internal-error detail, and the total is reported next to it (finding_count / error_count); no effect on any computed value. |
| P7b-F16 | dropped | Drop reason: a file that says 2.0 is the supported version in every respect that matters; refusing or accepting it changes no result. |
| P7b-F17 | dropped | Drop reason: an architecture-boundary guard with no bearing on a computed value, and no offending import exists. The docstring overstates what the runtime test covers; correcting that sentence costs nothing. |
