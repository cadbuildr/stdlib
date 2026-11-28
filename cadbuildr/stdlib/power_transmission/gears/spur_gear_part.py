"""Parametric spur gear with an involute tooth profile (20° pressure angle)."""

import math

from cadbuildr.foundation import (
    Circle,
    Extrusion,
    Part,
    Point,
    Polygon,
    Sketch,
    anchor_plane,
    make_anchor,
)
from cadbuildr.foundation.interfaces import Bore, ScrewHole
from cadbuildr.foundation.library import Num, part
from cadbuildr.stdlib.common import STEEL, add_axial_anchors

PRESSURE_ANGLE_DEG = 20.0
ADDENDUM = 1.0  # x module
DEDENDUM = 1.25  # x module (0.25 m tip clearance)
BACKLASH = 0.1  # x module, taken off each tooth's circular thickness


def _involute(a: float) -> float:
    return math.tan(a) - a


ROOT_FILLET = 0.38  # x module, ISO 53 profile A root radius


def _root_fillet(rf: float, rho: float, line_angle: float, side: int, n: int):
    """Points of a fillet of radius ``rho`` tangent to the root circle ``rf``
    and to the radial line at ``line_angle``, on the gap side ``side``
    (-1: the gap is at smaller angles). Ordered root -> line when side=-1."""
    rc = rf + rho
    delta = math.asin(rho / rc)
    ca = line_angle + side * delta  # fillet centre angle
    cx, cy = rc * math.cos(ca), rc * math.sin(ca)
    a_root = ca + math.pi  # direction centre -> root tangent point
    a_line = line_angle - side * math.pi / 2  # centre -> line tangent point
    # sweep the short way from a_root to a_line
    d = (a_line - a_root + math.pi) % (2 * math.pi) - math.pi
    pts = [
        (
            cx + rho * math.cos(a_root + d * i / n),
            cy + rho * math.sin(a_root + d * i / n),
        )
        for i in range(n + 1)
    ]
    return pts


def spur_gear_outline(
    module: float,
    teeth: int,
    backlash: float = BACKLASH,
    pressure_angle_deg: float = PRESSURE_ANGLE_DEG,
    flank_points: int = 12,
    root_fillet: float = ROOT_FILLET,
    fillet_points: int = 4,
) -> list[tuple[float, float]]:
    """Closed 2D outline (counter-clockwise, no repeated first point) of a
    standard involute spur gear in its own frame, tooth 0 centred on +X.

    Flanks are involutes of the base circle from max(root, base) to the tip
    circle (``flank_points`` + 1 points each); below the base circle the flank
    runs radially and meets the root circle through a fillet of
    ``root_fillet`` x module (ISO 53 profile A: 0.38, reduced when the gap is
    too narrow). Each tooth is thinned by ``backlash`` x module (at the pitch
    circle) so two gears at the standard centre distance r1 + r2 mesh without
    overlap. Not modelled: generation undercut of small pinions (< 17 teeth
    at 20°), whose real flank is a trochoid below the base circle.
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
    gap_half = pitch / 2 - h0  # angular half-width of the gap at the root
    # Fillet radius: ISO value, reduced so it fits the gap and stays below r0.
    rho = root_fillet * module
    while rho > 1e-3 and (
        math.asin(rho / (rf + rho)) > 0.9 * gap_half
        or math.sqrt((rf + rho) ** 2 - rho**2) > r0 + 1e-9
    ):
        rho *= 0.9
    pts: list[tuple[float, float]] = []

    def polar(r: float, a: float) -> None:
        pts.append((r * math.cos(a), r * math.sin(a)))

    for k in range(teeth):
        c = k * pitch
        left = _root_fillet(rf, rho, c - h0, -1, fillet_points)
        right = _root_fillet(rf, rho, c + h0, +1, fillet_points)
        g = gap_half - math.asin(rho / (rf + rho))  # free root arc half-width
        for f in (-0.5, 0.0, 0.5):  # root arc across the gap
            polar(rf, c - pitch / 2 + f * g)
        pts.extend(left)  # root -> radial line below the left flank
        for r in radii:
            polar(r, c - half_angle(r))
        for r in reversed(radii):
            polar(r, c + half_angle(r))
        pts.extend(reversed(right))  # radial line -> root
    return pts


@part(
    category="Power Transmission/Gears",
    name="Spur Gear",
    standard="ISO module · involute 20°",
    description="Parametric spur gear by module and tooth count, with a central bore. Involute teeth (20° pressure angle) with a little backlash, so gears placed by mesh_gears() do not overlap.",
    configurations={
        "m1 12T pinion (5 mm bore)": dict(module=1, teeth=12, face_width=6, bore=5),
        "m1 30T wheel (8 mm bore)": dict(module=1, teeth=30, face_width=6, bore=8),
        "m1.5 20T (8 mm bore)": dict(module=1.5, teeth=20, face_width=8, bore=8),
        "m1 30T with hub (8 mm bore)": dict(
            module=1, teeth=30, face_width=6, bore=8, hub_length=8
        ),
    },
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
        hub_length: Num(min=0, max=20, step=1) = 0,
    ):
        """Args:
        module: tooth size (pitch diameter / teeth); meshing gears share it.
        teeth: number of teeth.
        face_width: gear thickness along its axis.
        bore: diameter of the central bore (the shaft diameter).
        hub_length: set-screw hub on the top face (0 = plain gear, like a
            plate gear); stock gears (Misumi GEABG, KHK SS) have one.

        Sources: ISO 53 profile A basic rack (20°, ha 1 m, hf 1.25 m, root
        radius 0.38 m). Estimated: hub diameter (1.6 x bore + 4, kept inside
        the root circle) and a radial M3 / M4 set screw at mid hub.
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

        rf = pitch_r - DEDENDUM * module
        top = float(face_width)
        hub_d = 0.0
        if hub_length:
            hub_d = min(1.6 * bore + 4.0, 2 * rf - 2.0)
            if hub_d < bore + 3.0:
                raise ValueError(
                    f"SpurGear: no room for a hub on {self.teeth} teeth at module "
                    f"{module:g} with a {bore:g} mm bore (root diameter {2 * rf:.1f} mm)."
                )
            self.add_operation(
                Extrusion(
                    Circle(Point(Sketch(self.xy()), 0, 0), hub_d / 2),
                    top,
                    top + hub_length,
                )
            )
            top += hub_length
        # Bore.
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), bore / 2), top, cut=True)
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
        self.hub_diameter, self.hub_length = hub_d, float(hub_length)
        if hub_length:
            screw = "M3" if bore <= 6 else "M4"
            self.add_anchor(make_anchor("hub_end", (0.0, 0.0, top)))
            seat = self.add_anchor(
                make_anchor(
                    "set_screw",
                    (hub_d / 2, 0.0, face_width + hub_length / 2),
                    z_axis=(1.0, 0.0, 0.0),
                    x_axis=(0.0, 0.0, 1.0),
                )
            )
            drill = Circle(Sketch(anchor_plane(seat)).origin, 0.42 * float(screw[1:]))
            self.add_operation(
                Extrusion(drill, 0.0, -(hub_d - bore) / 2 - 0.1, cut=True)
            )
            self.add_interface(
                ScrewHole(size=screw, depth=(hub_d - bore) / 2, thread=True), seat
            )
        self.paint(STEEL)
