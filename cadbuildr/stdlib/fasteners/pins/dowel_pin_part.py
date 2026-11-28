"""Parallel dowel pins (ISO 8734 hardened, m6) — location, not clamping."""

from __future__ import annotations

from typing import ClassVar

from cadbuildr.foundation import Part
from cadbuildr.foundation.interfaces.features import ShaftFeature
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import (
    STAINLESS,
    add_axial_anchors,
    lathe_revolve,
    require_option,
    require_range,
)


@part(
    category="Fasteners/Pins",
    name="Dowel Pin",
    standard="ISO 8734 (hardened, m6) / DIN 6325",
    description="Hardened parallel pin with chamfered ends that locates two parts precisely; press it into a reamed bore.",
    configurations={
        "3 x 10": dict(diameter="3", length=10),
        "4 x 16": dict(diameter="4", length=16),
        "6 x 20": dict(diameter="6", length=20),
    },
    catalog_id="iso8734-dowel-pin",
    example={"diameter": "4", "length": 20},
)
class DowelPin(Part):
    # nominal diameter -> end chamfer (mm)
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "2": {"d": 2.0, "c": 0.3},
        "3": {"d": 3.0, "c": 0.4},
        "4": {"d": 4.0, "c": 0.5},
        "5": {"d": 5.0, "c": 0.6},
        "6": {"d": 6.0, "c": 0.8},
        "8": {"d": 8.0, "c": 1.0},
        "10": {"d": 10.0, "c": 1.2},
    }

    def __init__(
        self,
        diameter: OneOf[TABLE] = "4",
        length: Num(min=4, max=60, step=1) = 20,
    ):
        """Args:
        diameter: nominal pin diameter (``TABLE`` key).
        length: overall length.
        """
        t = require_option(self.TABLE, str(diameter), what="diameter", owner="DowelPin")
        d, c = t["d"], t["c"]
        length = require_range(
            length, lo=max(2 * d, 4.0), hi=60.0, what="length", owner="DowelPin"
        )
        r = d / 2
        lathe_revolve(
            self,
            [
                (0.0, 0.0),
                (r - c, 0.0),
                (r, c),
                (r, length - c),
                (r - c, length),
                (0.0, length),
            ],
        )
        self.diameter, self.length = d, length
        add_axial_anchors(self, length, ends=("end_a", "end_b"))
        # Interfaces: Shaft on the axis, ShaftEnd at each end (into a Bore).
        ShaftFeature(self, d=d, length=length)
        self.paint(STAINLESS)
