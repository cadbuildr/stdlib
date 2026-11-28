"""Hex-socket set screws (grub screws): ISO 4026 / 4027 / 4028 / 4029.

A set screw has no head: it is driven fully into a tapped hole and its point
bears on a shaft (a pulley hub, a coupling, a collar). Built like every
stdlib screw — point at z=0, socket end at z=``length`` — and it honours the
fastener contract with the seat at the flush socket end, so
``connect_with_screw(..., drill=False)`` drops it into a tapped hole.
"""

from __future__ import annotations

from typing import ClassVar, Literal

from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import (
    BLACK_OXIDE,
    ISO_COARSE_PITCH,
    add_external_thread,
    add_hex_socket,
    lathe_revolve,
    nominal_diameter,
    require_option,
)
from cadbuildr.stdlib.fasteners.base import Fastener

Point = Literal["flat", "cone", "dog", "cup"]

POINT_STANDARD = {
    "flat": "ISO 4026 / DIN 913",
    "cone": "ISO 4027 / DIN 914",
    "dog": "ISO 4028 / DIN 915",
    "cup": "ISO 4029 / DIN 916",
}


@part(
    category="Fasteners/Screws & Bolts",
    name="Set Screw (hex socket)",
    standard="ISO 4026 / 4027 / 4028 / 4029",
    description="Headless hex-socket grub screw with a flat, cone, dog or cup point — locks a hub or collar on a shaft.",
    inputs={"with_thread": {"label": "Modeled thread"}},
    configurations={
        "M3 x 4 cup (GT2 pulley hub)": dict(size="M3", length=4, point="cup"),
        "M4 x 6 cup (coupling)": dict(size="M4", length=6, point="cup"),
        "M5 x 8 flat": dict(size="M5", length=8, point="flat"),
        "M6 x 10 cone": dict(size="M6", length=10, point="cone"),
        "M8 x 12 dog": dict(size="M8", length=12, point="dog"),
    },
    catalog_id="iso4029-set-screw",
    example={"size": "M4", "length": 10, "point": "cup"},
)
class SetScrew(Fastener):
    # s = socket across flats, t = socket depth, dp = dog-point diameter,
    # dz = cup diameter (ISO 4026-4029 nominal values).
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M3": {"s": 1.5, "t": 1.2, "dp": 2.0, "dz": 1.4},
        "M4": {"s": 2.0, "t": 1.6, "dp": 2.5, "dz": 2.0},
        "M5": {"s": 2.5, "t": 2.0, "dp": 3.5, "dz": 2.5},
        "M6": {"s": 3.0, "t": 2.0, "dp": 4.0, "dz": 3.0},
        "M8": {"s": 4.0, "t": 3.0, "dp": 5.5, "dz": 5.0},
        "M10": {"s": 5.0, "t": 4.0, "dp": 7.0, "dz": 6.0},
        "M12": {"s": 6.0, "t": 4.8, "dp": 8.5, "dz": 8.0},
    }

    def __init__(
        self,
        size: OneOf[TABLE] = "M4",
        length: Num(min=3, max=30, step=1) = 10,
        point: Point = "cup",
        with_thread: bool = True,
    ):
        """Args:
        size: metric thread size (socket and point dimensions from ``TABLE``).
        length: overall length (the screw sits flush, no head).
        point: point form — flat (ISO 4026), cone (4027), dog (4028), cup (4029).
        with_thread: model the helical thread (slower to render).
        """
        d = require_option(self.TABLE, size, what="size", owner="SetScrew")
        require_option(POINT_STANDARD, point, what="point", owner="SetScrew")
        radius = nominal_diameter(size) / 2
        pitch = ISO_COARSE_PITCH[size]
        length = float(length)
        core_r = radius - (0.15 * pitch if with_thread else 0.0)
        chamfer = 0.6 * pitch
        profile = self._point_profile(point, d, core_r, chamfer)
        point_len = max(z for _, z in profile)
        if length < point_len + d["t"] + pitch:
            raise ValueError(
                f"SetScrew: {length:g} mm is too short for an {size} {point} point "
                f"(minimum {point_len + d['t'] + pitch:.1f} mm)."
            )
        lathe_revolve(self, profile + [(core_r, length), (0.0, length)])
        add_hex_socket(self, top_z=length, width=d["s"], depth=d["t"])
        if with_thread and length - point_len > pitch:
            add_external_thread(self, radius=radius, length=length, pitch=pitch)
        self.size, self.length, self.point = size, length, point
        self.socket_depth = d["t"]
        # Flush: the "head seat" is the socket end, the tip is the point.
        self._set_fastener_contract(body_radius=radius, body_height=length)
        self.paint(BLACK_OXIDE)

    @staticmethod
    def _point_profile(point, d, core_r, chamfer):
        """(r, z) points of the point end, from the axis to the full core."""
        if point == "flat":
            return [(0.0, 0.0), (core_r - chamfer, 0.0), (core_r, chamfer)]
        if point == "cone":
            tip_r = 0.1 * core_r
            return [(0.0, 0.0), (tip_r, 0.0), (core_r, core_r - tip_r)]
        if point == "dog":
            dog_r = d["dp"] / 2
            dog_len = 0.25 * 2 * core_r + 0.5
            return [
                (0.0, 0.0),
                (dog_r, 0.0),
                (dog_r, dog_len),
                (core_r, dog_len + (core_r - dog_r)),
            ]
        # cup: a conical recess of diameter dz in a chamfered flat end.
        cup_r = d["dz"] / 2
        return [
            (0.0, cup_r * 0.6),
            (cup_r, 0.0),
            (core_r - chamfer, 0.0),
            (core_r, chamfer),
        ]
