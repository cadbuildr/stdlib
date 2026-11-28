"""GT2 belts and idlers, and ``belt_drive`` — two pulleys and the closed belt
around them, placed by anchors.

A belt is built in its own frame: the driver pulley centre at the origin,
the driven pulley centre on +X at ``center_distance``, the belt plane on
z=0 (the belt is extruded symmetrically, so it mates on a pulley's
``belt_plane`` anchor with no offset). Its length is the open-belt length
of the two pitch circles; ``teeth`` is that length / 2 mm, and
:func:`gt2_center_distance` solves the centre distance for a catalogue
closed-loop belt.
"""

from __future__ import annotations

import math
from typing import Any, ClassVar, Literal

from cadbuildr.foundation import (
    BoolParameter,
    Circle,
    Extrusion,
    Part,
    Point,
    Polygon,
    RigidJoint,
    Sketch,
    make_anchor,
)
from cadbuildr.foundation.interfaces import Bore, PlaneFace, ScrewHole
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import (
    ALUMINIUM,
    add_axial_anchors,
    require_option,
    require_range,
)

GT2_PITCH = 2.0  # mm per tooth
BELT_THICKNESS = 1.38  # overall belt height, tooth tip to back (Gates GT2 2MGT)
TOOTH_HEIGHT = 0.75  # tooth height below the land
TOOTH_WIDTH = 1.0  # tooth width at the land (Estimated: GT2 drawings give ~1.0-1.1)
PLD = 0.254  # pitch line differential: land sits this far inside the pitch line
BELT_BLACK = "#1c1d1f"

# Closed-loop GT2 belt lengths (mm) sold off the shelf.
GT2_CLOSED_LENGTHS = (110, 158, 200, 280, 300, 400, 500, 610, 852, 1000)


def gt2_pitch_radius(teeth: int) -> float:
    """Pitch radius of a GT2 pulley / toothed idler with ``teeth`` teeth."""
    return teeth * GT2_PITCH / (2 * math.pi)


def open_belt_length(r1: float, r2: float, center_distance: float) -> float:
    """Pitch length of an open belt around two circles (exact)."""
    c = float(center_distance)
    if c <= abs(r1 - r2):
        raise ValueError(
            f"centre distance {c:g} mm is too short for pitch radii {r1:.2f} / {r2:.2f} mm."
        )
    phi = math.asin((r2 - r1) / c)
    return 2 * c * math.cos(phi) + math.pi * (r1 + r2) + 2 * phi * (r2 - r1)


def gt2_center_distance(belt_length: float, teeth_a: int, teeth_b: int) -> float:
    """Centre distance (mm) that makes a closed GT2 belt of ``belt_length``
    fit pulleys of ``teeth_a`` / ``teeth_b`` teeth (bisection)."""
    r1, r2 = gt2_pitch_radius(teeth_a), gt2_pitch_radius(teeth_b)
    lo = abs(r1 - r2) + 1e-6
    hi = belt_length / 2
    if open_belt_length(r1, r2, hi) < belt_length or (
        open_belt_length(r1, r2, lo) > belt_length
    ):
        raise ValueError(
            f"a {belt_length:g} mm belt cannot wrap {teeth_a}T and {teeth_b}T pulleys."
        )
    for _ in range(80):
        mid = (lo + hi) / 2
        if open_belt_length(r1, r2, mid) < belt_length:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _hull(points):
    """Convex hull (monotone chain), counter-clockwise, no repeated point."""
    pts = sorted(set(points))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def toothed_loop(land, teeth: int, height=TOOTH_HEIGHT, width=TOOTH_WIDTH, n=7):
    """``land`` (a closed CCW outline) with ``teeth`` GT2 teeth pointing
    inward, evenly spaced along it: each tooth a semi-elliptic bump of
    ``width`` at the land and ``height`` deep, with land between teeth."""
    segs = []
    total = 0.0
    for i, a in enumerate(land):
        b = land[(i + 1) % len(land)]
        ln = math.dist(a, b)
        segs.append((total, a, b, ln))
        total += ln

    def at(s):
        s %= total
        for s0, a, b, ln in segs:
            if s0 <= s <= s0 + ln:
                t = (s - s0) / ln if ln else 0.0
                tx, ty = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
                return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), (-ty, tx)
        a, b = segs[-1][1], segs[-1][2]
        return b, (0.0, 0.0)

    spacing = total / teeth
    if spacing <= width:
        raise ValueError("belt too short for its tooth count")
    pts = []
    for i in range(teeth):
        c = i * spacing
        for j in range(n):
            u = -width / 2 + width * j / (n - 1)
            depth = height * math.sqrt(max(0.0, 1.0 - (2 * u / width) ** 2))
            (x, y), (nx, ny) = at(c + u)
            pts.append((x + nx * depth, y + ny * depth))
        (x, y), _ = at(c + spacing / 2)
        pts.append((x, y))
    return pts


def belt_loop(r1: float, r2: float, center_distance: float, segments: int = 48):
    """Closed outline of the belt path at radial offsets r1 / r2 around
    (0, 0) and (center_distance, 0): the convex hull of both circles."""
    pts = []
    for cx, r in ((0.0, r1), (float(center_distance), r2)):
        for i in range(segments):
            a = 2 * math.pi * i / segments
            pts.append((round(cx + r * math.cos(a), 6), round(r * math.sin(a), 6)))
    return _hull(pts)


@part(
    category="Power Transmission/Belts",
    name="GT2 Timing Belt (closed loop)",
    standard="GT2 · 2 mm pitch · 6 / 9 / 10 mm wide",
    description="Closed GT2 belt wrapped around two pulleys at a centre distance; reports its pitch length and tooth count.",
    configurations={
        "20T-20T at 100 mm": dict(
            teeth_a=20, teeth_b=20, center_distance=100, width="6"
        ),
        "20T-40T at 80 mm (2:1)": dict(
            teeth_a=20, teeth_b=40, center_distance=80, width="6"
        ),
        "16T-60T at 60 mm (3.75:1)": dict(
            teeth_a=16, teeth_b=60, center_distance=60, width="6"
        ),
    },
    catalog_id="gt2-belt-loop",
    example={"teeth_a": 20, "teeth_b": 40, "center_distance": 80, "width": "6"},
)
class GT2Belt(Part):
    """Closed GT2 belt. Sources: Gates PowerGrip GT2 2MGT (pitch 2, height 1.38,
    tooth 0.75, PLD 0.254). Estimated: tooth flank modelled as a semi-ellipse
    1.0 wide (the real GT2 flank is a compound arc); no tensile cords."""

    WIDTHS: ClassVar[dict[str, float]] = {"6": 6.0, "9": 9.0, "10": 10.0}

    def __init__(
        self,
        teeth_a: Num(min=10, max=80, step=1, integer=True, unit=None) = 20,
        teeth_b: Num(min=10, max=80, step=1, integer=True, unit=None) = 20,
        center_distance: Num(min=20, max=1000, step=1) = 100,
        width: OneOf[WIDTHS] = "6",
    ):
        """Args:
        teeth_a: tooth count of the pulley at the origin (driver).
        teeth_b: tooth count of the pulley at ``center_distance`` on +X.
        center_distance: distance between the two pulley axes.
        width: belt width (6, 9 or 10 mm).
        """
        w = require_option(self.WIDTHS, str(width), what="width", owner="GT2Belt")
        r1, r2 = gt2_pitch_radius(int(teeth_a)), gt2_pitch_radius(int(teeth_b))
        c = require_range(
            center_distance, lo=1, hi=1000, what="center_distance", owner="GT2Belt"
        )
        if c <= r1 + r2 + 1.0:
            raise ValueError(
                f"GT2Belt: centre distance {c:g} mm makes the pulleys touch "
                f"(pitch radii {r1:.2f} + {r2:.2f} mm)."
            )
        self.pitch_length = open_belt_length(r1, r2, c)
        land = (r1 - PLD, r2 - PLD)
        back = BELT_THICKNESS - TOOTH_HEIGHT
        self.back_offset = (land[0] + land[1]) / 2 + back
        self.teeth = round(self.pitch_length / GT2_PITCH)
        self.ratio = int(teeth_b) / int(teeth_a)
        self.center_distance, self.width = c, w
        outer = (land[0] + back, land[1] + back)
        self.add_operation(
            Extrusion(
                Polygon.from_points(Sketch(self.xy()), belt_loop(*outer, c)),
                -w / 2,
                w / 2,
            )
        )
        self.add_operation(
            Extrusion(
                Polygon.from_points(
                    Sketch(self.xy()),
                    toothed_loop(belt_loop(*land, c, segments=96), self.teeth),
                ),
                -w / 2 - 0.1,
                w / 2 + 0.1,
                cut=True,
            )
        )
        # Anchors: the two pulley centres on the belt plane (+Z = pulley axis).
        self.add_anchor(make_anchor("pulley_a", (0.0, 0.0, 0.0)))
        self.add_anchor(make_anchor("pulley_b", (c, 0.0, 0.0)))
        back = self.add_anchor(
            make_anchor(
                "back", (c / 2, (outer[0] + outer[1]) / 2, 0.0), z_axis=(0, 1, 0)
            )
        )
        self.add_interface(PlaneFace(), back)
        self.paint(BELT_BLACK)


@part(
    category="Power Transmission/Pulleys",
    name="GT2 Idler",
    standard="GT2 · smooth / 20T toothed · 3 or 5 mm bore",
    description="Flanged belt idler on a bearing: smooth (runs on the belt back) or 20-tooth toothed (runs on the teeth).",
    configurations={
        "20T toothed, 5 mm bore": dict(kind="toothed", bore="5", belt_width=6),
        "Smooth, 3 mm bore (F623)": dict(kind="smooth", bore="3", belt_width=6),
        "Smooth, 5 mm bore (F625)": dict(kind="smooth", bore="5", belt_width=6),
    },
    catalog_id="gt2-idler",
    example={"kind": "toothed", "bore": "5", "belt_width": 6},
)
class GT2Idler(Part):
    """GT2 idler. Estimated: flange diameter and thickness (pitch + 4 / 1 mm);
    the bearings inside are not modelled (bore = bearing bore)."""

    BORES: ClassVar[dict[str, float]] = {"3": 3.0, "5": 5.0}

    def __init__(
        self,
        kind: Literal["toothed", "smooth"] = "toothed",
        bore: OneOf[BORES] = "5",
        belt_width: Num(min=6, max=12, step=1) = 6,
    ):
        """Args:
        kind: ``toothed`` (20T, meshes the teeth) or ``smooth`` (same pitch circle, no teeth).
        bore: bearing bore (the idler screw / shaft diameter).
        belt_width: width of the band between the flanges.
        """
        if kind not in ("toothed", "smooth"):
            raise ValueError(
                f"GT2Idler: unknown kind {kind!r} (choose from toothed, smooth)."
            )
        d = require_option(self.BORES, str(bore), what="bore", owner="GT2Idler")
        teeth = 20
        pitch_r = gt2_pitch_radius(teeth)
        flange_r, flange_t = pitch_r + 2.0, 1.0
        z0, z1 = flange_t, flange_t + float(belt_width)
        top = z1 + flange_t
        body_r = pitch_r - PLD  # GT2 OD = pitch diameter - 2 x PLD
        for r, a, b in ((flange_r, 0.0, z0), (body_r, z0, z1), (flange_r, z1, top)):
            self.add_operation(
                Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), r), a, b)
            )
        if kind == "toothed":
            for i in range(teeth):
                a = 2 * math.pi * i / teeth
                gr = body_r - TOOTH_HEIGHT + 0.555  # R0.555 groove, 0.75 deep
                c = Point(Sketch(self.xy()), gr * math.cos(a), gr * math.sin(a))
                self.add_operation(Extrusion(Circle(c, 0.555), z0, z1, cut=True))
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), d / 2), 0, top, cut=True)
        )
        self.kind, self.teeth, self.bore = kind, teeth, d
        self.pitch_radius, self.height = pitch_r, top
        add_axial_anchors(self, top)
        self.add_anchor(make_anchor("belt_plane", (0.0, 0.0, (z0 + z1) / 2)))
        self.add_interface(Bore(d=d), "axis")
        self.add_interface(PlaneFace(), "bottom")
        self.add_interface(ScrewHole(size=f"M{d:g}", depth=top), "top")
        self.paint(ALUMINIUM)


def belt_drive(
    assembly: Any,
    driver: Any,
    driven: Any,
    center_distance: float,
    angle: float = 0.0,
    width: str = "6",
) -> tuple[Any, Any]:
    """Place ``driven`` at ``center_distance`` from the (already placed)
    ``driver`` on the driver's ``belt_plane``, along its +X turned by
    ``angle`` rad, and wrap a :class:`GT2Belt` around both.

    Both pulleys need ``teeth`` and a ``belt_plane`` anchor (``GT2Pulley``,
    ``GT2Idler``). Returns ``(driven_joint, belt)``; ``belt.ratio`` is the
    speed ratio and ``belt.teeth`` the belt's tooth count.
    """
    for p in (driver, driven):
        if not hasattr(p, "teeth"):
            raise TypeError(
                f"belt_drive: {type(p).__name__} is not a GT2 pulley (no teeth)."
            )
    belt = GT2Belt(int(driver.teeth), int(driven.teeth), center_distance, width)
    tag = f"belt_{len(assembly.joints)}"
    line = driver.anchor("belt_plane").rotated(float(angle), name=f"{tag}_dir")
    joint = RigidJoint(
        parent_anchor=line.offset([float(center_distance), 0.0, 0.0], name=f"{tag}_b"),
        child_anchor=driven.anchor("belt_plane"),
        flip=BoolParameter(value=False),
    )
    assembly.add_joint(joint)
    assembly.add_joint(
        RigidJoint(
            parent_anchor=line,
            child_anchor=belt.anchor("pulley_a"),
            flip=BoolParameter(value=False),
        )
    )
    return joint, belt
