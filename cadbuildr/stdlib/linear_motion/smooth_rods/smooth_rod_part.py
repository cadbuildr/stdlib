"""Hardened smooth rod for linear motion (the round shafts a linear bearing rides)."""

from typing import ClassVar

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import STEEL


@catalog_part(
    id="smooth-rod",
    category="Linear Motion",
    subcategory="Smooth Rods",
    name="Smooth Rod",
    standard="h6 hardened chrome shafting",
    description="Ground and hardened round rod for linear motion — the rail an LMxUU bearing slides along.",
    params=[
        ParamSpec.enum("diameter", choices=["6", "8", "10", "12", "16"], default="8", unit="mm"),
        ParamSpec.number("length", min=40, max=500, default=300, step=10),
    ],
    featured=True,
    example_config={"diameter": "8", "length": 250},
)
class SmoothRod(Part):
    def __init__(self, diameter="8", length=300):
        self.diameter = float(diameter)
        self.length = length
        s = Sketch(self.xy())
        self.add_operation(Extrusion(Circle(Point(s, 0, 0), self.diameter / 2), length))
        self.paint(STEEL)
