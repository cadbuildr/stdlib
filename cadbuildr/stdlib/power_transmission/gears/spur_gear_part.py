"""Parametric spur gear with an involute tooth profile (20° pressure angle)."""

import math

from cadbuildr.foundation import (
    Circle,
    Extrusion,
    Part,
    Point,
    Polygon,
    Sketch,
    make_anchor,
)
from cadbuildr.foundation.interfaces import Bore
from cadbuildr.foundation.library import Num, part
from cadbuildr.stdlib.common import STEEL, add_axial_anchors

PRESSURE_ANGLE_DEG = 20.0
ADDENDUM = 1.0  # x module
DEDENDUM = 1.25  # x module (0.25 m tip clearance)
BACKLASH = 0.1  # x module, taken off each tooth's circular thickness


def _involute(a: float) -> float:
    return math.tan(a) - a


def spur_gear_outline(
    module: float,
    teeth: int,
    backlash: float = BACKLASH,
    pressure_angle_deg: float = PRESSURE_ANGLE_DEG,
    flank_points: int = 6,
) -> list[tuple[float, float]]:
    """Closed 2D outline (counter-clockwise, no repeated first point) of a
    standard involute spur gear in its own frame, tooth 0 centred on +X.

    Flanks are involutes of the base circle from max(root, base) to the tip
    circle; below the base circle the flank runs radially to the root. Each
    tooth is thinned by ``backlash`` x module (at the pitch circle) so two gears
    at the standard centre distance r1 + r2 mesh without overlap.
    """
    pa = math.radians(pressure_angle_deg)
    rp = module * teeth / 2
    rb = rp * math.cos(pa)
    ra = rp + ADDENDUM * module
    rf = rp - DEDENDUM * module
    half_pitch_thickness = (math.pi / 2 - backlash) * module / (2 * rp)

    def half_angle(r: float) -> float:
        return (
            half_pitch_thickness + _involute(pa) - _involute(math.acos(rb / max(r, rb)))
        )

    r0 = max(rf, rb)
    radii = [r0 + (ra - r0) * i / flank_points for i in range(flank_points + 1)]
    pitch = 2 * math.pi / teeth
    h0 = half_angle(r0)
    pts: list[tuple[float, float]] = []

    def polar(r: float, a: float) -> None:
        pts.append((r * math.cos(a), r * math.sin(a)))

    for k in range(teeth):
        c = k * pitch
        for j in range(2):  # root arc from mid-gap up to this tooth
            polar(rf, c - pitch / 2 + (pitch / 2 - h0) * j / 2)
        if rf < rb:
            polar(rf, c - h0)
        for r in radii:
            polar(r, c - half_angle(r))
        for r in reversed(radii):
            polar(r, c + half_angle(r))
        if rf < rb:
            polar(rf, c + h0)
        polar(rf, c + h0 + (pitch / 2 - h0) / 2)
    return pts


@part(
    category="Power Transmission/Gears",
    name="Spur Gear",
    standard="ISO module · involute 20°",
    description="Parametric spur gear by module and tooth count, with a central bore. Involute teeth (20° pressure angle) with a little backlash, so gears placed by mesh_gears() do not overlap.",
    catalog_id="spur-gear",
    featured=True,
    example={"module": 1, "teeth": 20, "face_width": 6, "bore": 5},
)
class SpurGear(Part):
    def __init__(
        self,
        module: Num(min=0.5, max=3, step=0.5) = 1,
        teeth: Num(min=8, max=60, step=1, integer=True, unit=None) = 20,
        face_width: Num(min=2, max=20, step=1) = 6,
        bore: Num(min=2, max=12, step=1) = 5,
    ):
        """Args:
        module: tooth size (pitch diameter / teeth); meshing gears share it.
        teeth: number of teeth.
        face_width: gear thickness along its axis.
        bore: diameter of the central bore (the shaft diameter).
        """
        self.module = module
        self.teeth = int(teeth)
        pitch_r = module * self.teeth / 2
        outer_r = pitch_r + ADDENDUM * module

        # One closed involute outline (all teeth) extruded to face width.
        outline = Polygon.from_points(
            Sketch(self.xy()), spur_gear_outline(module, self.teeth)
        )
        self.add_operation(Extrusion(outline, face_width))

        # Bore.
        self.add_operation(
            Extrusion(
                Circle(Point(Sketch(self.xy()), 0, 0), bore / 2), face_width, cut=True
            )
        )
        # Anchors: both faces, bore axis, and the pitch plane (mid face width,
        # +Z along the axis, +X through the centre of tooth 0) — the frame
        # mesh_gears() places meshing gears in.
        self.pitch_radius = pitch_r
        self.outer_radius = outer_r
        self.face_width = face_width
        self.bore = bore
        add_axial_anchors(self, face_width)
        self.add_anchor(make_anchor("pitch_plane", (0.0, 0.0, face_width / 2)))
        # Interface: the bore on a Shaft (CylindricalJoint: offset + mesh phase).
        self.add_interface(Bore(d=bore), "axis")
        self.paint(STEEL)
