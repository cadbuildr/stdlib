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
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
import math


@catalog_part(
    id="threaded-rod-generic",
    category="Fasteners",
    subcategory="Threaded Rods",
    name="Threaded Rod (generic)",
    standard="DIN 975 / ISO 4042",
    description="Fully-threaded metric rod; set the diameter, length and pitch directly.",
    params=[
        ParamSpec.number("diameter", min=3, max=24, default=8, step=1),
        ParamSpec.number("length", min=20, max=300, default=80, step=5),
        ParamSpec.number("thread_pitch", min=0.5, max=3, default=1.25, step=0.05),
        ParamSpec.boolean("with_thread", default=True, label="Modeled thread"),
    ],
    featured=False,
    example_config={"diameter": 8, "length": 80, "thread_pitch": 1.25},
)
class ThreadedRod(Part):
    def __init__(self, diameter, length, thread_pitch=1.25, with_thread=True):
        self.diameter = diameter
        self.length = length
        self.thread_pitch = thread_pitch
        self.with_thread = with_thread

        self.create_body()

        if with_thread:
            self.add_thread()

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
