"""Gearbox side plate: two bearing seats at the gear centre distance, four
corner holes for the spacer through-bolts and two mounting holes."""

from __future__ import annotations

from typing import ClassVar

from cadbuildr.foundation import (
    Circle,
    Extrusion,
    Part,
    Point,
    Rectangle,
    Sketch,
    make_anchor,
)
from cadbuildr.foundation.interfaces import PlaneFace, ScrewHole
from cadbuildr.foundation.interfaces import features as F
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.bearings.ball_bearings.deep_groove_part import (
    DeepGrooveBearing,
)
from cadbuildr.stdlib.common import ALUMINIUM
from cadbuildr.stdlib.gearbox.geometry import (
    CLEARANCE,
    PLATE_THICKNESS,
    StageGeometry,
)

BEARINGS: dict = DeepGrooveBearing.TABLE


@part(
    category="Gearbox/Housing",
    name="Gearbox Plate",
    description="Housing side plate of a spur gear stage: two bearing seats at the centre distance module x (z1 + z2) / 2, corner holes for DIN 912 through-bolts and spacers, two mounting holes.",
    example={"module": 2, "z_pinion": 11, "z_gear": 33, "bearing": "608"},
)
class GearboxPlate(Part):
    """Gearbox side plate (built in XY, outer face on z=0, inner face on z=thickness).

    The input bore is on the origin, the output bore at
    ``x = module * (z_pinion + z_gear) / 2``. Bearing seats open on the outer
    face (diameter and depth from the bearing) with a shoulder behind them.
    Corner holes and outline depend on the centre distance, module and
    screw only, so they stay put when the bearing changes.

    Anchors: ``bore_in`` / ``bore_out`` (seat mouth on the outer face, +Z
    into the plate along the bore), ``seat_in`` / ``seat_out`` (seat shoulder,
    normal toward the opening: mate a bearing's ``top``), ``hole_1..4``
    (corner holes, counter-clockwise from the -X/-Y corner) and
    ``mount_1`` / ``mount_2`` on the outer face (outward normal), ``outer`` /
    ``inner`` faces.

    Args:
        module: gear module of the stage.
        z_pinion: pinion (input) tooth count.
        z_gear: gear (output) tooth count.
        bearing: the deep groove bearing both seats are sized for.
        screw: through-bolt size of the corner and mounting holes.
        thickness: plate thickness (at least the bearing width + 1 mm).
    """

    BEARINGS: ClassVar[dict] = BEARINGS
    CLEARANCE: ClassVar[dict] = CLEARANCE

    def __init__(
        self,
        module: Num(min=0.5, max=3, step=0.5) = 2,
        z_pinion: Num(min=8, max=60, step=1, integer=True, unit=None) = 11,
        z_gear: Num(min=8, max=120, step=1, integer=True, unit=None) = 33,
        bearing: OneOf[BEARINGS] = "608",
        screw: OneOf[CLEARANCE] = "M5",
        thickness: Num(min=4, max=20, step=0.5) = PLATE_THICKNESS,
    ):
        g = StageGeometry(
            module=float(module),
            z_pinion=int(z_pinion),
            z_gear=int(z_gear),
            bearing=bearing,
            screw=screw,
            thickness=float(thickness),
        )
        t = g.thickness
        cd = g.center_distance

        # Rounded-rectangle outline: two crossed rectangles + four corner discs.
        w, h, r = g.x_max - g.x_min, 2.0 * g.y_half, g.edge
        cx = (g.x_min + g.x_max) / 2.0
        for sw, sh in ((w - 2 * r, h), (w, h - 2 * r)):
            rect = Rectangle.from_center_and_sides(
                Point(Sketch(self.xy()), cx, 0.0), sw, sh
            )
            self.add_operation(Extrusion(rect, t))
        for sx in (g.x_min + r, g.x_max - r):
            for sy in (-g.y_half + r, g.y_half - r):
                self.add_operation(
                    Extrusion(Circle(Point(Sketch(self.xy()), sx, sy), r), t)
                )

        # Bearing seats from the outer face (BearingPocket: counterbore +
        # BearingSeat on the shoulder, seat_in / seat_out), shaft clearance
        # through the shoulder.
        B, D = g.bearing_width, float(g.bearing_spec["D"])
        outer = self.add_anchor(make_anchor("outer", (0.0, 0.0, 0.0), z_down=True))
        for x, seat in ((0.0, "seat_in"), (cd, "seat_out")):
            F.BearingPocket(
                face=outer,
                at=(x, 0.0),
                model=bearing,
                name=seat,
                depth=t,
                through_d=g.shoulder_hole,
                D=D,
                B=B,
            )
        # Corner (spacer through-bolt) and mounting holes.
        clearance = CLEARANCE[screw] / 2.0
        holes = g.hole_positions()
        mounts = g.mount_positions()
        for x, y in holes + mounts:
            self.add_operation(
                Extrusion(
                    Circle(Point(Sketch(self.xy()), x, y), clearance), t, cut=True
                )
            )

        # Lightening holes between the bearing seats, above and below the mesh line.
        for sy in (-1.0, 1.0):
            self.add_operation(
                Extrusion(
                    Circle(
                        Point(Sketch(self.xy()), cd / 2.0, sy * g.y_half * 0.54),
                        min(9.0, g.y_half * 0.18),
                    ),
                    t,
                    cut=True,
                )
            )

        self.module, self.z_pinion, self.z_gear = g.module, g.z_pinion, g.z_gear
        self.bearing, self.screw, self.thickness = bearing, screw, t
        self.center_distance = cd
        self.geometry = g

        into = (0.0, 0.0, 1.0)
        self.add_anchor(make_anchor("bore_in", (0.0, 0.0, 0.0), z_axis=into))
        self.add_anchor(make_anchor("bore_out", (cd, 0.0, 0.0), z_axis=into))
        # Corner holes: ScrewHole on the outer face (a washer / head / nut
        # lands there, group "corner") and a flat seat on the inner face (a
        # spacer end, ``hole_<i>_in``); mounting holes (group "mount").
        for i, (x, y) in enumerate(holes, start=1):
            hole = self.add_anchor(make_anchor(f"hole_{i}", (x, y, 0.0), z_down=True))
            self.add_interface(ScrewHole(size=screw, depth=t), hole, group="corner")
            inside = self.add_anchor(make_anchor(f"hole_{i}_in", (x, y, t)))
            self.add_interface(PlaneFace(), inside, group="corner_in")
        for i, (x, y) in enumerate(mounts, start=1):
            hole = self.add_anchor(make_anchor(f"mount_{i}", (x, y, 0.0), z_down=True))
            self.add_interface(ScrewHole(size=screw, depth=t), hole, group="mount")
        self.add_anchor(make_anchor("inner", (0.0, 0.0, t)))
        self.paint(ALUMINIUM)
