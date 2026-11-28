"""Pilot and clearance holes for screws into wood and wood panels.

::

    wood_pilot("#8", "hardwood")     # WoodPilot(pilot=3.17, clearance=4.37, ...)
    wood_pilot(5.0, "softwood")      # metric 5 mm screw: pilot 2.5, clearance 5.5
    wood_pilot(4.0, "mdf")           # MDF: pilot 2.8 (0.7 d), min_edge 20 mm (5 d)

Sources: gauge screws (#4..#14) use the common woodworking chart (pilot
drill for hardwood / softwood, shank clearance), as printed in Machinery's
Handbook-style tables and screw makers' charts; metric screws use the usual
factors of the nominal diameter (softwood ~0.5 d, hardwood ~0.65 d, plywood
~0.55 d, MDF / particle board ~0.7 d, shank clearance d + 0.5 mm). Wood
varies: drill a test hole in your stock.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, Union

from ._common import StandardsError, lookup

__all__ = ["GAUGE_PILOTS", "WOOD_FACTORS", "WoodPilot", "wood_pilot"]

INCH = 25.4

# gauge -> (major in, hardwood pilot in, softwood pilot in, shank clearance in).
# fmt: off
GAUGE_PILOTS: Dict[str, Tuple[float, float, float, float]] = {
    "#4": (0.112, 5 / 64, 1 / 16, 7 / 64),
    "#6": (0.138, 7 / 64, 3 / 32, 9 / 64),
    "#8": (0.164, 1 / 8, 7 / 64, 11 / 64),
    "#10": (0.190, 9 / 64, 1 / 8, 3 / 16),
    "#12": (0.216, 5 / 32, 9 / 64, 7 / 32),
    "#14": (0.242, 3 / 16, 5 / 32, 1 / 4),
}
# fmt: on

# Pilot = factor x nominal screw diameter, by material.
WOOD_FACTORS: Dict[str, float] = {
    "softwood": 0.5,
    "hardwood": 0.65,
    "plywood": 0.55,
    "mdf": 0.7,
    "particle board": 0.7,
}

# Minimum edge distance (x d) to avoid splitting / bursting.
EDGE_DISTANCE: Dict[str, float] = {
    "softwood": 4.0,
    "hardwood": 5.0,
    "plywood": 3.0,
    "mdf": 5.0,
    "particle board": 5.0,
}


@dataclass(frozen=True)
class WoodPilot:
    """Holes for one screw into one wood (mm)."""

    screw: str
    material: str
    diameter: float
    pilot: float
    clearance: float
    min_edge: float


def wood_pilot(screw: Union[str, float], material: str = "softwood") -> WoodPilot:
    """Pilot (in the part the screw bites) and clearance (in the part it clamps)
    for a gauge screw (``"#8"``, always with ``#``) or a metric diameter (``5.0`` / ``"5"``).
    """
    mat = str(material).lower()
    factor = lookup(WOOD_FACTORS, mat, "wood material")
    edge = EDGE_DISTANCE[mat]
    key = str(screw).strip()
    if key.startswith("#"):
        g = key
        major, hard, soft, shank = lookup(GAUGE_PILOTS, g, "wood screw gauge")
        if mat == "hardwood":
            pilot = hard
        elif mat == "softwood":
            pilot = soft
        else:
            pilot = factor * major
        d = major * INCH
        return WoodPilot(
            g,
            mat,
            round(d, 3),
            round(pilot * INCH, 2),
            round(shank * INCH, 2),
            round(edge * d, 1),
        )
    if not _is_float(key):
        raise StandardsError(
            f"wood_pilot: screw must be a gauge ('#8') or a diameter in mm, got {screw!r}"
        )
    d = float(key)
    if not 1.5 <= d <= 12:
        raise StandardsError(f"wood_pilot: {d:g} mm is outside 1.5..12 mm wood screws")
    return WoodPilot(
        f"{d:g} mm", mat, d, round(factor * d, 2), round(d + 0.5, 2), round(edge * d, 1)
    )


def _is_float(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True
