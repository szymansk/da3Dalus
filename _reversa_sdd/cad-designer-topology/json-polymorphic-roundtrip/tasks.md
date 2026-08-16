# json-polymorphic-roundtrip — Implementation Tasks

> Use-case task list, nested under the module
> [`cad-designer-topology`](../tasks.md).
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
>
> ⚠ **`GeneralJSONEncoderDecoder.py` is FROZEN (ADR 0002).** These tasks describe
> **what a re-implementation must reproduce**, not edits to make in
> `cad_designer/`. See `### Preservation constraints` for the split between
> behaviour to carry forward and defects to leave behind.

## Prerequisites

- [ ] The Creator contract and both node classes exist
      (→ [`../creator-execution-model/tasks.md`](../creator-execution-model/tasks.md)
      T-CX-01, T-CX-06, T-CX-08) — they are the objects being serialised.
- [ ] The topology classes exist with their public attribute sets settled
      (→ [`../wingconfiguration-coordinate-system/tasks.md`](../wingconfiguration-coordinate-system/tasks.md)),
      because the encoder's output *is* `__dict__` minus private fields.
- [ ] CadQuery available — the serialisation module imports the plugin package
      for its side effect, so decoding is unavailable without it (ADR 0017).
- [ ] A decision on **whether stored plans get a schema version**
      (→ [`../tasks.md`](../tasks.md) TM-03). Everything below assumes the legacy
      answer: no version, class name only.
- [ ] The five **injection kwarg names** are agreed with
      [`construction-plans`](../../construction-plans/tasks.md) and
      [`cad-generation`](../../cad-generation/tasks.md): `wing_config`,
      `fuselage_config`, `printer_settings`, `servo_information`,
      `engine_information`, `component_information`.

## Tasks

### Encoding

- [ ] **T-JS-01 — `GeneralJSONEncoder`.**
  `JSON_CLASS_TYPE_ID = '$TYPE'`; `default(o)` emitting
  `{k: v for k, v in o.__dict__.items() if not k.startswith('_')}` plus
  `"$TYPE" = o.__class__.__name__`.
  - Legacy origin: `cad_designer/airplane/GeneralJSONEncoderDecoder.py:13-25`
  - Definition of done: a creator holding `self._config` round-trips with no
    underscore-prefixed key in the JSON; `_shapes_of_interest_keys`,
    `ConstructionRootNode._output_shapes` and `JSONStepNode._to_be_injected` are
    all absent; a root node's JSON has no `"creator"` key while a step node's
    does.
  - Confidence: 🟢

### Class resolution

- [ ] **T-JS-02 — `$TYPE` resolution and the resolvable namespace.**
  `getattr(sys.modules[<serialisation module>], dic["$TYPE"])`, with the module
  importing the two node classes and star-importing the Creator package. Document
  in the module that these imports are **load-bearing**, not incidental — the
  legacy file carries exactly that comment.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:1-11, 193-198`
  - Definition of done: every registered Creator decodes; an unregistered class
    raises; a **topology** class name raises (they are deliberately not
    importable into the namespace); a test asserts the complete resolvable set so
    an accidental import widening it is caught.
  - Confidence: 🟢

- [ ] **T-JS-03 — Plain-dict passthrough.**
  A dict without `$TYPE` is returned unchanged.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:194-195`
  - Definition of done: a nested parameter object and the `successors` map both
    survive as plain dicts; bottom-up hook ordering means a node's `creator` and
    `successors` are already live objects when the node itself is built.
  - Confidence: 🟢

### Parameter selection and injection

- [ ] **T-JS-04 — Decoder kwargs split.**
  Retain the full payload as the injection source; forward to `JSONDecoder` only
  the arguments it declares, via a set-intersection of the payload keys with
  `inspect.signature(JSONDecoder.__init__).parameters`.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:180-191`
  - Definition of done: a decoder built with both `object_pairs_hook` and
    `wing_config` works; `object_pairs_hook` reaches `JSONDecoder` and
    `wing_config` reaches the Creators. See T-JS-14 for the leak in the other
    direction.
  - Confidence: 🟢

- [ ] **T-JS-05 — The two parameter-selection branches.**
  When `"kwargs" in inspect.signature(cls.__init__).parameters`: pass the whole
  stored dict **plus all** injections. Otherwise: intersect the stored dict with
  the declared parameter names, then overlay the injections that match declared
  names. In both branches **injections win** over stored values of the same name.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:199-210`
  - Definition of done: a Creator with `**kwargs` receives `wing_config`; one
    without receives only its declared parameters; a stored `wing_config` value
    is overridden by the injected object; an unknown stored key is **dropped**
    rather than raising `TypeError`.
  - Confidence: 🟢

### Coercion

- [ ] **T-JS-06 — `_coerce_params` driver.**
  Read `cls.__init__.__annotations__` minus `"return"`; on `AttributeError`
  return the parameters untouched; per key, pass through `None` values and
  unannotated keys; otherwise apply the list guard (T-JS-07) then the scalar
  resolution (T-JS-08).
  - Legacy origin: `GeneralJSONEncoderDecoder.py:125-176`
  - Definition of done: an unannotated class decodes with every value exactly as
    JSON produced it; a `None` on a `float` parameter stays `None` and is not
    coerced to `0.0`.
  - Confidence: 🟢

- [ ] **T-JS-07 — The `list[...]`-from-string guard, ordered first.**
  When the annotation is a list type and the value is a `str`, wrap it into a
  one-element list (`[]` for an empty or whitespace-only string). When the
  annotation is a list type and the value is neither list nor str, pass through.
  `_is_list_type` must handle both real annotations (`__origin__ is list`) and
  string annotations (`"list["` prefix, or exactly `"list"`).
  **This check must run before scalar type resolution.**
  - Legacy origin: `GeneralJSONEncoderDecoder.py:87-92, 144-152`
  - Definition of done: `"fuselage"` on a `list[ShapeId]` yields `["fuselage"]`,
    never a list of characters; `""` yields `[]`; a real list passes through; a
    regression test documents that moving the guard after scalar resolution
    stringifies the list (because `_resolve_base_type(list[str])` returns `str`).
  - Confidence: 🟢

- [ ] **T-JS-08 — `_resolve_base_type`.**
  Resolve in order: **string** annotations (case-insensitive:
  `"float"`/`"confloat…"` → `float`; `"int"`/`"nonnegativeint"`/`"conint…"` →
  `int`; `"bool"` → `bool`; `"str"` → `str`;
  `"creatorid"`/`"shapeid"` → `str`; a hint containing `"factor"` → `float`;
  `"annotated[...]"` → parse the first argument), then `NewType.__supertype__`,
  then `__origin__`/`__args__[0]` recursion, then the four plain scalars;
  `None` when nothing matches.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:28-84`
  - Definition of done: `Factor`, `ShapeId`, `CreatorId`,
    `Annotated[float, Field(...)]`, `confloat(...)`, a plain `float` and the
    string forms of each all resolve correctly; an unresolvable hint yields
    `None` and the value is left alone. See T-JS-15 for the `"factor"`
    heuristic.
  - Confidence: 🟢

- [ ] **T-JS-09 — Scalar coercion and its failure mode.**
  `float → float(normalize(value))`; `int → int(float(normalize(value)))`;
  `bool → bool(value)`; `str → str(value)`; each skipped when the value is
  already of that type (`int` also skips `bool`). On `ValueError`/`TypeError`
  log `"Type coercion failed for %s.%s: value=%r, expected=%s (%s)"` and **keep
  the raw value**.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:158-175`
  - Definition of done: `"0.1"` → `0.1`; `"12"` on an `int` → `12`;
    `"abc"` on a `float` logs a warning naming class and parameter and survives
    as `"abc"` with the object still constructed.
  - Confidence: 🟢

- [ ] **T-JS-10 — Locale-aware numeric normalisation.**
  Strip; if both `.` and `,` are present the **last** separator is the decimal
  mark (`"1.234,56"` → `1234.56`; `"1,234.56"` → `1234.56`); if only `,` is
  present treat it as the decimal mark (`"0,1"` → `0.1`); otherwise unchanged.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:95-122`
  - Definition of done: all four documented cases plus a whitespace-padded input
    are covered by a table test. See T-JS-16 for the ambiguity.
  - Confidence: 🟢

### Placeholders

- [ ] **T-JS-11 — `creator_id` placeholder substitution.**
  Run **after** coercion, only when `creator_id` is a `str`;
  `re.sub(r"\{(\w+)\}", …)` substituting from the same object's coerced values; a
  value that is missing, `None`, a `dict` or a `list` leaves the token verbatim.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:212-223`
  - Definition of done: `"{wing_index}.loft"` with `wing_index = "main"` yields
    `"main.loft"`; `"{missing}.loft"` is unchanged; a `list`-valued parameter does
    not interpolate; `"{thickness}.shell"` with a stored `"0,5"` yields
    `"0.5.shell"` (proving the ordering).
  - Confidence: 🟢

### The topology format

- [ ] **T-JS-12 — The second, marker-less serialisation system.**
  `__getstate__() -> dict` plus `@staticmethod from_json_dict(data) -> Self` on
  `WingConfiguration`, `WingSegment`, `Airfoil`, `Spare`, `TrailingEdgeDevice`,
  `Turbulator`, `Servo`, `CoordinateSystem`, `AirplaneConfiguration`,
  `FuselageConfiguration` — with **no** type marker.
  - Legacy origin: `code-analysis.md` §A second, independent serialisation
    system; `CoordinateSystem.py:55-63, 101-117`;
    `AirplaneConfiguration.py:34-46`
  - Definition of done: each class round-trips through the pair; a test asserts
    that no serialised topology dict contains `$TYPE`.
  - Confidence: 🟢

- [ ] **T-JS-13 — Keep the two systems structurally separate.**
  Topology classes must **not** be importable into the `$TYPE` resolvable
  namespace, and a Creator's injected topology object must be stored privately so
  the encoder cannot emit it. The only channel between them is decoder-kwarg
  injection.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:4-7`;
    `_creator_template.py:27-29`
  - Definition of done: a test asserts that `$TYPE: "WingConfiguration"` raises;
    a test asserts that no encoded plan in the corpus contains a serialised
    topology object.
  - Confidence: 🟢

- [ ] **T-JS-17 — Plugin installation as an import side effect.**
  The serialisation module imports the CadQuery plugin package, so decoding a
  plan is sufficient to guarantee `Workplane.sewAndFix` and friends exist.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:7`
  - Definition of done: importing only the serialisation module makes the
    documented `Workplane`/`Sketch` attributes available; the dependency is
    documented rather than incidental.
  - Confidence: 🟢

### Preservation constraints

> Behaviour to **reproduce**, and defects **not** to carry forward. Nothing here
> authorises editing the legacy file (ADR 0002).

- [ ] **T-JS-14 — REPRODUCE: tolerant decoding.**
  Three tolerances are load-bearing and must survive: (a) an unknown stored key
  is dropped, so a plan written against an older Creator still decodes;
  (b) a coercion failure warns and preserves rather than aborting, so one bad
  field cannot make a stored plan unloadable; (c) a class with no annotations
  coerces nothing.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:133-136, 169-175, 206-208`
  - Definition of done: each of the three is covered by a test whose name states
    the intent, so a later "strictness" refactor has to argue with them.
  - Confidence: 🟢

- [ ] **T-JS-15 — RESOLVE: the `"factor"` string heuristic.**
  `_resolve_base_type` coerces **any** annotation string containing `"factor"`
  to `float`, regardless of the parameter's real type — the loosest rule in the
  module. It exists because `from __future__ import annotations` turns every
  annotation into a string.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:51-53`
  - Definition of done: a decision on whether to keep the heuristic or resolve
    annotations properly (e.g. `typing.get_type_hints` with the defining module's
    namespace); if kept, its scope is narrowed to the actual `Factor` alias and
    covered by a test naming the risk.
  - Confidence: 🟡

- [ ] **T-JS-16 — RESOLVE: ambiguous single-separator numerics.**
  `"1,234"` normalises to `1.234`, not `1234` — right for a `Factor` bounded to
  `[0,1]`, off by 1000× for a millimetre length. Nothing disambiguates.
  - Legacy origin: `_normalize_numeric_string` l.118-120
  - Definition of done: a decision on whether the frontend should send canonical
    numbers (making the whole normaliser unnecessary) or whether the ambiguity is
    accepted and documented; either way the chosen reading is pinned by a test.
  - Confidence: 🟢 — decided in the validation interview.

- [ ] **T-JS-18 — DO NOT REPRODUCE: in-place mutation of the parsed dict.**
  The `**kwargs` branch aliases the parsed `dic` and mutates it, making the
  object hook impure, and passes `$TYPE` through to such constructors.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:201-203`
  - Definition of done: the hook builds a fresh dict; `$TYPE` is removed before
    construction; a test asserts the input dict is unchanged.
  - Confidence: 🟢

- [ ] **T-JS-19 — DO NOT REPRODUCE: decoder options leaking into constructors.**
  The full payload — including `JSONDecoder`'s own options — is retained as the
  injection source, so a Creator declaring a parameter named `strict` or
  `parse_float` would receive the decoder's value. No current Creator does.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:187, 206`
  - Definition of done: the injection payload excludes the decoder's own
    options; a test constructs a decoder with `strict=True` and a Creator
    declaring `strict`, asserting the Creator does not receive it.
  - Confidence: 🟢

- [ ] **T-JS-20 — RESOLVE: diagnostics for undecodable plans.**
  An unknown `$TYPE` raises a bare `AttributeError` naming only the missing
  attribute — no plan id, no `creator_id`, no path into the tree. A silently
  dropped stored key produces no signal at all.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:198, 206-208`
  - Definition of done: the re-implementation raises a typed error carrying the
    `$TYPE` name and the enclosing `creator_id`; a decision is recorded on
    whether dropped keys should be logged at `debug`/`warning` (weighing it
    against T-JS-14's forward-compatibility guarantee).
  - Confidence: 🟡

- [ ] **T-JS-21 — RESOLVE: required-parameter pre-validation and signature
  caching.**
  A constructor parameter with no stored value and no default fails as a raw
  `TypeError` from `cls(**...)` with no plan context. Separately,
  `inspect.signature` and `__annotations__` are read **per object**, not per
  class — no memoisation.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:199, 224`
  - Definition of done: a decision on whether to pre-validate required
    parameters and report them with context; signature/annotation lookups are
    memoised per class if profiling on a large plan justifies it.
  - Confidence: 🟡

- [ ] **T-JS-22 — RESOLVE: `JSONStepNode` is not referenceable from a stored
  plan.**
  It is importable in Python but is not re-exported into the resolvable
  namespace, so `$TYPE: "JSONStepNode"` cannot be decoded — making sub-tree
  inclusion usable only from hand-written Python, never from the frontend plan
  editor.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:4-6`;
    `cad_designer/airplane/creator/__init__.py`
  - Definition of done: a human decides whether sub-tree inclusion is a supported
    plan feature; if yes the class joins the namespace, if no the capability is
    documented as Python-only.
  - Confidence: 🟢 — decided in the validation interview.

## Test Tasks

- [ ] **TT-JS-01 — Happy path:** a two-branch tree encodes, decodes and executes,
      producing the same shape keys as the in-memory original.
- [ ] **TT-JS-02 — Failure:** a `$TYPE` naming a non-existent class raises, with
      the agreed diagnostic (T-JS-20).
- [ ] **TT-JS-03 — Privacy:** no key starting with `_` appears in the encoded
      JSON, asserted for a Creator, a step node, a root node and a
      `JSONStepNode`.
- [ ] **TT-JS-04 — `$TYPE` value** equals the class `__name__` for every node
      type; a root node's JSON has no `"creator"` key.
- [ ] **TT-JS-05 — Plain-dict passthrough:** a nested parameter object without
      `$TYPE` survives as a dict.
- [ ] **TT-JS-06 — Bottom-up ordering:** a step node's `creator` and `successors`
      are live objects at the moment the node is constructed.
- [ ] **TT-JS-07 — Topology class not resolvable:** `$TYPE: "WingConfiguration"`
      raises.
- [ ] **TT-JS-08 — Resolvable-set snapshot:** the namespace contains exactly the
      documented classes, so an accidental import is caught.
- [ ] **TT-JS-09 — `**kwargs` branch:** a Creator with `**kwargs` receives every
      injection.
- [ ] **TT-JS-10 — Intersection branch:** a Creator without `**kwargs` receives
      only its declared parameters.
- [ ] **TT-JS-11 — Injection precedence:** an injected `wing_config` overrides a
      stored key of the same name in both branches.
- [ ] **TT-JS-12 — Unknown stored key dropped:** a plan carrying a parameter the
      current Creator no longer declares still decodes (T-JS-14a).
- [ ] **TT-JS-13 — Decoder options split:** `object_pairs_hook` reaches
      `JSONDecoder`; `wing_config` does not; and a Creator declaring `strict`
      does not receive the decoder's value (T-JS-19).
- [ ] **TT-JS-14 — Coercion table:** `str→float`, `str→int`, `str→bool`,
      `str→str`, `NewType`, `Annotated`, `confloat`, plain scalars, and the
      string form of each.
- [ ] **TT-JS-15 — Locale table:** `"0,1"`, `"1.234,56"`, `"1,234.56"`,
      `"1234"`, `"  1,5 "`, and the ambiguous `"1,234"` per T-JS-16's decision.
- [ ] **TT-JS-16 — Coercion failure is non-fatal:** `"abc"` on a `float` logs a
      warning naming class and parameter, keeps the raw value, and the object is
      still constructed (T-JS-14b).
- [ ] **TT-JS-17 — `None` and unannotated passthrough:** a `None` on a `float`
      stays `None`; an unannotated key is untouched; an unannotated class coerces
      nothing (T-JS-14c).
- [ ] **TT-JS-18 — List guard:** `"fuselage"` → `["fuselage"]`; `""` → `[]`; a
      real list passes through; a `None` on a list parameter passes through.
- [ ] **TT-JS-19 — Guard ordering regression:** moving the list guard after
      scalar resolution stringifies the list — a test that documents *why* the
      order is fixed.
- [ ] **TT-JS-20 — Placeholder matrix:** resolvable, missing, `None`-valued,
      `list`-valued, `dict`-valued; plus `"{thickness}.shell"` with `"0,5"`
      proving substitution happens after coercion.
- [ ] **TT-JS-21 — Topology round-trip:** `__getstate__` → `from_json_dict` for
      each of the ten classes, asserting no `$TYPE` is emitted.
- [ ] **TT-JS-22 — System separation:** no encoded plan in the corpus contains a
      serialised topology object.
- [ ] **TT-JS-23 — Plugin side effect:** importing only the serialisation module
      makes the documented `Workplane`/`Sketch` attributes available.
- [ ] **TT-JS-24 — Input dict unchanged:** decoding does not mutate the parsed
      JSON dict (T-JS-18).
- [ ] **TT-JS-25 — Corpus decodability:** every JSON under
      `components/constructions/` either decodes or appears in the known-broken
      allowlist (TM-JS-01).
- [ ] **TT-JS-26 — Signature drift:** a Creator that gains an optional parameter
      and one that loses an optional parameter both still decode old plans.

## Data Migration Tasks

- [ ] **TM-JS-01 — 🟢 **Delete the three undecodable plan JSONs** (`Q-CT-1`, derived from `P-DEAD-0`).**
      `wings.root.json`, `fuselage.root.json` and `full_wing.json` reference nine
      Creator classes that no longer exist: `FullWingLoftShapeCreator`,
      `FullFuselageLoftShapeCreator`, `WingRibCageCreator`,
      `ReinforcementPipesCreator`, `WingOffsetCreator`, `MirrorShapeCreator`,
      `EngineMountPanelShapeCreator`, `CPACSTrailingEdgeDeviceCreator`,
      `CPACSTrailingEdgeDeviceCutOutCreator`, `CPACSServoCutOutCreator`
      (9 of 32 `$TYPE` names). The remaining five —
      `RV-7.root.json`, `RV-7-wing.root.json`, `eHawk-wing.root.json`,
      `punisher.root.json`, `configurator-test-wing.root.json` — resolve
      cleanly. Nothing under `app/` reads the directory, so this is latent.
      **Decide: delete, migrate to surviving Creators, or archive with a
      README.** Blocked on the ownership question for the `test/` root.
- [ ] **TM-JS-02 — Add the corpus test (TT-JS-25) so this cannot regress
      silently.** 🟡 It would have caught the drift the moment a Creator was
      renamed. Requires TM-JS-01 to settle the allowlist first.
- [ ] **TM-JS-03 — Audit `construction_plans.tree_json` rows against the current
      resolvable namespace.** 🟡 The shipped files are known; **live database
      rows are not**. A one-off audit reporting every `$TYPE` in every stored
      plan that no longer resolves would size the real migration. Read-only; no
      schema change.
- [ ] **TM-JS-04 — Stored plans need a schema version.** 🟡 See TM-03.
      Today the class name is the entire compatibility contract — no version
      field, no registry, no alias table, no deprecation path — so any Creator
      rename is a breaking change to stored rows with no migration hook. Owned
      jointly with [`construction-plans`](../../construction-plans/tasks.md);
      duplicated as [`../tasks.md`](../tasks.md) TM-03.

## Suggested Order

1. **T-JS-01 → T-JS-03** first. Encoding and class resolution are the smallest
   closed loop and everything else is tested through them. T-JS-02 blocks
   [`../creator-execution-model/tasks.md`](../creator-execution-model/tasks.md)
   T-CX-09 (`JSONStepNode` cannot decode without it) and T-CX-12 (registration is
   what makes a class decodable).
2. **T-JS-04 → T-JS-05** — parameter selection and injection. T-JS-04 blocks
   T-JS-05. Implement **T-JS-18 and T-JS-19 here**, not as a later cleanup —
   retrofitting purity after the tests exist invites a test that asserts the
   broken behaviour.
3. **T-JS-07 before T-JS-08**, always. The list guard must precede scalar
   resolution in both the implementation and the test suite; write TT-JS-19
   (the ordering regression test) at the same time so the constraint is
   self-documenting.
4. **T-JS-08 → T-JS-10** — type resolution and coercion. T-JS-10 is used by
   T-JS-09 and must be table-tested independently. **Raise T-JS-16 with the
   maintainer here**, before the ambiguous case is baked into a test.
5. **T-JS-11** after coercion, since substitution consumes coerced values — the
   `"0,5"` → `"0.5.shell"` test is what pins the ordering.
6. **T-JS-14** as a review gate across steps 2–5 rather than a discrete task:
   each of the three tolerances must be covered by a test whose *name* states the
   intent, so a later strictness refactor has to argue with it.
7. **T-JS-12 → T-JS-13** — the topology format. Depends on the topology classes
   from
   [`../wingconfiguration-coordinate-system/tasks.md`](../wingconfiguration-coordinate-system/tasks.md);
   T-JS-13 is a structural assertion that belongs with them.
8. **T-JS-17** any time after T-JS-02 — small, but document the dependency
   explicitly rather than leaving it as an incidental import.
9. **T-JS-20 → T-JS-22** last, and raised with the maintainer **before** the
   corresponding code is written. T-JS-20 in particular interacts with T-JS-14:
   better diagnostics must not turn a tolerated condition into a failure.
10. **TM-JS-01 → TM-JS-04** are independent of the implementation and can run in
    parallel, but TM-JS-03 (the live-row audit) should happen **early** — it is
    the only thing that sizes the real migration risk.

## Pending Gaps

- **Should stored plans carry a schema version?** The class name is the entire
  compatibility contract; there is no registry, no alias table and no deprecation
  path, so any Creator rename silently breaks stored `tree_json` rows.
- **How many *live* database rows reference a `$TYPE` that no longer resolves?**
  The three broken shipped files are known; the state of
  `construction_plans.tree_json` in a real database is not. This is the question
  that sizes the migration.
- **Who owns `components/constructions/*.json` and the `test/` root that authored
  them?** Three of eight files are undecodable; nothing under `app/` reads them;
  the directory is excluded from ruff but not from pytest.
- **Is `"1,234"` one-point-two-three-four or one thousand two hundred
  thirty-four?** The normaliser resolves it positionally, which is right for a
  bounded `Factor` and off by 1000× for a millimetre length. Should the frontend
  send canonical numbers instead, making the normaliser unnecessary?
- **Is the `"factor" in hint_lower → float` heuristic acceptable?** It coerces
  any parameter whose annotation *string* contains "factor", regardless of its
  real type. Could `typing.get_type_hints` with the defining module's namespace
  replace the whole string branch?
- **Should a dropped stored key be logged?** The set-intersection is what makes
  plans forward-compatible, but it is indistinguishable from a typo in a
  parameter name — the Creator is simply built from defaults, silently.
- **Should sub-tree inclusion be a supported plan feature?** `JSONStepNode` is
  not in the resolvable namespace, so `$TYPE: "JSONStepNode"` cannot be decoded —
  the capability exists only from hand-written Python, never from the frontend
  plan editor.
- **Should missing required constructor parameters be pre-validated?** Today the
  failure is a raw `TypeError` from `cls(**...)` with no plan, step or parameter
  context.
