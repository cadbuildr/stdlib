"""Spacer / standoff tube that a through-bolt clamps between two plates."""

from __future__ import annotations

from typing import ClassVar

from cadbuildr.foundation import Circle, Extrusion, Part, Point, Sketch
from cadbuildr.foundation.interfaces import PlaneFace
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import BRASS, add_axial_anchors
from cadbuildr.stdlib.gearbox.geometry import CLEARANCE


@part(
    category="Gearbox/Housing",
    name="Spacer Tube",
    description="Plain spacer / standoff tube with a clearance bore for a through-bolt; sets the gap between two plates.",
    example={"screw": "M5", "length": 20, "outer_diameter": 12},
)
class Spacer(Part):
    """Spacer tube along +Z from z=0 to ``length``.

    Anchors: ``bottom`` / ``top`` end faces (outward normals) and ``axis``.

    Args:
        screw: the bolt that passes through (clearance bore, DIN EN 20273 medium).
        length: spacer length (the gap between the plates).
        outer_diameter: tube outer diameter.
    """

    CLEARANCE: ClassVar[dict] = CLEARANCE

    def __init__(
        self,
        screw: OneOf[CLEARANCE] = "M5",
        length: Num(min=1, max=200, step=1) = 20,
        outer_diameter: Num(min=4, max=40, step=0.5) = 12,
    ):
        bore = CLEARANCE[screw]
        if outer_diameter <= bore + 1.0:
            raise ValueError(
                f"Spacer outer diameter {outer_diameter} leaves no wall around a {screw} bore"
            )
        self.add_operation(
            Extrusion(
                Circle(Point(Sketch(self.xy()), 0, 0), outer_diameter / 2), length
            )
        )
        self.add_operation(
            Extrusion(
                Circle(Point(Sketch(self.xy()), 0, 0), bore / 2), length, cut=True
            )
        )
        self.screw, self.length, self.outer_diameter = screw, length, outer_diameter
        add_axial_anchors(self, length)
        # Interfaces: both end faces sit flat on a plate (PlaneFace).
        self.add_interface(PlaneFace(), "bottom")
        self.add_interface(PlaneFace(), "top")
        self.paint(BRASS)
