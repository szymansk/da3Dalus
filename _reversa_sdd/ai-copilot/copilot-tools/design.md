# ai-copilot / copilot-tools — Technical Design

> Use-case design. Parent module: [`../design.md`](../design.md).
> Tool contract: [`../contracts.md`](../contracts.md) §"The copilot tool
> surface".

## Interface

```python
@dataclass
class ToolEntry:
    schema: dict          # OpenAI function-calling schema, sent verbatim
    impl:   Callable      # fn(db, aeroplane_id, **kwargs) -> dict

TOOL_REGISTRY: dict[str, ToolEntry]        # 6 entries (l.828)
def list_schemas() -> list[dict]
def execute(name: str, db: Session, aeroplane_id: int, **kwargs) -> dict   # l.866

DEFAULT_ANALYSIS_TIMEOUT_S = 60.0
_READ_RETARGETED_TOOLS = {"get_design_snapshot", "get_wing_geometry", "run_analysis"}
```

| Tool | Impl | Parameters (JSON schema) |
|---|---|---|
| `get_design_snapshot` | `_get_design_snapshot` | `{}` |
| `get_wing_geometry` | `_get_wing_geometry` | `{wing?: string}` |
| `run_analysis` | `_run_analysis` | `{kind: "polar"\|"stability"}` **required** |
| `get_version_tree` | `_get_version_tree` | `{}` |
| `apply_design_edits` | `_apply_design_edits` | `{ops: array}` **required** |
| `discard_proposal` | `_discard_proposal` | `{}` |

## Main Flow

### F1 — Dispatch 🟢

```
execute(name, db, aeroplane_id, **kwargs):
    entry = TOOL_REGISTRY.get(name)
    if entry is None:
        known = ", ".join(sorted(TOOL_REGISTRY))
        return {"error": f"Unknown tool {name!r}. Known tools: {known}"}

    effective_id = _effective_target_id(db, aeroplane_id) if name in _READ_RETARGETED_TOOLS \
                   else aeroplane_id
    return entry.impl(db, effective_id, **kwargs)
```

The docstring states the invariant: *"Write tools always receive the live
`aeroplane_id` so they can find/open the proposal branch."* A retargeted write
tool would look for a proposal *of the proposal* and open a second branch. 🟢

```
_effective_target_id(db, live_id):
    try:
        branch = _find_open_proposal(db, live_id)      # copilot_apply_service
        if branch: return branch.head_id
    except Exception:
        pass                                          # 🟡 must surface (Q-CO-3)
    return live_id
```

### F2 — `_get_design_snapshot` 🟢

A one-line delegation to `versioning._metrics_payload(node)` after resolving the
node by PK. The tool therefore inherits that payload's contract *and its
quirks*: `assumption_computation_context` is present only when non-empty,
`wings[i].n_xsecs` is what the model uses for a tip-append `at_index`, and
`stability` comes from `stability_results[-1]` — the last **inserted** row. 🟡

### F3 — `_get_wing_geometry` (gh-958) 🟢

```
wing = kwargs.get("wing") or the aircraft's single/main wing
cfg  = validated WingConfig for that wing                       # millimetres
xs   = persisted WingXSecModel rows, ordered                    # metres

editable[i] per SEGMENT:
    chord_root_mm, chord_tip_mm, length_mm, sweep_mm,
    dihedral_rel_deg, incidence_deg, airfoil                    # from cfg

derived[j] per STATION:
    xyz_le_mm = xs[j].xyz_le * 1000
    chord_mm, twist_deg
    accumulated_dihedral_deg = degrees(atan2(dz, dy)) between consecutive LE points
    te_x_mm = xyz_le_mm.x + chord_mm

wing level: projected_semi_span_mm, tip_xyz_le_mm
note: "chord_root_mm is read-only — a segment's root chord follows the previous
       segment's tip chord; taper by setting chord_tip_mm"
```

The docstring is explicit that reading the **persisted** frame (rather than
re-walking the segments) is what keeps the block aligned with `cad_designer`,
whose accumulator is seeded with the *root-airfoil* dihedral — a re-walk starting
at zero would diverge. 🟢

### F4 — `_run_analysis` 🟢

```
async def run(kind):
    if kind == "polar":     return await _run_polar_async(...)
    if kind == "stability": return await _run_stability_async(...)
    return {"error": "kind must be 'polar' or 'stability'"}

try:
    return asyncio.run(asyncio.wait_for(run(kind), DEFAULT_ANALYSIS_TIMEOUT_S))
except asyncio.TimeoutError:
    return {"status": "timeout",
            "note": "analysis exceeded 60s — check the Analysis tab"}
except Exception as exc:
    return {"error": str(exc)}
```

`asyncio.run` is legal here **only** because `execute` runs inside
`asyncio.to_thread` (see [`../copilot-turn-loop`](../copilot-turn-loop/design.md)
F3). This is the single strongest coupling between the two use cases. 🟢

### F5 — `_run_polar_async` 🟢

```
alphas = linspace(-10, +15, 26)      # degrees
AeroBuildup at V = 20 m/s, h = 0
report: cl_max, cl_min, cd_min, cl_cd_max
        drag_breakdown = _polar_drag_breakdown(...)
        best_glide     ← the max CL/CD point
        min_drag       ← the min CD point
        cl_max_point   ← the max CL point
        stall          ← the post-CL_max characterisation
```

The four points are **renamed for the model** — the raw solver labels are not
what a hobbyist reads.

```
_polar_drag_breakdown(polar, ctx):
    i  = nanargmax(CL / CD)                       # NaN-safe
    ar = ctx["aspect_ratio"] ; e = ctx["e_oswald"]     # SAME source as the polar's e
    return _drag_breakdown(CL[i], CD[i], ar, e)
```

### F6 — `_drag_breakdown` 🟢

```
if cl is None or cd_total is None or ar is None or e is None: return None
if ar <= 0 or e <= 0 or cd_total <= 0:                        return None
cd_i   = cl**2 / (pi * ar * e)          # lifting-line
cd_par = cd_total - cd_i                # ONE source; never mixes snapshot cd0
if cd_i < 0 or cd_par < 0 or cd_i > cd_total:
    return {"note": "physically implausible split — reporting raw inputs",
            "cl": cl, "cd_total": cd_total, "aspect_ratio": ar, "e": e}
return {"cd_induced": cd_i, "cd_parasite": cd_par, "cl": cl, "cd_total": cd_total}
```

The comment gives the reason the function exists at all: *"the LLM is unreliable
at this arithmetic (it has produced both physically-impossible splits and 10x
errors)"*. Returning the note dict rather than a number is ADR 0012 in
miniature — a design warning beats a fabricated fallback. 🟢

### F7 — `_run_stability_async` (gh-924) 🟢

```
ctx   = node.assumption_computation_context or {}
v     = ctx.get("v_cruise_mps") or 20.0
alpha = 0.0                                  # the CRUISE design point

result = <stability solver at (alpha, v)>

# The two stability paths normalise x_np against DIFFERENT reference chords, so a
# fresh run would surface a second neutral point (0.109 m vs the dashboard's 0.080 m).
if "x_np_m" in ctx:
    x_np = ctx["x_np_m"]
    result["neutral_point_x"]  = x_np
    result["static_margin_pct"] = (x_np - ctx["cg_x"]) / ctx["mac"] * 100
return result
```

*One op-point → one neutral point.* 🟢

### F8 — The write tools

`_apply_design_edits` and `_discard_proposal` are thin wrappers over
`copilot_apply_service`; their behaviour is specified in
[`../proposal-adopt-discard`](../proposal-adopt-discard/design.md). Both catch
every exception and return `{"error": …}` after `logger.exception`. 🟢

## Alternative Flows

- **Unknown tool name:** the error carries the sorted known list. 🟢
- **`run_analysis` with a bad `kind`:** an error dict (the JSON schema's `enum`
  usually prevents it, but the impl still checks). 🟢
- **No `assumption_computation_context`:** `_polar_drag_breakdown` gets `None`
  for `AR`/`e` and the split is `None` — the polar is still returned. 🟢
- **`x_np_m` absent from the context:** the solver's own neutral point is
  reported unchanged. 🟡 Two values can then coexist in the UI — the exact
  failure the override exists to prevent.
- **`get_wing_geometry` with an unknown wing name:** `{"error": …}` listing the
  available names. 🟡
- **Aircraft with no wings:** the tool errors rather than returning empty
  blocks. 🟡
- **Retarget lookup raises:** the failure surfaces in the tool result (`Q-CO-3`). 🟡
- **Analysis over 60 s:** `{"status": "timeout"}`. 🟢

## Dependencies

- `versioning._metrics_payload` — imported despite its `_` prefix (also imported
  by `copilot_apply_service`). 🟡
- `copilot_apply_service._find_open_proposal` / `apply_edits` /
  `discard_open_proposal` / `get_or_open_proposal` / `compute_metrics_diff`.
- `aero-analysis` — AeroBuildup and the stability summary.
- `mission-and-sizing` — `assumption_computation_context` is the single source
  of `x_np_m`, `aspect_ratio`, `e_oswald`, `v_cruise_mps`, `mac`, `cg_x`.
- `wing-design` — the validated `WingConfig` and persisted `WingXSecModel`.
- **`asyncio.to_thread` from the turn loop** — the precondition for
  `asyncio.run` inside `_run_analysis`.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Curate to 6 tools rather than expose the API | module header; `TOOL_REGISTRY` | 🟢 |
| Errors are return values so the model can self-correct | BR-46 | 🟢 |
| Retarget reads, never writes | `execute:866` docstring (gh-938) | 🟢 |
| Compute the drag split in Python | `_drag_breakdown:242` comment | 🟢 |
| Report an impossible split instead of a plausible wrong one | the note dict; ADR 0012 | 🟢 |
| Take `AR` and `e` from the same context the polar used | `_polar_drag_breakdown` | 🟢 |
| Override the neutral point from the computation context | gh-924; ADR 0004 | 🟢 |
| Return mm/degrees from one tool, breaking the SI convention deliberately | module docstring | 🟢 |
| Read the persisted `xyz_le` rather than re-walking segments | `_get_wing_geometry` docstring (gh-958) | 🟢 |
| A timeout is a status, not an error | `_run_analysis` | 🟢 |
| `asyncio.run` inside a tool, enabled by the off-loop dispatch | `:609-612` + `_run_analysis` | 🟢 |

## Internal State

The tools are **stateless**. All state lives in the session, the database and
the proposal branch. The only cached value is the effective target id, recomputed
per call. 🟢

## Observability

- `logger.exception` in `_apply_design_edits` and `_discard_proposal` before
  returning their error dicts. 🟢
- 🟡 `_effective_target_id` logs **nothing** on failure — `Q-CO-3` requires the failure to surface in the tool result (derived).
- 🔴 **Not addressed by the validation interview**; at single-user scale (ADR 0024) metrics have no consumer. Left open. No tool logs its own invocation, arguments, duration or result size — the
  only trace of a tool call is the SSE event the client happened to receive and
  the `tool_calls` JSON on the persisted row.
- 🔴 Nothing counts timeouts, so the adequacy of the 60 s cap is unmeasurable. **Not addressed by the validation interview**; at single-user scale (ADR 0024) metrics have no consumer. Left open.

## Risks and Gaps

- 🟡 **`_effective_target_id` swallows every exception** (`Q-CO-3`, derived: must surface in the tool result), so "the proposal
  lookup failed" and "there is no proposal" are indistinguishable and the model
  reads the live design believing otherwise.
- 🟡 **`get_design_snapshot` inherits `stability_results[-1]`** — the last
  inserted row, not the newest by `computed_at`.
- 🟢 **The mm/degrees exception is an ADR 0019 leak and is removed** (`Q-CO-11`, `Q-CO-11`/`Q-CO-11` tool-schema units): five tools speak SI and one
  speaks mm; only the module docstring and the `note` field say so.
- 🔴 **Not addressed by the validation interview**; at single-user scale (ADR 0024) metrics have no consumer. Left open. No duration, no invocation count, no
  timeout rate.
- 🟡 **`_metrics_payload` is private**: three call sites across two modules
  depend on a `_`-prefixed function.
- 🟡 **Missing `x_np_m` silently disables the single-source guarantee**, which is
  the one case where two neutral points can still appear.
- 🟡 **The polar sweep is hard-coded** (α range, 26 points, V = 20 m/s, h = 0) —
  a 30 m/s cruise aircraft is still polared at 20 m/s.
