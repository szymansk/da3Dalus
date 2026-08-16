# Flowcharts — airfoil-catalog

## 1. Ingestion — `.dat` files into the catalogue

```mermaid
flowchart TD
    A["POST /airfoils/import (directory)"] --> B["resolve directory"]
    B --> C{"inside <repo>/components ?"}
    C -->|no| C1["ValidationError — import is sandboxed"]
    C -->|yes| D["load existing names, lowercased (dedup set)"]
    D --> E["rglob('*.dat') sorted"]
    E --> F["_parse_dat_file"]

    F --> F1{"< 3 lines?"}
    F1 -->|yes| X1["ValueError -> errors += 1"]
    F1 -->|no| F2["name = FILE STEM (not the Selig header)"]
    F2 --> F3["skip line 1 (header);<br/>parse 2 floats per line, skip unparseable lines"]
    F3 --> F4{"< 3 valid coordinates?"}
    F4 -->|yes| X1
    F4 -->|no| G{"name.lower() already known?"}

    G -->|yes| H["skipped += 1"]
    G -->|no| I["INSERT airfoils(name, coordinates, source_file)"]
    I --> J["db.flush(); imported += 1"]
    I -->|SQLAlchemyError| K["db.rollback(); errors += 1<br/>(loop continues)"]

    J --> L["AirfoilImportResult{imported, skipped, errors,<br/>error_files, imported_names}"]
    H --> L
    X1 --> L

    note["Selig format ONLY — there is no Lednicer sniffing.<br/>No normalisation, no re-panelling."]
    F3 -.- note
```

## 2. Low-Re backfill (gh-821) — geometry + polars

```mermaid
flowchart TD
    A["scripts/backfill_airfoil_low_re.py"] --> B["for each airfoil in airfoils"]
    B --> C["classify_family(coords)"]
    C --> D["UPSERT airfoil_geometry<br/>{max_thickness_pct, max_camber_pct,<br/>camber_at_te (= camber at x=0.9), family}"]
    B --> E["compute_airfoil_low_re(name, coords, low_re_grid)"]

    E --> E0{"aerosandbox importable?"}
    E0 -->|no, e.g. linux/aarch64| E1["log warning, return [] "]
    E0 -->|yes| E2["alpha grid = arange(-5.0, 18.0, 0.2)"]
    E2 --> E3["for Re in [40k,50k,60k,75k,90k,110k,130k,<br/>160k,200k,250k,350k,500k,750k]"]
    E3 --> E4["get_aero_from_neuralfoil(alpha, Re, mach=0,<br/>n_crit=9.0, model_size='xxxlarge')"]
    E4 --> E5["GATE: keep only alpha with<br/>analysis_confidence >= 0.90"]
    E5 --> E6["_extract_metrics on the trusted arrays"]
    E6 --> E7["_windowed_min_confidence over<br/>[alpha_attached_lo, alpha_attached_hi]<br/>(fallback: whole-sweep min if window < 4 pts)"]
    E7 --> F["UPSERT airfoil_low_re_polar<br/>UNIQUE(airfoil_name, reynolds)"]

    subgraph METRICS["Stored per (airfoil, Re)"]
        M1["ld_max, cl_max"]
        M2["alpha_attached_lo/hi"]
        M3["drag_bucket_width = dCL where CD <= 1.15 x CD_min"]
        M4["cd_min, stall_gentleness (dCL/dalpha past peak)"]
        M5["parabolic fit: CD = cd0 + k(CL - cl0)^2"]
        M6["cl_valid_lo/hi, min_analysis_confidence"]
        M7["provenance: neuralfoil_model_size, n_crit, computed_at"]
    end
    F -.- METRICS
```

## 3. Family classifier — evaluation order matters

```mermaid
flowchart TD
    A["coords"] --> B["derive camber line + upper/lower surfaces"]
    B --> C{"REFLEXED?"}
    C --> C1["Signal A: camber(x=0.9)/max_camber < 0.06<br/>(NACA 4412 = 0.31, Clark Y = 0.28)"]
    C --> C2["Signal B: quadratic coeff of camber line<br/>over x in [0.5,1] > 0.015 AND max_camber > 2%<br/>(Clark YH ~ +0.039, NACA 4412 ~ -0.11)"]
    C1 -->|either fires| R["reflexed"]
    C2 -->|either fires| R

    C -->|no| D{"max_camber_pct <= 0.5 ?"}
    D -->|yes| S["symmetric"]
    D -->|no| E{"FLAT BOTTOM?<br/>quadratic coeff of lower surface<br/>over x in [0.30, 1.0] < 0.005"}
    E -->|yes| FB["flat_bottom"]
    E -->|no| G{"max_camber_pct <= 2.0 ?"}
    G -->|yes| SS["semi_symmetric"]
    G -->|no| CA["cambered"]

    note["symmetric MUST be tested before flat_bottom:<br/>a symmetric section also passes the linearity test"]
    D -.- note
```

## 4. Suitability query — the ranking pipeline

`GET /airfoils/db/suitability`

```mermaid
flowchart TD
    A["query: chord_m, speed_ms, mission_type,<br/>optional aeroplane context"] --> B["Re = rho x V x c / mu<br/>rho = 1.225, mu = 1.81e-5"]
    B --> C["_clamp_re_to_grid -> (re_clamped_root, re_clamped flag)"]
    C --> D["per-lens speeds (gh-838/839):<br/>v_cruise, v_md, v_min_sink -> their own clamped Re"]
    D --> E["compute_re_cd0_reference(fleet, Re, percentile=20)<br/>-> robust 'best achievable cd0' at this Re<br/>(fallback 0.020)"]
    E --> F["for each airfoil"]

    F --> G["interpolate_polar_at_re — LINEAR IN ln(Re)"]
    G --> H1["score_re_agnostic"]
    G --> H2["score_mission"]
    G --> H3["score_target_cl (cruise / best-glide / min-sink)"]
    G --> H4["compute_tags (query-time, no DB column)"]

    H1 --> I["SuitabilityItem"]
    H2 --> I
    H3 --> I
    H4 --> I
    I --> J["sort by (confidence tier, -active_lens score)"]
    J --> K["SuitabilityResponse{query, caveat, results}"]

    L["active_lens in {re_agnostic, mission, target_cl_cruise}"] -.->|"glide points are DISPLAY-ONLY —<br/>they never drive the default sort"| J
    M["caveat.ignores_tip_re_clmax_collapse = True (always)"] -.- K
```

## 5. The three scoring lenses

```mermaid
flowchart TD
    subgraph L1["Lens 1 — score_re_agnostic (weighted sum)"]
        A1["min(ld_max/60, 1)        w = 0.35"]
        A2["min(cl_max/1.5, 1)       w = 0.25"]
        A3["min(bucket/0.8, 1)       w = 0.20"]
        A4["clamp(1 + stall/0.15,0,1) w = 0.10"]
        A5["min(0.008/cd_min, 1)     w = 0.10"]
        A6["score = SUM(v x w) / SUM(w), clamped [0,1]<br/>(only the components actually present)"]
        A1 --> A6
        A2 --> A6
        A3 --> A6
        A4 --> A6
        A5 --> A6
    end

    subgraph L2["Lens 2 — score_mission (multiplicative)"]
        B1["family_bonus = 1.0 if preferred else 0.7"]
        B2["thickness_match = 1.0 in band,<br/>else max(0, 1 - gap/5.0)"]
        B3["cl_bonus = (1-w) + w x min(cl_max/1.5, 1)"]
        B4["score = re_agnostic x family_bonus<br/>x thickness_match x cl_bonus"]
        B1 --> B4
        B2 --> B4
        B3 --> B4
    end

    subgraph L3["Lens 3 — score_target_cl = Match x Efficiency"]
        C1["cl_star = sqrt(cl0^2 + cd0/k)"]
        C2["r = CD(cl_target) / cd0"]
        C3["tolerance = (bucket / 0.6) x 0.5"]
        C4{"r <= 1 ?"}
        C4 -->|yes| C5["Match = 1.0"]
        C4 -->|no| C6{"r >= r_poor = 2.5 ?"}
        C6 -->|no| C7["Match = 1 - (r-1)/(r_poor-1)"]
        C6 -->|"yes AND cl_max known"| C8["CL_max fallback:<br/>Match = clamp((cl_max - cl_target)/0.30, 0, 1)"]
        C6 -->|"yes, no cl_max"| C9["Match = 0.0"]
        C10["Efficiency = min(re_cd0_reference / cd0, 1.0)"]
        C5 --> C11["score = clamp(Match x Efficiency, 0, 1)"]
        C7 --> C11
        C8 --> C11
        C9 --> C11
        C10 --> C11
        C1 --> C2
        C2 --> C4
        C3 --> C7
    end

    N["CL_max fallback exists because glider min-sink CL<br/>(~ sqrt(3) x CL_md) sits far above cl_star,<br/>collapsing r-based Match to 0 for GOOD glider sections"]
    C8 -.- N
```

## 6. Role tags (gh-835) — computed at query time

```mermaid
flowchart TD
    A["family, max_thickness_pct t, max_camber_pct c, polars"] --> B["compute_tags"]

    B --> T1{"symmetric AND c <= 0.5 AND 6 <= t <= 15"}
    T1 -->|yes| R1["v_stabilizer"]
    T1 -->|yes| R2["h_stabilizer  (same gate, separate tag for UX)"]

    B --> T2{"symmetric AND c <= 0.5 AND 7 <= t <= 12"}
    T2 -->|yes| R3["acro"]

    B --> T3{"t <= 10 AND family in {symmetric, semi_symmetric, reflexed}<br/>AND c <= 3 AND confident polar at Re <= 150k"}
    T3 -->|yes| R4["winglet"]

    B --> T4{"any polar Re <= 150 000 with confidence >= 0.85"}
    T4 -->|yes| R5["low_re"]

    B --> T5{"any polar Re >= 500 000 with confidence >= 0.85"}
    T5 -->|yes| R6["high_re  (APPROXIMATE — grid tops at 750k)"]

    R1 --> Z["sorted(tags) — deterministic"]
    R2 --> Z
    R3 --> Z
    R4 --> Z
    R5 --> Z
    R6 --> Z
```

## 7. The two Reynolds concepts — never conflate

```mermaid
flowchart LR
    subgraph A["gh-821 — this module (2D per airfoil)"]
        A1["absolute Re grid 40k..750k"]
        A2["NeuralFoil per airfoil SHAPE"]
        A3["independent of any aircraft"]
        A4["tables: airfoil_geometry, airfoil_low_re_polar"]
    end
    subgraph B["gh-493 — polar_re_table_service (aircraft level)"]
        B1["re-bins aircraft fine-sweep data"]
        B2["'Re' is a SPEED PROXY at the main-wing MAC"]
        B3["depends on the current flight condition"]
    end
    A -. "documented as MUST NOT be conflated" .- B
```
