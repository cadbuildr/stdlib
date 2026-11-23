"""Wood screws: gauge-sized, pointed tip, countersunk flat head.

The machine screws in this folder have flat-ended shanks and metric
sizes; a wood screw is sized by GAUGE (#4-#12), tapers to a sharp point,
and its ~82° countersunk head pulls flush into the wood. Follows the
``connect_with_screw`` contract (`head_seat` anchor + ``body_radius`` /
``body_height``): the screw embeds fully, so the seat plane is the head
TOP, flush with the face it is driven into.
"""

import math
from typing import ClassVar

from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import add_screwdriver_slot, lathe_revolve
from cadbuildr.stdlib.fasteners.base import Fastener


@catalog_part(
    id="wood-screw-countersunk",
    category="Fasteners",
    subcategory="Screws & Bolts",
    name="Wood Screw (countersunk)",
    standard="ASME B18.6.1 (gauge sizes)",
    description=(
        "Pointed, gauge-sized wood screw with a flush countersunk head — "
        "the fastener for slat/board construction (decks, chairs, fences)."
    ),
    params=[
        ParamSpec.enum("gauge", choices=["4", "6", "8", "10", "12"], default="8"),
        ParamSpec.number("length", min=12, max=100, default=32, step=1),
    ],
    featured=True,
    example_config={"gauge": "8", "length": 32},
)
class WoodScrew(Fastener):
    # gauge -> major thread diameter d, head diameter dk (mm, ASME B18.6.1)
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "4": {"d": 2.9, "dk": 5.7},
        "6": {"d": 3.5, "dk": 7.0},
        "8": {"d": 4.2, "dk": 8.4},
        "10": {"d": 4.8, "dk": 9.7},
        "12": {"d": 5.5, "dk": 11.1},
    }

    def __init__(self, gauge="8", length=32.0):
        gauge = str(gauge)
        if gauge not in self.TABLE:
            raise ValueError(
                f"Gauge '#{gauge}' not supported (choose from {sorted(self.TABLE)})."
            )
        t = self.TABLE[gauge]
        shank_r = t["d"] / 2.0
        head_r = t["dk"] / 2.0
        # 82° included-angle countersunk head: k = (dk - d)/2 / tan(41°)
        k = (head_r - shank_r) / math.tan(math.radians(41.0))
        if length < 2.5 * t["d"]:
            raise ValueError(
                f"length {length} too short for a #{gauge} wood screw "
                f"(minimum ~{2.5 * t['d']:.0f}mm)."
            )
        tip_h = min(1.6 * t["d"], max(length - k - 1.0, 1.0))

        # Point -> straight shank -> countersunk cone -> flat top.
        lathe_revolve(
            self,
            [
                (0.0, 0.0),
                (shank_r, tip_h),
                (shank_r, length - k),
                (head_r, length),
                (0.0, length),
            ],
        )
        add_screwdriver_slot(
            self,
            top_z=length,
            across=t["dk"] + 0.5,
            width=0.25 * t["d"],
            depth=0.3 * t["d"],
        )

        # connect_with_screw contract: fully embedded, head flush.
        self.head_radius = head_r
        self.head_height = k
        self._set_fastener_contract(body_radius=shank_r, body_height=length)
        self.gauge, self.length = gauge, length
        self.paint("grey")
