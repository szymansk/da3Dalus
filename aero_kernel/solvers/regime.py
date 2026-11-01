"""The regime check of the aerodynamic adapters: Reynolds and Mach numbers (ADR 0028, ch. 8.2, #1342).

The Reynolds number is evaluated at every station and aggregated per surface (at its mean aerodynamic
chord) and per control device (its own stations); the Mach number once per evaluation. Adapters know
no canon names: the warnings carry no ``origin``; the engine sets it.
"""

import math
from collections.abc import Mapping, Sequence
from itertools import pairwise
from typing import Self

from aero_kernel.geometry import Wing
from aero_kernel.schema import KernelWarning
from aero_kernel.solvers.devices import segment_label
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

__all__ = ["SurfaceSections", "regime_by_surface"]

# The RC/UAV regime of ADR 0028, defined by flow physics.
_RE_BAND_MIN = 3.0e4
_RE_BUBBLE_MAX = 7.0e4
_RE_BAND_MAX = 1.0e6
_MACH_LIMIT = 0.3
_MACH_VALIDITY = 0.6


class SurfaceSections(BaseModel):
    """The sections of one lifting surface, in stored order, as the regime check reads them (#1342).

    Attributes:
        chords_m: The chord of each section (station) in m, all > 0.
        spans_m: The span of each segment between two adjacent stations in m: the distance of the
            leading edges in the y-z plane, the plane AeroBuildup measures a section's span in (y for a
            wing, z for a fin, both for a dihedral panel); at least one > 0.
        c_mac_m: The mean aerodynamic chord of the surface in m (AeroSandbox's, the one producer:
            ``Wing.mean_aerodynamic_chord()``, which is the area-weighted chord ``int c^2 dy / int c dy``).
        devices: The label of the control device on each segment, ``None`` where there is none.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    chords_m: tuple[float, ...] = Field(min_length=2)
    spans_m: tuple[float, ...]
    c_mac_m: float = Field(gt=0.0, allow_inf_nan=False)
    devices: tuple[str | None, ...]

    @model_validator(mode="after")
    def _check_sections(self) -> Self:
        """Require positive finite chords, one span and one device per segment, and an area."""
        segments = len(self.chords_m) - 1
        if len(self.spans_m) != segments or len(self.devices) != segments:
            msg = "spans_m and devices need one entry per segment between two chords"
            raise ValueError(msg)
        if not all(math.isfinite(c) and c > 0.0 for c in self.chords_m):
            msg = "every chord must be finite and > 0"
            raise ValueError(msg)
        if not all(math.isfinite(s) and s >= 0.0 for s in self.spans_m) or sum(self.spans_m) <= 0.0:
            msg = "the spans must be finite, >= 0 and not all zero"
            raise ValueError(msg)
        return self

    @classmethod
    def of(cls, wing: Wing, c_mac_m: float) -> Self:
        """The sections of a validated surface, with its mean aerodynamic chord.

        Args:
            wing: One surface of a validated geometry document.
            c_mac_m: Its mean aerodynamic chord in m, from AeroSandbox.

        Returns:
            Chords, the y-z spans of the segments and their devices, in stored order.
        """
        sections = wing.x_secs
        return cls(
            chords_m=tuple(s.chord for s in sections),
            spans_m=tuple(
                math.dist(inner.xyz_le[1:], outer.xyz_le[1:]) for inner, outer in pairwise(sections)
            ),
            c_mac_m=c_mac_m,
            devices=tuple(
                None if s.trailing_edge_device is None else segment_label(s.trailing_edge_device, i)
                for i, s in enumerate(sections[:-1])
            ),
        )


def _require_positive(name: str, value: float) -> None:
    """Raise ``ValueError`` unless ``value`` is greater than zero."""
    if not value > 0.0:
        msg = f"{name} must be > 0, got {value}"
        raise ValueError(msg)


def _check_flow(v_ms: float, speed_of_sound_ms: float, kinematic_viscosity_m2s: float) -> None:
    """Raise ``ValueError`` for a speed, speed of sound or viscosity that is not physical."""
    for name, value in (
        ("v_ms", v_ms),
        ("speed_of_sound_ms", speed_of_sound_ms),
        ("kinematic_viscosity_m2s", kinematic_viscosity_m2s),
    ):
        if not math.isfinite(value):
            msg = f"{name} must be finite, got {value}"
            raise ValueError(msg)
    if v_ms < 0.0:
        msg = f"v_ms must be >= 0, got {v_ms}"
        raise ValueError(msg)
    _require_positive("speed_of_sound_ms", speed_of_sound_ms)
    _require_positive("kinematic_viscosity_m2s", kinematic_viscosity_m2s)


def _share_below(chord_a: float, chord_b: float, chord_limit: float) -> tuple[float, float]:
    """The span and area fractions of a linearly tapered segment whose chord is below a limit.

    Returns:
        The fraction of the segment's span, and its area below the limit per metre of span.
    """
    low, high = min(chord_a, chord_b), max(chord_a, chord_b)
    if chord_limit <= low:
        return 0.0, 0.0
    if chord_limit >= high:
        return 1.0, (low + high) / 2.0
    fraction = (chord_limit - low) / (high - low)
    return fraction, fraction * (low + chord_limit) / 2.0


class _Shares(BaseModel):
    """The span and area of some segments of a surface, and the parts below a chord limit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    span: float
    area: float
    span_below: float
    area_below: float


def _shares(sections: SurfaceSections, segments: Sequence[int], chord_limit: float) -> _Shares:
    """Sum span and area of ``segments``, and the parts whose chord lies below ``chord_limit``."""
    span = area = span_below = area_below = 0.0
    for k in segments:
        chord_a, chord_b, width = (
            sections.chords_m[k],
            sections.chords_m[k + 1],
            sections.spans_m[k],
        )
        fraction, area_per_span = _share_below(chord_a, chord_b, chord_limit)
        span += width
        area += width * (chord_a + chord_b) / 2.0
        span_below += width * fraction
        area_below += width * area_per_span
    return _Shares(span=span, area=area, span_below=span_below, area_below=area_below)


def _ratio(part: float, whole: float) -> float:
    """``part / whole``; zero for an empty whole (a device on segments of zero span)."""
    return part / whole if whole > 0.0 else 0.0


def _lowest(chords: Sequence[float], stations: Sequence[int]) -> int:
    """The station of the smallest chord among ``stations`` (the first one on a tie)."""
    return min(stations, key=lambda i: chords[i])


class _Flow(BaseModel):
    """Speed and kinematic viscosity, and the chords of the band edges they give."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    v_ms: float
    nu: float

    def reynolds(self, chord: float) -> float:
        """The chord Reynolds number ``V c / nu``."""
        return self.v_ms * chord / self.nu

    def chord_at(self, reynolds: float) -> float:
        """The chord of a Reynolds number; any chord is below it at rest."""
        return reynolds * self.nu / self.v_ms if self.v_ms > 0.0 else math.inf


def _surface_detail(name: str, sections: SurfaceSections, flow: _Flow) -> dict[str, JsonValue]:
    """What every Reynolds warning of a surface carries: where, and how much of it (#1342)."""
    everything = range(len(sections.spans_m))
    band = _shares(sections, everything, flow.chord_at(_RE_BAND_MIN))
    bubble = _shares(sections, everything, flow.chord_at(_RE_BUBBLE_MAX))
    station = _lowest(sections.chords_m, range(len(sections.chords_m)))
    return {
        "wing": name,
        "re_mac": flow.reynolds(sections.c_mac_m),
        "c_mac_m": sections.c_mac_m,
        "re_min": flow.reynolds(sections.chords_m[station]),
        "re_min_station": station,
        "area_share_below_band": _ratio(band.area_below, band.area),
        "area_share_below_bubble": _ratio(bubble.area_below, bubble.area),
        "span_share_below_band": _ratio(band.span_below, band.span),
    }


def _surface_warning(
    name: str, detail: dict[str, JsonValue], re_mac: float
) -> KernelWarning | None:
    """The one Reynolds warning of a surface, judged by the Reynolds number at its MAC."""
    where = (
        f"lowest {detail['re_min']:.0f} at x_secs[{detail['re_min_station']}], "
        f"{detail['area_share_below_band']:.0%} of the area below {_RE_BAND_MIN:.0f}"
    )
    if re_mac < _RE_BAND_MIN:
        code, message = (
            "reynolds_outside_band",
            f"below the core band {_RE_BAND_MIN:.0f}..{_RE_BAND_MAX:.0f} (ADR 0028): its section "
            "polars (C_L,max, C_D) are less reliable",
        )
    elif re_mac < _RE_BUBBLE_MAX:
        code, message = (
            "reynolds_bubble_sensitive",
            f"below {_RE_BUBBLE_MAX:.0f}: laminar separation bubbles dominate and the result is "
            "sensitive to transition",
        )
    elif re_mac > _RE_BAND_MAX:
        code, message = (
            "reynolds_above_band",
            f"above the core band's {_RE_BAND_MAX:.0f}: the tools stay valid and the physics more benign",
        )
    else:
        return None
    return KernelWarning.of(
        code,
        f"Wing {name!r}: the Reynolds number at the mean aerodynamic chord is {re_mac:.0f}, "
        f"{message} ({where}).",
        detail=detail,
    )


def _device_segments(sections: SurfaceSections) -> dict[str, list[int]]:
    """The segments of each device, in stored order."""
    found: dict[str, list[int]] = {}
    for k, device in enumerate(sections.devices):
        if device is not None:
            found.setdefault(device, []).append(k)
    return found


def _device_warnings(
    name: str, sections: SurfaceSections, flow: _Flow, detail: dict[str, JsonValue]
) -> list[KernelWarning]:
    """A warning per device with a station of its span below the band (#1342).

    Stall and control effectiveness of a device are decided on its own span, so a device is judged by
    its stations, not by the surface's MAC.
    """
    warnings: list[KernelWarning] = []
    limit = flow.chord_at(_RE_BAND_MIN)
    for device, segments in _device_segments(sections).items():
        stations = sorted(set(segments) | {k + 1 for k in segments})
        station = _lowest(sections.chords_m, stations)
        re_min = flow.reynolds(sections.chords_m[station])
        if re_min >= _RE_BAND_MIN:
            continue
        shares = _shares(sections, segments, limit)
        span_share = _ratio(shares.span_below, shares.span)
        warnings.append(
            KernelWarning.of(
                "reynolds_outside_band_at_device",
                f"Wing {name!r}, device {device!r}: the Reynolds number falls to {re_min:.0f} at "
                f"x_secs[{station}], below the core band's {_RE_BAND_MIN:.0f} (ADR 0028), on "
                f"{span_share:.0%} of the device span; stall and control effectiveness of the "
                "device are decided there.",
                detail={
                    **detail,
                    "device": device,
                    "device_re_min": re_min,
                    "device_re_min_station": station,
                    "device_span_share_below_band": span_share,
                },
            )
        )
    return warnings


def _mach_warning(mach: float) -> KernelWarning | None:
    """The Mach warning of an evaluation; it depends on no chord, so it is raised once."""
    if mach > _MACH_VALIDITY:
        return KernelWarning.of(
            "mach_beyond_validity",
            f"Mach {mach:.2f} is beyond {_MACH_VALIDITY}: compressibility not modelled",
            detail={"mach": mach},
        )
    if mach > _MACH_LIMIT:
        return KernelWarning.of(
            "mach_above_limit",
            f"Mach {mach:.2f} is above {_MACH_LIMIT}: compressibility is neglected",
            detail={"mach": mach},
        )
    return None


def regime_by_surface(
    surfaces: Mapping[str, SurfaceSections],
    v_ms: float,
    speed_of_sound_ms: float,
    kinematic_viscosity_m2s: float,
) -> list[KernelWarning]:
    """Check the Reynolds and Mach numbers of an evaluation against the RC/UAV regime (ADR 0028).

    The Reynolds number ``V c / nu`` is evaluated at every station; it is aggregated per surface and
    per device (#1342, ADR 0028 amended 2026-11-01): **one** warning per surface, judged by the
    Reynolds number at its mean aerodynamic chord (the area-weighted Reynolds number) —
    ``reynolds_outside_band`` below 3e4 (warning), ``reynolds_bubble_sensitive`` from 3e4 to 7e4
    (notice), ``reynolds_above_band`` above 1e6 (notice) — and one ``reynolds_outside_band_at_device``
    (warning) per control device with a station of its span below 3e4. Every Reynolds warning names
    the surface and carries where and how much: the Reynolds number at the MAC, the lowest station
    and its Reynolds number, and the area and span shares below the band edges. The Mach warning is
    raised once: ``mach_above_limit`` (0.3 < M <= 0.6, notice), ``mach_beyond_validity`` (M > 0.6,
    error). Raised where Re and Mach become known, in the adapters (ch. 8.2).

    Args:
        surfaces: The sections of each surface by wing key.
        v_ms: Evaluated airspeed in m/s (>= 0).
        speed_of_sound_ms: Speed of sound at the altitude in m/s (> 0).
        kinematic_viscosity_m2s: Kinematic viscosity at the altitude in m^2/s (> 0).

    Returns:
        The warnings, surfaces in the order given (each surface before its devices), Mach last.

    Raises:
        ValueError: If the speed, the speed of sound or the viscosity is not finite or not physical.
    """
    _check_flow(v_ms, speed_of_sound_ms, kinematic_viscosity_m2s)
    flow = _Flow(v_ms=v_ms, nu=kinematic_viscosity_m2s)
    warnings: list[KernelWarning] = []
    for name, sections in surfaces.items():
        detail = _surface_detail(name, sections, flow)
        surface = _surface_warning(name, detail, flow.reynolds(sections.c_mac_m))
        warnings += [] if surface is None else [surface]
        warnings += _device_warnings(name, sections, flow, detail)
    mach = _mach_warning(v_ms / speed_of_sound_ms)
    return [*warnings, *([] if mach is None else [mach])]
