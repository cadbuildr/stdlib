"""Straight gear rack (module, 20° pressure angle) — the linear partner of
:class:`~cadbuildr.stdlib.power_transmission.gears.SpurGear`.

Frame: the rack lies in the part XY plane like a spur gear (face width along
+Z from 0), its pitch line on the X axis, teeth pointing +Y, body down to
``-height``. A gap is centred on x=0. The ``slide`` anchor (+Z along the rack,
+X = part -Z) is what :func:`mesh_rack` puts on a ``SliderJoint`` next to a
pinion, coupled to the pinion's ``RevoluteJoint`` by a ``RackPinionRelation``.
"""

from __future__ import annotations

import math

from cadbuildr.foundation import Extrusion, Part, Polygon, Sketch, make_anchor
from cadbuildr.foundation.interfaces import PlaneFace
from cadbuildr.foundation.library import Num, part
from cadbuildr.stdlib.common import STEEL, require_range
from cadbuildr.stdlib.power_transmission.gears.spur_gear_part import (
    ADDENDUM,
    BACKLASH,
    DEDENDUM,
    PRESSURE_ANGLE_DEG,
    ROOT_FILLET,
)


def _fillet(corner, toward_root, toward_flank, rho, n=4):
    """Arc of radius ``rho`` rounding ``corner`` between the root line
    (unit direction ``toward_root``) and the flank (``toward_flank``)."""
    ux, uy = toward_root
    vx, vy = toward_flank
    cos_t = ux * vx + uy * vy
    theta = math.acos(max(-1.0, min(1.0, cos_t)))
    t = rho / math.tan(theta / 2)
    p_root = (corner[0] + ux * t, corner[1] + uy * t)
    p_flank = (corner[0] + vx * t, corner[1] + vy * t)
    bx, by = ux + vx, uy + vy
    bl = math.hypot(bx, by)
    d = rho / math.sin(theta / 2)
    cx, cy = corner[0] + bx / bl * d, corner[1] + by / bl * d
    a0 = math.atan2(p_root[1] - cy, p_root[0] - cx)
    a1 = math.atan2(p_flank[1] - cy, p_flank[0] - cx)
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    return [
        (cx + rho * math.cos(a0 + da * i / n), cy + rho * math.sin(a0 + da * i / n))
        for i in range(n + 1)
    ]


def rack_outline(
    module: float,
    teeth: int,
    height: float,
    backlash: float = BACKLASH,
    root_fillet: float = ROOT_FILLET,
) -> list[tuple[float, float]]:
    """Closed outline of a rack of ``teeth`` straight-flanked teeth (ISO 53
    basic rack: 20°, addendum 1 m, dedendum 1.25 m, root radius 0.38 m),
    centred on x=0 (a gap at x=0 when ``teeth`` is even), pitch line on y=0."""
    p = math.pi * module
    a = math.radians(PRESSURE_ANGLE_DEG)
    tan_a = math.tan(a)
    half_t = (math.pi / 2 - backlash) * module / 2  # half thickness at pitch line
    add, ded = ADDENDUM * module, DEDENDUM * module
    rho = root_fillet * module
    up_l, up_r = (math.sin(a), math.cos(a)), (-math.sin(a), math.cos(a))
    x0 = -teeth * p / 2
    pts = [(x0, -height), (x0, -ded)]
    for k in range(teeth):
        c = x0 + (k + 0.5) * p
        left = (c - half_t - ded * tan_a, -ded)
        right = (c + half_t + ded * tan_a, -ded)
        pts += _fillet(left, (-1.0, 0.0), up_l, rho)
        pts += [(c - half_t + add * tan_a, add), (c + half_t - add * tan_a, add)]
        pts += list(reversed(_fillet(right, (1.0, 0.0), up_r, rho)))
    pts += [(-x0, -ded), (-x0, -height)]
    return pts


@part(
    category="Power Transmission/Gears",
    name="Gear Rack",
    standard="ISO module · straight 20°",
    description="Straight-toothed gear rack by module and length; mesh it with a spur gear pinion through mesh_rack() and a rack-and-pinion joint relation.",
    configurations={
        "m1 x 200": dict(module=1, length=200, face_width=6, height=8),
        "m1.5 x 300": dict(module=1.5, length=300, face_width=10, height=12),
    },
    catalog_id="gear-rack",
    example={"module": 1, "length": 200, "face_width": 6, "height": 8},
)
class GearRack(Part):
    def __init__(
        self,
        module: Num(min=0.5, max=3, step=0.5) = 1,
        length: Num(min=20, max=1000, step=5) = 200,
        face_width: Num(min=2, max=30, step=1) = 6,
        height: Num(min=3, max=40, step=1) = 8,
    ):
        """Args:
        module: tooth size (circular pitch = pi x module); the pinion shares it.
        length: nominal length, rounded down to an even number of pitches.
        face_width: rack thickness along part +Z.
        height: body depth below the pitch line.
        """
        module = require_range(module, lo=0.1, hi=10, what="module", owner="GearRack")
        p = math.pi * module
        teeth = 2 * int(float(length) // (2 * p))
        if teeth < 2:
            raise ValueError(
                f"GearRack: length {length:g} mm holds no tooth pair at module {module:g} "
                f"(pitch {p:.2f} mm)."
            )
        if height <= DEDENDUM * module:
            raise ValueError(
                f"GearRack: height {height:g} mm must exceed the dedendum "
                f"{DEDENDUM * module:g} mm."
            )
        outline = Polygon.from_points(
            Sketch(self.xy()), rack_outline(module, teeth, float(height))
        )
        self.add_operation(Extrusion(outline, face_width))

        self.module, self.teeth, self.pitch = module, teeth, p
        self.length = teeth * p
        self.face_width, self.height = face_width, height
        # Anchors: slide (pitch point, mid face, +Z along +X), back face,
        # both ends.
        self.add_anchor(
            make_anchor(
                "slide",
                (0.0, 0.0, face_width / 2),
                z_axis=(1.0, 0.0, 0.0),
                x_axis=(0.0, 0.0, -1.0),
            )
        )
        back = self.add_anchor(
            make_anchor(
                "back", (0.0, -float(height), face_width / 2), z_axis=(0, -1, 0)
            )
        )
        self.add_interface(PlaneFace(), back)
        self.add_anchor(
            make_anchor(
                "end_a", (-self.length / 2, 0.0, face_width / 2), z_axis=(-1, 0, 0)
            )
        )
        self.add_anchor(
            make_anchor(
                "end_b", (self.length / 2, 0.0, face_width / 2), z_axis=(1, 0, 0)
            )
        )
        self.paint(STEEL)
