"""Washer variants: DIN 127 split spring lock washer and DIN 9021 fender washer."""

from typing import ClassVar

from cadbuildr.foundation import Part, Sketch, Extrusion
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import lathe_revolve
from cadbuildr.stdlib.fasteners.washers.din125_part import Washer


@catalog_part(
    id="din127-split-lock-washer",
    category="Fasteners",
    subcategory="Washers",
    name="Split Lock Washer",
    standard="DIN 127 B",
    description="Square-section spring ring with a radial split that bites into the joint to resist loosening.",
    params=[
        ParamSpec.enum("size", choices=["M3", "M4", "M5", "M6", "M8", "M10", "M12"], default="M6"),
    ],
    featured=False,
    example_config={"size": "M6"},
)
class SplitLockWasher(Part):
    # d1 = inner dia, d2 = outer dia, s = section size (square wire)
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M3": {"d1": 3.1, "d2": 6.2, "s": 0.8},
        "M4": {"d1": 4.1, "d2": 7.6, "s": 0.9},
        "M5": {"d1": 5.1, "d2": 9.2, "s": 1.2},
        "M6": {"d1": 6.1, "d2": 11.8, "s": 1.6},
        "M8": {"d1": 8.2, "d2": 14.8, "s": 2.0},
        "M10": {"d1": 10.2, "d2": 18.1, "s": 2.2},
        "M12": {"d1": 12.2, "d2": 21.1, "s": 2.5},
    }

    def __init__(self, size):
        d = self.TABLE[size]
        ri, ro, s = d["d1"] / 2, d["d2"] / 2, d["s"]
        # Square-section annulus revolved into a flat ring.
        lathe_revolve(self, [(ri, 0), (ro, 0), (ro, s), (ri, s), (ri, 0)])
        self._cut_split(ri, ro, s)
        self.paint("grey")
        self.size = size

    def _cut_split(self, ri, ro, s):
        """Remove a thin radial slice on +X so the ring reads as split."""
        gap = max(0.5, s * 0.5)
        sk = Sketch(self.xy())
        x0, x1 = ri - 0.5, ro + 0.5
        sk.pencil.move_to(x0, -gap / 2)
        sk.pencil.line_to(x1, -gap / 2)
        sk.pencil.line_to(x1, gap / 2)
        sk.pencil.line_to(x0, gap / 2)
        shape = sk.pencil.close()
        self.add_operation(Extrusion(shape, 0, s, cut=True))


@catalog_part(
    id="din9021-fender-washer",
    category="Fasteners",
    subcategory="Washers",
    name="Fender Washer",
    standard="DIN 9021 / ISO 7093",
    description="Oversized-OD flat washer that spreads load over a wide area (~3× the bolt diameter).",
    params=[
        ParamSpec.enum("size", choices=["M3", "M4", "M5", "M6", "M8", "M10", "M12"], default="M6"),
    ],
    featured=False,
    example_config={"size": "M6"},
)
class FenderWasher(Washer):
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M3": {"d1": 3.2, "d2": 9.0, "s": 0.8},
        "M4": {"d1": 4.3, "d2": 12.0, "s": 1.0},
        "M5": {"d1": 5.3, "d2": 15.0, "s": 1.2},
        "M6": {"d1": 6.4, "d2": 18.0, "s": 1.6},
        "M8": {"d1": 8.4, "d2": 24.0, "s": 2.0},
        "M10": {"d1": 10.5, "d2": 30.0, "s": 2.5},
        "M12": {"d1": 13.0, "d2": 37.0, "s": 3.0},
    }

    def __init__(self, size):
        d = self.TABLE[size]
        super().__init__(
            outer_radius=d["d2"] / 2, inner_radius=d["d1"] / 2, thickness=d["s"]
        )
        self.paint("grey")
        self.size = size
