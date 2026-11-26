"""GT2 timing-belt pulley, parameterised by tooth count and bore."""

import math

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion, make_anchor
from cadbuildr.foundation.interfaces import Bore, PlaneFace, ScrewHole
from cadbuildr.foundation.library import Num, part
from cadbuildr.stdlib.common import ALUMINIUM, add_axial_anchors

_GT2_PITCH = 2.0  # mm, belt tooth pitch
_FLANGE_T = 1.0  # flange thickness
_FLANGE_EXTRA = 2.0  # flange radius beyond pitch radius


@part(
    category="Power Transmission/Pulleys",
    name="GT2 Timing Pulley",
    standard="GT2 · 2 mm pitch",
    description="Toothed GT2 timing-belt pulley with flanges and a bore; set the tooth count, bore and belt width.",
    catalog_id="gt2-pulley",
    featured=True,
    example={"teeth": 20, "bore": 5, "belt_width": 6},
)
class GT2Pulley(Part):
    def __init__(
        self,
        teeth: Num(min=10, max=60, step=1, unit=None, integer=True) = 20,
        bore: Num(min=3, max=10, step=1) = 5,
        belt_width: Num(min=6, max=12, step=1) = 6,
    ):
        """Args:
        teeth: tooth count (pitch radius = teeth x 2 mm / 2 pi).
        bore: shaft bore diameter.
        belt_width: width of the toothed band between the flanges.
        """
        self.teeth = int(teeth)
        pitch_r = (self.teeth * _GT2_PITCH) / (2 * math.pi)
        flange_r = pitch_r + _FLANGE_EXTRA
        body_z0 = _FLANGE_T
        body_z1 = body_z0 + belt_width
        top = body_z1 + _FLANGE_T

        # Bottom flange, toothed body, top flange.
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), flange_r), 0, body_z0)
        )
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), pitch_r), body_z0, body_z1)
        )
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), flange_r), body_z1, top)
        )

        # Tooth grooves: small scallops cut at the pitch radius around the body.
        tooth_r = _GT2_PITCH * 0.27
        for i in range(self.teeth):
            a = 2 * math.pi * i / self.teeth
            c = Point(Sketch(self.xy()), pitch_r * math.cos(a), pitch_r * math.sin(a))
            self.add_operation(
                Extrusion(Circle(c, tooth_r), body_z0, body_z1, cut=True)
            )

        # Central bore.
        self.add_operation(
            Extrusion(
                Circle(Point(Sketch(self.xy()), 0, 0), bore / 2), 0, top, cut=True
            )
        )
        # Anchors: both flange faces, bore axis, and the belt plane (centre of
        # the toothed band, +Z along the axis) for aligning belts / idlers.
        self.pitch_radius = pitch_r
        self.height = top
        add_axial_anchors(self, top)
        self.add_anchor(make_anchor("belt_plane", (0.0, 0.0, (body_z0 + body_z1) / 2)))
        # Interfaces: the bore on a Shaft, the bottom flange on a face, and the
        # top flange as the face an idler screw head lands on.
        self.add_interface(Bore(d=bore), "axis")
        self.add_interface(PlaneFace(), "bottom")
        self.add_interface(ScrewHole(size=f"M{bore:g}", depth=top), "top")
        self.paint(ALUMINIUM)
