from cadbuildr.foundation import (
    Part,
    Sketch,
    Point,
    Axis,
    Line,
    Lathe,
    Thread,
    Point3D,
)
from cadbuildr.foundation.interfaces import ScrewTip
from cadbuildr.foundation.library import Num, part
from cadbuildr.stdlib.common import add_axial_anchors
import math


@part(
    category="Fasteners/Threaded Rods",
    name="Threaded Rod (generic)",
    standard="DIN 975 / ISO 4042",
    description="Fully-threaded metric rod; set the diameter, length and pitch directly.",
    inputs={"with_thread": {"label": "Modeled thread"}},
    configurations={
        "M8 x 80 (1.25 pitch)": dict(diameter=8, length=80, thread_pitch=1.25),
        "M10 x 100 (1.5 pitch)": dict(diameter=10, length=100, thread_pitch=1.5),
        "M8 fine x 80 (1.0 pitch)": dict(diameter=8, length=80, thread_pitch=1.0),
    },
    catalog_id="threaded-rod-generic",
    example={"diameter": 8, "length": 80, "thread_pitch": 1.25},
)
class ThreadedRod(Part):
    def __init__(
        self,
        diameter: Num(min=3, max=24, step=1) = 8,
        length: Num(min=20, max=300, step=5) = 80,
        thread_pitch: Num(min=0.5, max=3, step=0.05) = 1.25,
        with_thread: bool = True,
    ):
        """Args:
        diameter: major (nominal) diameter.
        length: rod length (along +Z from z=0).
        thread_pitch: thread pitch (ISO coarse M8 = 1.25).
        with_thread: model the helical thread (slower to render).
        """
        if float(diameter) <= 0 or float(length) <= 0 or float(thread_pitch) <= 0:
            raise ValueError(
                f"ThreadedRod: diameter, length and thread_pitch must be > 0 "
                f"(got {diameter}, {length}, {thread_pitch})."
            )
        self.diameter = diameter
        self.length = length
        self.thread_pitch = thread_pitch
        self.with_thread = with_thread

        self.create_body()

        if with_thread:
            self.add_thread()
        # Anchors: end faces + axis (nuts mate on the ends or slide on axis).
        self.radius = diameter / 2
        add_axial_anchors(self, length, ends=("end_a", "end_b"))
        # Interfaces: a nut runs on from either end (NutSeat <-> ScrewTip).
        size = f"M{float(diameter):g}"
        for end in ("end_a", "end_b"):
            self.add_interface(ScrewTip(size=size), end)

    def create_body(self):
        s = Sketch(self.xz())
        radius = self.diameter / 2

        s.pencil.line(radius, 0)
        s.pencil.line(0, self.length)
        s.pencil.line_to(0, self.length)
        s.pencil.line_to(0, 0)
        s.pencil.close()

        shape = s.pencil.get_closed_shape()
        axis = Axis(Line(s.origin, Point(s, 0, self.length)))
        self.add_operation(Lathe(shape, axis))

    def add_thread(self):
        thread_height = self.length
        H = self.thread_pitch * math.sqrt(3) / 2

        thread_radius = self.diameter / 2 - H / 4

        s = Sketch(self.xz())
        s.pencil.line_to(0, -self.thread_pitch / 2 + self.thread_pitch / 16)
        s.pencil.line_to(5 / 8 * H, -self.thread_pitch / 8)
        s.pencil.line(0, self.thread_pitch / 4)
        s.pencil.line_to(0, self.thread_pitch / 2 - self.thread_pitch / 16)

        profile = s.pencil.close()

        thread = Thread(
            profile=profile,
            pitch=self.thread_pitch,
            height=thread_height - self.thread_pitch,
            radius=thread_radius,
            center=Point3D(0, 0, self.thread_pitch / 2),
            dir=Point3D(0, 0, 1),
        )
        self.add_operation(thread)
