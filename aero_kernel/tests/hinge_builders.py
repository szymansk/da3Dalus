"""Small airplanes with control surfaces on every wing, for the hinge-moment tests."""

from typing import Any

from aero_kernel.geometry import AirplaneGeometry

__all__ = ["conventional", "device", "v_tail_plane", "wing_document"]

NACA = "naca0012"


def device(
    name: str | None, role: str, root: float = 0.7, tip: float | None = None, **extra: Any
) -> dict[str, Any]:
    """A trailing-edge device on the segment that starts at the rib carrying it."""
    return {
        "name": name,
        "role": role,
        "rel_chord_root": root,
        "rel_chord_tip": root if tip is None else tip,
        **extra,
    }


def wing_document(
    name: str,
    surface_type: str,
    ribs: list[tuple[float, float, float, float]],
    devices: dict[int, dict[str, Any]] | None = None,
    symmetric: bool = True,
    airfoil: str = NACA,
) -> dict[str, Any]:
    """A wing from ribs ``(x, y, z, chord)``; ``devices`` by the index of the rib a segment starts at."""
    return {
        "name": name,
        "surface_type": surface_type,
        "symmetric": symmetric,
        "x_secs": [
            {
                "xyz_le": [x, y, z],
                "chord": chord,
                "twist": 0.0,
                "airfoil": airfoil,
                **({"trailing_edge_device": (devices or {})[k]} if k in (devices or {}) else {}),
            }
            for k, (x, y, z, chord) in enumerate(ribs)
        ],
    }


def conventional(
    main: dict[int, dict[str, Any]] | None = None,
    tail: dict[int, dict[str, Any]] | None = None,
    fin: dict[int, dict[str, Any]] | None = None,
    main_ys: tuple[float, ...] = (0.0, 0.2, 0.4),
) -> AirplaneGeometry:
    """A 0.8 m span wing, a horizontal tail and an unmirrored fin, with the given devices."""
    wings = {
        "Main": wing_document(
            "Main wing",
            "main_wing",
            [(0.0, y, 0.0, 0.2) for y in main_ys],
            {1: device("aileron", "aileron", 0.75)} if main is None else main,
        ),
        "Tail": wing_document(
            "Tail",
            "horizontal_tail",
            [(0.6, 0.0, 0.0, 0.1), (0.6, 0.15, 0.0, 0.1)],
            {0: device("elevator", "elevator", 0.6)} if tail is None else tail,
        ),
        "Fin": wing_document(
            "Fin",
            "vertical_tail",
            [(0.6, 0.0, 0.0, 0.12), (0.6, 0.0, 0.12, 0.1)],
            {0: device("rudder", "rudder", 0.6)} if fin is None else fin,
            symmetric=False,
        ),
    }
    return AirplaneGeometry.model_validate({"name": "plane", "wings": wings})


def v_tail_plane() -> AirplaneGeometry:
    """A wing and a V-tail whose panels carry ruddervators."""
    wings = {
        "Main": wing_document(
            "Main wing",
            "main_wing",
            [(0.0, 0.0, 0.0, 0.2), (0.0, 0.4, 0.0, 0.2)],
        ),
        "V": wing_document(
            "V-tail",
            "v_tail",
            [(0.6, 0.0, 0.0, 0.1), (0.6, 0.12, 0.12, 0.1)],
            {0: device("ruddervator", "ruddervator", 0.6)},
        ),
    }
    return AirplaneGeometry.model_validate({"name": "v", "wings": wings})
