"""Parametric spur gear (simplified trapezoidal teeth, not true involute)."""

import math

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import STEEL, oriented_rectangle_shape


@catalog_part(
    id="spur-gear",
    category="Power Transmission",
    subcategory="Gears",
    name="Spur Gear",
    standard="ISO module · simplified teeth",
    description="Parametric spur gear by module and tooth count, with a central bore. Teeth are simplified (trapezoidal), suitable for visualization and fit-checking.",
    params=[
        ParamSpec.number("module", min=0.5, max=3, default=1, step=0.5, unit="mm"),
        ParamSpec.number("teeth", min=8, max=60, default=20, step=1),
        ParamSpec.number("face_width", min=2, max=20, default=6, step=1),
        ParamSpec.number("bore", min=2, max=12, default=5, step=1),
    ],
    featured=True,
    example_config={"module": 1, "teeth": 20, "face_width": 6, "bore": 5},
)
class SpurGear(Part):
    def __init__(self, module=1, teeth=20, face_width=6, bore=5):
        self.module = module
        self.teeth = int(teeth)
        pitch_r = module * self.teeth / 2
        root_r = pitch_r - 1.25 * module
        outer_r = pitch_r + module

        # Root cylinder, then add a tooth block at each pitch position.
        self.add_operation(Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), root_r), face_width))
        tooth_thickness = math.pi * module / 2 * 0.9     # ~half the circular pitch
        tooth_len = (outer_r - root_r) + 0.5
        mid_r = (root_r + outer_r) / 2
        for i in range(self.teeth):
            a = 2 * math.pi * i / self.teeth
            shape = oriented_rectangle_shape(
                Sketch(self.xy()),
                mid_r * math.cos(a),
                mid_r * math.sin(a),
                tooth_thickness,   # tangential
                tooth_len,         # radial
                a + math.pi / 2,
            )
            self.add_operation(Extrusion(shape, face_width))

        # Bore.
        self.add_operation(Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), bore / 2), face_width, cut=True))
        self.paint(STEEL)
