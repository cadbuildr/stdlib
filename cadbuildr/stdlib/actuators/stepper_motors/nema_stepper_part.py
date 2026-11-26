"""NEMA stepper motors (frame sizes 14 / 17 / 23)."""

import math
from typing import ClassVar

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion, make_anchor
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import BLACK_OXIDE


@part(
    category="Actuators/Stepper Motors",
    name="NEMA Stepper Motor",
    standard="NEMA 14 / 17 / 23",
    description="Hybrid stepper motor: chamfered body, front boss, output shaft and four mounting holes. Pick the frame and body length.",
    catalog_id="nema-stepper-motor",
    featured=True,
    example={"frame": "NEMA17", "body_length": 40, "shaft_length": 24},
)
class StepperMotor(Part):
    # body = frame size, pitch = mounting-hole spacing, boss_d, shaft_d, hole_d
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "NEMA14": {
            "body": 35.2,
            "pitch": 26.0,
            "boss_d": 22.0,
            "shaft_d": 5.0,
            "hole_d": 3.0,
        },
        "NEMA17": {
            "body": 42.3,
            "pitch": 31.0,
            "boss_d": 22.0,
            "shaft_d": 5.0,
            "hole_d": 3.0,
        },
        "NEMA23": {
            "body": 56.4,
            "pitch": 47.14,
            "boss_d": 38.1,
            "shaft_d": 6.35,
            "hole_d": 5.0,
        },
    }

    def __init__(
        self,
        frame: OneOf[TABLE] = "NEMA17",
        body_length: Num(min=20, max=80, step=1) = 40,
        shaft_length: Num(min=10, max=40, step=1) = 24,
    ):
        """Args:
        frame: NEMA frame size (body square, hole pitch, boss and shaft from ``TABLE``).
        body_length: motor body length behind the mounting face.
        shaft_length: output shaft length beyond the mounting face.
        """
        if frame not in self.TABLE:
            raise ValueError(f"Unknown frame '{frame}'.")
        d = self.TABLE[frame]
        half = d["body"] / 2
        chamfer = d["body"] * 0.16

        # Chamfered-square body cross-section (octagon), extruded along Z.
        s = Sketch(self.xy())
        c = half - chamfer
        pts = [
            (half, c),
            (c, half),
            (-c, half),
            (-half, c),
            (-half, -c),
            (-c, -half),
            (c, -half),
            (half, -c),
        ]
        s.pencil.move_to(*pts[0])
        for p in pts[1:]:
            s.pencil.line_to(*p)
        body = s.pencil.close()
        self.add_operation(Extrusion(body, 0, body_length))

        # Front boss + shaft, out the +Z face.
        self.add_operation(
            Extrusion(
                Circle(Point(Sketch(self.xy()), 0, 0), d["boss_d"] / 2),
                body_length,
                body_length + 2,
            )
        )
        self.add_operation(
            Extrusion(
                Circle(Point(Sketch(self.xy()), 0, 0), d["shaft_d"] / 2),
                body_length,
                body_length + shaft_length,
            )
        )

        # Four mounting holes in the front face.
        r = d["pitch"] / 2
        for sx in (-1, 1):
            for sy in (-1, 1):
                c = Point(Sketch(self.xy()), sx * r, sy * r)
                self.add_operation(
                    Extrusion(
                        Circle(c, d["hole_d"] / 2),
                        body_length - 5,
                        body_length,
                        cut=True,
                    )
                )
        # Anchors (all +Z out of the front unless noted):
        #   mount_face   front face centre — mate onto a motor plate;
        #   shaft        shaft axis at the front face (RevoluteJoint for
        #                pulleys / gears / couplings riding the shaft);
        #   shaft_tip    end of the shaft — mate a coupling ``bore_a_stop``;
        #   back         rear face (outward normal -Z);
        #   mount_hole_<i>  the four tapped holes on the front face.
        self.body_length = body_length
        self.shaft_length = shaft_length
        self.shaft_radius = d["shaft_d"] / 2
        self.hole_pitch = d["pitch"]
        self.add_anchor(make_anchor("mount_face", (0.0, 0.0, body_length)))
        self.add_anchor(make_anchor("shaft", (0.0, 0.0, body_length)))
        self.add_anchor(
            make_anchor("shaft_tip", (0.0, 0.0, body_length + shaft_length))
        )
        self.add_anchor(make_anchor("back", (0.0, 0.0, 0.0), z_down=True))
        i = 0
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add_anchor(
                    make_anchor(f"mount_hole_{i}", (sx * r, sy * r, body_length))
                )
                i += 1
        self.paint(BLACK_OXIDE)
        self.frame_size = frame
