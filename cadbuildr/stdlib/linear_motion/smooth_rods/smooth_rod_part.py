"""Hardened smooth rod for linear motion (the round shafts a linear bearing rides)."""

from typing import ClassVar

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import STEEL, add_axial_anchors


@part(
    category="Linear Motion/Smooth Rods",
    name="Smooth Rod",
    standard="h6 hardened chrome shafting",
    description="Ground and hardened round rod for linear motion — the rail an LMxUU bearing slides along.",
    catalog_id="smooth-rod",
    featured=True,
    example={"diameter": "8", "length": 250},
)
class SmoothRod(Part):
    # nominal diameter -> the LMxUU bearing that rides it (LinearBearing.TABLE key)
    TABLE: ClassVar[dict[str, dict]] = {
        "6": {"d": 6.0, "bearing": "LM6UU"},
        "8": {"d": 8.0, "bearing": "LM8UU"},
        "10": {"d": 10.0, "bearing": "LM10UU"},
        "12": {"d": 12.0, "bearing": "LM12UU"},
        "16": {"d": 16.0, "bearing": "LM16UU"},
    }

    def __init__(
        self,
        diameter: OneOf[TABLE] = "8",
        length: Num(min=40, max=1000, step=10) = 300,
    ):
        """Args:
        diameter: rod diameter in mm (a ``TABLE`` key; numbers are accepted too).
        length: cut length, end to end.
        """
        self.diameter = float(diameter)
        self.length = length
        s = Sketch(self.xy())
        self.add_operation(Extrusion(Circle(Point(s, 0, 0), self.diameter / 2), length))
        # Anchors: end faces + axis (slide an LMxUU ``center`` along ``axis``).
        add_axial_anchors(self, length, ends=("end_a", "end_b"))
        self.paint(STEEL)
