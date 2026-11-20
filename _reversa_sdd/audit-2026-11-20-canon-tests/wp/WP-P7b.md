# WP-P7b — Bewertung (Evaluator, Regeltabelle, Drela-Bänder)

Self-contained brief for one implementer subagent. Frozen review state: commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

- **Production code under test:** aero_kernel/evaluation/, canon/model.py, registry.py
- **Requirement sources:** aero_kernel/CLAUDE.md „Judgement lives in evaluation/“, _reversa_sdd/calculations/evaluation/drela.yaml
- **Test files you may change:** `aero_kernel/tests/test_build.py`, `aero_kernel/tests/test_canon_formula.py`, `aero_kernel/tests/test_canon_load.py`, `aero_kernel/tests/test_canon_model.py`, `aero_kernel/tests/test_canon_quantity.py`, `aero_kernel/tests/test_canon_rules_model.py`, `aero_kernel/tests/test_evaluation_evaluator.py`, `aero_kernel/tests/test_evaluation_rules.py`, `aero_kernel/tests/test_evaluation_text.py`, `aero_kernel/tests/test_package.py`, `aero_kernel/tests/test_registry_check.py`
- **Findings:** 19 (4 high, 6 medium, 9 low)

A finding marked **DECISION** needs the maintainer's answer first: do not write its test, list it in your report as open.

## P7b-F01 · high · untested_error_path

- **Test file:** `aero_kernel/tests/test_evaluation_evaluator.py` · no test exists
- **Production:** `aero_kernel/evaluation/evaluator.py:199`
- **Gap:** A quantity the kernel returned with status error or skipped can be reported as not_applicable ('The kernel found it not applicable: no reason given') instead of not_available, and no test fails. The consumer then reads a failed computation as 'the rule does not apply to this aircraft'.
- **Evidence:** if quantity.status is not QuantityStatus.OK: return _verdict(rule, RuleStatus.NOT_AVAILABLE, f"`{slug}` has no value (status {quantity.status.value}).")  -- no test builds a QuantityResult with status ERROR or SKIPPED; evaluation_builders.py offers only ok, spread, not_applicable, not_given.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7b-M04:** in `aero_kernel/evaluation/evaluator.py` line 202: status not ok: RuleStatus.NOT_AVAILABLE -> RuleStatus.NOT_APPLICABLE. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_evaluation_evaluator.py. Add builders errored(slug) (QuantityResult status ERROR with a KernelError) and skipped(slug) (status SKIPPED with its Reason). For each: judge(result_of(x)) must have status RuleStatus.NOT_AVAILABLE, value None, severity None, and 'status error' resp. 'status skipped' in verdict.explanation; and caplog on logger aero_kernel.evaluation must stay empty.

## P7b-F02 · high · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_evaluation_rules.py` · no test exists
- **Production:** `aero_kernel/evaluation/rules.py:28`
- **Gap:** The rule-table types can lose extra='forbid' and frozen without a failing test. A mistyped key in drela.yaml (e.g. `abov_severity: caution`, `min_inclusiv: false`) would then be dropped silently and the rule would judge with the default (bad, inclusive).
- **Evidence:** _FROZEN = ConfigDict(extra="forbid", frozen=True)  -> ConfigDict(): 157 passed. No test passes an unknown key to Band, Level, QuantityRef, Rule or RuleTable, and none assigns to a field.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7b-M28:** in `aero_kernel/evaluation/rules.py` line 28: _FROZEN = ConfigDict(extra='forbid', frozen=True) -> ConfigDict(). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_evaluation_rules.py. (a) pytest.raises(ValidationError, match='Extra inputs') for rule_of(abov_severity='caution'), rule_of(band={'min': 0.05, 'max': 0.15, 'min_inclusiv': False}), rule_of(quantity={'slug': 'x', 'plannd': '#1'}) and RuleTable.model_validate({'source': 's', 'rules': [rule_dict()], 'extra': 1}). (b) pytest.raises(ValidationError, match='frozen') for rule_of().band.min = 0.0 and rule_of().title = 'x'. Same two checks for RuleVerdict (probe M29).

## P7b-F03 · high · weak_assertion

- **Test file:** `aero_kernel/tests/test_evaluation_text.py` · existing test `test_the_unit_is_shown_unless_it_is_dimensionless` (line 51)
- **Production:** `aero_kernel/evaluation/evaluator.py:294`
- **Gap:** The verdict text of a one-sided band can state the band in the wrong direction ('≥ 15' for the limit ≤ 15 deg, '≤ 5' for B > 5) and no test fails. Turn sideslip and all three spiral rules of the shipped table have one-sided bands, and the text is the LLM-facing contract.
- **Evidence:** assert "= 20 deg lies above" in verdict.text   -- the band part of the sentence is not asserted; test_the_shipped_table_words_a_vertical_tail_volume_caution covers only a two-ended band.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7b-M06:** in `aero_kernel/evaluation/evaluator.py` line 296: band text of an upper-only band: '≤ {max}' -> '≥ {max}'. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_evaluation_text.py. With rule_of(unit='deg', band={'max': 15.0}, below=None) and value 20.0 deg assert the full text: 'Static margin (rule `static-margin`, Drela, Lab 11 Notes, Eq. (2)): `static-margin-target` = 20 deg lies above the band ≤ 15 — bad: Large trim changes with speed.' With rule_of(band={'min': 5.0, 'min_inclusive': False}, above=None) and value 4.0 assert '= 4 lies below the band ≥ 5 — bad: Negative: unstable.' in the text. (Probe M07 covers the lower-only branch.)

## P7b-F04 · high · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_evaluation_rules.py` · existing test `test_the_shipped_table_holds_drelas_bands` (line 121)
- **Production:** `aero_kernel/evaluation/rule_table.json`
- **Gap:** Three decided properties of the shipped rule table can change without a failing fast test: the band of the two circling rules over spiral-parameter-mp (5 -> 4), the severity of spiral-stability-circling-aileron below the band (caution -> bad, maintainer decision 2026-10-26), and the level edges of turn-sideslip (5 -> 6 deg).
- **Evidence:** assert table["spiral-stability"].band.min == 5.0   -- the rules spiral-stability-circling-aileron and spiral-stability-circling-rudder-only appear in no assert of the package; `levels` of the shipped table are asserted nowhere except sideslip.level == "within-typical-limit-range" for one value.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7b-M30:** in `_reversa_sdd/calculations/evaluation/drela.yaml` line 121: data probe, JSON regenerated with the importer: spiral-stability-circling-aileron below_severity caution -> bad. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_evaluation_rules.py, against load_rule_table(DRELA). For both circling rules: band.min == 5.0, band.min_inclusive is False, band.max is None, quantity.slug == 'spiral-parameter-mp' (Drela rule 9: B > 5 stable, B = 5 neutral). spiral-stability-circling-aileron: below_severity is Severity.CAUTION, 'maintainer 2026-10-26' in below_basis, when == ('has_vertical_tail', 'has_aileron'). spiral-stability-circling-rudder-only: below_severity is Severity.BAD, when_not == ('has_aileron',). Levels: turn-sideslip level_of(5.0) == 'below-typical-limit', level_of(5.0001) == 'within-typical-limit-range', level_of(15.0) == 'within-typical-limit-range', level_of(15.1) is None (Drela rule 11: 5...15 deg); spiral-stability level_of(3.0) == level_of(4.0) == 'manageable-for-experienced-pilot', level_of(4.5) is None (Drela: B = 3...4).

## P7a-F06 · medium · untested_error_path

- **Test file:** `aero_kernel/tests/test_evaluation_rules.py` · existing test `test_the_shipped_json_is_current` (line 156)
- **Production:** `aero_kernel/importer/rule_table.py:81`
- **Gap:** 'python -m aero_kernel.importer.rule_table --check' (a CI gate) may exit 0 on a stale or missing rule_table.json; the writing branch is not executed by any test.
- **Evidence:** assert main([str(DRELA), "--check"]) == 0  -- the only call of main; mutation 'return 1' -> 'return 0' in the stale branch: 74 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7a-M29:** in `aero_kernel/importer/rule_table.py` line 81: main --check: stale -> return 0. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_evaluation_rules.py: monkeypatch aero_kernel.importer.rule_table.rules_module.__file__ (or Path resolution) to a tmp directory. (1) main([DRELA]) == 0 and tmp/rule_table.json == render_rule_table(load_rule_table(DRELA)). (2) main([DRELA, '--check']) == 0. (3) overwrite the file with '{}' -> main([DRELA, '--check']) == 1 and stdout contains 'rule_table.json is stale'. (4) delete it -> == 1.

## P7b-F05 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_evaluation_rules.py` · existing test `test_an_exclusive_end_is_outside` (line 37)
- **Production:** `aero_kernel/evaluation/rules.py:94`
- **Gap:** max_inclusive: false can be ignored (the upper edge counted inside) without a failing test; only the exclusive lower edge is tested.
- **Evidence:** band = Band(min=5.0, min_inclusive=False); assert band.position(5.0) is Position.BELOW   -- no counterpart with max_inclusive=False.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7b-M02:** in `aero_kernel/evaluation/rules.py` line 95: value > self.max or (value == self.max and not self.max_inclusive) -> value > self.max. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_evaluation_rules.py: band = Band(max=15.0, max_inclusive=False); position(15.0) is Position.ABOVE, position(14.9) is Position.INSIDE; and Band(min=0.0, max=1.0, min_inclusive=False, max_inclusive=False): position(0.0) BELOW, position(1.0) ABOVE, position(0.5) INSIDE.

## P7b-F06 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_evaluation_evaluator.py` · existing test `test_the_level_of_a_value_is_reported` (line 172)
- **Production:** `aero_kernel/evaluation/evaluator.py:257`
- **Gap:** An interval whose ends lie in two different levels can be reported with the level of its lower end (and that level's meaning in the text) without a failing test; the rule 'one level only if both ends share it' is unpinned.
- **Evidence:** verdict = judge(result_of(ok(SM, 0.03)), levels=[...]); assert verdict.level == "weak"   -- scalar only.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7b-M05:** in `aero_kernel/evaluation/evaluator.py` line 257: level = next(iter(levels)) if len(levels) == 1 else None -> level = rule.level_of(ends[0]). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_evaluation_evaluator.py, rule with levels weak [0.0, 0.05] and firm (0.05, 0.15]: spread(SM, 0.03, 0.10) -> verdict.level is None and 'Level' not in verdict.explanation; spread(SM, 0.06, 0.10) -> level == 'firm'; spread(SM, 0.2, 0.3) -> level is None.

## P7b-F07 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_evaluation_evaluator.py` · no test exists
- **Production:** `aero_kernel/evaluation/evaluator.py:255`
- **Gap:** No evaluator test places a value or an interval end exactly on a band edge; the edge behaviour is pinned only one layer down in Band.position. A change in how the evaluator hands ends to the band (e.g. rounding the value as it does for the text, `:.4g`) would pass.
- **Evidence:** assert judge(result_of(spread(SM, -0.1, 0.0))).status is RuleStatus.BELOW   -- the nearest case; every interval in the file keeps both ends clear of 0.05 and 0.15.
- **Status:** READ_ONLY
- **Test to write:** Fast, test_evaluation_evaluator.py, band 0.05..0.15 inclusive: ok(SM, 0.05) and ok(SM, 0.15) -> INSIDE, severity None; spread(SM, 0.05, 0.15) -> INSIDE; spread(SM, 0.05, 0.1500001) -> PARTLY with only the above meaning; ok(SM, 0.04999999) -> BELOW (shows no rounding to 4 digits before judging). With min_inclusive False: spread(SM, 0.05, 0.10) -> PARTLY.

## P7b-F08 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_registry_check.py` · no test exists
- **Production:** `aero_kernel/registry.py:260`
- **Gap:** A @relation registered for a slug the model does not have is not reported by check_traceability: Registry.slugs() collects implementations and checks only. Verified by execution: Registry().relation('no-such-formula')(f); check_traceability(flight_canon).ok is True. ARCHITECTURE 8.12 says traceability 'reports a registered slug ... the model does not have'.
- **Evidence:** return frozenset([*self._implementations, *(slug for slug, _ in self._checks)])   -- test_a_slug_the_model_does_not_have_is_unknown registers a formula, a precondition and a postcondition, no relation.
- **Status:** READ_ONLY
- **Test to write:** Fast, test_registry_check.py: registry = Registry(); registry.relation('no-such-formula')(lambda a: a); codes(registry.check_traceability(flight_canon)) == [('unknown_formula', 'calc:no-such-formula', None)]. This test fails today; whether a relation is traced is a decision for the maintainer (the test pins whichever answer is given).

## P7b-F09 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_canon_rules_model.py` · existing test `test_a_rule_names_exactly_one_existing_target` (line 58)
- **Production:** `aero_kernel/canon/model.py:1079`
- **Gap:** A canon validation rule may guard a derived or output quantity without a failing test, although _rule_target_problem requires an input or target quantity.
- **Evidence:** [{"quantity": "ghost"}, {"formula": "ghost"}, {}, {"quantity": "gravity", "formula": "weight-from-mass"}]   -- no case names an existing quantity of role derived/output.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7b-M20:** in `aero_kernel/canon/model.py` line 1079: rule target: role in (input, target) no longer required. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_canon_rules_model.py: with pytest.raises(ValidationError, match='weight is not an input or target quantity'): build(applies_to={'quantity': 'weight'}) (weight is role output in base_namespaces).

## P7b-F10 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_canon_quantity.py` · no test exists
- **Production:** `aero_kernel/canon/model.py:240`
- **Gap:** A data source named twice in `data` (or in `consistency`) is accepted after removing the check, with all tests green.
- **Evidence:** if self.data is not None and len(set(self.data)) != len(self.data): msg = "data names a source twice"   -- no test matches this message.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7b-M19:** in `aero_kernel/canon/model.py` line 240: Quantity: 'data names a source twice' check disabled. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_canon_quantity.py: pytest.raises(ValidationError, match='data names a source twice') for make_quantity(data=['geometry:a', 'geometry:a']); pytest.raises(ValidationError, match='consistency names a source twice') for make_quantity(consistency=['geometry:a', 'geometry:a']).

## P7b-F11 · low · misleading_name

- **Test file:** `aero_kernel/tests/test_canon_formula.py` · existing test `test_closure_is_sorted_and_unique` (line 251)
- **Production:** `aero_kernel/canon/model.py:526`
- **Gap:** The test proves 'sorted' only; a sorted closure that repeats an item passes when the uniqueness half of the check is removed.
- **Evidence:** items = ["calc:b.default", "calc:a.default"]; with pytest.raises(ValidationError, match="sorted"): make_formula(embeds=items, ..., embeds_closure=items)
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7b-M27:** in `aero_kernel/canon/model.py` line 526: embeds_closure != sorted(set(closure)) -> != sorted(closure). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, same test: add pytest.raises(ValidationError, match='sorted and unique') for embeds=['calc:a.default'], variables=['calc:aircraft-mass'], embeds_closure=['calc:a.default', 'calc:a.default'].

## P7b-F12 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_canon_model.py` · existing test `test_the_default_of_a_bounded_quantity_must_not_exceed_its_maximum` (line 294)
- **Production:** `aero_kernel/canon/model.py:770`
- **Gap:** A default exactly equal to at_most (admissible: an efficiency of 1.0) would be rejected after `>` -> `>=` with all tests green.
- **Evidence:** bounded = with_defaults(namespaces, gravity=GRAVITY_DEFAULT | {"value": 10.5})   -- only a value above the bound.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7b-M21:** in `aero_kernel/canon/model.py` line 770: default.value > quantity.at_most -> >=. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, same file: at_most = 10.0 with default value 10.0 builds and model.namespaces['calc'].defaults['gravity'].value == 10.0.

## P7b-F13 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_evaluation_rules.py` · existing test `test_a_band_needs_a_bound_and_min_below_max` (line 43)
- **Production:** `aero_kernel/evaluation/rules.py:76`
- **Gap:** A band with min == max is accepted after `>=` -> `>` with all tests green.
- **Evidence:** with pytest.raises(ValidationError): Band(min=2.0, max=1.0)
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7b-M10:** in `aero_kernel/evaluation/rules.py` line 76: self.min >= self.max -> self.min > self.max. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, same test: pytest.raises(ValidationError, match='must be below max') for Band(min=1.0, max=1.0).

## P7b-F14 · low · untested_error_path

- **Test file:** `aero_kernel/tests/test_evaluation_evaluator.py` · existing test `test_a_condition_without_a_fact_yet_is_not_available` (line 156)
- **Production:** `aero_kernel/evaluation/evaluator.py:222`
- **Gap:** A pending term in when_not is no longer reported as not_available when the loop looks at `when` only; facts.holds() would then raise ValueError out of evaluate_rules.
- **Evidence:** verdict = judge(result_of(ok(SM, 0.1)), when=["has_horizontal_tail"])   -- only `when`.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7b-M12:** in `aero_kernel/evaluation/evaluator.py` line 222: pending-term loop over (*rule.when, *rule.when_not) -> rule.when. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, same file with the pending_horizontal_tail fixture: judge(result_of(ok(SM, 0.1)), when_not=['has_horizontal_tail']).status is RuleStatus.NOT_AVAILABLE and '#1187' in the explanation.

## P7b-F15 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_build.py` · existing test `test_a_traceability_finding_is_a_load_failure` (line 66)
- **Production:** `aero_kernel/build.py:94`
- **Gap:** The cap of ten findings in the error detail (build and loader) is unpinned: finding_count/error_count and the list are only tested with one or two findings.
- **Evidence:** assert error.detail["finding_count"] == 1; assert error.detail["findings"] == [{...}]
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7b-M23:** in `aero_kernel/build.py` line 94: report.findings[:_MAX_FINDINGS] -> report.findings. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast: test_build.py registers 12 formulas 'ghost-01'..'ghost-12' -> detail['finding_count'] == 12 and len(detail['findings']) == 10, the first ten in sorted order. test_canon_load.py: a model with 12 quantities of unit 'furlong' -> detail['error_count'] == 12, len(detail['errors']) == 10.

## P7b-F16 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_canon_load.py` · existing test `test_unknown_schema_version_is_refused_before_type_validation` (line 65)
- **Production:** `aero_kernel/canon/load.py:122`
- **Gap:** Without the type check a file with schema_version 2.0 loads (CanonModel accepts 2.0 for Literal[2], verified by execution). Low impact: the JSON schema also treats 2.0 as 2.
- **Evidence:** @pytest.mark.parametrize("version", [1, 3, 0, "2", True, None])
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7b-M22:** in `aero_kernel/canon/load.py` line 122: type(version) is not int or version != SUPPORTED -> version != SUPPORTED. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, same parametrisation: add 2.0 (and 2.5); expect CanonLoadError with detail == {'schema_version': None, 'supported': 2}.

## P7b-F17 · low · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_package.py` · existing test `test_package_does_not_import_from_app` (line 66)
- **Production:** `aero_kernel/tests/test_package.py:17`
- **Gap:** A lazy `importlib.import_module('app.services.x')` inside a function body crosses the boundary unseen: the AST scan reads import statements only and the runtime check looks at sys.modules right after `import aero_kernel`.
- **Evidence:** "import sys, aero_kernel;" "roots = {'app', 'cad_designer', 'scripts'};" "print(sorted(m for m in sys.modules if m.split('.')[0] in roots))"
- **Status:** READ_ONLY
- **Test to write:** Fast, test_package.py: extend _imported_roots to report the first string argument of calls to importlib.import_module / __import__ (ast.Call with a constant argument) and add 'importlib.import_module("app.x")' and '__import__("scripts.y")' to the forbidden parametrisation. build.py's import_module('aero_kernel.formulas') must stay accepted.

## P7b-F18 · low · mirror_or_tautology

- **Test file:** `aero_kernel/tests/test_evaluation_rules.py` · existing test `test_the_json_rendering_is_stable` (line 160)
- **Production:** `aero_kernel/importer/rule_table.py`
- **Gap:** The test renders the same table twice and compares the results; it cannot fail for a deterministic function and says nothing about key order or content. test_every_not_yet_computable_rule_names_its_ticket asserts `planned == {}`, i.e. that no planned rule exists, which is not what its name says.
- **Evidence:** first = render_rule_table(table); second = render_rule_table(load_rule_table(DRELA)); assert first == second
- **Status:** READ_ONLY
- **Test to write:** Fast: replace by a test that renders a two-rule table built with keys in reversed order and asserts the text equals the rendering of the normally ordered table and json.loads(text)['rules'][0]['id'] is the first rule. Rename the planned test to test_no_shipped_rule_is_still_planned.
