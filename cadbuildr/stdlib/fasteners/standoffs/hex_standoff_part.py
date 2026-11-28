"""Hex standoffs (PCB spacers): female-female and male-female, M2 – M4.

Built along +Z: body from z=0 (``bottom``) to z=``length`` (``top``); a
male-female standoff carries its threaded stud above ``top`` up to
``stud_tip``. ``length`` is the body length (the spacing it sets), the
catalogue designation.
"""

from __future__ import annotations

from typing import ClassVar, Literal

from cadbuildr.foundation import Circle, Extrusion, Part, Point, Sketch, make_anchor
from cadbuildr.foundation.interfaces import NutSeat, ScrewTip
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import (
    BRASS,
    ISO_COARSE_PITCH,
    add_axial_anchors,
    add_internal_thread,
    hexagon_shape,
    nominal_diameter,
    require_option,
    require_range,
)

Kind = Literal["female-female", "male-female"]


@part(
    category="Fasteners/Standoffs & Spacers",
    name="Hex Standoff",
    standard="PCB hex spacer · M2 – M4 (brass)",
    description="Hexagonal spacer that holds a PCB or panel off a base: female-female, or male-female with a threaded stud.",
    inputs={"with_thread": {"label": "Modeled thread"}},
    configurations={
        "M3 x 10 F-F": dict(size="M3", length=10, kind="female-female"),
        "M3 x 10 M-F": dict(size="M3", length=10, kind="male-female"),
        "M2.5 x 11 M-F (Raspberry Pi)": dict(
            size="M2.5", length=11, kind="male-female"
        ),
        "M2 x 6 F-F": dict(size="M2", length=6, kind="female-female"),
    },
    catalog_id="hex-standoff",
    featured=True,
    example={"size": "M3", "length": 10, "kind": "male-female"},
)
class HexStandoff(Part):
    # waf = width across flats, stud = male stud length
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M2": {"waf": 4.0, "stud": 4.0},
        "M2.5": {"waf": 5.0, "stud": 5.0},
        "M3": {"waf": 5.5, "stud": 6.0},
        "M4": {"waf": 7.0, "stud": 8.0},
    }

    def __init__(
        self,
        size: OneOf[TABLE] = "M3",
        length: Num(min=3, max=40, step=1) = 10,
        kind: Kind = "female-female",
        with_thread: bool = False,
    ):
        """Args:
        size: thread size (hex width and stud length from ``TABLE``).
        length: body length — the spacing the standoff sets.
        kind: ``female-female`` (tapped both ends) or ``male-female`` (stud on top).
        with_thread: model the threads (off by default: small and slow).
        """
        d = require_option(self.TABLE, size, what="size", owner="HexStandoff")
        if kind not in ("female-female", "male-female"):
            raise ValueError(
                f"HexStandoff: unknown kind {kind!r} (choose from female-female, male-female)."
            )
        length = require_range(length, lo=3, hi=40, what="length", owner="HexStandoff")
        r = nominal_diameter(size) / 2
        pitch = ISO_COARSE_PITCH[size]

        self.add_operation(
            Extrusion(hexagon_shape(Sketch(self.xy()), d["waf"]), length)
        )
        if kind == "female-female":
            bore = Circle(Point(Sketch(self.xy()), 0, 0), r)
            self.add_operation(Extrusion(bore, 0.0, length, cut=True))
            if with_thread:
                add_internal_thread(self, nominal_radius=r, length=length, pitch=pitch)
        else:
            depth = min(length, 1.5 * d["stud"])
            bore = Circle(Point(Sketch(self.xy()), 0, 0), r)
            self.add_operation(Extrusion(bore, 0.0, depth, cut=True))
            stud = Circle(Point(Sketch(self.xy()), 0, 0), r - 0.1)
            self.add_operation(Extrusion(stud, length, length + d["stud"]))

        self.size, self.length, self.kind = size, length, kind
        self.waf = d["waf"]
        self.stud_length = d["stud"] if kind == "male-female" else 0.0
        add_axial_anchors(self, length)
        # Interfaces: each body end bears on a hole face (NutSeat); the stud
        # of a male-female standoff takes a nut (ScrewTip).
        self.add_interface(NutSeat(size=size), "bottom")
        self.add_interface(NutSeat(size=size), "top")
        if kind == "male-female":
            tip = self.add_anchor(
                make_anchor("stud_tip", (0.0, 0.0, length + d["stud"]))
            )
            self.add_interface(ScrewTip(size=size), tip)
            if with_thread:
                # Thread the stud only: a separate helix starting at the shoulder.
                self._stud_thread(r, d["stud"], pitch, length)
        self.paint(BRASS)

    def _stud_thread(self, r, stud, pitch, z0):
        from cadbuildr.foundation import Point3D, Thread
        from cadbuildr.stdlib.common import iso_thread_profile

        H = pitch * 3**0.5 / 2
        self.add_operation(
            Thread(
                profile=iso_thread_profile(Sketch(self.xz()), pitch, external=True),
                pitch=pitch,
                height=stud - pitch,
                radius=r - H / 4,
                center=Point3D(0, 0, z0 + pitch / 2),
                dir=Point3D(0, 0, 1),
            )
        )
