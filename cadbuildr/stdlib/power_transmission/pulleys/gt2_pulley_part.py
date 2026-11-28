"""GT2 timing-belt pulley, parameterised by tooth count and bore."""

import math

from cadbuildr.foundation import (
    Circle,
    Extrusion,
    Part,
    Point,
    Sketch,
    anchor_plane,
    make_anchor,
)
from cadbuildr.foundation.interfaces import Bore, PlaneFace, ScrewHole
from cadbuildr.foundation.library import Num, part
from cadbuildr.stdlib.common import ALUMINIUM, add_axial_anchors

_GT2_PITCH = 2.0  # mm, belt tooth pitch
_FLANGE_T = 1.0  # flange thickness
_FLANGE_EXTRA = 2.0  # flange radius beyond pitch radius
_PLD = 0.254  # GT2 pitch line differential: OD = pitch diameter - 2 x PLD


@part(
    category="Power Transmission/Pulleys",
    name="GT2 Timing Pulley",
    standard="GT2 · 2 mm pitch",
    description="Toothed GT2 timing-belt pulley with flanges and a bore; set the tooth count, bore and belt width.",
    configurations={
        "GT2 20T 5 mm bore (6 mm belt)": dict(teeth=20, bore=5, belt_width=6),
        "GT2 16T 5 mm bore (6 mm belt)": dict(teeth=16, bore=5, belt_width=6),
        "GT2 40T 8 mm bore (6 mm belt)": dict(teeth=40, bore=8, belt_width=6),
        "GT2 20T 8 mm bore (10 mm belt)": dict(teeth=20, bore=8, belt_width=10),
    },
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
        hub: bool = True,
        hub_length: Num(min=4, max=15, step=0.5) = 7,
    ):
        """Args:
        teeth: tooth count (pitch radius = teeth x 2 mm / 2 pi).
        bore: shaft bore diameter.
        belt_width: width of the toothed band between the flanges.
        hub: add the set-screw hub above the top flange (stock pulleys have one).
        hub_length: hub length along the axis.

        Sources: GT2 pitch 2 mm, PLD 0.254, groove R0.555 x 0.75 (Gates 2MGT).
        Estimated: flange diameter (pitch + 4) and thickness (1 mm); hub
        diameter (pitch diameter + 3, at least bore + 6, at most 25) and
        length (7 mm) from common 16T / 20T vendor pulleys; two M3 set screws
        at 90 degrees.
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
            Extrusion(
                Circle(Point(Sketch(self.xy()), 0, 0), pitch_r - _PLD), body_z0, body_z1
            )
        )
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), flange_r), body_z1, top)
        )

        # Tooth grooves: small scallops cut at the pitch radius around the body.
        # GT2 groove: R0.555 tip radius, 0.75 deep below the OD (Gates 2MGT).
        tooth_r = 0.555
        groove_r = pitch_r - _PLD - 0.75 + tooth_r
        for i in range(self.teeth):
            a = 2 * math.pi * i / self.teeth
            c = Point(Sketch(self.xy()), groove_r * math.cos(a), groove_r * math.sin(a))
            self.add_operation(
                Extrusion(Circle(c, tooth_r), body_z0, body_z1, cut=True)
            )

        flange_top = top
        hub_d = 0.0
        if hub:
            hub_d = min(25.0, max(2 * pitch_r + 3.0, bore + 6.0))
            self.add_operation(
                Extrusion(
                    Circle(Point(Sketch(self.xy()), 0, 0), hub_d / 2),
                    top,
                    top + hub_length,
                )
            )
            top = top + hub_length

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
        self.belt_z = (body_z0 + body_z1) / 2
        self.hub_diameter, self.hub_length = hub_d, hub_length if hub else 0.0
        add_axial_anchors(self, top)
        self.add_anchor(make_anchor("belt_plane", (0.0, 0.0, self.belt_z)))
        if hub:
            # Two radial M3 set screws at 90 degrees, mid hub (tap drill 2.5).
            z_ss = flange_top + hub_length / 2
            for i, (dx, dy) in enumerate(((1.0, 0.0), (0.0, 1.0))):
                seat = self.add_anchor(
                    make_anchor(
                        f"set_screw_{i}",
                        (dx * hub_d / 2, dy * hub_d / 2, z_ss),
                        z_axis=(dx, dy, 0.0),
                        x_axis=(0.0, 0.0, 1.0),
                    )
                )
                drill = Circle(Sketch(anchor_plane(seat)).origin, 1.25)
                self.add_operation(
                    Extrusion(drill, 0.0, -(hub_d - bore) / 2 - 0.1, cut=True)
                )
                self.add_interface(
                    ScrewHole(size="M3", depth=(hub_d - bore) / 2, thread=True), seat
                )
        # Interfaces: the bore on a Shaft, the bottom flange on a face, and the
        # top flange as the face an idler screw head lands on.
        self.add_interface(Bore(d=bore), "axis")
        self.add_interface(PlaneFace(), "bottom")
        self.add_interface(ScrewHole(size=f"M{bore:g}", depth=top), "top")
        self.paint(ALUMINIUM)
