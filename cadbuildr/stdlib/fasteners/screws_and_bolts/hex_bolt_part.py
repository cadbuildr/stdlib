"""Hex-head bolts (DIN 933 fully threaded / DIN 931 partially threaded)."""

import math
from typing import ClassVar

from cadbuildr.foundation import Part, Sketch, Axis, Line, Point, Lathe, Extrusion
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import (
    ISO_COARSE_PITCH,
    nominal_diameter,
    hexagon_shape,
    add_external_thread,
)


@catalog_part(
    id="hex-bolt",
    category="Fasteners",
    subcategory="Screws & Bolts",
    name="Hex Head Bolt",
    standard="DIN 933 / 931 · ISO 4017 / 4014",
    description="Hexagonal-head bolt. Fully threaded by default; set a grip length for a DIN 931 partial thread.",
    params=[
        ParamSpec.enum("size", choices=["M3", "M4", "M5", "M6", "M8", "M10", "M12"], default="M8"),
        ParamSpec.number("length", min=8, max=80, default=30, step=1),
        ParamSpec.number("grip_length", min=0, max=40, default=0, step=1, label="Unthreaded grip"),
        ParamSpec.boolean("with_thread", default=True, label="Modeled thread"),
    ],
    featured=True,
    example_config={"size": "M8", "length": 35, "grip_length": 12},
)
class HexBolt(Part):
    # width across flats (mm) and head height k (mm), ISO 4017/4014.
    HEAD_TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M3": {"waf": 5.5, "k": 2.0},
        "M4": {"waf": 7.0, "k": 2.8},
        "M5": {"waf": 8.0, "k": 3.5},
        "M6": {"waf": 10.0, "k": 4.0},
        "M8": {"waf": 13.0, "k": 5.3},
        "M10": {"waf": 16.0, "k": 6.4},
        "M12": {"waf": 18.0, "k": 7.5},
    }

    def __init__(self, size, length, grip_length=0, with_thread=True):
        if size not in self.HEAD_TABLE:
            raise ValueError(f"Size '{size}' not supported by HexBolt.")
        self.size = size
        self.length = length
        self.with_thread = with_thread

        head = self.HEAD_TABLE[size]
        self.waf = head["waf"]
        self.head_height = head["k"]
        self.radius = nominal_diameter(size) / 2
        self.pitch = ISO_COARSE_PITCH[size]
        # Grip is the unthreaded shank just under the head; clamp to the shank length.
        self.grip_length = max(0.0, min(grip_length, length))
        self.thread_length = length - self.grip_length

        self._build_shank()
        self._build_head()
        if with_thread and self.thread_length > self.pitch:
            add_external_thread(
                self, radius=self.radius, length=self.thread_length, pitch=self.pitch
            )
        self.paint("grey")

    def _build_shank(self):
        """Lathe a stepped profile: reduced core over the threaded portion,
        full nominal radius over the grip, so threads read as proud crests."""
        s = Sketch(self.xz())
        H = self.pitch * math.sqrt(3) / 2
        core_r = self.radius - (H / 4 + 0.01 if self.with_thread else 0.0)

        s.pencil.move_to(0, 0)
        s.pencil.line_to(core_r, 0)
        s.pencil.line_to(core_r, self.thread_length)
        if self.grip_length > 0:
            s.pencil.line_to(self.radius, self.thread_length)
            s.pencil.line_to(self.radius, self.length)
        s.pencil.line_to(0, self.length)
        shape = s.pencil.close()
        axis = Axis(Line(s.origin, Point(s, 0, self.length)))
        self.add_operation(Lathe(shape, axis))

    def _build_head(self):
        hexagon = hexagon_shape(Sketch(self.xy()), self.waf)
        self.add_operation(
            Extrusion(hexagon, self.length, self.length + self.head_height)
        )
