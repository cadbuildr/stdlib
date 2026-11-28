"""Wire thread inserts (DIN 8140, "Helicoil"-type), tanged, free-running.

A coil of diamond-section wire, modeled as installed: its outside fills an
STI (screw thread insert) tapped hole, its inside forms the nominal ISO
thread. Built along +Z from z=0 (the tang end, at the bottom of the hole)
to the insert length; ``top`` is flush with the part face.
:func:`wire_thread_insert_hole` drills the STI hole and binds ``InsertPocket``
so the insert connects; the insert then offers a threaded ``ScrewHole``.
"""

from __future__ import annotations

import math
from typing import Any, ClassVar, Literal, Optional

from cadbuildr.foundation import Circle, Extrusion, Part, Point, Point3D, Sketch, Thread, make_anchor
from cadbuildr.foundation.interfaces import ScrewHole
from cadbuildr.foundation.library import OneOf, part
from cadbuildr.stdlib.common import STAINLESS, add_axial_anchors, require_option
from cadbuildr.stdlib.interfaces import InsertBody, InsertPocket
from cadbuildr.stdlib.standards import thread
from cadbuildr.stdlib.standards.features import HoleFeature, _owner, revolve_cut

__all__ = ["WireThreadInsert", "wire_thread_insert_hole", "STI_DRILL", "sti_major"]

#: STI tap drill, DIN 8140-2 (e.g. M6 -> 6.3 mm; cf. the 6.30 mm drill on
#: https://www.zoro.com/... 3520-6.00X1.5D M6 insert data).
STI_DRILL: dict[str, float] = {
    "M3": 3.2, "M4": 4.2, "M5": 5.2, "M6": 6.3, "M8": 8.4, "M10": 10.5, "M12": 12.5,
}  # fmt: skip

Length = Literal["1d", "1.5d", "2d", "2.5d", "3d"]
_FACTOR = {"1d": 1.0, "1.5d": 1.5, "2d": 2.0, "2.5d": 2.5, "3d": 3.0}


def sti_major(size: str) -> float:
    """Major diameter of the STI hole thread: d + 2 x 0.6495 P (DIN 8140-2:
    the STI thread is the ISO profile enlarged by the wire's flank depth)."""
    t = thread(size)
    return t.major + 2 * 0.649519 * t.pitch


def wire_thread_insert_hole(
    face: Any, size: str = "M6", length: str = "1.5d", *, group: Optional[str] = None
) -> HoleFeature:
    """STI hole for a ``size`` x ``length`` insert at ``face``: drilled to
    ``STI_DRILL`` for the insert length plus 2 P (tap runout), countersunk
    90° to the STI major, with ``InsertPocket(size, depth)`` bound on
    ``face``; the fitted insert then offers the ``ScrewHole``."""
    drill = require_option(STI_DRILL, size, what="size", owner="wire_thread_insert_hole")
    k = require_option(_FACTOR, length, what="length", owner="wire_thread_insert_hole")
    t = thread(size)
    L = k * t.major
    depth = L + 2 * t.pitch
    r, rc = drill / 2, sti_major(size) / 2
    profile = [(0.0, 0.0), (rc, 0.0), (r, -(rc - r)), (r, -depth), (0.0, -depth)]
    op = revolve_cut(face, profile, f"sti_{face.name.value}")
    owner = _owner(face)
    node = owner.add_interface(InsertPocket(size=size, depth=L), face, group=group)
    return HoleFeature(op, node, face, None, drill)


@part(
    category="Fasteners/Inserts",
    name="Wire Thread Insert",
    standard="DIN 8140 (tanged, free-running)",
    description="Helical diamond-wire thread insert that repairs or reinforces a tapped hole in soft metal; the STI hole and the screw thread are included.",
    configurations={
        "M4 x 1.5d": dict(size="M4", length="1.5d"),
        "M6 x 1.5d": dict(size="M6", length="1.5d"),
        "M8 x 2d": dict(size="M8", length="2d"),
    },
    catalog_id="din8140-wire-thread-insert",
    example={"size": "M6", "length": "1.5d"},
)
class WireThreadInsert(Part):
    """DIN 8140 wire thread insert, as installed. Nominal lengths 1 d .. 3 d
    (DIN 8140-1). The coil spans radially from the internal minor diameter
    D1 = d - 1.0825 P (ISO 724, the screw thread's crests) to the STI major
    (:func:`sti_major`); ``L / P`` coils. The tang is a diametral bar at the
    bottom coil. Drill: ``STI_DRILL`` (DIN 8140-2).

    Estimated: the wire section is a rhombus (60° flanks are approximated
    by joining the inner and outer crest radii); the tang is a round bar
    0.6 P thick; the installed coil is shown (no free-state oversize)."""

    SIZES: ClassVar[dict[str, float]] = STI_DRILL

    def __init__(self, size: OneOf[SIZES] = "M6", length: Length = "1.5d"):
        """Args:
        size: nominal thread size (ISO 261 coarse).
        length: nominal insert length as a multiple of d.
        """
        owner = "WireThreadInsert"
        drill = require_option(STI_DRILL, size, what="size", owner=owner)
        k = require_option(_FACTOR, length, what="length", owner=owner)
        t = thread(size)
        P = t.pitch
        L = k * t.major
        r_in, r_out = t.minor_internal / 2, sti_major(size) / 2
        r_mid = (r_in + r_out) / 2
        h = 0.49 * P
        s = Sketch(self.xz())
        s.pencil.move_to(r_in - r_mid, 0.0)
        s.pencil.line_to(0.0, -h)
        s.pencil.line_to(r_out - r_mid, 0.0)
        s.pencil.line_to(0.0, h)
        self.coils = L / P - 1.0
        self.add_operation(
            Thread(
                profile=s.pencil.close(),
                pitch=P,
                height=L - P,
                radius=r_mid,
                center=Point3D(0.0, 0.0, P / 2),
                dir=Point3D(0.0, 0.0, 1.0),
            )
        )
        # Tang: diametral bar across the bottom coil (broken off after fitting).
        tang = Circle(Point(Sketch(self.yz()), 0.0, P / 2), 0.3 * P)
        self.add_operation(Extrusion(tang, start=-r_mid, end=r_mid))
        self.size, self.nominal_length, self.length = size, length, L
        self.pitch, self.drill_diameter = P, drill
        self.inner_diameter, self.outer_diameter = 2 * r_in, 2 * r_out
        add_axial_anchors(self, L)
        # ``seat`` (flush with the face) takes the pocket; ``top`` the screw.
        self.add_anchor(make_anchor("seat", (0.0, 0.0, L)))
        self.add_interface(InsertBody(size=size), "seat")
        self.add_interface(ScrewHole(size=size, depth=L, thread=True), "top")
        self.paint(STAINLESS)
