"""Socket-drive screws with non-cap heads: countersunk (DIN 7991) and button (DIN 7380)."""

import math
from typing import ClassVar

from cadbuildr.foundation import Part
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import (
    ISO_COARSE_PITCH,
    nominal_diameter,
    add_external_thread,
    add_hex_socket,
    lathe_revolve,
)


def _core_radius(radius: float, pitch: float, with_thread: bool) -> float:
    H = pitch * math.sqrt(3) / 2
    return radius - (H / 4 + 0.01 if with_thread else 0.0)


@catalog_part(
    id="din7991-countersunk-socket",
    category="Fasteners",
    subcategory="Screws & Bolts",
    name="Countersunk Socket Screw",
    standard="DIN 7991 / ISO 10642",
    description="Flat 90° countersunk head with a hex (Allen) socket — sits flush with the surface.",
    params=[
        ParamSpec.enum("size", choices=["M3", "M4", "M5", "M6", "M8", "M10", "M12"], default="M6"),
        ParamSpec.number("length", min=6, max=60, default=20, step=1),
        ParamSpec.boolean("with_thread", default=True, label="Modeled thread"),
    ],
    featured=True,
    example_config={"size": "M6", "length": 20},
)
class CountersunkSocketScrew(Part):
    # dk = head diameter, k = head height, s = socket width across flats, t = socket depth
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M3": {"dk": 6.0, "k": 1.7, "s": 2.0, "t": 1.1},
        "M4": {"dk": 8.0, "k": 2.3, "s": 2.5, "t": 1.5},
        "M5": {"dk": 10.0, "k": 2.8, "s": 3.0, "t": 1.9},
        "M6": {"dk": 12.0, "k": 3.3, "s": 4.0, "t": 2.2},
        "M8": {"dk": 16.0, "k": 4.4, "s": 5.0, "t": 3.0},
        "M10": {"dk": 20.0, "k": 5.5, "s": 6.0, "t": 3.6},
        "M12": {"dk": 24.0, "k": 6.5, "s": 8.0, "t": 4.3},
    }

    def __init__(self, size, length, with_thread=True):
        if size not in self.TABLE:
            raise ValueError(f"Size '{size}' not supported.")
        d = self.TABLE[size]
        radius = nominal_diameter(size) / 2
        pitch = ISO_COARSE_PITCH[size]
        core_r = _core_radius(radius, pitch, with_thread)
        head_r = d["dk"] / 2
        k = d["k"]

        # Tip at z=0, flush head top at z=length: shank then a 90° cone flaring to dk.
        lathe_revolve(
            self,
            [(0, 0), (core_r, 0), (core_r, length - k), (head_r, length), (0, length)],
        )
        add_hex_socket(self, top_z=length, width=d["s"], depth=d["t"])
        if with_thread and (length - k) > pitch:
            add_external_thread(self, radius=radius, length=length - k, pitch=pitch)
        self.size, self.length = size, length
        self.paint("grey")


@catalog_part(
    id="din7380-button-head-socket",
    category="Fasteners",
    subcategory="Screws & Bolts",
    name="Button Head Socket Screw",
    standard="DIN 7380 / ISO 7380",
    description="Low domed head with a hex (Allen) socket — a rounded, low-profile alternative to the cap screw.",
    params=[
        ParamSpec.enum("size", choices=["M3", "M4", "M5", "M6", "M8", "M10", "M12"], default="M6"),
        ParamSpec.number("length", min=6, max=60, default=20, step=1),
        ParamSpec.boolean("with_thread", default=True, label="Modeled thread"),
    ],
    featured=False,
    example_config={"size": "M6", "length": 16},
)
class ButtonHeadSocketScrew(Part):
    # dk = head diameter, k = head height, s = socket width across flats, t = socket depth
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M3": {"dk": 5.7, "k": 1.65, "s": 2.0, "t": 1.05},
        "M4": {"dk": 7.6, "k": 2.2, "s": 2.5, "t": 1.3},
        "M5": {"dk": 9.5, "k": 2.75, "s": 3.0, "t": 1.6},
        "M6": {"dk": 10.5, "k": 3.3, "s": 4.0, "t": 2.0},
        "M8": {"dk": 14.0, "k": 4.4, "s": 5.0, "t": 2.6},
        "M10": {"dk": 17.5, "k": 5.8, "s": 6.0, "t": 3.4},
        "M12": {"dk": 21.0, "k": 6.8, "s": 8.0, "t": 4.0},
    }

    DOME_SEGMENTS: ClassVar[int] = 8

    def __init__(self, size, length, with_thread=True):
        if size not in self.TABLE:
            raise ValueError(f"Size '{size}' not supported.")
        d = self.TABLE[size]
        radius = nominal_diameter(size) / 2
        pitch = ISO_COARSE_PITCH[size]
        core_r = _core_radius(radius, pitch, with_thread)
        head_r = d["dk"] / 2
        k = d["k"]

        # Shank to z=length, then a quarter-ellipse dome from (head_r, length) to (0, length+k).
        points = [(0, 0), (core_r, 0), (core_r, length), (head_r, length)]
        for i in range(1, self.DOME_SEGMENTS + 1):
            t = (math.pi / 2) * i / self.DOME_SEGMENTS
            points.append((head_r * math.cos(t), length + k * math.sin(t)))
        lathe_revolve(self, points)
        add_hex_socket(self, top_z=length + k, width=d["s"], depth=d["t"])
        if with_thread and length > pitch:
            add_external_thread(self, radius=radius, length=length, pitch=pitch)
        self.size, self.length = size, length
        self.paint("grey")
