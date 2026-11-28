"""SK-series shaft supports: clamp a smooth rod end above a mounting face.

Built like :class:`~cadbuildr.stdlib.bearings.housed.PillowBlock`: mounting
face on z=0, rod along part +Y at the centre height ``h``. The rod enters
from the ``face_b`` (+Y) side: ``rod_hole`` (+Z = part -Y, into the support)
takes a rod's ``end_a`` / ``end_b`` so the rod end sits flush with that face.
"""

from __future__ import annotations

from typing import ClassVar

from cadbuildr.foundation import Circle, Extrusion, Part, Point, Sketch, make_anchor
from cadbuildr.foundation.interfaces import PlaneFace, RodHole, ScrewHole
from cadbuildr.foundation.library import OneOf, part
from cadbuildr.stdlib.common import ALUMINIUM, rectangle_shape, require_option


@part(
    category="Linear Motion/Smooth Rods",
    name="Shaft Support (SK)",
    standard="SK8 / SK10 / SK12 / SK16",
    description="Aluminium rod-end support: a split clamp bore above a two-bolt foot that holds a smooth rod parallel to the mounting face.",
    catalog_id="sk-shaft-support",
    example={"model": "SK8"},
)
class ShaftSupport(Part):
    # d = rod, h = centre height, H = overall height, W = foot width,
    # T = thickness along the rod, B = bolt spacing, foot = foot height
    TABLE: ClassVar[dict[str, dict]] = {
        "SK8": {"d": 8, "h": 20, "H": 32.8, "W": 42, "T": 14, "B": 32, "foot": 6, "bolt": "M4"},
        "SK10": {"d": 10, "h": 20, "H": 32.8, "W": 42, "T": 14, "B": 32, "foot": 6, "bolt": "M4"},
        "SK12": {"d": 12, "h": 23, "H": 37.5, "W": 42, "T": 14, "B": 32, "foot": 6, "bolt": "M5"},
        "SK16": {"d": 16, "h": 27, "H": 44, "W": 48, "T": 16, "B": 38, "foot": 8, "bolt": "M5"},
    }  # fmt: skip

    def __init__(self, model: OneOf[TABLE] = "SK8"):
        """Args:
        model: support designation (rod diameter, centre height, foot from ``TABLE``).
        """
        t = require_option(self.TABLE, model, what="model", owner="ShaftSupport")
        d, h, H, W, T, B = (float(t[k]) for k in ("d", "h", "H", "W", "T", "B"))
        foot = float(t["foot"])
        boss_w = 1.0 * d + 10.0  # upright width around the bore
        self.add_operation(
            Extrusion(rectangle_shape(Sketch(self.xy()), W, T), 0.0, foot)
        )
        upright = rectangle_shape(Sketch(self.xy()), boss_w, T)
        self.add_operation(Extrusion(upright, foot, H))
        bore = Circle(Point(Sketch(self.xz()), 0.0, h), d / 2)
        self.add_operation(Extrusion(bore, -T, T, cut=True))
        # Clamp slit from the bore to the top.
        slit = Sketch(self.xz())
        slit.pencil.move_to(-0.5, h)
        slit.pencil.line_to(0.5, h)
        slit.pencil.line_to(0.5, H + 0.1)
        slit.pencil.line_to(-0.5, H + 0.1)
        self.add_operation(Extrusion(slit.pencil.close(), -T, T, cut=True))
        hole_r = float(t["bolt"][1:]) / 2 + 0.25
        for sx in (-1, 1):
            hole = Circle(Point(Sketch(self.xy()), sx * B / 2, 0.0), hole_r)
            self.add_operation(Extrusion(hole, 0.0, foot, cut=True))

        self.model, self.rod_diameter, self.center_height = model, d, h
        self.thickness = T
        self.bolt_spacing, self.foot_height = B, foot
        self.add_anchor(make_anchor("bottom", (0.0, 0.0, 0.0), z_down=True))
        self.add_interface(PlaneFace(), "bottom")
        self.add_anchor(
            make_anchor("axis", (0.0, 0.0, h), z_axis=(0, 1, 0), x_axis=(0, 0, 1))
        )
        self.add_anchor(
            make_anchor("face_b", (0.0, T / 2, h), z_axis=(0, 1, 0), x_axis=(0, 0, 1))
        )
        rod_hole = self.add_anchor(
            make_anchor(
                "rod_hole", (0.0, T / 2, h), z_axis=(0, -1, 0), x_axis=(0, 0, 1)
            )
        )
        self.add_interface(RodHole(d=d), rod_hole)
        for i, sx in enumerate((-1, 1)):
            seat = self.add_anchor(
                make_anchor(f"mount_hole_{i}", (sx * B / 2, 0.0, foot))
            )
            self.add_interface(
                ScrewHole(size=t["bolt"], depth=foot), seat, group="mount"
            )
        self.paint(ALUMINIUM)
