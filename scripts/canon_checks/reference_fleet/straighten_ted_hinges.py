"""Put every trailing-edge device of an aeroplane on ONE straight hinge line (gh-1163).

A control surface spanning several segments stores its hinge per segment as chord
fraction at the inboard (``rel_chord_root``) and outboard (``rel_chord_tip``)
section. Rounded or hand-edited values leave small kinks and mismatches at shared
sections. This fits, per device name and wing, a straight line through the stored
hinge points (plan view; side view for vertical surfaces) and rewrites root/tip of
every segment from that line, so neighbouring segments agree at their shared
section. Fractions outside 0..1 are clamped and reported; stored fractions of
exactly 0 or 1 are such clamps and do not define the line.

    # dry run against a running API (default: only print)
    poetry run python scripts/canon_checks/reference_fleet/straighten_ted_hinges.py \\
        --api http://localhost:8001 --aeroplane BRYAN
    # write the corrected values (PATCH .../trailing_edge_device per segment)
    ... --apply
    # correct a plugin export file in place instead of a database
    ... --json scripts/canon_checks/reference_fleet/bryan/bryan.airplane.json [--apply]
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import numpy as np

DECIMALS = 4


def _span_axis(x_secs: list[dict]) -> int:
    """1 (y) for horizontal surfaces, 2 (z) for vertical ones."""
    ys = [x["xyz_le"][1] for x in x_secs]
    zs = [x["xyz_le"][2] for x in x_secs]
    return 2 if np.ptp(zs) > np.ptp(ys) else 1


def _hinge_x(x: dict, rel: float) -> float:
    return x["xyz_le"][0] + rel * x["chord"] * math.cos(math.radians(x.get("twist") or 0.0))


def _rel(x: dict, hinge_x: float) -> float:
    return (hinge_x - x["xyz_le"][0]) / (x["chord"] * math.cos(math.radians(x.get("twist") or 0.0)))


def straighten(x_secs: list[dict]) -> list[dict]:
    """Return one change record per TED segment: index, name, old and new root/tip.

    ``x_secs`` are wing cross-sections as the API returns them (metres, degrees).
    """
    k = _span_axis(x_secs)
    by_name: dict[str, list[int]] = {}
    for i, x in enumerate(x_secs[:-1]):
        ted = x.get("trailing_edge_device")
        if ted and ted.get("rel_chord_root") is not None:
            by_name.setdefault(ted.get("name") or "", []).append(i)

    changes = []
    for name, segs in by_name.items():
        pts = []
        for i in segs:
            ted = x_secs[i]["trailing_edge_device"]
            root = ted["rel_chord_root"]
            tip = ted.get("rel_chord_tip")
            tip = root if tip is None else tip
            for x, rel in ((x_secs[i], root), (x_secs[i + 1], tip)):
                pts.append((x["xyz_le"][k], _hinge_x(x, rel), 0.0 < rel < 1.0))
        # A fraction of exactly 0 or 1 is a clamp at the leading/trailing edge, not a
        # hinge position: it must not pull the line (unless nothing else is left).
        inner = [q[:2] for q in pts if q[2]]
        p = np.array(inner if len({q[0] for q in inner}) >= 2 else [q[:2] for q in pts])
        if np.ptp(p[:, 0]) <= 0:
            continue
        slope, offset = np.polyfit(p[:, 0], p[:, 1], 1)

        def on_line(x: dict, slope: float = slope, offset: float = offset) -> tuple[float, bool]:
            r = _rel(x, slope * x["xyz_le"][k] + offset)
            c = min(1.0, max(0.0, r))
            return round(c, DECIMALS), c != r

        for i in segs:
            ted = x_secs[i]["trailing_edge_device"]
            (root, clamp_r), (tip, clamp_t) = on_line(x_secs[i]), on_line(x_secs[i + 1])
            changes.append(
                {
                    "index": i,
                    "name": name,
                    "old": (ted["rel_chord_root"], ted.get("rel_chord_tip")),
                    "new": (root, tip),
                    "clamped": bool(clamp_r or clamp_t),
                    "line_error_mm": round(
                        1000 * float(np.max(np.abs(p[:, 1] - (slope * p[:, 0] + offset)))), 2
                    ),
                }
            )
    return changes


def _report(wing: str, changes: list[dict]) -> None:
    for c in changes:
        mark = "  (auf 0..1 begrenzt)" if c["clamped"] else ""
        print(
            f"  {wing} #{c['index']:2d} {c['name']}: root {c['old'][0]} -> {c['new'][0]}, "
            f"tip {c['old'][1]} -> {c['new'][1]}{mark}"
        )
    for name in sorted({c["name"] for c in changes}):
        err = next(c["line_error_mm"] for c in changes if c["name"] == name)
        print(f"  {wing} {name}: alte Punkte max. {err} mm neben der Geraden")


def _run_json(path: pathlib.Path, apply: bool) -> None:
    text = path.read_text()
    geo = json.loads(text)
    second = text.splitlines()[1] if "\n" in text else ""
    indent = len(second) - len(second.lstrip(" ")) or None  # keep the file's own layout
    for wname, w in geo["wings"].items():
        changes = straighten(w["x_secs"])
        _report(wname, changes)
        for c in changes:
            ted = w["x_secs"][c["index"]]["trailing_edge_device"]
            ted["rel_chord_root"], ted["rel_chord_tip"] = c["new"]
            cs = w["x_secs"][c["index"]].get("control_surface")
            if cs is not None:
                cs["hinge_point"] = c["new"][0]
    if apply:
        out = json.dumps(geo, indent=indent, ensure_ascii=False)
        path.write_text(out + "\n" if text.endswith("\n") else out)
        print(f"geschrieben: {path}")


def _run_api(api: str, aeroplane: str, apply: bool) -> None:
    import httpx

    c = httpx.Client(base_url=api.rstrip("/"), timeout=30)
    r = c.get("/aeroplanes")
    r.raise_for_status()
    body = r.json()
    planes = body["aeroplanes"] if isinstance(body, dict) else body
    hits = [p for p in planes if aeroplane in (p.get("id"), p.get("name"))]
    if len(hits) != 1:
        sys.exit(f"Flugzeug {aeroplane!r}: {len(hits)} Treffer - Name oder id eindeutig angeben")
    pid = hits[0]["id"]
    wings = c.get(f"/aeroplanes/{pid}/wings").json()
    for wname in wings["wings"] if isinstance(wings, dict) else wings:
        wname = wname if isinstance(wname, str) else wname["name"]
        w = c.get(f"/aeroplanes/{pid}/wings/{wname}").json()
        changes = straighten(w["x_secs"])
        _report(wname, changes)
        if not apply:
            continue
        for ch in changes:
            r = c.patch(
                f"/aeroplanes/{pid}/wings/{wname}/cross_sections/{ch['index']}/trailing_edge_device",
                json={"rel_chord_root": ch["new"][0], "rel_chord_tip": ch["new"][1]},
            )
            if r.status_code >= 300:
                sys.exit(f"FEHLER {wname} #{ch['index']}: {r.status_code} {r.text[:300]}")
    print("geschrieben" if apply else "Trockenlauf - nichts geschrieben (--apply zum Schreiben)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--api", help="da3Dalus API base URL, e.g. http://localhost:8001")
    src.add_argument("--json", type=pathlib.Path, help="plugin export file (<key>.airplane.json)")
    ap.add_argument("--aeroplane", help="aeroplane name or id (with --api)")
    ap.add_argument("--apply", action="store_true", help="write the corrected values")
    a = ap.parse_args()
    if a.api:
        if not a.aeroplane:
            ap.error("--aeroplane is required with --api")
        _run_api(a.api, a.aeroplane, a.apply)
    else:
        _run_json(a.json, a.apply)


if __name__ == "__main__":
    main()
