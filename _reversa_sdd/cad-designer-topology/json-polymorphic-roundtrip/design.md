# json-polymorphic-roundtrip — Technical Design

> Use-case design, nested under the module
> [`cad-designer-topology`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Format specification in full: [`../contracts.md`](../contracts.md) §3–§4.
> Sibling slices: [`../creator-execution-model/`](../creator-execution-model/design.md),
> [`../wingconfiguration-coordinate-system/`](../wingconfiguration-coordinate-system/design.md).
>
> ⚠ `GeneralJSONEncoderDecoder.py` is **FROZEN** (ADR 0002).

## Interface

### `cad_designer/airplane/GeneralJSONEncoderDecoder.py` (224 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `GeneralJSONEncoder.JSON_CLASS_TYPE_ID` | class attribute | `'$TYPE'` | l.18 |
| `GeneralJSONEncoder.default` | `(o)` | `dict` | public attributes + `$TYPE` (l.20-25) |
| `GeneralJSONDecoder.__init__` | `(*args, **kwargs)` | — | splits `kwargs` into `JSONDecoder`'s own parameters and the injection payload (l.180-191) |
| `GeneralJSONDecoder.object_hook` | `(dic: dict)` | object \| `dict` | class resolution → parameter selection → coercion → placeholders → construct (l.193-224) |
| `_resolve_base_type` | `(hint)` | `type \| None` | unwraps string annotations, `NewType`, `Annotated`, `confloat` (l.28-84) |
| `_is_list_type` | `(hint)` | `bool` | real and string annotations (l.87-92) |
| `_normalize_numeric_string` | `(value)` | `str` | locale-aware decimal normalisation (l.95-122) |
| `_coerce_params` | `(cls, params: dict)` | `dict` | applies the above per parameter (l.125-176) |

Module-level imports (l.4-7) are **load-bearing**, not incidental — they define
the resolvable class universe and install the CadQuery monkey-patches. The file
carries a comment saying exactly that (l.10-11):
*"even though this imports may not be referenced directly they are needed as we
use inspection, where they are called"*. 🟢

### The topology format (second system) 🟢

| Symbol | Signature | Note |
|---|---|---|
| `<TopologyClass>.__getstate__` | `()` → `dict` | plain, JSON-safe, **no type marker** |
| `<TopologyClass>.from_json_dict` | `(data: dict)` → `Self` | `@staticmethod` |
| `AirplaneConfiguration.to_dict` / `save_to_json` / `save_to_zip` | — | envelopes layered on top |

Implemented by `WingConfiguration`, `WingSegment`, `Airfoil`, `Spare`,
`TrailingEdgeDevice`, `Turbulator`, `Servo`, `CoordinateSystem`,
`AirplaneConfiguration`, `FuselageConfiguration`. There is **no shared base
class and no marker** — the reader must already know the target type, which is
why this format only appears at endpoints whose schema fixes the type. 🟢

## Main Flow

### F1 — Encoding 🟢

```
json.dumps(root_node, cls=GeneralJSONEncoder)

GeneralJSONEncoder.default(o):                       # l.20-25
    dic = {k: v for k, v in o.__dict__.items() if not k.startswith('_')}
    dic["$TYPE"] = o.__class__.__name__
    return dic
```

`default` is only invoked for objects the standard encoder cannot serialise, so
scalars, lists and dicts inside a node pass through untouched. The recursion is
the encoder's own: a node's `successors` `OrderedDict` is serialised as a plain
JSON object whose values are themselves encoded through `default`. 🟢

What this excludes, by design:

| Attribute | Class | Why it must not be stored |
|---|---|---|
| `_shapes_of_interest_keys` | `AbstractShapeCreator` | reconstructed by the constructor from public parameters |
| `_output_shapes` | `ConstructionRootNode` | runtime state |
| `_to_be_injected` | `JSONStepNode` | runtime config |
| `_config`-style fields | any Creator | injected at decode time; storing them would pin a plan to one aircraft |

### F2 — Decoder construction 🟢

```
GeneralJSONDecoder(*args, **kwargs):                 # l.180-191
    self.kwargs = kwargs                             # the FULL payload
    init_params = inspect.signature(JSONDecoder.__init__).parameters
    intersection = {k: self.kwargs[k] for k in self.kwargs.keys() & init_params.keys()}
    JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **intersection)
```

The same set-intersection idiom used later for constructors: only the arguments
`JSONDecoder` actually declares (`object_pairs_hook`, `parse_float`,
`parse_int`, `strict`, …) are forwarded, while the whole payload is retained for
injection. 🟡 Note `self.kwargs` keeps **everything**, including any
`JSONDecoder` options — so a Creator declaring a parameter named `strict` would
receive the decoder's value.

### F3 — Decoding one object 🟢

```
object_hook(dic):                                    # l.193-224

  1. if "$TYPE" not in dic: return dic               # plain dict passthrough

  2. cls = getattr(sys.modules[__name__], dic["$TYPE"])        # AttributeError if absent
     init_params = inspect.signature(cls.__init__).parameters

  3. if "kwargs" in init_params:
         intersection_dict = dic                     # ← alias, then mutated in place 🟡
         intersection_dict.update(self.kwargs)
     else:
         intersection  = {k: self.kwargs[k] for k in self.kwargs.keys() & init_params.keys()}
         intersection_dict = {k: dic[k]     for k in dic.keys()         & init_params.keys()}
         intersection_dict.update(intersection)      # injections win

  4. intersection_dict = _coerce_params(cls, intersection_dict)

  5. if isinstance(intersection_dict.get("creator_id"), str):
         intersection_dict["creator_id"] = re.sub(r"\{(\w+)\}", _replace_placeholder,
                                                  intersection_dict["creator_id"])

  6. return cls(**intersection_dict)
```

`object_hook` fires **bottom-up** — Python's JSON parser calls it on the
innermost objects first — so by the time a `ConstructionStepNode` dict is
processed, its `creator` value is already a live Creator and its `successors`
values are already live nodes. No second pass is needed. 🟢

The `$TYPE` key itself is **not** removed from `dic` in step 3's `**kwargs`
branch, so a class accepting `**kwargs` receives `$TYPE` among them. 🟡 Harmless
for the two node classes (which swallow `**kwargs`), but a Creator with
`**kwargs` that inspects its keys would see it.

### F4 — Parameter coercion 🟢

```
_coerce_params(cls, params):                         # l.125-176
  try:    raw_hints = {k: v for k, v in cls.__init__.__annotations__.items() if k != "return"}
  except AttributeError: return params               # unannotated class → no coercion at all

  for key, value in params.items():
      if value is None or key not in raw_hints:
          keep; continue

      hint = raw_hints[key]

      if _is_list_type(hint) and isinstance(value, str):
          → [value] if value.strip() else []         # ← the guard, BEFORE type resolution
          continue
      if _is_list_type(hint) and not isinstance(value, list):
          keep; continue

      target = _resolve_base_type(hint)
      if target is None: keep; continue

      try:
          float → float(_normalize_numeric_string(value))   if not already float
          int   → int(float(_normalize_numeric_string(value))) if not already int/bool
          bool  → bool(value)                                if not already bool
          str   → str(value)                                 if not already str
      except (ValueError, TypeError) as exc:
          logging.warning("Type coercion failed for %s.%s: value=%r, expected=%s (%s)", ...)
          keep raw value
```

Ordering is the whole design here. `_resolve_base_type(list[str])` returns
`str`, because its `__origin__` branch recurses into `__args__[0]` — so without
the list guard running first, a genuine list parameter would be stringified.
🟢 The guard is documented in the source with exactly that rationale
(l.144-146: *"This prevents iterating over characters of a string when the code
expects a list of shape keys."*).

`_resolve_base_type` (l.28-84) resolves in this order:

| Input form | Handling |
|---|---|
| `str` annotation (from `from __future__ import annotations`) | case-insensitive prefix matching: `"float"`/`"confloat…"` → `float`; `"int"`/`"nonnegativeint"`/`"conint…"` → `int`; `"bool"` → `bool`; `"str"` → `str`; `"creatorid"`/`"shapeid"` → `str`; **any** hint containing `"factor"` → `float`; `"annotated[...]"` → parse the first argument |
| `NewType` | `hint.__supertype__` |
| generic / `Annotated` | recurse into `__args__[0]` |
| plain `float`/`int`/`bool`/`str` | itself |
| anything else | `None` → no coercion |

🟡 The string branch exists because most Creator modules use
`from __future__ import annotations`, which turns every annotation into a
string and defeats normal introspection. It is a heuristic, and the
`"factor" in hint_lower` rule is the loosest part of it.

### F5 — Locale-aware numeric normalisation 🟢

```
_normalize_numeric_string(value):                    # l.95-122
  s = str(value).strip()
  has_dot, has_comma = "." in s, "," in s

  if has_dot and has_comma:
      # the LAST separator is the decimal mark
      if s.rfind(",") > s.rfind("."):  s = s.replace(".", "").replace(",", ".")   # 1.234,56
      else:                            s = s.replace(",", "")                     # 1,234.56
  elif has_comma and not has_dot:
      s = s.replace(",", ".")                                                     # 0,1
  return s
```

| Input | Output | Interpretation |
|---|---|---|
| `"0,1"` | `"0.1"` | comma as decimal |
| `"1.234,56"` | `"1234.56"` | German: dot = thousands |
| `"1,234.56"` | `"1234.56"` | English: comma = thousands |
| `"1234"` | `"1234"` | no separator |
| `"  1,5 "` | `"1.5"` | stripped first |

🟡 Ambiguous inputs resolve by position, not by locale detection: `"1,234"`
(one separator, comma) becomes `1.234`, not `1234`. For a `Factor` bounded to
`[0,1]` that is the safer reading; for a length in millimetres it is off by
1000×. Nothing disambiguates.

### F6 — Placeholder substitution 🟢

```
if "creator_id" in intersection_dict and isinstance(..., str):    # l.212-223
    def _replace_placeholder(m):
        val = intersection_dict.get(m.group(1))
        if val is not None and not isinstance(val, (dict, list)):
            return str(val)
        return m.group(0)                            # keep unresolved

    intersection_dict["creator_id"] = re.sub(r"\{(\w+)\}", _replace_placeholder, ...)
```

It runs **after** coercion, so `"{thickness}.shell"` with a stored `"0,5"`
interpolates as `"0.5.shell"`, not `"0,5.shell"`. The `\w+` pattern means a
placeholder can only name a simple identifier. Unresolvable tokens survive
verbatim, producing an identifier containing braces — which then becomes a shape
key no other step can reference by hand. 🟢

### F7 — The topology format 🟢

```
obj.__getstate__()          → plain dict, no marker
Class.from_json_dict(data)  → Class          @staticmethod
```

Used at two boundaries:

| Boundary | Direction | Owner |
|---|---|---|
| `GET/PUT /aeroplanes/{id}/wings/{name}/wingconfig`, `POST .../from-wingconfig` | both, in **millimetres** | [`wing-design`](../../wing-design/contracts.md) |
| `AirplaneConfiguration.to_dict()` / `save_to_json` / `save_to_zip` | out only | [`aeroplane-core`](../../aeroplane-core/contracts.md) |

The two systems are kept apart structurally: a topology class is not in the
`$TYPE` resolvable namespace, and a Creator stores its injected topology object
privately, so the encoder cannot emit it. The only channel is the decoder-kwarg
injection of F3 step 3. 🟢

One asymmetry worth recording: `CoordinateSystem.__getstate__` emits
`euler_xyz`, but `from_json_dict` ignores it and recomputes from the direction
vectors — see
[`../wingconfiguration-coordinate-system/design.md`](../wingconfiguration-coordinate-system/design.md)
§F2. 🟢

## Alternative Flows

- **Dict without `$TYPE`** — returned unchanged, which is how nested parameter
  objects and the `successors` map survive. 🟢
- **Unknown `$TYPE`** — `AttributeError` from `getattr`. Not a domain error, so
  `construction-plans` wraps it into
  `ValidationError("Failed to decode construction plan: …")` → 422. 🟢
- **Topology class named as `$TYPE`** — same `AttributeError`; they are
  deliberately not importable into the namespace. 🟢
- **Class with no `__init__` annotations** — `_coerce_params` catches
  `AttributeError` and returns the parameters untouched; every value stays as
  JSON produced it. 🟢
- **`None` value or unannotated key** — passed through, so a `None` default is
  never coerced into `0.0` or `"None"`. 🟢
- **Uncoercible value** — warning logged, raw value kept, object constructed
  anyway. The failure surfaces later inside the Creator as a `TypeError`, or not
  at all if the parameter is unused on that path. 🟡
- **Stored key the constructor no longer declares** — dropped by the
  set-intersection, so an old plan decodes against a newer Creator. 🟢
- **Constructor parameter with no stored value and no default** — `TypeError:
  missing required positional argument`, raised from `cls(**...)`. 🟡 Nothing
  pre-validates required parameters.
- **Injected kwarg colliding with a stored value** — the injection wins in both
  branches. 🟢
- **Creator declaring a parameter named like a `JSONDecoder` option**
  (`strict`, `parse_float`, …) — it would receive the decoder's value from
  `self.kwargs`. 🟡 No occurrence found in the current Creator set.
- **Unresolvable placeholder** — left verbatim in `creator_id`. 🟢
- **CadQuery absent** — the module's own `import cad_designer.cq_plugins`
  raises `ImportError` at import time, so decoding is unavailable rather than
  degraded (ADR 0017). 🟢

## Dependencies

- **stdlib** — `json` (`JSONEncoder` / `JSONDecoder`), `inspect`, `re`, `sys`,
  `typing`, `logging`.
- **pydantic** — indirectly: `confloat`-derived annotations are what
  `_resolve_base_type` unwraps.
- **`cad_designer.airplane.creator`** — the star-import that populates the
  resolvable namespace; **`ConstructionRootNode` / `ConstructionStepNode`** for
  the two node types.
- **`cad_designer.cq_plugins`** — imported for its monkey-patching side effect,
  which is why decoding a plan guarantees `Workplane.sewAndFix` exists.
- **CadQuery** — transitively, via all of the above.
- **Consumers:** `construction-plans` (`execute_plan` /
  `execute_plan_streaming` decode `tree_json` with the five injections;
  `_migrate_tree_json` and `_rewrite_export_paths` pre-process the raw dict
  **before** decoding), `cad-generation` (`build_wing_blueprint` synthesises
  this dialect in memory, then the worker decodes it), `JSONStepNode` (decodes a
  sub-tree at construction time), and the `test/` scripts that authored the
  shipped plan files.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Polymorphism by class **name**, resolved with `getattr` on one module namespace | `GeneralJSONEncoderDecoder.py:18-25, 196-198` | 🟢 |
| No schema version, no registry, no alias table — the name is the whole contract | absence of any version field; BR-71 | 🟢 |
| The resolvable universe is defined by **imports**, which doubles as the registration mechanism for new Creators | l.4-7 + the module comment l.10-11 | 🟢 |
| Privacy (`_` prefix) is the mechanism for excluding runtime config from storage | encoder l.22; `_creator_template.py:27-29` | 🟢 |
| Runtime config is **injected** at decode time, making a plan portable between aircraft | `object_hook` l.203, l.210 | 🟢 |
| Injections override stored values rather than the reverse | l.203, l.210 | 🟢 |
| Set-intersection of stored keys with constructor parameters, so plans survive signature drift | l.206-208 | 🟢 |
| `**kwargs` in a constructor deliberately opts into receiving everything | l.201-203 | 🟢 |
| Decoding is **tolerant**: coercion failures warn and preserve rather than abort | l.169-175 | 🟢 |
| Locale-aware numeric parsing, because the frontend submits raw form strings | l.95-122 | 🟢 |
| The list guard is ordered before type resolution, deliberately | l.144-152 + the source comment | 🟢 |
| String annotations are handled heuristically, because `from __future__ import annotations` defeats introspection | `_resolve_base_type` l.39-65 | 🟢 |
| Placeholders resolve after coercion, so they interpolate normalised values | l.211-223 | 🟢 |
| Topology objects use a **separate**, marker-less format and never enter a plan JSON | `__getstate__`/`from_json_dict` + injection-only channel | 🟢 |
| Importing the serialisation module installs the CadQuery extensions | l.7 | 🟢 |

## Internal State

- **Per decoder instance** — `self.kwargs`: the full injection payload, held for
  the lifetime of one `json.loads` call and consulted for every object. It is
  never mutated. 🟢
- **Per decoded object** — `intersection_dict`, a transient parameter map. 🟡 In
  the `**kwargs` branch it is an **alias of the parsed `dic`**, which is mutated
  in place, so `object_hook` is not pure. The parsed dict is discarded
  immediately afterwards, so the impurity is currently unobservable.
- **No caching.** Class resolution, signature inspection and annotation reading
  happen per object, not per class — `inspect.signature` is called once for
  every node in the tree. 🟡 A measurable cost only for very large plans; no
  memoisation exists.
- **No persistent state.** The module holds no registry, no cache and no
  configuration. 🟢

## Observability

- **Coercion warnings** are the only diagnostic this slice emits:
  `"Type coercion failed for %s.%s: value=%r, expected=%s (%s)"` (l.171-174),
  naming the class, the parameter, the offending value, the expected type and
  the underlying exception. Well-formed and actionable. 🟢
- 🟡 **An unknown `$TYPE` must produce a diagnostic naming the plan, step and type** (`P-WARN-0`). Today a bare `AttributeError` naming only the
  missing attribute — no plan id, no `creator_id`, no path into the tree. For
  the shipped corpus this means "one of the nine deleted Creators" without
  saying which node referenced it. `construction-plans` re-wraps it with a
  generic message.
- 🟡 Must emit a `DesignWarning` rather than failing silently (`P-WARN-0`). Previously a silently dropped stored key produced no signal at all. The
  set-intersection is what makes plans forward-compatible, but it is
  indistinguishable from a typo in a parameter name — the Creator is simply
  constructed with its default.
- **No metrics, no timing, no decode counters.** 🟢

## Risks and Gaps

- 🟡 **BR-71 has already bitten: nine deleted Creator classes** are still
  referenced by `components/constructions/{wings.root.json, fuselage.root.json,
  full_wing.json}` (9 of 32 `$TYPE` names). Latent — nothing under `app/` reads
  that directory — but the files ship in the repository and fail on any load.
- 🟡 **There is no schema version on stored plans.** The class name is the
  entire compatibility contract, so any Creator rename is a breaking change to
  `construction_plans.tree_json` rows with no migration hook, no alias table and
  no deprecation path.
- 🟡 Must emit a `DesignWarning` rather than failing silently (`P-WARN-0`). Previously a typo in a stored parameter name was silently dropped, producing a
  Creator built from defaults rather than an error.
- 🟡 **Unknown-`$TYPE` diagnostics carry no context** (`P-WARN-0`) — no plan, no step, no
  path.
- 🟡 **`_resolve_base_type`'s string branch is heuristic.** Any annotation string
  containing `"factor"` resolves to `float`, regardless of the parameter's actual
  type — the loosest rule in the module.
- 🟡 **Locale normalisation is positional, not locale-aware.** `"1,234"` becomes
  `1.234`; for a `Factor` that is right, for a millimetre length it is off by
  1000×, and nothing disambiguates.
- 🟡 **`object_hook` mutates the parsed dict** in the `**kwargs` branch, and
  passes `$TYPE` through to such constructors.
- 🟡 **`self.kwargs` retains `JSONDecoder`'s own options**, so a Creator
  declaring a parameter named `strict` or `parse_float` would receive the
  decoder's value. No current Creator does.
- 🟡 **Missing required constructor parameters are not pre-validated** — the
  failure is a raw `TypeError` from `cls(**...)` with no plan context.
- 🟡 **`inspect.signature` is called per object**, not per class; no memoisation.
- 🟡 **`JSONStepNode` is not in the resolvable namespace**, so it cannot be
  referenced as a `$TYPE` from a stored plan unless imported elsewhere in the
  chain — which makes it usable only from hand-written Python, not from the
  frontend plan editor.
- 🟢 **The two serialisation systems are separated structurally, not by
  convention** — topology classes are simply not importable into the resolvable
  namespace. Robust, and worth preserving deliberately in any re-implementation.
