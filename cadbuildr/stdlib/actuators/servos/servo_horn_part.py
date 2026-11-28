"""Servo horns (arms / discs) for the :class:`Servo` output spline.

Built along +Z: the hub from z=0 (the face that sits on the servo boss) up
to ``hub_height``, the arm plate on top. The spline bore runs up from z=0
to ``spline_stop`` (``Bore``, +Z pointing back down the bore, like a
coupling's bore stop), so ``assembly.connect(servo.interface("horn"),
horn.interface("spline_stop"))`` seats it. ``arm_tip_<i>`` anchors sit on
the outermost hole of each arm (+Z up) to hang linkages on.
"""

from __future__ import annotations

import math
from typing import ClassVar, Literal

from cadbuildr.foundation import Circle, Extrusion, Part, Point, Sketch, make_anchor
from cadbuildr.foundation.interfaces import Bore, PlaneFace, ScrewHole
from cadbuildr.foundation.library import OneOf, part
from cadbuildr.stdlib.common import (
    NYLON,
    add_axial_anchors,
    oriented_rectangle_shape,
    require_option,
)

Kind = Literal["single", "double", "cross", "disc"]
_ARMS = {"single": 1, "double": 2, "cross": 4, "disc": 0}


@part(
    category="Actuators/Servos",
    name="Servo Horn",
    standard="SG90 / MG90S (21T, 4.8 mm) · MG996R (25T, 5.9 mm)",
    description="Plastic servo horn — single, double or cross arm, or a disc — that fits the output spline of an RC servo.",
    configurations={
        "SG90 double arm": dict(servo="SG90", kind="double"),
        "SG90 cross": dict(servo="SG90", kind="cross"),
        "MG996R disc": dict(servo="MG996R", kind="disc"),
    },
    catalog_id="servo-horn",
    example={"servo": "SG90", "kind": "double"},
)
class ServoHorn(Part):
    """Simplified servo horn.

    For detailed servos and horns (serrated 21T / 25T splines, tapered arms
    with hole rows, gear-cover step, cable) use ``cadbuildr.robotics``
    (``servos.HobbyServo``, ``horns.ServoHorn``); this stdlib version is a
    simplified stand-in kept for compatibility and is not developed further.

    Estimated: arm length, widths, plate thickness and hole sizes from
    measured stock SG90 / MG996R horns (no published drawing); the spline
    is a plain bore of the spline major diameter (no 21T / 25T serrations)."""

    # spline_d / spline_h spline bore, hub_d / hub_h hub, arm length (centre
    # to tip), arm root / tip widths, plate thickness, disc diameter, hole d
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "SG90": dict(spline_d=4.8, spline_h=3.0, hub_d=7.0, hub_h=4.2, arm=15.5,
                     root_w=6.0, tip_w=4.0, t=1.5, disc=20.0, hole=1.0),
        "MG90S": dict(spline_d=4.8, spline_h=3.2, hub_d=7.0, hub_h=4.4, arm=15.5,
                      root_w=6.0, tip_w=4.0, t=1.6, disc=20.0, hole=1.0),
        "MG996R": dict(spline_d=5.9, spline_h=4.0, hub_d=9.5, hub_h=6.0, arm=20.0,
                       root_w=8.0, tip_w=5.5, t=2.0, disc=25.0, hole=1.5),
    }  # fmt: skip

    def __init__(self, servo: OneOf[TABLE] = "SG90", kind: Kind = "double"):
        """Args:
        servo: servo model the horn fits (spline and size from ``TABLE``).
        kind: ``single``, ``double`` or ``cross`` arm, or a ``disc``.
        """
        t = require_option(self.TABLE, servo, what="servo", owner="ServoHorn")
        if kind not in _ARMS:
            raise ValueError(
                f"ServoHorn: unknown kind {kind!r} (choose from {', '.join(_ARMS)})."
            )
        hub_h, plate = t["hub_h"], t["t"]
        z0 = hub_h - plate
        origin = lambda: Point(Sketch(self.xy()), 0.0, 0.0)  # noqa: E731
        self.add_operation(Extrusion(Circle(origin(), t["hub_d"] / 2), 0.0, hub_h))
        n = _ARMS[kind]
        tips = []
        if kind == "disc":
            self.add_operation(Extrusion(Circle(origin(), t["disc"] / 2), z0, hub_h))
            r_tip = t["disc"] / 2 - 2.0
            tips = [
                (r_tip * math.cos(a), r_tip * math.sin(a))
                for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2)
            ]
        else:
            for i in range(n):
                a = 2 * math.pi * i / n
                mid = t["arm"] / 2
                arm = oriented_rectangle_shape(
                    Sketch(self.xy()),
                    mid * math.cos(a),
                    mid * math.sin(a),
                    t["arm"],
                    (t["root_w"] + t["tip_w"]) / 2,
                    a,
                )
                self.add_operation(Extrusion(arm, z0, hub_h))
                tip = Circle(
                    Point(
                        Sketch(self.xy()),
                        t["arm"] * math.cos(a),
                        t["arm"] * math.sin(a),
                    ),
                    t["tip_w"] / 2,
                )
                self.add_operation(Extrusion(tip, z0, hub_h))
                r_tip = t["arm"] - 1.0
                tips.append((r_tip * math.cos(a), r_tip * math.sin(a)))
        for x, y in tips:
            hole = Circle(Point(Sketch(self.xy()), x, y), t["hole"] / 2)
            self.add_operation(Extrusion(hole, z0, hub_h, cut=True))
        # Spline bore from the bottom, and the horn screw hole through the top.
        self.add_operation(
            Extrusion(Circle(origin(), t["spline_d"] / 2), 0.0, t["spline_h"], cut=True)
        )
        self.add_operation(Extrusion(Circle(origin(), 1.1), 0.0, hub_h, cut=True))

        self.servo, self.kind = servo, kind
        self.hub_height, self.spline_depth = hub_h, t["spline_h"]
        self.arm_tips = tips
        add_axial_anchors(self, hub_h)
        stop = self.add_anchor(
            make_anchor("spline_stop", (0.0, 0.0, t["spline_h"]), z_down=True)
        )
        self.add_interface(Bore(d=t["spline_d"]), stop)
        self.add_interface(PlaneFace(), "bottom")
        self.add_interface(ScrewHole(size="M2", depth=hub_h - t["spline_h"]), "top")
        for i, (x, y) in enumerate(tips):
            self.add_anchor(make_anchor(f"arm_tip_{i}", (x, y, hub_h)))
        self.paint(NYLON)
