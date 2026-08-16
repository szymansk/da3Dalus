# Flowcharts — openvsp-import

## 1. End-to-end pipeline

```mermaid
flowchart TD
    A["POST /api/v2/import/openvsp  (multipart .vsp3)<br/>or /api/v2/import/openvsp/stream"] --> B["NamedTemporaryFile"]
    B --> C["import_openvsp_file(db, path, target_span_m?, scale_factor?, name?)"]
    C --> D["import_vsp3 — pct 5"]
    D --> E["source-unit detection (gh-808) — pct 16"]
    E --> F["_resolve_scale_factor + _scale_aeroplane_lengths — pct 18"]
    F --> G["_persist_aeroplane — pct 20…90"]
    G --> H["OpenVspImportResponse<br/>{uuid, name, n_wings, n_fuselages,<br/>n_weight_items, warnings[], lossy_components[]}"]
    B --> Z["finally: asyncio.to_thread(unlink)"]

    subgraph V["import_vsp3 — the critical sequence (gh-640)"]
        D1["_ensure_handlers_loaded — lazy, ONCE per process"]
        D2["vsp.ClearVSPModel()"]
        D3["vsp.ReadVSPFile(path)"]
        D4["_read_source_length_unit — FindParm 'LengthUnit'/'Vehicle_Info'<br/>returns None on OpenVSP 3.50+"]
        D5["if hasattr(vsp,'SetLengthUnit'): SetLengthUnit(LEN_M)  — legacy only"]
        D6["vsp.Update()"]
        D7["for gid in FindGeoms(): dispatch"]
        D8["for fn in _POST_PASSES: fn(aeroplane, ctx, vsp)"]
        D1 --> D2 --> D3 --> D4 --> D5 --> D6 --> D7 --> D8
    end
    D -.- V
```

## 2. Geom dispatch and the canonical type token

```mermaid
flowchart TD
    A["vsp.GetGeomTypeName(gid) → Title-Case display name"] --> B["_canonicalize_geom_type<br/>_DISPLAY_TO_CANONICAL, else .upper()"]
    B --> C{"_HANDLERS.get(token)"}
    C -->|WING| H1["openvsp_wing_handler._handle_wing"]
    C -->|FUSELAGE| H2["openvsp_fuselage_handler._handle_fuselage"]
    C -->|BLANK| H3["openvsp_blank_handler._handle_blank"]
    C -->|CUSTOM| H4["openvsp_custom_handler._handle_custom"]
    C -->|none| U["ctx.add_warning(_UNSUPPORTED_REASONS[token]<br/>or 'not supported in Phase 1') + ctx.mark_lossy(gid)"]

    N["'Wing'→WING, 'Fuselage'→FUSELAGE, 'BodyOfRevolution'→BOR,<br/>'Propeller'→PROP, … (16 entries).<br/>AddGeom / GetGeomTypes use the UPPERCASE tokens,<br/>GetGeomTypeName does not — verified on OpenVSP 3.50.4."]
    B -.- N

    P["registered post-passes:<br/>blank._resolve_vehicle_cg · fuselage._drop_degenerate_fuselages"]
    D["ss_control._post_pass is NOT registered —<br/>_ensure_handlers_loaded never imports the module"]
    D8["_POST_PASSES"] --> P
    D8 -.-|"missing"| D
```

## 3. The adapter and its module-level state

```mermaid
flowchart TD
    A["openvsp_adapter._attempt_import()"] --> B{"_import_attempted?"}
    B -->|yes| B1["return _cached_module (may be None)"]
    B -->|no| C["importlib.import_module('openvsp')"]
    C -->|ok| C1["_cached_module = module"]
    C -->|ImportError| C2["_cached_module = None; _import_error = exc"]
    C1 --> D["is_available() / get_vsp()"]
    C2 --> D
    D -->|"module None"| E["ImportError(_OPENVSP_MISSING_MSG)<br/>3 documented install paths"]
    F["reset_for_tests() — the only way to clear the memo"]

    G["Module-level state that survives uvicorn --reload:<br/>· adapter: _cached_module / _import_attempted / _import_error<br/>· importer: _handlers_loaded / _HANDLERS / _POST_PASSES<br/>· the openvsp SWIG module's own native VSP model<br/>→ restart the process after changing importer code"]
    A -.- G
```

## 4. Wing handler — planform derivation

```mermaid
flowchart TD
    A["XSec_1.Root_Chord"] -->|"&le; 0"| A1["warning + default 1.0 m"]
    A --> B["xsec[0] = {xyz_le:[0,0,0], chord:root_chord,<br/>twist:0, x_sec_type:'root'}"]
    B --> C["read per-wing RelativeDihedralFlag / RelativeTwistFlag (gh-755)"]
    C --> D["for i in 1..n_sec:  group XSec_i (fallback XSec_{i-1})"]
    D --> E["Span, Tip_Chord, Sweep, Sweep_Location, Dihedral, Twist"]
    E --> F{"Span &le; 0?"}
    F -->|yes| F1["warning + mark_lossy + skip the section"]
    F -->|no| G["dihedral: relative → cum += parm ; absolute → cum = parm<br/>twist:    relative → cum += parm ; absolute → cum = parm"]
    G --> H["le_sweep = sweep_at_le(Sweep, Sweep_Location, Span, c_root, c_tip)"]
    H --> I["cum_x += Span · tan(le_sweep)<br/>cum_y += Span · cos(cum_dihedral)<br/>cum_z += Span · sin(cum_dihedral)"]
    I --> J["xsec[i] = {xyz_le:[cum_x,cum_y,cum_z], chord:Tip_Chord,<br/>twist:cum_twist, x_sec_type: 'segment' or None on the last}"]

    K["sweep reference change:<br/>tan(Λ_to) = tan(Λ_from) − (xref_to − xref_from)·(c_root − c_tip)/span<br/>returns Λ_from unchanged when span ≤ 0"]
    H -.- K

    L["XForm group: X/Y/Z_Location, X/Y/Z_Rotation<br/>Sym group: Sym_Planar_Flag → wing.symmetric<br/>EndCap group: cap flags for the tip"]
    D -.- L
```

## 5. Airfoil resolution — `import_airfoil_from_xsec`

```mermaid
flowchart TD
    A["vsp.GetXSecShape(xs_id)"] --> B{"shape"}
    B -->|XS_FOUR_SERIES| C1["naca_4series_name(Camber, CamberLoc, ThickChord)<br/>+ ensure_naca4_dat  (gh-700)"]
    B -->|XS_FOUR_DIGIT_MOD| C2["same name + '-mod' suffix, plain 4-digit .dat<br/>(no MeanLine_a parm exists — verified 3.50)"]
    B -->|XS_FIVE_DIGIT| C3["naca_5series_name(Camber, CamberLoc, Reflex, ThickChord)<br/>+ ensure_naca5_dat  (gh-733)"]
    B -->|XS_FIVE_DIGIT_MOD| C4["same + '-mod', base 5-digit .dat"]
    B -->|XS_SIX_SERIES| C5["naca_6series_name(Series, IdealCl, ThickChord, A)<br/>a-family mean line + 4-digit thickness<br/>+ info warning: t/c and design Cl exact, shape approximated"]
    B -->|XS_ONE_SIX_SERIES| C6["naca_16series_name(IdealCl, ThickChord)<br/>a = 1.0 mean line + 4-digit thickness + info warning"]
    B -->|XS_FILE_AIRFOIL| C7["_export_selig — verbatim"]
    B -->|XS_CST_AIRFOIL| C8["info warning + _export_selig(tag='vsp_imported_cst')"]
    B -->|other| C9["warning + _export_selig(tag='vsp_imported_unknown')<br/>last resort ./components/airfoils/naca0012.dat"]

    D["write_imported_airfoil_dat:<br/>_dedup_consecutive_points(tol=1e-9) → gh-789<br/>then content hash → skip the write if identical"]
    C7 --> D
    C8 --> D
    C9 --> D

    E["_NACA_DAT_HALF_POINTS = 80 (cosine-spaced half surface)"]
    C1 -.- E

    F["morph_airfoils(ref_a, ref_b, t):<br/>Kulfan/CST fit both, blend weights, rebuild;<br/>_raw_blend fallback when the fit fails  (gh-796)"]
```

## 6. SS_CONTROL → TrailingEdgeDevice (registered nowhere)

```mermaid
flowchart TD
    A["_post_pass over ctx.wing_geom_ids"] --> B["vsp.GetSubSurfIDVec(wing_gid)"]
    B --> C{"GetSubSurfType(sid) == SS_CONTROL?"}
    C -->|no| C1["skip"]
    C -->|yes| D["grp = 'SS_Control_{index+1}'"]
    D --> E{"LE_Flag &ge; 0.5?"}
    E -->|yes| E1["info warning — LE devices out of scope, skip"]
    E -->|no| F{"EtaFlag &ge; 0.5?"}
    F -->|yes| F1["u_start/u_end = EtaStart / EtaEnd"]
    F -->|no| F2["u_start/u_end = UStart / UEnd"]
    F1 --> G
    F2 --> G["rel_chord_root = 1 − Length_C_Start<br/>rel_chord_tip  = 1 − Length_C_End<br/>(VSP measures from the TE, we from the LE)"]
    G --> H["deflection_deg = Deflection ; role = OTHER ;<br/>symmetric inherited from the wing"]
    H --> I["u_mid → _u_to_segment_index(u, n_sec) → xsec_idx = seg−1"]
    I --> J{"that xsec already has a TED?"}
    J -->|yes| J1["warning: only the first SS_CONTROL per segment is imported"]
    J -->|no| J2["attach"]

    X["register() is called only from app/tests/test_openvsp_ss_control.py.<br/>_ensure_handlers_loaded imports wing/fuselage/blank/custom only,<br/>so in production this pass never runs and control surfaces<br/>are silently absent from an imported aeroplane."]
    A -.- X
```

## 7. Source-unit detection (gh-808) and the scaling order

```mermaid
flowchart TD
    A["fuselages present?"] -->|no| A1["skip — import unchanged"]
    A -->|yes| B["ref = fuselage with the largest handler X-span"]
    B --> C["export_geom_step(ref) → metric STEP<br/>(STEPSettings.LenUnit forced to LEN_M)"]
    C --> D["cq.importStep(...).BoundingBox().xlen / 1000 = metric_span_m<br/>(OCC normalises STEP to mm)"]
    D --> E["ratio = metric_span / handler_span"]
    E --> F["_snap_to_unit_scale — ±2 % of<br/>{m:1, yd:0.9144, ft:0.3048, in:0.0254, cm:0.01, mm:0.001}"]
    F -->|"None or 'm'"| F1["leave unchanged"]
    F -->|"non-metre"| G["_convert_aeroplane_to_metres(factor)<br/>wings + fuselages + xyz_ref + weight-item positions"]
    G --> H["warning severity=warning: 'converted to metres (×f). Verify the scale.'"]
    C --> I["finally: rmtree the throwaway _unitdetect_* STEP dir"]

    J["ORDER MATTERS:<br/>1. unit conversion (whole aeroplane)<br/>2. _resolve_scale_factor + _scale_aeroplane_lengths<br/>   — wings, xyz_ref, weight positions only<br/>3. fuselage xsecs scaled later in _persist_aeroplane,<br/>   AFTER the slicer refinement runs in the unscaled STEP frame (gh-765)"]
    G -.- J

    K["mutex: target_span_m XOR scale_factor<br/>scale_factor ∈ (0.001, 10.0) · target_span_m ∈ (0.1, 50.0) m<br/>violation → ScaleValidationError → HTTP 400 / 422<br/>masses are NEVER scaled — info warning says so"]
```

## 8. Fuselage refinement gates and STEP artefacts

```mermaid
flowchart TD
    A["_persist_aeroplane, per fuselage"] --> B["export_geom_step (gh-729) → step_path"]
    B --> C["sew_imported_geom_to_solid (gh-731) → solid_step_path"]
    C --> C1["BRepBuilderAPI_Sewing @ 0.001 (1 mm)"]
    C1 -->|"no shells"| C2["retry @ 0.005 (5 mm)"]
    C1 --> C3["ShapeFix_Solid + BRepCheck gate,<br/>reverse when the volume is negative"]
    C2 --> C3
    C3 -->|fail| C4["solid_step_path stays NULL"]

    B --> D["_select_xsec_slice_source: prefer the SURFACE STEP (gh-812)<br/>— the sewn solid fragments at sharp fillets"]
    D --> E{"_is_x_dominant_fuselage(handler xsecs)?<br/>extent_x ≥ 1.2 · extent_y and ≥ 1.2 · extent_z"}
    E -->|no| E1["skip refinement — keep the handler schema"]
    E -->|yes| F["budget = min(80, max(15, n + 5(n−1)))"]
    F --> G["vsp_anchored_x_stations — VSP anchors are mandatory,<br/>intermediates weighted by shape change"]
    G --> H["symmetric geom → clip to the handler's y side"]
    H --> I["slice + fit superellipse → mm → × _MM_TO_M"]
    I --> J{"_slicer_frame_matches_handler?<br/>0.5 ≤ x_span_ratio ≤ 2.0  (gh-803)"}
    J -->|no| J1["REJECT the refinement — handler schema wins"]
    J -->|yes| K["_replace_fuselage_xsecs"]
    K --> L["_scale_fuselage_xsecs(import factor) + scale_geom_step"]
```

## 9. Error policy — nothing aborts the import

```mermaid
flowchart LR
    A["per-geom handler raises"] --> W["ctx.add_warning + mark_lossy"]
    B["post-pass raises"] --> W2["warning component_type='POST_PASS'"]
    C["one component write fails"] --> W3["_record_persist_failure → warning, other rows still persist"]
    D["unit detection fails"] --> S["silently skipped (best-effort)"]
    E["slicer unavailable / rejected"] --> S2["handler schema retained"]
    F["sewing fails"] --> S3["solid_step_path = NULL"]
    W --> R["ImportResult.warnings[] + lossy_components[]"]
    W2 --> R
    W3 --> R
    R --> U["frontend warning banner (gh-648)"]

    H["hard failures only:<br/>ImportError (openvsp missing) · FileNotFoundError ·<br/>ScaleValidationError"]
```

## 10. Streaming progress (gh-737)

```mermaid
flowchart TD
    A["POST /api/v2/import/openvsp/stream"] --> B["asyncio.Queue + asyncio.create_task(run_import)"]
    B --> C["import runs in a thread; progress_cb(step, pct, detail)<br/>hops back via loop.call_soon_threadsafe(queue.put_nowait, …)"]
    C --> D["event: progress  data {step, pct, detail}"]
    D --> E["parsing 5 → parsing 15 → units 16 → scaling 18<br/>→ persist … → finalising 95"]
    E --> F["event: complete  — same body as the non-stream endpoint"]
    E --> G["event: error  data {detail}"]
    F --> H["StreamingResponse media_type=text/event-stream<br/>X-Accel-Buffering: no · Cache-Control: no-cache"]
    G --> H
```
