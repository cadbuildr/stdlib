"""V-wheels for V-slot extrusion (OpenBuilds-style solid / mini), with their
two 625 bearings modelled as a 5 mm bore.

Built along +Z from z=0 to the wheel width; the V ridge peaks at mid width.
``contact`` sits on the ridge tip on +X (+Z = part +X, out of the wheel) —
the point that runs in a V-slot groove; ``axis`` carries a ``Bore`` for the
5 mm eccentric / plain spacer screw.
"""

from __future__ import annotations

from typing import ClassVar

from cadbuildr.foundation import Part, make_anchor
from cadbuildr.foundation.interfaces import Bore, PlaneFace
from cadbuildr.foundation.library import OneOf, part
from cadbuildr.stdlib.common import (
    NYLON,
    add_axial_anchors,
    lathe_revolve,
    require_option,
)


@part(
    category="Linear Motion/Wheels",
    name="V-Wheel (V-slot)",
    standard="OpenBuilds solid / mini V-wheel · 2 x 625 bearings",
    description="Delrin V-wheel that rides the V groove of V-slot aluminium extrusion — the roller of V-slot gantry plates.",
    catalog_id="v-wheel",
    example={"model": "solid"},
)
class VWheel(Part):
    """Sources: OpenBuilds solid / mini V-wheel drawings (OD, width).
    Estimated: V flank depth; the two 625 bearings are merged into the
    wheel body (5 mm bore)."""

    # od = ridge tip diameter, w = width, flank = V depth, bore = bearing bore
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "solid": {"od": 23.9, "w": 10.23, "flank": 2.6, "bore": 5.0},
        "mini": {"od": 15.23, "w": 8.8, "flank": 2.2, "bore": 5.0},
    }

    def __init__(self, model: OneOf[TABLE] = "solid"):
        """Args:
        model: ``solid`` (23.9 mm) or ``mini`` (15.2 mm) V-wheel.
        """
        t = require_option(self.TABLE, model, what="model", owner="VWheel")
        r_tip, w, f = t["od"] / 2, t["w"], t["flank"]
        r_base, r_bore = r_tip - f, t["bore"] / 2
        shoulder = w / 2 - f  # 90 degree V: flank height = flank depth
        lathe_revolve(
            self,
            [
                (r_bore, 0.0),
                (r_base, 0.0),
                (r_base, shoulder),
                (r_tip, w / 2),
                (r_base, w - shoulder),
                (r_base, w),
                (r_bore, w),
            ],
        )
        self.model, self.width, self.tip_radius = model, w, r_tip
        add_axial_anchors(self, w)
        self.add_anchor(
            make_anchor(
                "contact", (r_tip, 0.0, w / 2), z_axis=(1, 0, 0), x_axis=(0, 0, 1)
            )
        )
        self.add_interface(Bore(d=t["bore"]), "axis")
        self.add_interface(PlaneFace(), "bottom")
        self.add_interface(PlaneFace(), "top")
        self.paint(NYLON)
