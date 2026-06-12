"""Metric threaded rod addressed by size (the pitch is looked up, not passed)."""

from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import ISO_COARSE_PITCH, nominal_diameter
from cadbuildr.stdlib.fasteners.threaded_rods.base_part import ThreadedRod


@catalog_part(
    id="threaded-rod-metric",
    category="Fasteners",
    subcategory="Threaded Rods",
    name="Threaded Rod (metric)",
    standard="DIN 975 · ISO 261 coarse",
    description="Fully-threaded metric rod — pick the size and length; the ISO coarse pitch is applied automatically.",
    params=[
        ParamSpec.enum("size", choices=list(ISO_COARSE_PITCH.keys()), default="M8"),
        ParamSpec.number("length", min=20, max=300, default=100, step=5),
        ParamSpec.boolean("with_thread", default=True, label="Modeled thread"),
    ],
    featured=True,
    example_config={"size": "M8", "length": 100},
)
class MetricThreadedRod(ThreadedRod):
    def __init__(self, size, length, with_thread=True):
        if size not in ISO_COARSE_PITCH:
            raise ValueError(f"Size '{size}' not a known metric coarse thread.")
        super().__init__(
            diameter=nominal_diameter(size),
            length=length,
            thread_pitch=ISO_COARSE_PITCH[size],
            with_thread=with_thread,
        )
        self.size = size
