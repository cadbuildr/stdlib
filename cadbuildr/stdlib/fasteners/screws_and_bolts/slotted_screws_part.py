"""Slotted-drive screws: cheese head (DIN 84) and countersunk slotted (DIN 963)."""

import math
from typing import ClassVar

from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import (
    ISO_COARSE_PITCH,
    nominal_diameter,
    add_external_thread,
    add_screwdriver_slot,
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
    name="Cheese Head Slotted Screw",
    standard="DIN 84 / ISO 1207",
    description="Cylindrical head with a straight screwdriver slot — a classic slotted machine screw.",
    inputs={"with_thread": {"label": "Modeled thread"}},
    catalog_id="din84-cheese-head-slotted",
    example={"size": "M4", "length": 16},
)
class CheeseHeadSlottedScrew(Fastener):
    # dk = head diameter, k = head height, n = slot width, t = slot depth
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M3": {"dk": 5.5, "k": 2.0, "n": 0.8, "t": 0.85},
        "M4": {"dk": 7.0, "k": 2.6, "n": 1.0, "t": 1.1},
        "M5": {"dk": 8.5, "k": 3.3, "n": 1.2, "t": 1.3},
        "M6": {"dk": 10.0, "k": 3.9, "n": 1.6, "t": 1.6},
        "M8": {"dk": 13.0, "k": 5.0, "n": 2.0, "t": 2.0},
        "M10": {"dk": 16.0, "k": 6.0, "n": 2.5, "t": 2.4},
    }

    def __init__(
        self,
        size: OneOf[TABLE] = "M4",
        length: Num(min=5, max=50, step=1) = 16,
        with_thread: bool = True,
    ):
        """Args:
        size: metric thread size (head and slot dimensions from ``TABLE``).
        length: nominal length under the head.
        with_thread: model the helical thread (slower to render).
        """
        d = require_option(self.TABLE, size, what="size", owner=type(self).__name__)
        radius = nominal_diameter(size) / 2
        pitch = ISO_COARSE_PITCH[size]
        core_r = _core_radius(radius, pitch, with_thread)
        head_r = d["dk"] / 2
        top = length + d["k"]

        # Shank then a cylindrical head; slot cut across the top.
        lathe_revolve(
            self,
            [
                (0, 0),
                (core_r, 0),
                (core_r, length),
                (head_r, length),
                (head_r, top),
                (0, top),
            ],
        )
        add_screwdriver_slot(
            self, top_z=top, across=d["dk"] + 0.5, width=d["n"], depth=d["t"]
        )
        if with_thread and length > pitch:
            add_external_thread(self, radius=radius, length=length, pitch=pitch)
        # Under-head seat at the top of the shank.
        self.head_radius, self.head_height = head_r, d["k"]
        self._set_fastener_contract(body_radius=radius, body_height=length)
        self.size, self.length = size, length
        self.paint("grey")


@part(
    category="Fasteners/Screws & Bolts",
    name="Countersunk Slotted Screw",
    standard="DIN 963 / ISO 2009",
    description="Flat 90° countersunk head with a straight screwdriver slot — sits flush with the surface.",
    inputs={"with_thread": {"label": "Modeled thread"}},
    catalog_id="din963-countersunk-slotted",
    example={"size": "M4", "length": 16},
)
class CountersunkSlottedScrew(Fastener):
    # dk = head diameter, k = head height, n = slot width, t = slot depth
    # ISO 2009 (DIN 963): dk = theoretical head diameter (max, the
    # countersink size), dka = actual head diameter (min), k = head height
    # (max), n = slot width (nominal), t = slot depth (max).
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M3": {"dk": 6.3, "dka": 5.5, "k": 1.65, "n": 0.8, "t": 0.85},
        "M4": {"dk": 9.4, "dka": 8.4, "k": 2.7, "n": 1.2, "t": 1.3},
        "M5": {"dk": 10.4, "dka": 9.3, "k": 2.7, "n": 1.2, "t": 1.4},
        "M6": {"dk": 12.6, "dka": 11.3, "k": 3.3, "n": 1.6, "t": 1.6},
        "M8": {"dk": 17.3, "dka": 15.8, "k": 4.65, "n": 2.0, "t": 2.3},
        "M10": {"dk": 20.0, "dka": 18.3, "k": 5.0, "n": 2.5, "t": 2.6},
    }

    def __init__(
        self,
        size: OneOf[TABLE] = "M4",
        length: Num(min=5, max=50, step=1) = 16,
        with_thread: bool = True,
    ):
        """Args:
        size: metric thread size (head and slot dimensions from ``TABLE``).
        length: overall length, head included (the head sits flush).
        with_thread: model the helical thread (slower to render).
        """
        d = require_option(self.TABLE, size, what="size", owner=type(self).__name__)
        radius = nominal_diameter(size) / 2
        pitch = ISO_COARSE_PITCH[size]
        core_r = _core_radius(radius, pitch, with_thread)
        head_r = d["dk"] / 2
        k = d["k"]

        lathe_revolve(
            self,
            countersunk_head_profile(core_r, length, 2 * radius, d["dk"], d["dka"]),
        )
        add_screwdriver_slot(
            self, top_z=length, across=d["dk"] + 0.5, width=d["n"], depth=d["t"]
        )
        if with_thread and (length - k) > pitch:
            add_external_thread(self, radius=radius, length=length - k, pitch=pitch)
        # Countersunk: embeds fully, the seat is the flush head top.
        self.head_radius, self.head_height = head_r, k
        self._set_fastener_contract(body_radius=radius, body_height=length)
        self.size, self.length = size, length
        self.paint("grey")
