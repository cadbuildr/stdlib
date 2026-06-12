from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec


@catalog_part(
    id="shaft-plain",
    category="Power Transmission",
    subcategory="Shafts",
    name="Plain Shaft",
    standard="ISO h6 round stock",
    description="Plain cylindrical shaft / round stock of the given diameter and length.",
    params=[
        ParamSpec.number("diameter", min=3, max=40, default=10, step=1),
        ParamSpec.number("length", min=10, max=400, default=100, step=10),
    ],
    featured=False,
    example_config={"diameter": 10, "length": 100},
)
class Shaft(Part):
    def __init__(self, diameter=10, length=100):
        self.DIAMETER = diameter
        self.LENGTH = length
        self.create_shaft()

    def create_shaft(self):
        s = Sketch(self.xy())
        center = Point(s, 0, 0)
        circle = Circle(center, self.DIAMETER / 2)
        extrusion = Extrusion(circle, self.LENGTH)
        self.add_operation(extrusion)
