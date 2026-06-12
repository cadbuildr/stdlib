"""Clamp-style shaft coupling joining two shafts (e.g. NEMA shaft to lead screw)."""

import math

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import ALUMINIUM


@catalog_part(
    id="clamp-shaft-coupling",
    category="Power Transmission",
    subcategory="Couplings",
    name="Shaft Coupling (clamp)",
    standard="aluminium clamp coupling",
    description="Aluminium clamping coupling with a stepped bore for two shaft diameters and a clamp slit at each end.",
    params=[
        ParamSpec.number("bore_a", min=3, max=12, default=5, step=1, label="Bore A"),
        ParamSpec.number("bore_b", min=3, max=12, default=8, step=1, label="Bore B"),
        ParamSpec.number("length", min=15, max=40, default=25, step=1),
    ],
    featured=False,
    example_config={"bore_a": 5, "bore_b": 8, "length": 25},
)
class ClampCoupling(Part):
    def __init__(self, bore_a=5, bore_b=8, length=25):
        outer_d = max(bore_a, bore_b) * 2.4 + 4
        outer_r = outer_d / 2
        half = length / 2

        # Body.
        self.add_operation(Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), outer_r), length))
        # Stepped bores from each end.
        self.add_operation(Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), bore_a / 2), 0, half + 0.1, cut=True))
        self.add_operation(Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), bore_b / 2), half, length, cut=True))

        # A radial grub-screw hole near each end (bored across Y into the bore).
        for z in (length * 0.18, length * 0.82):
            hole = Circle(Point(Sketch(self.xz()), 0, z), 1.5)
            self.add_operation(Extrusion(hole, -outer_r - 1, outer_r + 1, cut=True))
        self.paint(ALUMINIUM)
