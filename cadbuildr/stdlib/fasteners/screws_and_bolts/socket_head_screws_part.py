"""Socket-drive screws with non-cap heads: countersunk (DIN 7991) and button (DIN 7380)."""

import math
from typing import ClassVar

from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import (
    ISO_COARSE_PITCH,
    nominal_diameter,
    add_external_thread,
    add_hex_socket,
    countersunk_head_profile,
    lathe_revolve,
    require_option,
)
from cadbuildr.stdlib.fasteners.base import Fastener


def _core_radius(radius: float, pitch: float, with_thread: bool) -> float:
    H = pitch * math.sqrt(3) / 2
    return radius - (H / 4 + 0.01 if with_thread else 0.0)


@part(
    category="Fasteners/Screws & Bolts",
    name="Countersunk Socket Screw",
    standard="DIN 7991 / ISO 10642",
    description="Flat 90° countersunk head with a hex (Allen) socket — sits flush with the surface.",
    inputs={"with_thread": {"label": "Modeled thread"}},
    catalog_id="din7991-countersunk-socket",
    featured=True,
    example={"size": "M6", "length": 20},
)
class CountersunkSocketScrew(Fastener):
    # ISO 10642: dk = theoretical head diameter (max, the countersink
    # size), dka = actual head diameter (min), k = head height (max),
    # s = socket across flats, t = socket depth (min).
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M3": {"dk": 6.72, "dka": 5.54, "k": 1.86, "s": 2.0, "t": 1.1},
        "M4": {"dk": 8.96, "dka": 7.53, "k": 2.48, "s": 2.5, "t": 1.5},
        "M5": {"dk": 11.20, "dka": 9.43, "k": 3.10, "s": 3.0, "t": 1.9},
        "M6": {"dk": 13.44, "dka": 11.34, "k": 3.72, "s": 4.0, "t": 2.2},
        "M8": {"dk": 17.92, "dka": 15.24, "k": 4.96, "s": 5.0, "t": 3.0},
        "M10": {"dk": 22.40, "dka": 19.22, "k": 6.20, "s": 6.0, "t": 3.6},
        "M12": {"dk": 26.88, "dka": 23.12, "k": 7.44, "s": 8.0, "t": 4.3},
    }

    def __init__(
        self,
        size: OneOf[TABLE] = "M6",
        length: Num(min=6, max=60, step=1) = 20,
        with_thread: bool = True,
    ):
        """Args:
        size: metric thread size (head and socket dimensions from ``TABLE``).
        length: overall length, head included (the head sits flush).
        with_thread: model the helical thread (slower to render).
        """
        d = require_option(self.TABLE, size, what="size", owner=type(self).__name__)
        radius = nominal_diameter(size) / 2
        pitch = ISO_COARSE_PITCH[size]
        core_r = _core_radius(radius, pitch, with_thread)
        head_r = d["dk"] / 2
        k = d["k"]

        # Tip at z=0, flush head top at z=length: shank, 90° cone, truncated
        # head edge at the actual diameter (ISO 10642).
        nominal = 2 * radius
        lathe_revolve(
            self,
            countersunk_head_profile(core_r, length, nominal, d["dk"], d["dka"]),
        )
        add_hex_socket(self, top_z=length, width=d["s"], depth=d["t"])
        if with_thread and (length - k) > pitch:
            add_external_thread(self, radius=radius, length=length - k, pitch=pitch)
        # Countersunk: embeds fully, the seat is the flush head top.
        self.head_radius, self.head_height = head_r, k
        self._set_fastener_contract(body_radius=radius, body_height=length)
        self.size, self.length = size, length
        self.paint("grey")


@part(
    category="Fasteners/Screws & Bolts",
    name="Button Head Socket Screw",
    standard="ISO 7380-1 / DIN 7380",
    description="Low domed head with a hex (Allen) socket — a rounded, low-profile alternative to the cap screw.",
    inputs={"with_thread": {"label": "Modeled thread"}},
    catalog_id="din7380-button-head-socket",
    example={"size": "M6", "length": 16},
)
class ButtonHeadSocketScrew(Fastener):
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

    def __init__(
        self,
        size: OneOf[TABLE] = "M6",
        length: Num(min=6, max=60, step=1) = 20,
        with_thread: bool = True,
    ):
        """Args:
        size: metric thread size (head and socket dimensions from ``TABLE``).
        length: nominal length under the head.
        with_thread: model the helical thread (slower to render).
        """
        d = require_option(self.TABLE, size, what="size", owner=type(self).__name__)
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
        # Under-dome seat at the top of the shank.
        self.head_radius, self.head_height = head_r, k
        self._set_fastener_contract(body_radius=radius, body_height=length)
        self.size, self.length = size, length
        self.paint("grey")
