"""Pan head cross-recess machine screws (ISO 7045, Phillips H).

The small-electronics screw: M2 / M2.5 / M3 pan heads hold servos, PCBs and
displays (projects used to hand-roll it). The cross recess is modelled as two
crossed slots — enough to read as Phillips at catalogue scale.
"""

from __future__ import annotations

import math
from typing import ClassVar

from cadbuildr.foundation import Extrusion, Sketch
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import (
    ISO_COARSE_PITCH,
    STEEL,
    add_external_thread,
    lathe_revolve,
    nominal_diameter,
    oriented_rectangle_shape,
    require_option,
)
from cadbuildr.stdlib.fasteners.base import Fastener


@part(
    category="Fasteners/Screws & Bolts",
    name="Pan Head Screw (Phillips)",
    standard="ISO 7045 · cross recess H",
    description="Low domed pan head with a Phillips cross recess — the screw for servos, PCBs and small electronics.",
    inputs={"with_thread": {"label": "Modeled thread"}},
    configurations={
        "M2 x 6 (servo horn / PCB)": dict(size="M2", length=6),
        "M2.5 x 8 (Raspberry Pi)": dict(size="M2.5", length=8),
        "M3 x 10": dict(size="M3", length=10),
    },
    catalog_id="iso7045-pan-head-phillips",
    example={"size": "M3", "length": 10},
)
class PanHeadScrew(Fastener):
    # dk = head diameter, k = head height, m = recess diameter (ISO 7045).
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M2": {"dk": 4.0, "k": 1.6, "m": 1.9},
        "M2.5": {"dk": 5.0, "k": 2.1, "m": 2.7},
        "M3": {"dk": 5.6, "k": 2.4, "m": 3.0},
        "M4": {"dk": 8.0, "k": 3.1, "m": 4.4},
        "M5": {"dk": 9.5, "k": 3.7, "m": 4.9},
        "M6": {"dk": 12.0, "k": 4.6, "m": 6.9},
    }
    DOME_SEGMENTS: ClassVar[int] = 6

    def __init__(
        self,
        size: OneOf[TABLE] = "M3",
        length: Num(min=3, max=50, step=1) = 10,
        with_thread: bool = True,
    ):
        """Args:
        size: metric thread size (head and recess dimensions from ``TABLE``).
        length: nominal length under the head.
        with_thread: model the helical thread (slower to render).
        """
        d = require_option(self.TABLE, size, what="size", owner="PanHeadScrew")
        radius = nominal_diameter(size) / 2
        pitch = ISO_COARSE_PITCH[size]
        length = float(length)
        core_r = radius - (0.15 * pitch if with_thread else 0.0)
        head_r, k = d["dk"] / 2, d["k"]

        # Shank, a straight head side (60 % of k), then a flat dome.
        side = 0.6 * k
        points = [(0.0, 0.0), (core_r, 0.0), (core_r, length), (head_r, length)]
        points.append((head_r, length + side))
        for i in range(1, self.DOME_SEGMENTS + 1):
            t = (math.pi / 2) * i / self.DOME_SEGMENTS
            points.append(
                (head_r * math.cos(t), length + side + (k - side) * math.sin(t))
            )
        lathe_revolve(self, points)
        top = length + k
        width = 0.22 * d["m"]
        for angle in (0.0, math.pi / 2):
            slot = oriented_rectangle_shape(
                Sketch(self.xy()), 0.0, 0.0, width, d["m"], angle
            )
            self.add_operation(Extrusion(slot, top - 0.5 * k, top + 0.1, cut=True))
        if with_thread and length > pitch:
            add_external_thread(self, radius=radius, length=length, pitch=pitch)
        self.head_radius, self.head_height = head_r, k
        self._set_fastener_contract(body_radius=radius, body_height=length)
        self.size, self.length = size, length
        self.paint(STEEL)
