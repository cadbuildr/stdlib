"""Slotted-drive screws: cheese head (DIN 84) and countersunk slotted (DIN 963)."""

import math
from typing import ClassVar

from cadbuildr.foundation import Part
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import (
    ISO_COARSE_PITCH,
    nominal_diameter,
    add_external_thread,
    add_screwdriver_slot,
    lathe_revolve,
)


def _core_radius(radius: float, pitch: float, with_thread: bool) -> float:
    H = pitch * math.sqrt(3) / 2
    return radius - (H / 4 + 0.01 if with_thread else 0.0)


@catalog_part(
    id="din84-cheese-head-slotted",
    category="Fasteners",
    subcategory="Screws & Bolts",
    name="Cheese Head Slotted Screw",
    standard="DIN 84 / ISO 1207",
    description="Cylindrical head with a straight screwdriver slot — a classic slotted machine screw.",
    params=[
        ParamSpec.enum("size", choices=["M3", "M4", "M5", "M6", "M8", "M10"], default="M4"),
        ParamSpec.number("length", min=5, max=50, default=16, step=1),
        ParamSpec.boolean("with_thread", default=True, label="Modeled thread"),
    ],
    featured=False,
    example_config={"size": "M4", "length": 16},
)
class CheeseHeadSlottedScrew(Part):
    # dk = head diameter, k = head height, n = slot width, t = slot depth
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M3": {"dk": 5.5, "k": 2.0, "n": 0.8, "t": 0.85},
        "M4": {"dk": 7.0, "k": 2.6, "n": 1.0, "t": 1.1},
        "M5": {"dk": 8.5, "k": 3.3, "n": 1.2, "t": 1.3},
        "M6": {"dk": 10.0, "k": 3.9, "n": 1.6, "t": 1.6},
        "M8": {"dk": 13.0, "k": 5.0, "n": 2.0, "t": 2.0},
        "M10": {"dk": 16.0, "k": 6.0, "n": 2.5, "t": 2.4},
    }

    def __init__(self, size, length, with_thread=True):
        if size not in self.TABLE:
            raise ValueError(f"Size '{size}' not supported.")
        d = self.TABLE[size]
        radius = nominal_diameter(size) / 2
        pitch = ISO_COARSE_PITCH[size]
        core_r = _core_radius(radius, pitch, with_thread)
        head_r = d["dk"] / 2
        top = length + d["k"]

        # Shank then a cylindrical head; slot cut across the top.
        lathe_revolve(
            self,
            [(0, 0), (core_r, 0), (core_r, length), (head_r, length), (head_r, top), (0, top)],
        )
        add_screwdriver_slot(self, top_z=top, across=d["dk"] + 0.5, width=d["n"], depth=d["t"])
        if with_thread and length > pitch:
            add_external_thread(self, radius=radius, length=length, pitch=pitch)
        self.size, self.length = size, length
        self.paint("grey")


@catalog_part(
    id="din963-countersunk-slotted",
    category="Fasteners",
    subcategory="Screws & Bolts",
    name="Countersunk Slotted Screw",
    standard="DIN 963 / ISO 2009",
    description="Flat 90° countersunk head with a straight screwdriver slot — sits flush with the surface.",
    params=[
        ParamSpec.enum("size", choices=["M3", "M4", "M5", "M6", "M8", "M10"], default="M4"),
        ParamSpec.number("length", min=5, max=50, default=16, step=1),
        ParamSpec.boolean("with_thread", default=True, label="Modeled thread"),
    ],
    featured=False,
    example_config={"size": "M4", "length": 16},
)
class CountersunkSlottedScrew(Part):
    # dk = head diameter, k = head height, n = slot width, t = slot depth
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M3": {"dk": 5.6, "k": 1.65, "n": 0.8, "t": 0.85},
        "M4": {"dk": 7.5, "k": 2.2, "n": 1.0, "t": 1.0},
        "M5": {"dk": 9.2, "k": 2.5, "n": 1.2, "t": 1.25},
        "M6": {"dk": 11.0, "k": 3.0, "n": 1.6, "t": 1.4},
        "M8": {"dk": 14.5, "k": 4.0, "n": 2.0, "t": 2.0},
        "M10": {"dk": 18.0, "k": 5.0, "n": 2.5, "t": 2.3},
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

        lathe_revolve(
            self,
            [(0, 0), (core_r, 0), (core_r, length - k), (head_r, length), (0, length)],
        )
        add_screwdriver_slot(self, top_z=length, across=d["dk"] + 0.5, width=d["n"], depth=d["t"])
        if with_thread and (length - k) > pitch:
            add_external_thread(self, radius=radius, length=length - k, pitch=pitch)
        self.size, self.length = size, length
        self.paint("grey")
