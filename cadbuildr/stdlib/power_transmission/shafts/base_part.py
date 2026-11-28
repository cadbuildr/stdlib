from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion
from cadbuildr.foundation.interfaces.features import ShaftFeature
from cadbuildr.foundation.library import Num, part
from cadbuildr.stdlib.common import add_axial_anchors


@part(
    category="Power Transmission/Shafts",
    name="Plain Shaft",
    standard="ISO h6 round stock",
    description="Plain cylindrical shaft / round stock of the given diameter and length.",
    configurations={
        "8 x 100": dict(diameter=8, length=100),
        "10 x 200": dict(diameter=10, length=200),
        "5 x 50": dict(diameter=5, length=50),
    },
    catalog_id="shaft-plain",
    example={"diameter": 10, "length": 100},
)
class Shaft(Part):
    def __init__(
        self,
        diameter: Num(min=3, max=40, step=1) = 10,
        length: Num(min=10, max=400, step=1) = 100,
    ):
        """Args:
        diameter: shaft diameter.
        length: shaft length (along +Z from z=0).
        """
        self.DIAMETER = diameter
        self.LENGTH = length
        self.create_shaft()
        # Anchors: end faces + axis.
        add_axial_anchors(self, length, ends=("end_a", "end_b"))
        # Interfaces: Shaft on the axis (bores ride it), ShaftEnd at each end.
        ShaftFeature(self, d=diameter, length=length)

    def create_shaft(self):
        s = Sketch(self.xy())
        center = Point(s, 0, 0)
        circle = Circle(center, self.DIAMETER / 2)
        extrusion = Extrusion(circle, self.LENGTH)
        self.add_operation(extrusion)
