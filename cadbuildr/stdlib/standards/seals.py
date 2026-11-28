"""O-rings and their grooves (glands): AS568 sizes, ISO 3601 sections, gland design.

::

    oring("AS568-010")                 # ORing(id=6.07, cs=1.78)
    gland(1.78, "static_radial")       # Gland(depth=1.388, width=2.6, squeeze=22 %, fill=70 %)
    piston_groove(bore=20, cs=1.78)    # groove Ø + the AS568 ring that stretches 0-5 % onto it (2 % target)

Sources: AS568 (aerospace size standard, inch ID x cross-section; the dash
numbers here are the common -0xx, -1xx, -2xx, -3xx rings), ISO 3601-1 metric
cross-sections, and the usual gland design rules (Parker O-Ring Handbook ORD
5700): squeeze 15-30 % static radial, 10-20 % dynamic, 20-35 % face seal;
gland fill <= 85 % (design for ~70-75 %); installed stretch on the groove 0-5 % (target 2 %).
Grooves are modelled at the nominal; apply ISO 286 / Parker tolerances on top.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from ._common import StandardsError, lookup

__all__ = [
    "AS568",
    "GLAND_RULES",
    "ISO3601_SECTIONS",
    "Gland",
    "ORing",
    "PistonGroove",
    "gland",
    "oring",
    "piston_groove",
]

INCH = 25.4


# AS568 dash number -> (inside diameter in, cross-section in). From -011 / -110
# / -210 the IDs step by 1/16 in, from -325 by 1/8 in (AS568 size table).
def _r3(x: float) -> float:
    return float(f"{x + 1e-9:.3f}")


# fmt: off
AS568: Dict[str, Tuple[float, float]] = {
    **{f"AS568-{n:03d}": (i, 0.070) for n, i in
       ((4, 0.070), (5, 0.101), (6, 0.114), (7, 0.145), (8, 0.176), (9, 0.208), (10, 0.239))},
    **{f"AS568-{n:03d}": (_r3(0.301 + (n - 11) * 0.0625), 0.070) for n in range(11, 29)},
    **{f"AS568-{n:03d}": (i, 0.103) for n, i in
       ((104, 0.112), (105, 0.143), (106, 0.174), (107, 0.206), (108, 0.237), (109, 0.299))},
    **{f"AS568-{n:03d}": (_r3(0.362 + (n - 110) * 0.0625), 0.103) for n in range(110, 126)},
    **{f"AS568-{n:03d}": (_r3(0.734 + (n - 210) * 0.0625), 0.139) for n in range(210, 223)},
    **{f"AS568-{n:03d}": (_r3(1.475 + (n - 325) * 0.125), 0.210) for n in range(325, 331)},
}

# fmt: on
# ISO 3601-1 metric cross-sections (mm) in common supply.
ISO3601_SECTIONS: Tuple[float, ...] = (
    1.0,
    1.5,
    1.78,
    2.0,
    2.5,
    2.62,
    3.0,
    3.53,
    4.0,
    5.33,
    7.0,
)

# application -> (min squeeze, design squeeze, max squeeze).
GLAND_RULES: Dict[str, Tuple[float, float, float]] = {
    "static_radial": (0.15, 0.22, 0.30),
    "dynamic_radial": (0.10, 0.15, 0.20),
    "face": (0.20, 0.25, 0.35),
}
MAX_FILL = 0.85
STRETCH = (0.0, 0.05)  # installed stretch on the groove; 2 % is the target
STRETCH_TARGET = 0.02


@dataclass(frozen=True)
class ORing:
    """An O-ring: inside diameter ``id`` and cross-section ``cs`` (mm)."""

    name: str
    id: float
    cs: float

    @property
    def od(self) -> float:
        return round(self.id + 2 * self.cs, 3)


def oring(name: str) -> ORing:
    """An AS568 ring by dash number ("AS568-010", "010" or "-010")."""
    key = str(name).strip().upper().replace("AS568", "").lstrip("-").strip()
    id_in, cs_in = lookup(AS568, f"AS568-{key.zfill(3)}", "AS568 O-ring")
    return ORing(
        f"AS568-{key.zfill(3)}", round(id_in * INCH, 3), round(cs_in * INCH, 3)
    )


@dataclass(frozen=True)
class Gland:
    """A rectangular O-ring groove for cross-section ``cs`` (mm)."""

    cs: float
    application: str
    depth: float
    width: float
    squeeze: float
    fill: float


def gland(
    cs: float,
    application: str = "static_radial",
    *,
    squeeze: Optional[float] = None,
    fill: float = 0.70,
) -> Gland:
    """Groove depth (radial wall) and width for an O-ring of cross-section ``cs``.

    ``depth = cs (1 - squeeze)``, ``width`` from the gland fill (ring section
    area / groove area). Raises when ``squeeze`` or ``fill`` leaves the rules."""
    lo, design, hi = lookup(GLAND_RULES, application, "O-ring application")
    sq = design if squeeze is None else float(squeeze)
    if not lo <= sq <= hi:
        raise StandardsError(
            f"{application}: squeeze {sq:.0%} outside {lo:.0%}..{hi:.0%} (Parker ORD 5700)"
        )
    if not 0.4 <= fill <= MAX_FILL:
        raise StandardsError(f"gland fill {fill:.0%} outside 40 %..{MAX_FILL:.0%}")
    cs = float(cs)
    depth = cs * (1.0 - sq)
    width = (math.pi * cs * cs / 4.0) / (depth * fill)
    return Gland(cs, application, round(depth, 3), round(width, 2), sq, fill)


@dataclass(frozen=True)
class PistonGroove:
    """A piston (male) gland in a ``bore``: groove-bottom diameter and the ring."""

    bore: float
    groove_d: float
    gland: Gland
    ring: ORing
    stretch: float


def piston_groove(
    bore: float, cs: float = 1.78, application: str = "static_radial"
) -> PistonGroove:
    """Piston groove for ``bore`` (mm) with an AS568 ring of section ``cs`` (mm):
    groove Ø = bore - 2 x gland depth, ring = the AS568 size that stretches
    0-5 % onto the groove (closest to 2 % wins)."""
    g = gland(cs, application)
    groove_d = round(float(bore) - 2.0 * g.depth, 3)
    best = None
    for name in AS568:
        ring = oring(name)
        if abs(ring.cs - float(cs)) > 0.02:
            continue
        stretch = groove_d / ring.id - 1.0
        if STRETCH[0] <= stretch <= STRETCH[1] and (
            best is None
            or abs(stretch - STRETCH_TARGET) < abs(best[1] - STRETCH_TARGET)
        ):
            best = (ring, stretch)
    if best is None:
        raise StandardsError(
            f"No AS568 ring of section {cs:g} mm stretches 0-5 % onto a {groove_d:g} mm groove"
            f" (bore {bore:g} mm); pick another section or a metric ISO 3601 ring"
        )
    return PistonGroove(float(bore), groove_d, g, best[0], round(best[1], 4))
