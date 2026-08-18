"""Dimensional algebra for the calculation canon.

Tracks the SI dimension vector (M, L, T, Theta, I, N, J) AND the length scale, because
this codebase's specific hazard is millimetres inside a metre world (ADR 0001): a pure
dimension check passes mm against m, and that is exactly the bug class it must catch.
Angle is carried as its own slot so degrees cannot silently meet radians.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field

BASES = ("M", "L", "T", "K", "I", "N", "J", "ANG")


@dataclass(frozen=True)
class Dim:
    e: tuple = field(default=(0,) * len(BASES))
    scale: float = 1.0  # metres per unit of length used, 1e-3 for mm

    def __mul__(self, o):
        return Dim(tuple(a + b for a, b in zip(self.e, o.e, strict=True)), self.scale * o.scale)

    def __truediv__(self, o):
        return Dim(tuple(a - b for a, b in zip(self.e, o.e, strict=True)), self.scale / o.scale)

    def __pow__(self, n):
        return Dim(tuple(a * n for a in self.e), self.scale**n)

    def sqrt(self):
        return self**0.5

    @property
    def dimensionless(self):
        return all(a == 0 for a in self.e)

    def same_dim(self, o):
        return self.e == o.e

    def __str__(self):
        num = [f"{b}^{a:g}" if a != 1 else b for b, a in zip(BASES, self.e, strict=True) if a > 0]
        den = [f"{b}^{-a:g}" if a != -1 else b for b, a in zip(BASES, self.e, strict=True) if a < 0]
        s = "·".join(num) or "1"
        if den:
            s += " / " + "·".join(den)
        return s


def _d(**kw):
    return Dim(tuple(kw.get(b, 0) for b in BASES), kw.pop("_scale", 1.0))


ONE = Dim()
UNITS = {
    "-": ONE,
    "": ONE,
    "1": ONE,
    "none": ONE,
    "dimensionless": ONE,
    "ratio": ONE,
    "fraction": ONE,
    "%": ONE,
    "pct": ONE,
    "count": ONE,
    "index": ONE,
    "bool": ONE,
    "kg": _d(M=1),
    "g": _d(M=1),
    "m": _d(L=1),
    "mm": Dim(_d(L=1).e, 1e-3),
    "cm": Dim(_d(L=1).e, 1e-2),
    "km": Dim(_d(L=1).e, 1e3),
    "s": _d(T=1),
    "min": _d(T=1),
    "h": _d(T=1),
    "hr": _d(T=1),
    "k": _d(K=1),
    "a": _d(I=1),
    "mol": _d(N=1),
    "cd": _d(J=1),
    "rad": _d(ANG=1),
    "deg": _d(ANG=1),
    "degree": _d(ANG=1),
    "°": _d(ANG=1),
    "n": _d(M=1, L=1, T=-2),
    "pa": _d(M=1, L=-1, T=-2),
    "j": _d(M=1, L=2, T=-2),
    "w": _d(M=1, L=2, T=-3),
    "v": _d(M=1, L=2, T=-3, I=-1),
    "wh": _d(M=1, L=2, T=-2),
    "mpa": _d(M=1, L=-1, T=-2),
    "gpa": _d(M=1, L=-1, T=-2),
    "bar": _d(M=1, L=-1, T=-2),
    "hz": _d(T=-1),
    "rpm": _d(T=-1),
    "kt": _d(L=1, T=-1),
    "knot": _d(L=1, T=-1),
}
#: unit strings that are prose for "dimensionless" in this codebase's registers
_PROSE_ONE = re.compile(
    r"^(–|-|—)?\s*(dimensionless|fraction|ratio|boolean|bool|enum|count|panels|points|"
    r"stations|x/c|chord fraction|fraction of mac|span fraction|percent|pct|%|n/a|na|"
    r"flag|index|-|—|–)\s*$"
)


def parse_unit(u: str) -> Dim | None:
    """'N·m', 'm/s^2', 'kg/m3', 'mm³' -> Dim, or None when unparseable."""
    if u is None:
        return None
    s = u.strip().lower()
    if s in UNITS:
        return UNITS[s]
    # strip trailing prose in parentheses: "– (fraction of MAC)" -> "–"
    core = re.sub(r"\s*\(.*?\)\s*", " ", s).strip()
    if _PROSE_ONE.match(core) or _PROSE_ONE.match(s):
        return ONE
    s = core or s
    if s in UNITS:
        return UNITS[s]
    m1 = re.match(r"^1\s*/\s*(.+)$", s)  # "1/rad", "1/s"
    if m1:
        inner = parse_unit(m1.group(1))
        return (ONE / inner) if inner is not None else None
    s = (
        s.replace("²", "^2")
        .replace("³", "^3")
        .replace("⁴", "^4")
        .replace("⁻", "^-")
        .replace("·", "*")
        .replace("×", "*")
        .replace(" per ", "/")
        .replace("•", "*")
    )
    s = re.sub(r"\s*\(.*?\)\s*", "", s).strip()
    if not s or s in UNITS:
        return UNITS.get(s)
    num: list[Dim] = []
    den: list[Dim] = []
    cur = num
    for part in re.split(r"([*/])", s):
        if part == "/":
            cur = den
            continue
        if part == "*":
            cur = num
            continue
        p = part.strip()
        if not p:
            continue
        m = re.match(r"^([a-zA-Zµ°%]+)\^?(-?\d+(?:\.\d+)?)?$", p)
        if not m:
            m2 = re.match(r"^([a-zA-Zµ°%]+?)(\d)$", p)  # kg/m3
            if not m2:
                return None
            base, exp = m2.group(1), float(m2.group(2))
        else:
            base, exp = m.group(1), float(m.group(2) or 1)
        if base not in UNITS:
            return None
        cur.append(UNITS[base] ** exp)
    out = ONE
    for d in num:
        out = out * d
    for d in den:
        out = out / d
    return out


def check(expr_dim: Dim, declared: Dim) -> str:
    """Compare a computed dimension against a declared unit."""
    if expr_dim is None or declared is None:
        return "UNPARSEABLE"
    if not expr_dim.same_dim(declared):
        return "DIMENSION_MISMATCH"
    if abs(expr_dim.scale / declared.scale - 1.0) > 1e-9:
        return "SCALE_MISMATCH"
    return "OK"
