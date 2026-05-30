"""Compare VSPAERO vs ASB polars against each other and real anchors.

Reads whatever polar CSVs exist in an aircraft result dir, computes a
small set of headline metrics per source, writes:
  - comparison.json   (aligned curves + metrics + anchors → dashboard)
  - RESULTS.md        (human-readable Δ-table + interpretation)
"""
from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict
from pathlib import Path

from benchmark_config import AircraftConfig

# Maps a source key → (csv filename, human label, method family)
SOURCES = [
    ("vspaero",      "vspaero_polar.csv",            "VSPAERO (VLM, wings-only)"),
    ("asb_vlm",      "asb_vortex_lattice_polar.csv", "ASB VortexLattice (inviscid)"),
    ("asb_aerobuildup", "asb_aerobuildup_polar.csv", "ASB AeroBuildup (app default)"),
]


def _read_csv(path: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with path.open() as f:
        for r in csv.DictReader(f):
            rows.append({k: float(v) if v not in ("", "nan") else math.nan
                         for k, v in r.items()})
    return rows


def _col(rows: list[dict], name: str) -> list[float]:
    return [r.get(name, math.nan) for r in rows]


def _interp_at(x: list[float], y: list[float], x0: float) -> float:
    """Linear interpolation of y(x0); NaN if out of range / insufficient data."""
    pts = [(a, b) for a, b in zip(x, y, strict=False) if not (math.isnan(a) or math.isnan(b))]
    pts.sort()
    if len(pts) < 2:
        return math.nan
    (x1, y1), (x2, y2) = pts[0], pts[1]            # default: extrapolate low end
    if x0 >= pts[-1][0]:
        (x1, y1), (x2, y2) = pts[-2], pts[-1]      # extrapolate high end
    elif x0 > pts[0][0]:
        for i in range(1, len(pts)):
            if pts[i][0] >= x0:
                (x1, y1), (x2, y2) = pts[i - 1], pts[i]
                break
    if x2 == x1:
        return y1
    return y1 + (y2 - y1) * (x0 - x1) / (x2 - x1)


def _linfit_slope(x: list[float], y: list[float], lo: float, hi: float) -> float:
    """Least-squares slope dy/dx over the window [lo, hi] (per degree)."""
    pts = [(a, b) for a, b in zip(x, y, strict=False)
           if not (math.isnan(a) or math.isnan(b)) and lo <= a <= hi]
    n = len(pts)
    if n < 2:
        return math.nan
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    sxx = sum(p[0] ** 2 for p in pts)
    sxy = sum(p[0] * p[1] for p in pts)
    denom = n * sxx - sx * sx
    return (n * sxy - sx * sy) / denom if denom else math.nan


def _metrics(rows: list[dict]) -> dict[str, float]:
    a = _col(rows, "alpha_deg")
    cl = _col(rows, "CL") if "CL" in rows[0] else _col(rows, "CLtot")
    cd = _col(rows, "CD") if "CD" in rows[0] else _col(rows, "CDtot")
    cm = _col(rows, "CM") if "CM" in rows[0] else _col(rows, "CMytot")
    lod = _col(rows, "LoD")
    eff = _col(rows, "eff_e_vsp") if "eff_e_vsp" in rows[0] else _col(rows, "eff_e")

    lod_valid = [(v, a[i]) for i, v in enumerate(lod) if not math.isnan(v)]
    max_lod, a_at_max = (max(lod_valid) if lod_valid else (math.nan, math.nan))
    cd_valid = [v for v in cd if not math.isnan(v)]
    eff_valid = [v for v in eff if not math.isnan(v)]
    return {
        "CL0": _interp_at(a, cl, 0.0),
        "CL_alpha_per_deg": _linfit_slope(a, cl, -2.0, 4.0),
        "CD_min": min(cd_valid) if cd_valid else math.nan,
        "max_LD": max_lod,
        "alpha_at_max_LD": a_at_max,
        "CM_alpha_per_deg": _linfit_slope(a, cm, -2.0, 4.0),
        "e_mean": (sum(eff_valid) / len(eff_valid)) if eff_valid else math.nan,
        "CL_max_in_sweep": max((v for v in cl if not math.isnan(v)), default=math.nan),
    }


def _flags(metrics: dict, curves: dict, is_boxwing: bool) -> list[str]:
    """Surface non-physical / failed results rather than hiding them."""
    out: list[str] = []
    cl = curves.get("CL", [])
    if cl and all(math.isnan(v) for v in cl):
        return ["method produced all-NaN (failed for this geometry)"]
    sl = metrics.get("CL_alpha_per_deg", math.nan)
    if not math.isnan(sl) and not (0.03 <= sl <= 0.18):
        out.append(f"non-physical lift slope C_Lα={sl:.3f}/deg "
                   f"(expected 0.03–0.18); suspect geometry/reference")
    e = metrics.get("e_mean", math.nan)
    if not math.isnan(e) and e < 0.3:
        out.append(f"non-physical span efficiency e={e:.3f} (≪ typical 0.7–1.0) — "
                   f"induced-drag solve looks unreliable for this geometry")
    if not math.isnan(e) and e > 1.1 and not is_boxwing:
        out.append(f"non-physical span efficiency e={e:.2f} > 1.0 "
                   f"(VLM tip-discretisation / back-computed artifact)")
    if is_boxwing and not math.isnan(e) and e > 1.1:
        out.append(f"span efficiency e={e:.2f} > 1.0 — expected for a box "
                   f"wing (beats the monoplane limit), but the AR-based "
                   f"formula is only indicative here")
    return out


def compare_aircraft(cfg: AircraftConfig) -> dict:
    result_dir = cfg.result_dir
    sources: dict[str, dict] = {}
    for key, fname, label in SOURCES:
        path = result_dir / fname
        if not path.exists():
            continue
        rows = _read_csv(path)
        if not rows:
            continue
        # normalise curve column names for the dashboard
        a = _col(rows, "alpha_deg")
        cl = _col(rows, "CL") if "CL" in rows[0] else _col(rows, "CLtot")
        cd = _col(rows, "CD") if "CD" in rows[0] else _col(rows, "CDtot")
        cm = _col(rows, "CM") if "CM" in rows[0] else _col(rows, "CMytot")
        lod = _col(rows, "LoD")
        metrics = _metrics(rows)
        curves = {"alpha": a, "CL": cl, "CD": cd, "CM": cm, "LoD": lod}
        is_boxwing = "box" in cfg.topology.lower()
        sources[key] = {
            "label": label,
            "curves": curves,
            "metrics": metrics,
            "flags": _flags(metrics, curves, is_boxwing),
        }

    comparison = {
        "key": cfg.key,
        "name": cfg.name,
        "category": cfg.category,
        "topology": cfg.topology,
        "notes": cfg.notes,
        "velocity_mps": cfg.velocity_mps,
        "altitude_m": cfg.altitude_m,
        "anchors": [asdict(an) for an in cfg.anchors],
        "reference_polar": asdict(cfg.reference_polar) if cfg.reference_polar else None,
        "sources": sources,
    }
    (result_dir / "comparison.json").write_text(json.dumps(comparison, indent=2))
    _write_results_md(cfg, comparison)
    return comparison


def _fmt(v: float) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.4g}"


def _write_results_md(cfg: AircraftConfig, comp: dict) -> None:
    src = comp["sources"]
    keys = list(src.keys())
    lines: list[str] = []
    lines.append(f"# {cfg.name} — VSPAERO vs AeroSandbox\n")
    lines.append(f"- **Topology:** {cfg.topology}")
    lines.append(f"- **Category:** {cfg.category}")
    lines.append(f"- **Flight point:** V = {cfg.velocity_mps} m/s, "
                 f"altitude = {cfg.altitude_m} m")
    if cfg.notes:
        lines.append(f"- **Notes:** {cfg.notes}")
    lines.append("")

    # Real-world anchors
    if cfg.anchors:
        lines.append("## Real-world anchors\n")
        lines.append("| Metric | Value | Source |")
        lines.append("|---|---|---|")
        for an in cfg.anchors:
            lines.append(f"| {an.metric} | {_fmt(an.value)} | {an.source} |")
        lines.append("")

    # Metrics table
    metric_names = [
        ("CL0", "C_L at α=0"),
        ("CL_alpha_per_deg", "C_Lα [1/deg]"),
        ("CD_min", "C_D,min"),
        ("max_LD", "max L/D"),
        ("alpha_at_max_LD", "α at max L/D [deg]"),
        ("CM_alpha_per_deg", "C_Mα [1/deg]"),
        ("e_mean", "mean span-eff e"),
        ("CL_max_in_sweep", "C_L max (in sweep)"),
    ]
    lines.append("## Computed metrics\n")
    header = "| Metric | " + " | ".join(src[k]["label"] for k in keys) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (len(keys) + 1))
    for mkey, mlabel in metric_names:
        cells = " | ".join(_fmt(src[k]["metrics"][mkey]) for k in keys)
        lines.append(f"| {mlabel} | {cells} |")
    lines.append("")

    # Data-quality flags
    flagged = [(src[k]["label"], f) for k in keys for f in src[k].get("flags", [])]
    if flagged:
        lines.append("## ⚠️ Data-quality flags\n")
        for label, f in flagged:
            lines.append(f"- **{label}:** {f}")
        lines.append("")

    # Auto interpretation hooks
    lines.append("## Interpretation\n")
    lines.append("> Auto-generated headline comparisons; fill in narrative below.\n")
    if "vspaero" in src and "asb_vlm" in src:
        v = src["vspaero"]["metrics"]
        a = src["asb_vlm"]["metrics"]
        if not (math.isnan(v["CL_alpha_per_deg"]) or math.isnan(a["CL_alpha_per_deg"])):
            d = 100 * (a["CL_alpha_per_deg"] - v["CL_alpha_per_deg"]) / v["CL_alpha_per_deg"]
            lines.append(f"- **VLM C_Lα agreement (ASB vs VSPAERO):** "
                         f"{a['CL_alpha_per_deg']:.4f} vs {v['CL_alpha_per_deg']:.4f} "
                         f"/deg → Δ = {d:+.1f} %.")
        if not (math.isnan(v["CL0"]) or math.isnan(a["CL0"])):
            lines.append(f"- **C_L0 offset (ASB vs VSPAERO VLM):** "
                         f"{a['CL0']:.3f} vs {v['CL0']:.3f} → Δ = {a['CL0'] - v['CL0']:+.3f}. "
                         f"A matched slope with a C_L0 offset points to an airfoil "
                         f"camber / zero-lift-angle interpretation difference, not "
                         f"reference area.")
    # max L/D vs real anchor
    real_lod = next((an.value for an in cfg.anchors if an.metric == "max_LD"), None)
    if real_lod is not None:
        for k in keys:
            m = src[k]["metrics"]["max_LD"]
            if not math.isnan(m):
                d = 100 * (m - real_lod) / real_lod
                lines.append(f"- **max L/D — {src[k]['label']}:** {m:.1f} vs "
                             f"real {real_lod:.1f} → {d:+.0f} %.")
    # non-physical span efficiency flag (per design-error-feedback memory)
    for k in keys:
        e = src[k]["metrics"]["e_mean"]
        if not math.isnan(e) and e > 1.05:
            lines.append(f"- ⚠️ **{src[k]['label']}: mean span efficiency e = {e:.3f} "
                         f"> 1.0** — non-physical; flag rather than hide (VLM tip "
                         f"discretisation / back-computed-e artifact).")
    lines.append("")

    (cfg.result_dir / "RESULTS.md").write_text("\n".join(lines))


def main() -> int:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from benchmark_config import AIRCRAFT
    for cfg in AIRCRAFT:
        if (cfg.result_dir / "comparison.json").parent.exists() and \
           any((cfg.result_dir / s[1]).exists() for s in SOURCES):
            comp = compare_aircraft(cfg)
            print(f"[compare] {cfg.key}: {len(comp['sources'])} sources → "
                  f"{cfg.result_dir / 'RESULTS.md'}")
        else:
            print(f"[compare] {cfg.key}: no polar CSVs yet, skipping")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
