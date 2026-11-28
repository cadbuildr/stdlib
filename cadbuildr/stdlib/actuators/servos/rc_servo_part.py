"""Hobby RC servos (SG90 / MG90S micro, MG996R standard).

Body from z=0 (bottom) up to the top face, output spline above it offset
along +X; the two mounting ears sit on a panel (``mount_face``, outward -Z)
with the body through a ``cutout_length`` x ``cutout_width`` opening.
Dimensions are nominal datasheet values.
"""

from __future__ import annotations

from typing import ClassVar

from cadbuildr.foundation import Circle, Extrusion, Part, Point, Sketch, make_anchor
from cadbuildr.foundation.interfaces import PlaneFace, ScrewHole, Shaft, ShaftEnd
from cadbuildr.foundation.library import OneOf, part
from cadbuildr.stdlib.common import rectangle_shape, require_option

SERVO_BLUE = "#2f5fa7"
SERVO_BLACK = "#26282b"


@part(
    category="Actuators/Servos",
    name="RC Servo",
    standard="SG90 / MG90S micro · MG996R standard",
    description="Hobby RC servo: body, two mounting ears and an offset output spline — the actuator of small robots and pan-tilt rigs.",
    catalog_id="rc-servo",
    featured=True,
    example={"model": "SG90"},
)
class Servo(Part):
    """Simplified RC servo envelope (body, ears, boss, spline).

    For detailed servos and horns (serrated 21T / 25T splines, tapered arms
    with hole rows, gear-cover step, cable) use ``cadbuildr.robotics``
    (``servos.HobbyServo``, ``horns.ServoHorn``); this stdlib version is a
    simplified stand-in kept for compatibility and is not developed further.
    """

    # L / W / H body, ear_l total ear length, ear_t ear thickness, ear_z ear
    # underside height, hole_sp / hole_d ear holes (+ screw), boss_d / boss_h
    # top boss, off spline offset along +X, spline_d / spline_h output spline.
    TABLE: ClassVar[dict[str, dict]] = {
        "SG90": dict(L=22.5, W=12.2, H=22.7, ear_l=32.2, ear_t=2.5, ear_z=15.9,
                     hole_sp=27.8, hole_d=2.0, screw="M2", boss_d=11.8, boss_h=4.0,
                     off=5.9, spline_d=4.8, spline_h=3.2, color=SERVO_BLUE),
        "MG90S": dict(L=22.8, W=12.2, H=22.5, ear_l=32.5, ear_t=2.5, ear_z=16.0,
                      hole_sp=28.0, hole_d=2.0, screw="M2", boss_d=11.8, boss_h=4.5,
                      off=5.8, spline_d=4.8, spline_h=3.5, color=SERVO_BLACK),
        "MG996R": dict(L=40.7, W=19.7, H=37.0, ear_l=54.0, ear_t=2.5, ear_z=27.0,
                       hole_sp=49.5, hole_d=4.5, screw="M4", boss_d=20.0, boss_h=2.0,
                       off=10.0, spline_d=5.9, spline_h=4.0, color=SERVO_BLACK),
    }  # fmt: skip

    def __init__(self, model: OneOf[TABLE] = "SG90"):
        """Args:
        model: servo model (body, ears and spline from ``TABLE``).
        """
        t = require_option(self.TABLE, model, what="model", owner="Servo")
        L, W, H = t["L"], t["W"], t["H"]
        self.add_operation(Extrusion(rectangle_shape(Sketch(self.xy()), L, W), 0.0, H))
        ears = rectangle_shape(Sketch(self.xy()), t["ear_l"], W)
        self.add_operation(Extrusion(ears, t["ear_z"], t["ear_z"] + t["ear_t"]))
        for sx in (-1, 1):
            hole = Circle(
                Point(Sketch(self.xy()), sx * t["hole_sp"] / 2, 0.0), t["hole_d"] / 2
            )
            self.add_operation(
                Extrusion(hole, t["ear_z"], t["ear_z"] + t["ear_t"], cut=True)
            )
        top = H + t["boss_h"]
        boss = Circle(Point(Sketch(self.xy()), t["off"], 0.0), t["boss_d"] / 2)
        self.add_operation(Extrusion(boss, H, top))
        spline = Circle(Point(Sketch(self.xy()), t["off"], 0.0), t["spline_d"] / 2)
        self.add_operation(Extrusion(spline, top, top + t["spline_h"]))

        self.model = model
        self.cutout_length, self.cutout_width = L + 0.5, W + 0.5
        self.spline_diameter = t["spline_d"]
        self.spline_offset, self.spline_length, self.top_z = (
            t["off"],
            t["spline_h"],
            top,
        )
        self.ear_z, self.ear_thickness, self.hole_spacing = (
            t["ear_z"],
            t["ear_t"],
            t["hole_sp"],
        )
        # Anchors: body bottom, ear underside (on the panel), output shaft
        # base and horn seat (spline tip), the two ear holes (screw heads).
        self.add_anchor(make_anchor("bottom", (0.0, 0.0, 0.0), z_down=True))
        mount = self.add_anchor(
            make_anchor("mount_face", (0.0, 0.0, t["ear_z"]), z_down=True)
        )
        shaft = self.add_anchor(make_anchor("shaft", (t["off"], 0.0, top)))
        horn = self.add_anchor(
            make_anchor("horn", (t["off"], 0.0, top + t["spline_h"]))
        )
        self.add_interface(PlaneFace(), mount)
        self.add_interface(Shaft(d=t["spline_d"]), shaft)
        self.add_interface(ShaftEnd(d=t["spline_d"]), horn)
        for i, sx in enumerate((-1, 1)):
            seat = self.add_anchor(
                make_anchor(
                    f"mount_hole_{i}",
                    (sx * t["hole_sp"] / 2, 0.0, t["ear_z"] + t["ear_t"]),
                )
            )
            self.add_interface(
                ScrewHole(size=t["screw"], depth=t["ear_t"]), seat, group="mount"
            )
        self.paint(t["color"])
