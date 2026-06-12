"""T-slot nut for 6 mm aluminium-extrusion slots (2020 / 2040 series)."""

from typing import ClassVar

from cadbuildr.foundation import Part, Sketch, Circle, Extrusion
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import rectangle_shape, add_internal_thread


@catalog_part(
    id="t-slot-nut-6mm",
    category="Fasteners",
    subcategory="Nuts",
    name="T-Slot Nut (6 mm)",
    standard="6 mm slot · 2020 / 2040 series",
    description="Slide-in T-nut for the 6 mm slot of 2020/2040 aluminium extrusion: wide flange under the lips, narrow neck through the opening.",
    params=[
        ParamSpec.enum("size", choices=["M3", "M4", "M5", "M6"], default="M5"),
    ],
    featured=False,
    example_config={"size": "M5"},
)
class TSlotNut(Part):
    # Geometry of the 6 mm slot interface (mm), shared by all thread sizes.
    FLANGE_W: ClassVar[float] = 10.0   # across the slot, catches under the lips
    NECK_W: ClassVar[float] = 5.8      # passes through the 6 mm opening
    LENGTH: ClassVar[float] = 6.0      # along the slot
    FLANGE_H: ClassVar[float] = 1.6
    NECK_H: ClassVar[float] = 1.6
    PITCH: ClassVar[dict[str, float]] = {"M3": 0.5, "M4": 0.7, "M5": 0.8, "M6": 1.0}

    def __init__(self, size, with_thread=True):
        if size not in self.PITCH:
            raise ValueError(f"Size '{size}' not supported.")
        nominal = float(size[1:])
        total_h = self.FLANGE_H + self.NECK_H

        flange = rectangle_shape(Sketch(self.xy()), self.FLANGE_W, self.LENGTH)
        self.add_operation(Extrusion(flange, 0, self.FLANGE_H))
        neck = rectangle_shape(Sketch(self.xy()), self.NECK_W, self.LENGTH)
        self.add_operation(Extrusion(neck, self.FLANGE_H, total_h))

        bore = Circle(Sketch(self.xy()).origin, nominal / 2)
        self.add_operation(Extrusion(bore, 0, total_h, cut=True))
        if with_thread:
            add_internal_thread(self, nominal_radius=nominal / 2, length=total_h, pitch=self.PITCH[size])
        self.paint("grey")
        self.size = size
