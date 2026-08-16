# creator-catalog — Technical Design

> Use-case design, nested under the module
> [`construction-plans`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Response schemas in full: [`../contracts.md`](../contracts.md).

## Interface

### Service surface — `app/services/construction_plan_service.py` 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `list_creators` | `()` | `list[CreatorInfo]` | entry point; `[]` on `ImportError` (l.483-504) |
| `_collect_creators` | `(cls, acc)` | `None` | recursive subclass walk; skips the three tree classes but recurses through them (l.507-553) |
| `_type_to_str` | `(annotation) -> str` | `str` | generics **before** `__name__`; strips `typing.` and `cad_designer.airplane.types.` (l.423-436) |
| `_extract_literal_values` | `(annotation)` | `list[str] \| None` | `Literal`, `Optional[Literal]`, `Annotated[Literal]`, nested unions (l.450-480) |
| `_parse_docstring_attributes` | `(docstring)` | `dict[str, str]` | `Attributes:` block; regex `(\w+)\s*\([^)]*\)\s*:\s*(.*)` (l.330-359) |
| `_parse_docstring_returns` | `(docstring)` | `list[CreatorOutput]` | `Returns:` block; keys like `{id}` / `{id}.cape` (l.362-403) |

Constants: `_INTERNAL_PARAMS` (l.257-268), `_CATEGORY_MAP` (l.406-420). 🟢

### Endpoint surface 🟢

| Method | Path | Handler (`operation_id`) | Response | Status |
|---|---|---|---|---|
| GET | `/construction-plans/creators` | `list_creators` | `list[CreatorInfo]` | 200 · 500 |

Declared **before** `/construction-plans/{plan_id}` — the in-code comment reads
*"Creator catalog (MUST be before /{plan_id} to avoid route conflict)"*
(`construction_plans.py:51-59`). 🟢

### Response schemas 🟢

| Schema | Fields |
|---|---|
| `CreatorParam` (l.68) | `name: str`, `type: str`, `default: Any \| None`, `required: bool`, `description: str \| None`, `options: list[str] \| None` |
| `CreatorOutput` (l.79) | `key: str`, `description: str` |
| `CreatorInfo` (l.86) | `class_name`, `category`, `description: str \| None`, `parameters: list[CreatorParam]`, `outputs: list[CreatorOutput] = []`, `suggested_id: str \| None` |

## Main Flow

### F1 — `list_creators` and the platform guard 🟢

```
try:
    from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
    import cad_designer.airplane.creator        # side effect: registers subclasses
except ImportError:
    return []                                    # ADR 0017 — aarch64 guard

acc: list[CreatorInfo] = []
_collect_creators(AbstractShapeCreator, acc)
return sorted(acc, key=lambda c: (c.category, c.class_name))
```

The import of `cad_designer.airplane.creator` is not decorative: subclasses only
appear in `__subclasses__()` once their defining module has executed, and that
package's `__init__.py` is what imports every subpackage
(`cad_operations`, `components`, `export_import`, `fuselage`, `wing`), each of
which re-exports its Creators explicitly. A Creator missing from its subpackage
`__init__.py` is therefore invisible here **and** undecodable in a stored plan —
the same registration rule seen from two sides. 🟢

### F2 — `_collect_creators` (l.507-553) 🟢

```
_SKIP = {"ConstructionRootNode", "ConstructionStepNode", "JSONStepNode"}

def _collect_creators(cls, acc):
    for sub in cls.__subclasses__():
        if sub.__name__ not in _SKIP:
            acc.append(_describe(sub))
        _collect_creators(sub, acc)      # recurse REGARDLESS of the skip

def _describe(cls) -> CreatorInfo:
    doc        = cls.__doc__ or ""
    description = doc.strip().splitlines()[0] if doc.strip() else None
    attr_docs   = _parse_docstring_attributes(doc)
    params      = []
    for name, p in inspect.signature(cls.__init__).parameters.items():
        if name in _INTERNAL_PARAMS:
            continue
        params.append(CreatorParam(
            name        = name,
            type        = _type_to_str(p.annotation),
            default     = None if p.default is inspect.Parameter.empty else p.default,
            required    = p.default is inspect.Parameter.empty,
            description = attr_docs.get(name),
            options     = _extract_literal_values(p.annotation),
        ))
    return CreatorInfo(
        class_name   = cls.__name__,
        category     = _category_for(cls.__module__),
        description  = description,
        parameters   = params,
        outputs      = _parse_docstring_returns(doc),
        suggested_id = getattr(cls, "suggested_creator_id", None),
    )
```

The **skip-but-recurse** shape is the important detail: the three tree classes
are themselves `AbstractShapeCreator` subclasses and must not appear as
selectable steps, but a Creator that inherits from one of them still has to be
reachable. 🟢

`_INTERNAL_PARAMS` is exactly *framework arguments* ∪ *decoder-injected kwargs*:

```
{self, loglevel, kwargs, creator_id,
 wing_config, printer_settings, servo_information,
 engine_information, component_information}                         (l.257-268)
```

so the gallery shows only what a human must supply. Note that `creator_id` is
hidden here even though the user does choose it — it is edited as the step's
identity in the plan editor, not as a Creator parameter. 🟡

### F3 — `_type_to_str` (l.423-436) 🟢

```
def _type_to_str(annotation):
    if annotation is inspect.Parameter.empty:  return "Any"
    origin = typing.get_origin(annotation)
    if origin is not None:                 # GENERICS FIRST — before __name__
        return _strip(str(annotation))     # list[X].__name__ == "list" loses [X]
    name = getattr(annotation, "__name__", None)
    return _strip(name or str(annotation))

def _strip(s):
    return s.replace("typing.", "").replace("cad_designer.airplane.types.", "")
```

The ordering is the whole point of the function: falling back to `__name__` first
would render `list[ShapeId]` as `list`, and the frontend would offer a text field
where it needs a multi-select. `NewType` aliases such as `ShapeId` and
`CreatorId` survive because their `__name__` is the alias name. 🟢

### F4 — `_extract_literal_values` (l.450-480) 🟢

```
def _extract_literal_values(annotation):
    if annotation is inspect.Parameter.empty:  return None
    origin = typing.get_origin(annotation)
    if origin is Literal:
        return [str(v) for v in typing.get_args(annotation)]
    if origin in (Union, UnionType) or is_Annotated(annotation):
        for arg in typing.get_args(annotation):
            vals = _extract_literal_values(arg)      # recurse into the wrappings
            if vals: return vals
    return None
```

Covers `Literal["a","b"]`, `Optional[Literal[...]]` (a `Union` with `NoneType`),
`Annotated[Literal[...], ...]` and nested unions. A non-literal parameter returns
`None`, which the schema keeps distinct from `[]` — the UI can then tell "no
constraint" from "an enum with no members". 🟢

This is what surfaces `cad_designer.airplane.types`'s literal aliases as
selectable option lists: `WingSides` → `["LEFT","RIGHT","BOTH"]`,
`WingSegmentType` → `["root","segment","tip"]`, `TipType` →
`["flat","round"]`, `CoordinateSystemBase` →
`["world","wing","root_airfoil","tip_airfoil"]`. 🟢

### F5 — Docstring parsing 🟢

```
_parse_docstring_attributes(doc):                                    (l.330-359)
    # locate the "Attributes:" section, then per line:
    #     name (type): free text
    m = re.match(r"(\w+)\s*\([^)]*\)\s*:\s*(.*)", line.strip())
    → {name: text}
    # the declared type in parentheses is DISCARDED — the signature is the truth

_parse_docstring_returns(doc):                                       (l.362-403)
    # locate the "Returns:" section, then per line:
    #     {id}.cape: free text
    → [CreatorOutput(key, description)]
```

Both parsers are convention-driven and enforced nowhere. A Creator whose
docstring does not follow `_creator_template.py` simply yields `None`
descriptions and an empty `outputs` list — degradation, not failure. 🟡

### F6 — Category assignment (l.406-420) 🟢

```
_CATEGORY_MAP = {
    ".creator.wing":           "wing",
    ".creator.fuselage":       "fuselage",
    ".creator.cad_operations": "cad_operations",
    ".creator.export_import":  "export_import",
    ".creator.components":     "components",
}
category = first value whose key is a substring of cls.__module__, else "other"
```

Because the mapping is by module path, moving a Creator between subpackages
silently reclassifies it in the gallery — there is no per-class override. 🟡

## Alternative Flows

- **`cad_designer` unimportable:** `[]` with HTTP 200. The gallery renders empty
  and the plan editor offers no steps; nothing signals *why*. 🟢 (the missing
  signal: 🟡)
- **A Creator with no docstring:** `description = None`, every parameter
  description `None`, `outputs = []`. No exception. 🟡 INFERRED — the code paths
  guard on an empty docstring, but a docstring with an `Attributes:` header and
  no conforming lines was not exercised.
- **A Creator whose `__init__` has no annotations:** `_type_to_str` returns
  `"Any"` and `options` is `None`; the parameter is still listed. 🟡
- **A parameter documented in `Attributes:` but absent from the signature:** the
  entry is simply never looked up — `attr_docs.get(name)` is keyed by signature
  name. Silent, harmless. 🟡
- **A parameter in the signature but absent from `Attributes:`:** `description`
  is `None`; the UI shows a field with no tooltip. 🟢
- **A Creator under an unmapped module path:** `category == "other"`, which is
  the documented catch-all. 🟢
- **Route declared after `/{plan_id}`:** `"creators"` is parsed as an integer
  path parameter and the catalog becomes unreachable — guarded only by
  declaration order and a comment. 🟢

## Dependencies

- **`cad-designer-topology`** — `AbstractShapeCreator`, the Creator subpackages
  and their `__init__.py` re-exports, the `suggested_creator_id` attribute, and
  the docstring conventions in `_creator_template.py`. Frozen (ADR 0002); this
  slice only reads them, which is why every convention here is a *reading* rule
  rather than an enforced contract.
- **`platform-core`** — the `ImportError` degradation pattern of ADR 0017. Note
  this slice implements the guard **inline** rather than via
  `cad_available()` / `Depends(require_*)`. 🟡
- **Python stdlib** — `inspect.signature`, `typing.get_origin` /
  `get_args`, `re`.
- Consumed by **`frontend-workbench`** — the Creator gallery and the parameter
  form are generated from this payload; `type` drives the input control and
  `options` drives the select.
- Consumed indirectly by **`plan-execution`** — a plan authored from this catalog
  must decode, so the catalog's visibility rule and the decoder's resolution rule
  must agree.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The gallery is generated by reflection rather than a maintained registry | `_collect_creators:507-553` | 🟢 |
| Registration in a subpackage `__init__.py` is the single visibility rule for both the gallery and the decoder | `list_creators` imports `cad_designer.airplane.creator` | 🟢 |
| The three construction-tree classes are skipped as entries but recursed through | `_collect_creators:507-553` | 🟢 |
| Framework and decoder-injected parameters are hidden from the author | `_INTERNAL_PARAMS:257-268` | 🟢 |
| Generic annotations are resolved before `__name__`, deliberately | `_type_to_str:423-436` | 🟢 |
| `options is None` and `options == []` are kept distinct | `_extract_literal_values:450-480` + schema `Optional[list[str]]` | 🟢 |
| The docstring is the documentation source; the signature is the type source | `_parse_docstring_attributes` discards the declared type | 🟢 |
| `suggested_creator_id` is returned unresolved, with its `{param}` placeholders intact | `getattr(cls, "suggested_creator_id", None)` | 🟢 |
| Category is derived from the module path, with no per-class override | `_CATEGORY_MAP:406-420` | 🟢 |
| Output is sorted explicitly rather than left in subclass-registration order | `sorted(..., key=(category, class_name))` | 🟢 |
| An absent CAD library is an empty catalog, not an error | `list_creators:483-504` (ADR 0017) | 🟢 |
| The platform guard is inline rather than the codebase's `Depends(require_*)` pattern | `list_creators:483-504` | 🟢 (intent 🟡) |

## Internal State

Entirely stateless. The catalog is recomputed on every request — there is no
cache, no memoisation and no invalidation, so a hot-reloaded Creator module is
picked up on the next call.

The one piece of implicit state is Python's own subclass registry: what appears
in the catalog depends on **which modules have been imported in this process**.
Since `list_creators` performs the import itself, the first call is what
populates it, and the result is stable thereafter. 🟡

## Observability

- No logging at all on this path — a Creator that fails to describe (an
  unparseable signature, an exotic annotation) would raise into the endpoint's
  `_handle_service_error` and surface as a **500** with a `detail` string, since
  no `ServiceException` subtype is involved. 🟡
- The `ImportError` degradation is **silent**: an empty gallery on a machine
  without CadQuery is indistinguishable from a genuinely empty Creator set. No
  log line, no marker in the response. 🔴
- No metric for catalog size or build time; the reflection cost is paid per
  request with no visibility.

## Risks and Gaps

- 🔴 **Silent platform degradation.** `ImportError` → `[]` with a 200 gives the
  user an empty plan editor and no explanation. Every other capability-gated
  route in the codebase returns a clean 503 naming the missing capability
  (ADR 0017); this one deliberately does not, because an empty gallery is
  survivable — but nothing tells the client which case it is in.
- 🔴 **The route ordering is protected only by a comment.** Moving the
  declaration below `/{plan_id}` silently makes the catalog unreachable, and the
  failure looks like a 422 on an integer parse rather than a routing bug.
- 🟡 **Docstring conventions are unenforced.** `_creator_template.py` documents
  the `Attributes:` / `Returns:` blocks and `suggested_creator_id`, but nothing
  validates them. A Creator author can ship an undocumented parameter and the
  gallery will render a bare field with no tooltip and no type help. Enforcement
  would have to live in `cad-designer-topology`, which is frozen (ADR 0002).
- 🟡 **A single malformed class can 500 the whole catalog.** There is no per-class
  `try/except` inside `_collect_creators`, so an annotation that
  `typing.get_origin` cannot handle takes the entire endpoint down rather than
  omitting one entry.
- 🟡 **Category is positional.** Moving a Creator to another subpackage
  reclassifies it in the UI with no per-class override and no deprecation path.
- 🟡 **`creator_id` is hidden although the user does choose it.** It is edited as
  the step's identity in the plan editor rather than as a parameter — a
  reasonable split, but it means the catalog is not a complete description of
  what a step needs.
- 🟡 **No caching.** The full reflection walk runs per request. Harmless at 29
  Creators; it is a hidden cost that grows with the library.
- 🟡 **The declared type inside `Attributes:` parentheses is discarded**, so a
  docstring whose declared type disagrees with the signature is never flagged —
  the mismatch is invisible to both the author and the user.
