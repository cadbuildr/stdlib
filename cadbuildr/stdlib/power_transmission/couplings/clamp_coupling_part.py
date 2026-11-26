"""Clamp-style shaft coupling joining two shafts (e.g. NEMA shaft to lead screw)."""

import math

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion, make_anchor
from cadbuildr.foundation.interfaces import Bore
from cadbuildr.foundation.library import Num, part
from cadbuildr.stdlib.common import ALUMINIUM, add_axial_anchors


@part(
    category="Power Transmission/Couplings",
    name="Shaft Coupling (clamp)",
    standard="aluminium clamp coupling",
    description="Aluminium clamping coupling with a stepped bore for two shaft diameters and a clamp slit at each end.",
    inputs={"bore_a": {"label": "Bore A"}, "bore_b": {"label": "Bore B"}},
    catalog_id="clamp-shaft-coupling",
    featured=False,
    example={"bore_a": 5, "bore_b": 8, "length": 25},
)
class ClampCoupling(Part):
    def __init__(
        self,
        bore_a: Num(min=3, max=12, step=1) = 5,
        bore_b: Num(min=3, max=12, step=1) = 8,
        length: Num(min=15, max=40, step=1) = 25,
    ):
        """Args:
        bore_a: bore diameter at ``end_a`` (e.g. the 5 mm NEMA 17 shaft).
        bore_b: bore diameter at ``end_b`` (e.g. the 8 mm lead screw).
        length: overall length; each shaft goes in half of it.
        """
        outer_d = max(bore_a, bore_b) * 2.4 + 4
        outer_r = outer_d / 2
        half = length / 2

        # Body.
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), outer_r), length)
        )
        # Stepped bores from each end.
        self.add_operation(
            Extrusion(
                Circle(Point(Sketch(self.xy()), 0, 0), bore_a / 2),
                0,
                half + 0.1,
                cut=True,
            )
        )
        self.add_operation(
            Extrusion(
                Circle(Point(Sketch(self.xy()), 0, 0), bore_b / 2),
                half,
                length,
                cut=True,
            )
        )

        # A radial grub-screw hole near each end (bored across Y into the bore).
        for z in (length * 0.18, length * 0.82):
            hole = Circle(Point(Sketch(self.xz()), 0, z), 1.5)
            self.add_operation(Extrusion(hole, -outer_r - 1, outer_r + 1, cut=True))
        # Anchors: end_a (bore A side, z=0) / end_b (bore B side), the axis,
        # and the two shaft stops at mid-length: a shaft TIP mated onto
        # ``bore_a_stop`` / ``bore_b_stop`` is inserted half the coupling.
        self.bore_a, self.bore_b, self.length = bore_a, bore_b, length
        add_axial_anchors(self, length, ends=("end_a", "end_b"))
        self.add_anchor(make_anchor("bore_a_stop", (0.0, 0.0, half), z_down=True))
        self.add_anchor(make_anchor("bore_b_stop", (0.0, 0.0, half)))
        # Interfaces: a ShaftEnd stops in either bore.
        self.add_interface(Bore(d=bore_a), "bore_a_stop")
        self.add_interface(Bore(d=bore_b), "bore_b_stop")
        self.paint(ALUMINIUM)
