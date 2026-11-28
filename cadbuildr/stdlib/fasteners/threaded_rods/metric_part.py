"""Metric threaded rod addressed by size (the pitch is looked up, not passed)."""

from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import (
    ISO_COARSE_PITCH,
    nominal_diameter,
    require_option,
)
from cadbuildr.stdlib.fasteners.threaded_rods.base_part import ThreadedRod


@part(
    category="Fasteners/Threaded Rods",
    name="Threaded Rod (metric)",
    standard="DIN 975 · ISO 261 coarse",
    description="Fully-threaded metric rod — pick the size and length; the ISO coarse pitch is applied automatically.",
    inputs={"with_thread": {"label": "Modeled thread"}},
    catalog_id="threaded-rod-metric",
    featured=True,
    example={"size": "M8", "length": 100},
)
class MetricThreadedRod(ThreadedRod):
    def __init__(
        self,
        size: OneOf[ISO_COARSE_PITCH] = "M8",
        length: Num(min=20, max=300, step=5) = 100,
        with_thread: bool = True,
    ):
        """Args:
        size: metric thread size (ISO 261 coarse pitch looked up).
        length: rod length (along +Z from z=0).
        with_thread: model the helical thread (slower to render).
        """
        pitch = require_option(
            ISO_COARSE_PITCH, size, what="size", owner="MetricThreadedRod"
        )
        super().__init__(
            diameter=nominal_diameter(size),
            length=length,
            thread_pitch=pitch,
            with_thread=with_thread,
        )
        self.size = size
