"""Pillow block bearing units (KP08 / KP000 / KP001): a self-aligning
insert bearing in a two-bolt cast housing that holds a shaft parallel to the
mounting face — the lead-screw end support of most 3D printers and CNCs.

Built with the mounting face on z=0 and the bore along part +Y at the centre
height ``H1``; dimensions are nominal catalogue values (housings vary by
maker by a few tenths).
"""

from __future__ import annotations

from typing import ClassVar

from cadbuildr.foundation import Circle, Extrusion, Part, Point, Sketch, make_anchor
from cadbuildr.foundation.interfaces import Bore, PlaneFace, ScrewHole
from cadbuildr.foundation.library import OneOf, part
from cadbuildr.stdlib.common import rectangle_shape, require_option

HOUSING_GREY = "#8d939a"


@part(
    category="Bearings/Housed Units",
    name="Pillow Block Bearing",
    standard="KP08 / KP000 / KP001 (zinc housing)",
    description="Two-bolt pillow block: an insert bearing in a cast housing that carries a shaft parallel to the mounting face (lead-screw end supports).",
    catalog_id="pillow-block-kp",
    featured=True,
    example={"model": "KP08"},
)
class PillowBlock(Part):
    # d = bore, L = length, J = bolt spacing, A = width (along the shaft),
    # H = overall height, H1 = shaft centre height, N = bolt hole, bolt = screw size
    TABLE: ClassVar[dict[str, dict]] = {
        "KP08": {
            "d": 8.0,
            "L": 55.0,
            "J": 42.0,
            "A": 13.0,
            "H": 28.0,
            "H1": 15.0,
            "N": 5.0,
            "bolt": "M4",
        },
        "KP000": {
            "d": 10.0,
            "L": 67.0,
            "J": 53.0,
            "A": 16.0,
            "H": 31.0,
            "H1": 17.0,
            "N": 7.0,
            "bolt": "M6",
        },
        "KP001": {
            "d": 12.0,
            "L": 71.0,
            "J": 56.0,
            "A": 16.0,
            "H": 34.0,
            "H1": 19.0,
            "N": 7.0,
            "bolt": "M6",
        },
    }

    def __init__(self, model: OneOf[TABLE] = "KP08"):
        """Args:
        model: housing designation (bore, footprint and centre height from ``TABLE``).
        """
        t = require_option(self.TABLE, model, what="model", owner="PillowBlock")
        d, L, J, A, H, H1 = (t[k] for k in ("d", "L", "J", "A", "H", "H1"))
        boss_r = H - H1
        base_t = 0.4 * H1
        # Base plate, web up to the shaft centre, round boss around the bore.
        base = rectangle_shape(Sketch(self.xy()), L, A)
        self.add_operation(Extrusion(base, 0.0, base_t))
        web = Sketch(self.xz())
        web.pencil.move_to(-boss_r, 0.0)
        web.pencil.line_to(boss_r, 0.0)
        web.pencil.line_to(boss_r, H1)
        web.pencil.line_to(-boss_r, H1)
        self.add_operation(Extrusion(web.pencil.close(), -A / 2, A / 2))
        boss = Circle(Point(Sketch(self.xz()), 0.0, H1), boss_r)
        self.add_operation(Extrusion(boss, -A / 2, A / 2))
        bore = Circle(Point(Sketch(self.xz()), 0.0, H1), d / 2)
        self.add_operation(Extrusion(bore, -A, A, cut=True))
        for sx in (-1, 1):
            hole = Circle(Point(Sketch(self.xy()), sx * J / 2, 0.0), t["N"] / 2)
            self.add_operation(Extrusion(hole, 0.0, base_t, cut=True))

        self.model, self.bore = model, d
        self.center_height, self.width, self.bolt_spacing = H1, A, J
        self.base_thickness = base_t
        # Anchors: mounting face (bottom, outward -Z), bore axis (+Z along
        # the shaft = part +Y), both boss faces, the two bolt-hole seats.
        self.add_anchor(make_anchor("bottom", (0.0, 0.0, 0.0), z_down=True))
        axis = self.add_anchor(
            make_anchor("axis", (0.0, 0.0, H1), z_axis=(0, 1, 0), x_axis=(0, 0, 1))
        )
        self.add_anchor(
            make_anchor(
                "face_a", (0.0, -A / 2, H1), z_axis=(0, -1, 0), x_axis=(0, 0, 1)
            )
        )
        self.add_anchor(
            make_anchor("face_b", (0.0, A / 2, H1), z_axis=(0, 1, 0), x_axis=(0, 0, 1))
        )
        self.add_interface(PlaneFace(), "bottom")
        self.add_interface(Bore(d=d), axis)
        for i, sx in enumerate((-1, 1)):
            seat = self.add_anchor(
                make_anchor(f"mount_hole_{i}", (sx * J / 2, 0.0, base_t))
            )
            self.add_interface(
                ScrewHole(size=t["bolt"], depth=base_t), seat, group="mount"
            )
        self.paint(HOUSING_GREY)
