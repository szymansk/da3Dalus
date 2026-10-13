"""Put every trailing-edge device of an aeroplane on ONE straight hinge line (gh-1163).

A control surface spanning several segments stores its hinge per segment as chord
fraction at the inboard (``rel_chord_root``) and outboard (``rel_chord_tip``)
section. Rounded or hand-edited values leave small kinks and mismatches at shared
sections. This fits, per device name and wing, a straight line through the stored
hinge points (plan view; side view for vertical surfaces) and rewrites root/tip of
every segment from that line, so neighbouring segments agree at their shared
section. Where the straight hinge leaves the outline behind the trailing edge the
device ends: the segment is split there by a new section on the existing outline and
the outer piece gets no device. A hinge ahead of the leading edge means the whole
section moves (fraction 0). Stored fractions of exactly 0 or 1 are such edge values
and do not define the line.

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
import copy
import json
import math
import pathlib
import sys

import numpy as np

DECIMALS = 4
EDGE_TOL_M = 1e-5  # a hinge within 0.01 mm of the trailing edge is on it


def _span_axis(x_secs: list[dict]) -> int:
    """1 (y) for horizontal surfaces, 2 (z) for vertical ones."""
    ys = [x["xyz_le"][1] for x in x_secs]
    zs = [x["xyz_le"][2] for x in x_secs]
    return 2 if np.ptp(zs) > np.ptp(ys) else 1


def _hinge_x(x: dict, rel: float) -> float:
    return x["xyz_le"][0] + rel * x["chord"] * math.cos(math.radians(x.get("twist") or 0.0))


def _rel(x: dict, hinge_x: float) -> float:
    return (hinge_x - x["xyz_le"][0]) / (x["chord"] * math.cos(math.radians(x.get("twist") or 0.0)))


def _fit_lines(x_secs: list[dict]) -> dict[str, tuple[list[int], float, float, float]]:
    """Per device name: its segments and the straight hinge line x = slope*span + offset.

    Also returns the largest distance (mm) of the stored hinge points from that line.
    """
    k = _span_axis(x_secs)
    by_name: dict[str, list[int]] = {}
    for i, x in enumerate(x_secs[:-1]):
        ted = x.get("trailing_edge_device")
        if ted and ted.get("rel_chord_root") is not None:
            by_name.setdefault(ted.get("name") or "", []).append(i)

    lines = {}
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
        err = 1000 * float(np.max(np.abs(p[:, 1] - (slope * p[:, 0] + offset))))
        lines[name] = (segs, float(slope), float(offset), round(err, 2))
    return lines


def _rel_on_line(x: dict, k: int, slope: float, offset: float) -> float:
    return _rel(x, slope * x["xyz_le"][k] + offset)


def straighten(x_secs: list[dict]) -> list[dict]:
    """Return one change record per TED segment: index, name, old and new root/tip.

    ``x_secs`` are wing cross-sections as the API returns them (metres, degrees).
    Fractions are clamped to 0..1; ``rebuild`` instead ends a device where its hinge
    leaves the outline.
    """
    k = _span_axis(x_secs)
    changes = []
    for name, (segs, slope, offset, err) in _fit_lines(x_secs).items():

        def on_line(x: dict, slope: float = slope, offset: float = offset) -> tuple[float, bool]:
            r = _rel_on_line(x, k, slope, offset)
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
                    "line_error_mm": err,
                }
            )
    return changes


def _between(a: dict, b: dict, t: float) -> dict:
    """Cross-section at fraction ``t`` of the straight segment a -> b (same outline)."""
    x = {key: v for key, v in a.items() if key not in _SEGMENT_KEYS}
    x["xyz_le"] = [
        round(p + t * (q - p), 6) for p, q in zip(a["xyz_le"], b["xyz_le"], strict=True)
    ]  # micrometres, like the stored sections
    x["chord"] = round(a["chord"] + t * (b["chord"] - a["chord"]), 6)
    tw_a, tw_b = a.get("twist") or 0.0, b.get("twist") or 0.0
    x["twist"] = round(tw_a + t * (tw_b - tw_a), 4)
    # spars continue on their own line through the new section
    spars = [dict(sp, spare_mode="follow") for sp in a.get("spare_list") or []]
    if "spare_list" in a:
        x["spare_list"] = spars
    return x


# per-segment data that belongs to the segment starting at a section, not to its shape
_SEGMENT_KEYS = ("trailing_edge_device", "control_surface", "spare_list")


def rebuild(x_secs: list[dict]) -> tuple[list[dict], dict]:
    """Put every device on its straight hinge line and end it where the line leaves the outline.

    Where the straight hinge would lie behind the trailing edge (fraction > 1) there
    is no control surface: the segment is split at the crossing by a new section on
    the existing outline, the device ends there at fraction 1 and the outer piece
    carries none. A fraction below 0 (hinge ahead of the leading edge) means the whole
    section moves and is stored as 0. A hinge that leaves the outline between two
    sections of the same device cannot be one control surface: ``ValueError``.

    Returns the new cross-section list (input untouched) and a report:
    ``changes`` (as ``straighten``, final indices), ``inserted``, ``removed``.
    """
    k = _span_axis(x_secs)
    xs = copy.deepcopy(x_secs)
    cuts: list[tuple[int, float]] = []  # (segment, fraction along it) to split
    removed: list[int] = []
    lines = _fit_lines(xs)
    for name, (segs, slope, offset, _err) in lines.items():
        span = [segs[0]] + [i + 1 for i in segs]  # sections of this device, in order
        rel = {i: _rel_on_line(xs[i], k, slope, offset) for i in span}
        # behind the trailing edge by more than the stored micrometre resolution
        beyond = [i for i in span if (rel[i] - 1.0) * xs[i]["chord"] > EDGE_TOL_M]
        if not beyond:
            continue
        # beyond the trailing edge is only allowed in a closed run at the outer end
        tail = span[span.index(beyond[0]) :]
        if beyond != tail or len(tail) == len(span):
            raise ValueError(
                f"{name}: Scharniergerade verlaesst die Kontur zwischen den Schnitten "
                f"{beyond} - das ist kein durchgehendes Ruder"
            )
        a = span[span.index(beyond[0]) - 1]  # last section with the hinge inside
        b = beyond[0]
        te_a = _hinge_x(xs[a], 1.0) - (slope * xs[a]["xyz_le"][k] + offset)
        te_b = _hinge_x(xs[b], 1.0) - (slope * xs[b]["xyz_le"][k] + offset)
        cuts.append((a, te_a / (te_a - te_b)))
        removed += [i for i in segs if i >= b]

    for i in removed:
        xs[i].pop("trailing_edge_device", None)
        xs[i].pop("control_surface", None)
    removed_ids = {id(xs[i]) for i in removed}
    inserted = []
    for seg, t in sorted(cuts, reverse=True):
        new = _between(xs[seg], xs[seg + 1], t)
        if xs[seg].get("x_sec_type") == "tip":
            xs[seg]["x_sec_type"], xs[seg]["tip_type"] = "segment", None
        elif new.get("x_sec_type") == "root":
            new["x_sec_type"] = "segment"
        xs.insert(seg + 1, new)
        inserted = [j + 1 for j in inserted] + [seg + 1]
    inserted.sort()
    removed = [i for i, x in enumerate(xs) if id(x) in removed_ids]

    # values from the line fitted to the stored input (refitting the cut device would
    # move the line away from the crossing it was split at)
    changes = []
    for i, x in enumerate(xs[:-1]):
        ted = x.get("trailing_edge_device")
        if not ted or (ted.get("name") or "") not in lines:
            continue
        name = ted.get("name") or ""
        _segs, slope, offset, err = lines[name]
        r_root, r_tip = (_rel_on_line(y, k, slope, offset) for y in (x, xs[i + 1]))
        new = tuple(round(min(1.0, max(0.0, r)), DECIMALS) for r in (r_root, r_tip))
        changes.append(
            {
                "index": i,
                "name": name,
                "old": (ted["rel_chord_root"], ted.get("rel_chord_tip")),
                "new": new,
                "clamped": bool(r_root < 0 or r_tip < 0),
                "line_error_mm": err,
            }
        )
        ted["rel_chord_root"], ted["rel_chord_tip"] = new
        cs = x.get("control_surface")
        if cs is not None:
            cs["hinge_point"] = new[0]
    return xs, {"changes": changes, "inserted": inserted, "removed": removed}


_GEOMETRY_KEYS = ("xyz_le", "chord", "twist", "airfoil", "x_sec_type", "tip_type")


def _report(wing: str, changes: list[dict], inserted: list[int], removed: list[int]) -> None:
    for c in changes:
        mark = "  (Scharnier vor der Nasenleiste: ganze Tiefe beweglich)" if c["clamped"] else ""
        print(
            f"  {wing} #{c['index']:2d} {c['name']}: root {c['old'][0]} -> {c['new'][0]}, "
            f"tip {c['old'][1]} -> {c['new'][1]}{mark}"
        )
    for i in inserted:
        print(
            f"  {wing} #{i:2d} neuer Schnitt: hier verlaesst das Scharnier die Endleiste, Ruder endet"
        )
    for i in removed:
        print(f"  {wing} #{i:2d} kein Ruder mehr (Scharnier hinter der Endleiste)")
    for name in sorted({c["name"] for c in changes}):
        err = next(c["line_error_mm"] for c in changes if c["name"] == name)
        print(f"  {wing} {name}: alte Punkte max. {err} mm neben der Geraden")


def _run_json(path: pathlib.Path, apply: bool) -> None:
    text = path.read_text()
    geo = json.loads(text)
    second = text.splitlines()[1] if "\n" in text else ""
    indent = len(second) - len(second.lstrip(" ")) or None  # keep the file's own layout
    for wname, w in geo["wings"].items():
        w["x_secs"], rep = rebuild(w["x_secs"])
        _report(wname, rep["changes"], rep["inserted"], rep["removed"])
    if apply:
        out = json.dumps(geo, indent=indent, ensure_ascii=False)
        path.write_text(out + "\n" if text.endswith("\n") else out)
        print(f"geschrieben: {path}")


def _run_api(api: str, aeroplane: str, apply: bool) -> None:
    import httpx

    c = httpx.Client(base_url=api.rstrip("/"), timeout=30)

    def ok(r: httpx.Response, what: str) -> httpx.Response:
        if r.status_code >= 300:
            sys.exit(f"FEHLER {what}: {r.status_code} {r.text[:300]}")
        return r

    r = ok(c.get("/aeroplanes"), "Flugzeuge")
    body = r.json()
    planes = body["aeroplanes"] if isinstance(body, dict) else body
    hits = [p for p in planes if aeroplane in (p.get("id"), p.get("name"))]
    if len(hits) != 1:
        sys.exit(f"Flugzeug {aeroplane!r}: {len(hits)} Treffer - Name oder id eindeutig angeben")
    pid = hits[0]["id"]
    wings = c.get(f"/aeroplanes/{pid}/wings").json()
    for wname in wings["wings"] if isinstance(wings, dict) else wings:
        wname = wname if isinstance(wname, str) else wname["name"]
        old = ok(c.get(f"/aeroplanes/{pid}/wings/{wname}"), wname).json()["x_secs"]
        new, rep = rebuild(old)
        _report(wname, rep["changes"], rep["inserted"], rep["removed"])
        if not apply:
            continue
        base = f"/aeroplanes/{pid}/wings/{wname}/cross_sections"
        for i in rep["inserted"]:  # ascending: each index is final once the ones before exist
            geo = {key: new[i][key] for key in _GEOMETRY_KEYS if new[i].get(key) is not None}
            ok(c.post(f"{base}/{i}", json=geo), f"{wname} neuer Schnitt #{i}")
            for sp in new[i].get("spare_list") or []:
                body = {
                    key: v for key, v in sp.items() if key not in ("spare_origin", "spare_vector")
                }
                ok(c.post(f"{base}/{i}/spars", json=body), f"{wname} Holm @{i}")
            prev = new[i - 1]  # may have handed its tip classification to the new section
            geo = {key: prev.get(key) for key in _GEOMETRY_KEYS}
            ok(c.put(f"{base}/{i - 1}", json=geo), f"{wname} Schnitt #{i - 1}")
        for i in rep["removed"]:
            ok(c.delete(f"{base}/{i}/trailing_edge_device"), f"{wname} Ruder #{i} entfernen")
        for ch in rep["changes"]:
            ok(
                c.patch(
                    f"{base}/{ch['index']}/trailing_edge_device",
                    json={"rel_chord_root": ch["new"][0], "rel_chord_tip": ch["new"][1]},
                ),
                f"{wname} #{ch['index']}",
            )
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
