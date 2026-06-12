"""GT2 timing-belt pulley, parameterised by tooth count and bore."""

import math

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import ALUMINIUM

_GT2_PITCH = 2.0      # mm, belt tooth pitch
_FLANGE_T = 1.0       # flange thickness
_FLANGE_EXTRA = 2.0   # flange radius beyond pitch radius


@catalog_part(
    id="gt2-pulley",
    category="Power Transmission",
    subcategory="Pulleys",
    name="GT2 Timing Pulley",
    standard="GT2 · 2 mm pitch",
    description="Toothed GT2 timing-belt pulley with flanges and a bore; set the tooth count, bore and belt width.",
    params=[
        ParamSpec.number("teeth", min=10, max=60, default=20, step=1),
        ParamSpec.number("bore", min=3, max=10, default=5, step=1),
        ParamSpec.number("belt_width", min=6, max=12, default=6, step=1),
    ],
    featured=True,
    example_config={"teeth": 20, "bore": 5, "belt_width": 6},
)
class GT2Pulley(Part):
    def __init__(self, teeth=20, bore=5, belt_width=6):
        self.teeth = int(teeth)
        pitch_r = (self.teeth * _GT2_PITCH) / (2 * math.pi)
        flange_r = pitch_r + _FLANGE_EXTRA
        body_z0 = _FLANGE_T
        body_z1 = body_z0 + belt_width
        top = body_z1 + _FLANGE_T

        # Bottom flange, toothed body, top flange.
        self.add_operation(Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), flange_r), 0, body_z0))
        self.add_operation(Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), pitch_r), body_z0, body_z1))
        self.add_operation(Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), flange_r), body_z1, top))

        # Tooth grooves: small scallops cut at the pitch radius around the body.
        tooth_r = _GT2_PITCH * 0.27
        for i in range(self.teeth):
            a = 2 * math.pi * i / self.teeth
            c = Point(Sketch(self.xy()), pitch_r * math.cos(a), pitch_r * math.sin(a))
            self.add_operation(Extrusion(Circle(c, tooth_r), body_z0, body_z1, cut=True))

        # Central bore.
        self.add_operation(Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), bore / 2), 0, top, cut=True))
        self.paint(ALUMINIUM)
