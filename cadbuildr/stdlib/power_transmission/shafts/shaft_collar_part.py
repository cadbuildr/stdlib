"""Shaft collars: set-screw and one-piece clamp — axial stops on a shaft.

Built along +Z from z=0 (``bottom``) to the collar width (``top``). The bore
is a ``Bore`` on ``axis`` (rides a ``Shaft``: a cylindrical joint whose
offset is the collar's position), both faces are ``PlaneFace`` stops. The
set-screw collar's radial tapped hole is a ``ScrewHole`` on ``set_screw``
(+Z out of the collar) — drop a :class:`~cadbuildr.stdlib.fasteners.SetScrew`
into it with ``connect_with_screw(..., drill=False)``.
"""

from __future__ import annotations

from typing import ClassVar, Literal

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
from cadbuildr.foundation.library import OneOf, part
from cadbuildr.stdlib.common import (
    BLACK_OXIDE,
    add_axial_anchors,
    require_option,
)

Kind = Literal["set-screw", "clamp"]


@part(
    category="Power Transmission/Shafts",
    name="Shaft Collar",
    standard="DIN 705 style set-screw / one-piece clamp collar",
    description="Steel ring locked on a shaft by a set screw or a clamp screw — an axial stop for bearings, pulleys and gears.",
    configurations={
        "8 mm set-screw (lead screw / rod)": dict(bore="8", kind="set-screw"),
        "5 mm set-screw (NEMA 17 shaft)": dict(bore="5", kind="set-screw"),
        "10 mm clamp": dict(bore="10", kind="clamp"),
    },
    catalog_id="shaft-collar",
    example={"bore": "8", "kind": "set-screw"},
)
class ShaftCollar(Part):
    """Sources: DIN 705 A (set-screw collars). Estimated: clamp-collar width /
    OD taken equal to the set-screw series; no edge chamfers."""

    # D outer diameter, w width, screw = set / clamp screw thread
    TABLE: ClassVar[dict[str, dict]] = {
        "3": {"d": 3.0, "D": 7.0, "w": 4.0, "screw": "M3"},
        "4": {"d": 4.0, "D": 8.0, "w": 5.0, "screw": "M3"},
        "5": {"d": 5.0, "D": 10.0, "w": 6.0, "screw": "M3"},
        "6": {"d": 6.0, "D": 12.0, "w": 6.0, "screw": "M3"},
        "8": {"d": 8.0, "D": 16.0, "w": 8.0, "screw": "M4"},
        "10": {"d": 10.0, "D": 20.0, "w": 9.0, "screw": "M4"},
        "12": {"d": 12.0, "D": 22.0, "w": 10.0, "screw": "M5"},
        "15": {"d": 15.0, "D": 25.0, "w": 11.0, "screw": "M5"},
        "20": {"d": 20.0, "D": 32.0, "w": 14.0, "screw": "M6"},
    }

    def __init__(self, bore: OneOf[TABLE] = "8", kind: Kind = "set-screw"):
        """Args:
        bore: shaft diameter (outer diameter, width and screw from ``TABLE``).
        kind: ``set-screw`` (radial grub screw) or ``clamp`` (split, tangential screw).
        """
        t = require_option(self.TABLE, str(bore), what="bore", owner="ShaftCollar")
        if kind not in ("set-screw", "clamp"):
            raise ValueError(
                f"ShaftCollar: unknown kind {kind!r} (choose from set-screw, clamp)."
            )
        d, D, w = t["d"], t["D"], t["w"]
        screw_r = float(t["screw"][1:]) / 2
        o = lambda: Point(Sketch(self.xy()), 0.0, 0.0)  # noqa: E731
        self.add_operation(Extrusion(Circle(o(), D / 2), 0.0, w))
        self.add_operation(Extrusion(Circle(o(), d / 2), 0.0, w, cut=True))
        add_axial_anchors(self, w)
        if kind == "set-screw":
            seat = self.add_anchor(
                make_anchor(
                    "set_screw", (D / 2, 0.0, w / 2), z_axis=(1, 0, 0), x_axis=(0, 0, 1)
                )
            )
            hole = Circle(Sketch(anchor_plane(seat)).origin, screw_r * 0.85)
            self.add_operation(Extrusion(hole, 0.0, -(D - d) / 2 - 0.1, cut=True))
            self.add_interface(
                ScrewHole(
                    size=t["screw"], depth=(D - d) / 2, thread=True, drilled=True
                ),
                seat,
            )
        else:
            # Radial slit on +X and a tangential clamp screw hole across it.
            slit = Sketch(self.xy())
            slit.pencil.move_to(d / 2 - 0.1, -0.5)
            slit.pencil.line_to(D / 2 + 0.1, -0.5)
            slit.pencil.line_to(D / 2 + 0.1, 0.5)
            slit.pencil.line_to(d / 2 - 0.1, 0.5)
            self.add_operation(Extrusion(slit.pencil.close(), 0.0, w, cut=True))
            x_screw = (d / 2 + D / 2) / 2
            seat = self.add_anchor(
                make_anchor(
                    "clamp_screw",
                    (x_screw, D / 2, w / 2),
                    z_axis=(0, 1, 0),
                    x_axis=(0, 0, 1),
                )
            )
            hole = Circle(Sketch(anchor_plane(seat)).origin, screw_r + 0.2)
            self.add_operation(Extrusion(hole, 0.0, -D, cut=True))
            self.add_interface(ScrewHole(size=t["screw"], depth=D / 2), seat)
        self.add_interface(Bore(d=d), "axis")
        self.add_interface(PlaneFace(), "bottom")
        self.add_interface(PlaneFace(), "top")
        self.bore, self.outer_diameter, self.width, self.kind = d, D, w, kind
        self.paint(BLACK_OXIDE)
