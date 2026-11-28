"""Holes for fastening into plastic: heat-set inserts and self-tapping screws.

::

    heat_set_insert("M3")              # HeatSetInsert(hole=4.0, length=5.7, ...)
    heat_set_insert("M3", "short")     # 4.0 x 3.0
    self_tap_hole(3.0, "PC")           # 2.55 mm pilot (0.85 d), boss 6.75, engage 6.0

Sources: heat-set inserts are the common knurled brass inserts for 3D prints
(CNC Kitchen / ruthex-style dimensions: hole diameter, insert length, outer
diameter); hole depth leaves 1 mm below the insert for displaced melt. Always
check your insert vendor's datasheet. Self-tapping pilots follow the
thread-forming screw guidance for thermoplastics (EJOT PT / Delta PT style:
pilot = factor x d, boss outer diameter ~ 2.5 d, engagement ~ 2 d).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from ._common import lookup, metric_diameter

__all__ = [
    "HEAT_SET_INSERTS",
    "HeatSetInsert",
    "SELF_TAP_FACTORS",
    "SelfTapHole",
    "heat_set_insert",
    "self_tap_hole",
]

# size -> variant -> (hole Ø, insert length, insert outer Ø), mm.
HEAT_SET_INSERTS: Dict[str, Dict[str, Tuple[float, float, float]]] = {
    "M2": {"standard": (3.2, 4.0, 3.6), "short": (3.2, 3.0, 3.6)},
    "M2.5": {"standard": (3.5, 5.7, 4.6), "short": (3.5, 4.0, 4.6)},
    "M3": {"standard": (4.0, 5.7, 4.6), "short": (4.0, 3.0, 4.6)},
    "M4": {"standard": (5.6, 8.1, 6.3), "short": (5.6, 4.0, 6.3)},
    "M5": {"standard": (6.4, 9.5, 7.1), "short": (6.4, 5.8, 7.1)},
    "M6": {"standard": (8.0, 12.7, 8.7)},
    "M8": {"standard": (9.7, 12.7, 10.3)},
}

# Pilot hole = factor x nominal screw diameter, by thermoplastic.
SELF_TAP_FACTORS: Dict[str, float] = {
    "ABS": 0.80,
    "ASA": 0.80,
    "PC": 0.85,
    "PC/ABS": 0.82,
    "PA6": 0.75,
    "PA66": 0.75,
    "PA-GF30": 0.80,
    "PBT": 0.80,
    "POM": 0.75,
    "PP": 0.70,
    "PE": 0.70,
    "PLA": 0.80,
    "PETG": 0.80,
}


@dataclass(frozen=True)
class HeatSetInsert:
    """A heat-set insert and the hole it is melted into (mm)."""

    size: str
    variant: str
    hole: float
    length: float
    outer: float

    @property
    def depth(self) -> float:
        """Blind hole depth: insert length + 1 mm for displaced plastic."""
        return round(self.length + 1.0, 3)

    @property
    def min_wall(self) -> float:
        """Plastic to leave around the insert (~ 1.5 x its outer radius of wall)."""
        return round(max(1.2, 0.75 * self.outer), 3)

    @property
    def boss(self) -> float:
        """Recommended boss outer diameter: insert outer Ø + 2 x ``min_wall``."""
        return round(self.outer + 2.0 * self.min_wall, 3)


def heat_set_insert(size: str = "M3", variant: str = "standard") -> HeatSetInsert:
    """The heat-set insert for screw ``size`` ("M2".."M8"), ``variant`` standard / short."""
    d, _ = metric_diameter(size)
    key = f"M{d:g}"
    row = lookup(HEAT_SET_INSERTS, key, "heat-set insert size")
    hole, length, outer = lookup(row, variant, f"{key} heat-set insert variant")
    return HeatSetInsert(key, variant, hole, length, outer)


@dataclass(frozen=True)
class SelfTapHole:
    """Pilot, boss and engagement for a thread-forming screw into plastic (mm)."""

    diameter: float
    material: str
    pilot: float
    boss: float
    engagement: float


def self_tap_hole(diameter: float, material: str = "PLA") -> SelfTapHole:
    """Pilot hole for a thread-forming screw of nominal ``diameter`` (mm, or
    ``"M3"``) into ``material`` (a :data:`SELF_TAP_FACTORS` key)."""
    d, _ = metric_diameter(diameter)
    factor = lookup(SELF_TAP_FACTORS, material, "plastic for self-tapping")
    return SelfTapHole(
        diameter=d,
        material=str(material),
        pilot=round(factor * d, 3),
        boss=round(2.5 * d, 3),
        engagement=round(2.0 * d, 3),
    )
