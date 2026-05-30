"""AeroSandbox side of the cross-validation benchmark.

Imports a .vsp3 through the SAME path the app uses
(import_vsp3 → AeroplaneSchema → asb.Airplane) and runs an α-sweep,
emitting a CSV shaped to line up with pipeline_vspaero.py's output.

Two methods are exposed:
  - "vortex_lattice"  → asb.VortexLatticeMethod   (apples-to-apples
                        inviscid comparison with VSPAERO's VLM; ASB's
                        VLM models lifting surfaces only — no fuselage,
                        matching our wings-only VSPAERO set)
  - "aerobuildup"     → asb.AeroBuildup           (the app's default;
                        includes fuselage parasite drag — a documented
                        assumption diff vs the wings-only VLM)

CSV columns:
    alpha_deg, CL, CD, CDi, CDo, CM, eff_e, LoD
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import aerosandbox as asb

# App imports (in-process; no REST, no DB).
from app.converters.openvsp_importer import import_vsp3
from app.converters.model_schema_converters import (
    aeroplane_schema_to_asb_airplane_async,
)
from app.api.utils import analyse_aerodynamics
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.schemas.AeroplaneRequest import AnalysisToolUrlType


@dataclass(frozen=True)
class AsbFlightCondition:
    velocity_mps: float
    altitude_m: float
    x_cg_m: float
    alpha_start_deg: float = -2.0
    alpha_end_deg: float = 12.0
    alpha_npts: int = 15


_METHODS = {
    "vortex_lattice": AnalysisToolUrlType.VORTEX_LATTICE,
    "aerobuildup": AnalysisToolUrlType.AEROBUILDUP,
}


def _as_list(value) -> list[float]:
    if value is None:
        return []
    arr = np.atleast_1d(np.asarray(value, dtype=float))
    return [float(x) for x in arr]


def _coef(model_field, n: int) -> list[float]:
    """Normalise a coefficient field to a length-n list of floats (NaN-filled)."""
    vals = _as_list(model_field)
    if len(vals) == n:
        return vals
    if len(vals) == 1:
        return vals * n
    return [math.nan] * n


def correct_reference_to_main_wing(asb_airplane) -> dict:
    """Force S/b/c reference to the LARGEST-area wing (the main wing).

    BENCHMARK-SIDE CORRECTION for a converter bug: the app's
    aeroplane_schema_to_asb_airplane converter sets airplane.s_ref from
    the FIRST wing geom, not the main wing. When the OpenVSP import
    order places the tailplane before the wing (e.g. Spitfire: HTP, VTP,
    Wing), s_ref becomes the *tail* area → every coefficient is wrong by
    the wing/tail area ratio (~8× for the Spitfire). We override the
    reference to the largest wing so the comparison is meaningful and
    both tools share identical references. Returns the applied refs.
    """
    if not asb_airplane.wings:
        return {"s_ref": asb_airplane.s_ref, "b_ref": asb_airplane.b_ref,
                "c_ref": asb_airplane.c_ref, "corrected": False}
    main = max(asb_airplane.wings, key=lambda w: w.area())
    s = float(main.area()); b = float(main.span())
    c = float(main.mean_aerodynamic_chord())
    corrected = abs(s - float(asb_airplane.s_ref)) / max(s, 1e-9) > 0.05
    if corrected:
        print(f"[asb] reference-area CORRECTION: airplane.s_ref="
              f"{float(asb_airplane.s_ref):.3f} → main wing '{main.name}' "
              f"area={s:.3f} (converter bug: ref taken from first wing geom)",
              flush=True)
    asb_airplane.s_ref = s
    asb_airplane.b_ref = b
    asb_airplane.c_ref = c
    return {"s_ref": s, "b_ref": b, "c_ref": c, "corrected": corrected,
            "main_wing": main.name}


def _sanitize_airfoils(asb_airplane) -> int:
    """Remove consecutive duplicate points from every xsec airfoil.

    BENCHMARK-SIDE WORKAROUND: the OpenVSP importer can emit airfoil
    .dat files with duplicate adjacent points, which makes ASB's
    Airfoil.repanel() (called during VLM section subdivision) raise
    "duplicate point". This is a genuine importer data-quality bug
    worth a GH ticket — here we just clean the in-memory ASB airfoils
    so the aero comparison can proceed. Returns the number of points
    removed across all airfoils.
    """
    removed = 0
    for wing in getattr(asb_airplane, "wings", []):
        for xsec in getattr(wing, "xsecs", []):
            af = getattr(xsec, "airfoil", None)
            if af is None or getattr(af, "coordinates", None) is None:
                continue
            coords = np.asarray(af.coordinates, dtype=float)
            if len(coords) < 2:
                continue
            keep = [0]
            for i in range(1, len(coords)):
                if np.linalg.norm(coords[i] - coords[keep[-1]]) > 1e-10:
                    keep.append(i)
            if len(keep) != len(coords):
                removed += len(coords) - len(keep)
                af.coordinates = coords[keep]
    return removed


def run(
    vsp_file: Path,
    flight: AsbFlightCondition,
    method: str,
    out_csv: Path,
) -> Path:
    tool = _METHODS[method]

    print(f"[asb:{method}] import {vsp_file.name} …", flush=True)
    result = import_vsp3(vsp_file)
    schema = result.aeroplane
    if result.warnings:
        print(f"[asb:{method}] importer warnings: {len(result.warnings)}",
              flush=True)

    asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=schema)
    correct_reference_to_main_wing(asb_airplane)
    removed = _sanitize_airfoils(asb_airplane)
    if removed:
        print(f"[asb:{method}] sanitized airfoils: removed {removed} "
              f"duplicate point(s) (importer data-quality bug)", flush=True)

    alphas = list(
        np.linspace(flight.alpha_start_deg, flight.alpha_end_deg, flight.alpha_npts)
    )
    print(f"[asb:{method}] analyse α=[{flight.alpha_start_deg}, "
          f"{flight.alpha_end_deg}]°×{flight.alpha_npts} "
          f"V={flight.velocity_mps} h={flight.altitude_m} …", flush=True)

    if method == "aerobuildup":
        rows = _rows_aerobuildup(tool, asb_airplane, flight, alphas)
    elif method == "vortex_lattice":
        rows = _rows_vlm_per_alpha(asb_airplane, flight, alphas)
    else:
        raise ValueError(f"unknown method {method}")

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    n_nan = sum(1 for r in rows if math.isnan(r["CL"]))
    with out_csv.open("w") as f:
        f.write("alpha_deg,CL,CD,CDi,CDo,CM,eff_e,LoD\n")
        for r in rows:
            f.write(
                f"{r['alpha']:.6f},{r['CL']:.6f},{r['CD']:.6f},{r['CDi']:.6f},"
                f"{r['CDo']:.6f},{r['CM']:.6f},{r['eff_e']:.6f},{r['LoD']:.6f}\n"
            )
    print(f"[asb:{method}] wrote {out_csv} ({len(rows)} rows, {n_nan} NaN)",
          flush=True)
    return out_csv


def _lod(cl: float, cd: float) -> float:
    return cl / cd if cd and not math.isnan(cd) and cd != 0 else math.nan


def _rows_aerobuildup(tool, asb_airplane, flight, alphas) -> list[dict]:
    """App path: vectorized AeroBuildup α-sweep with stability derivatives."""
    op = OperatingPointSchema(  # type: ignore[call-arg]  # optional Pydantic fields
        name="benchmark_aerobuildup",
        velocity=flight.velocity_mps,
        altitude=flight.altitude_m,
        alpha=alphas,
        beta=0.0, p=0.0, q=0.0, r=0.0,
        xyz_ref=[flight.x_cg_m, 0.0, 0.0],
    )
    model, _ = analyse_aerodynamics(tool, op, asb_airplane)
    n = len(alphas)
    alpha_out = _coef(model.flight_condition.alpha, n) or alphas
    CL  = _coef(model.coefficients.CL, n)
    CD  = _coef(model.coefficients.CD, n)
    CDi = _coef(model.coefficients.CDind, n)
    CDv = _coef(model.coefficients.CDvis, n)
    CM  = _coef(model.coefficients.Cm, n)
    eff = _coef(model.coefficients.e, n)
    rows = []
    for i in range(n):
        cd, cdi, cdv = CD[i], CDi[i], CDv[i]
        cdo = cdv if not math.isnan(cdv) else (
            cd - cdi if not (math.isnan(cd) or math.isnan(cdi)) else math.nan
        )
        rows.append({
            "alpha": alpha_out[i], "CL": CL[i], "CD": cd, "CDi": cdi,
            "CDo": cdo, "CM": CM[i], "eff_e": eff[i], "LoD": _lod(CL[i], cd),
        })
    return rows


# Target ~24 spanwise panels total. ASB's default spanwise_resolution=10
# subdivides EACH wing section into 10 panels — and the OpenVSP importer
# augments wings into many sections (e.g. Cessna → 31 xsecs), which makes
# a single default VLM solve take ~215 s. Scaling the per-section
# resolution to the section count keeps the panel count (and runtime)
# bounded while preserving fidelity. (NB: the app's default method is
# AeroBuildup, which is unaffected; this only matters for VLM on imports.)
_VLM_TARGET_SPANWISE_PANELS = 24
_VLM_CHORDWISE_RESOLUTION = 6


def _vlm_spanwise_resolution(asb_airplane) -> int:
    max_sec = max((len(w.xsecs) for w in asb_airplane.wings), default=1)
    return max(1, round(_VLM_TARGET_SPANWISE_PANELS / max_sec))


def _rows_vlm_per_alpha(asb_airplane, flight, alphas) -> list[dict]:
    """ASB VLM run, one α at a time.

    The app's run_with_stability_derivatives chokes on a vectorized α
    array for this geometry ("inhomogeneous shape"); a per-α loop is
    robust. VLM is inviscid → CD is purely induced (CDi == CD, CDo = 0).
    """
    span_res = _vlm_spanwise_resolution(asb_airplane)
    print(f"[asb:vortex_lattice] spanwise_resolution={span_res}, "
          f"chordwise_resolution={_VLM_CHORDWISE_RESOLUTION} "
          f"(max wing sections={max((len(w.xsecs) for w in asb_airplane.wings), default=0)})",
          flush=True)
    rows = []
    for a in alphas:
        op = asb.OperatingPoint(velocity=flight.velocity_mps, alpha=float(a))
        vlm = asb.VortexLatticeMethod(
            airplane=asb_airplane, op_point=op,
            xyz_ref=[flight.x_cg_m, 0.0, 0.0],
            spanwise_resolution=span_res,
            chordwise_resolution=_VLM_CHORDWISE_RESOLUTION,
        )
        try:
            d = vlm.run()
            cl = float(d["CL"]); cd = float(d["CD"])
            cdi = float(d.get("CDi", cd))   # VLM CD is induced
            cm = float(d.get("Cm", math.nan))
            ar = (asb_airplane.b_ref ** 2) / asb_airplane.s_ref
            e = (cl * cl) / (math.pi * ar * cdi) if cdi > 1e-9 else math.nan
            rows.append({"alpha": float(a), "CL": cl, "CD": cd, "CDi": cdi,
                         "CDo": 0.0, "CM": cm, "eff_e": e, "LoD": _lod(cl, cd)})
        except Exception as exc:
            print(f"[asb:vortex_lattice] α={a:.1f}° failed: {exc}", flush=True)
            rows.append({"alpha": float(a), "CL": math.nan, "CD": math.nan,
                         "CDi": math.nan, "CDo": math.nan, "CM": math.nan,
                         "eff_e": math.nan, "LoD": math.nan})
    return rows


# ---------------------------------------------------------------------------
# DG-101G entry point
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
DG101G_VSP = REPO_ROOT / "components" / "aircraft" / "vsp" / "dg101g.vsp3"

DG101G_FLIGHT = AsbFlightCondition(
    velocity_mps=29.17,
    altitude_m=1500.0,
    x_cg_m=2.0,
)


def main() -> int:
    base = Path(__file__).parent / "results" / "dg101g"
    failures = 0
    for method in ("vortex_lattice", "aerobuildup"):
        try:
            run(
                vsp_file=DG101G_VSP,
                flight=DG101G_FLIGHT,
                method=method,
                out_csv=base / f"asb_{method}_polar.csv",
            )
        except Exception as exc:  # keep one method's failure from blocking the other
            failures += 1
            print(f"[asb:{method}] FAILED: {type(exc).__name__}: {exc}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
