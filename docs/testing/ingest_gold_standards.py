"""Ingest the gold-standard aircraft into the running backend via REST.

Multi-step workflow (no single-endpoint upload exists):
1. POST /aeroplanes?name=...                         -> creates empty aeroplane
2. POST /aeroplanes/{id}/wings/{name}/from-wingconfig -> for each wing
3. PATCH each asymmetric trailing_edge_device         -> workaround for gh-523

Mass is intentionally NOT set here — /total_mass_kg is the obsolete path;
the canonical mass source is the component tree / weight items, which a
separate fixture (or the UI) is responsible for populating.

The asymmetric TED PATCH is a workaround for gh-523: the
/from-wingconfig endpoint silently drops trailing_edge_devices whose
`symmetric` field is `false`. Until that is fixed in the endpoint,
we add ailerons/rudders one-by-one via
PATCH /wings/{name}/cross_sections/{idx}/trailing_edge_device.

Run from the repo root with the backend listening on localhost:8001:

    poetry run python docs/testing/ingest_gold_standards.py
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx

BASE = "http://localhost:8001"
DOCS_TESTING = Path(__file__).parent

AIRCRAFT = [
    {
        "config_json": DOCS_TESTING / "airplane-config-ask21.json",
        "wing_names": ["main_wing", "horizontal_tail", "vertical_fin"],
    },
    {
        "config_json": DOCS_TESTING / "airplane-config-c172n.json",
        "wing_names": ["main_wing", "horizontal_tail", "vertical_fin"],
    },
]


def existing_aeroplane_id(client: httpx.Client, name: str) -> str | None:
    resp = client.get("/aeroplanes")
    resp.raise_for_status()
    for ap in resp.json()["aeroplanes"]:
        if ap["name"] == name:
            return ap["id"]
    return None


def ingest_aircraft(client: httpx.Client, config_path: Path, wing_names: list[str]) -> str:
    with open(config_path) as f:
        cfg = json.load(f)

    name = cfg["name"]

    # Drop any existing aeroplane with this name first
    existing = existing_aeroplane_id(client, name)
    if existing:
        print(f"  delete existing {name} ({existing})")
        client.delete(f"/aeroplanes/{existing}").raise_for_status()

    # 1) Create empty aeroplane
    resp = client.post("/aeroplanes", params={"name": name})
    resp.raise_for_status()
    aeroplane_id = resp.json()["id"]
    print(f"  created aeroplane {name} -> {aeroplane_id}")

    # 2) POST each wing
    assert len(cfg["wings"]) == len(wing_names), \
        f"{len(cfg['wings'])} wings in config vs {len(wing_names)} names supplied"
    for wing_name, wing_body in zip(wing_names, cfg["wings"]):
        resp = client.post(
            f"/aeroplanes/{aeroplane_id}/wings/{wing_name}/from-wingconfig",
            json=wing_body,
        )
        if resp.status_code >= 400:
            print(f"    ✗ wing {wing_name}: {resp.status_code} {resp.text[:400]}")
            resp.raise_for_status()
        print(f"    ✓ wing {wing_name}")

        # 2b) Workaround for gh-523: PATCH asymmetric TEDs that the
        # bulk endpoint silently dropped. The PATCH endpoint accepts a
        # strict subset of the WingConfig TED fields — strip servo
        # plumbing (handled via a separate endpoint).
        PATCH_TED_FIELDS = {
            "name", "rel_chord_root", "rel_chord_tip",
            "hinge_spacing", "side_spacing_root", "side_spacing_tip",
            "rel_chord_servo_position", "rel_length_servo_position",
            "servo_placement",
            "positive_deflection_deg", "negative_deflection_deg",
            "trailing_edge_offset_factor", "hinge_type", "symmetric",
        }
        for seg_idx, seg in enumerate(wing_body["segments"]):
            ted = seg.get("trailing_edge_device")
            if not ted or ted.get("symmetric") is not False:
                continue
            patch_body = {k: v for k, v in ted.items() if k in PATCH_TED_FIELDS}
            url = (f"/aeroplanes/{aeroplane_id}/wings/{wing_name}"
                   f"/cross_sections/{seg_idx}/trailing_edge_device")
            r = client.patch(url, json=patch_body)
            if r.status_code >= 400:
                print(f"      ✗ PATCH ted '{ted['name']}' @ xsec {seg_idx}: "
                      f"{r.status_code} {r.text[:200]}")
            else:
                print(f"      ✓ PATCH ted '{ted['name']}' @ xsec {seg_idx}")

    # Mass deliberately not set: /total_mass_kg is obsolete; mass comes
    # from the component tree / weight items, populated elsewhere.

    return aeroplane_id


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=60.0) as client:
        # Smoke ping
        resp = client.get("/aeroplanes")
        resp.raise_for_status()
        print(f"Backend reachable, {len(resp.json()['aeroplanes'])} aeroplanes present.\n")

        results: list[tuple[str, str]] = []
        for spec in AIRCRAFT:
            print(f"Ingesting {spec['config_json'].name}")
            aid = ingest_aircraft(client, spec["config_json"], spec["wing_names"])
            with open(spec["config_json"]) as f:
                name = json.load(f)["name"]
            results.append((name, aid))
            print()

        print("=" * 60)
        print("Aircraft now in backend:")
        for name, aid in results:
            print(f"  {name:30s}  {aid}")


if __name__ == "__main__":
    main()
