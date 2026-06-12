"""T8 lead screw and its brass nut (the Z-axis drive on most printers/CNC)."""

import math
from typing import ClassVar

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import (
    BRASS,
    STAINLESS,
    add_external_thread,
    add_internal_thread,
)


# T8 trapezoidal screw: 8 mm major, 2 mm pitch (modeled as a coarse helical thread).
_T8_MAJOR = 8.0
_T8_PITCH = 2.0


@catalog_part(
    id="lead-screw-t8",
    category="Linear Motion",
    subcategory="Lead Screws",
    name="Lead Screw T8",
    standard="Tr8x8(P2) trapezoidal",
    description="8 mm stainless lead screw with a coarse helical thread — the standard Z-axis drive screw.",
    params=[
        ParamSpec.number("length", min=50, max=500, default=300, step=10),
        ParamSpec.boolean("with_thread", default=True, label="Modeled thread"),
    ],
    featured=True,
    example_config={"length": 300},
)
class LeadScrewT8(Part):
    def __init__(self, length=300, with_thread=True):
        self.length = length
        radius = _T8_MAJOR / 2
        H = _T8_PITCH * math.sqrt(3) / 2
        core_r = radius - (H / 4 + 0.01 if with_thread else 0.0)
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), core_r), length)
        )
        if with_thread:
            add_external_thread(self, radius=radius, length=length, pitch=_T8_PITCH)
        self.paint(STAINLESS)


@catalog_part(
    id="lead-screw-nut-t8",
    category="Linear Motion",
    subcategory="Lead Screws",
    name="Lead Screw Nut T8 (brass)",
    standard="T8 flanged brass nut",
    description="Flanged brass nut for the T8 lead screw, with four M4 flange mounting holes.",
    params=[
        ParamSpec.boolean("with_thread", default=True, label="Modeled thread"),
    ],
    featured=False,
    example_config={},
)
class LeadScrewNutT8(Part):
    FLANGE_D: ClassVar[float] = 22.0
    FLANGE_H: ClassVar[float] = 3.5
    BODY_D: ClassVar[float] = 10.2
    BODY_H: ClassVar[float] = 11.5
    HOLE_PCD: ClassVar[float] = 16.0   # pitch circle of the flange holes
    HOLE_D: ClassVar[float] = 4.2

    def __init__(self, with_thread=True):
        total_h = self.FLANGE_H + self.BODY_H
        # Flange + body.
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), self.FLANGE_D / 2), 0, self.FLANGE_H)
        )
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), self.BODY_D / 2), self.FLANGE_H, total_h)
        )
        # Central bore + thread.
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), _T8_MAJOR / 2), 0, total_h, cut=True)
        )
        if with_thread:
            add_internal_thread(self, nominal_radius=_T8_MAJOR / 2, length=total_h, pitch=_T8_PITCH)
        # Four flange mounting holes.
        r = self.HOLE_PCD / 2
        for i in range(4):
            a = math.radians(45 + 90 * i)
            c = Point(Sketch(self.xy()), r * math.cos(a), r * math.sin(a))
            self.add_operation(Extrusion(Circle(c, self.HOLE_D / 2), 0, self.FLANGE_H, cut=True))
        self.paint(BRASS)
