"""Studs and threaded rod: DIN 938 / DIN 939 studs and DIN 976-1 rod.

Built along +Z from z=0. Thread pitch and minor diameter come from
:mod:`cadbuildr.stdlib.standards` (ISO 261 / ISO 724); both ends are
chamfered 45° down to the thread root (ISO 4753 "CH" end).
"""

from __future__ import annotations

import math
from typing import ClassVar, Literal

from cadbuildr.foundation import Part, Point3D, Sketch, Thread, make_anchor
from cadbuildr.foundation.interfaces import ScrewTip, Shaft
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import (
    STEEL,
    add_axial_anchors,
    iso_thread_profile,
    lathe_revolve,
    require_option,
    require_range,
)
from cadbuildr.stdlib.standards import thread

_THREAD_LABEL = {"with_thread": {"label": "Modeled thread"}}


def add_thread_section(part, *, d: float, pitch: float, z0: float, z1: float) -> None:
    """External ISO thread between z0 and z1 on a shank of diameter ``d``
    (same profile and pitch-line placement as ``common.add_external_thread``)."""
    if z1 - z0 <= 2 * pitch:
        return
    H = pitch * math.sqrt(3) / 2
    profile = iso_thread_profile(Sketch(part.xz()), pitch, external=True)
    part.add_operation(
        Thread(
            profile=profile,
            pitch=pitch,
            height=z1 - z0 - pitch,
            radius=d / 2 - H / 4,
            center=Point3D(0.0, 0.0, z0 + pitch / 2),
            dir=Point3D(0.0, 0.0, 1.0),
        )
    )


def _rod_profile(d: float, d3: float, length: float):
    """Lathe (r, z) points of a rod of diameter d with both ends chamfered
    45° down to the thread root d3."""
    c = (d - d3) / 2
    r = d / 2
    return [(0.0, 0.0), (r - c, 0.0), (r, c), (r, length - c), (r - c, length), (0.0, length)]


Series = Literal["DIN 938", "DIN 939"]


@part(
    category="Fasteners/Threaded Rods",
    name="Stud",
    standard="DIN 938 (bm = 1 d) · DIN 939 (bm = 1.25 d)",
    description="Double-ended stud: a metal end that screws into a tapped hole (1 d for steel, 1.25 d for cast iron), a plain shank and a nut end.",
    inputs=_THREAD_LABEL,
    configurations={
        "M8 x 30 DIN 938": dict(size="M8", length=30, series="DIN 938"),
        "M10 x 40 DIN 939": dict(size="M10", length=40, series="DIN 939"),
        "M12 x 50 DIN 938": dict(size="M12", length=50, series="DIN 938"),
    },
    catalog_id="din938-stud",
    example={"size": "M10", "length": 40},
)
class StudBolt(Part):
    """DIN 938 / DIN 939 stud. Metal end length bm = 1 d (DIN 938) or
    1.25 d (DIN 939); nut-end thread b = 2 d + 6 for l <= 125 mm (DIN 938
    Table 1); ``length`` l is the nut-end length above the metal end (the
    standard's nominal length). Total length bm + l. The metal end is at
    z=0 (``metal_end``, -Z); ``stud_seat`` at z = bm is where it sits flush
    with the tapped face; ``nut_end`` at the top. Both ends carry
    ``ScrewTip`` (a nut runs on, the tapped hole takes the metal end).

    Estimated: the shank is modeled at the nominal diameter (DIN 938 allows
    a reduced shank ~ pitch diameter for rolled studs)."""

    SIZES: ClassVar[list[str]] = ["M5", "M6", "M8", "M10", "M12", "M16", "M20", "M24"]
    BM: ClassVar[dict[str, float]] = {"DIN 938": 1.0, "DIN 939": 1.25}

    def __init__(
        self,
        size: OneOf[SIZES] = "M10",
        length: Num(min=10, max=200, step=1) = 40,
        series: Series = "DIN 938",
        with_thread: bool = True,
    ):
        """Args:
        size: metric thread size.
        length: nominal length l (nut end, above the metal end).
        series: ``DIN 938`` (bm = 1 d, steel) or ``DIN 939`` (bm = 1.25 d, cast iron).
        with_thread: model the helical threads (slower to render).
        """
        owner = "StudBolt"
        require_option({s: s for s in self.SIZES}, size, what="size", owner=owner)
        k = require_option(self.BM, series, what="series", owner=owner)
        th = thread(size)
        d, P = th.major, th.pitch
        bm = k * d
        b = 2 * d + 6 if length <= 125 else 2 * d + 12
        L = require_range(length, lo=max(b * 0.6, 1.5 * d), hi=200, what="length", owner=owner)
        b = min(b, L)
        total = bm + L
        lathe_revolve(self, _rod_profile(d, th.minor_external, total))
        if with_thread:
            add_thread_section(self, d=d, pitch=P, z0=0.0, z1=bm)
            add_thread_section(self, d=d, pitch=P, z0=total - b, z1=total)
        self.size, self.series, self.with_thread = size, series, with_thread
        self.nominal_diameter, self.thread_pitch = d, P
        self.metal_end_length, self.nut_thread_length = bm, b
        self.length, self.total_length = L, total
        self.add_anchor(make_anchor("metal_end", (0.0, 0.0, 0.0), z_down=True))
        self.add_anchor(make_anchor("nut_end", (0.0, 0.0, total)))
        self.add_anchor(make_anchor("stud_seat", (0.0, 0.0, bm)))
        self.add_anchor(make_anchor("axis", (0.0, 0.0, 0.0)))
        self.add_interface(ScrewTip(size=size), "metal_end")
        self.add_interface(ScrewTip(size=size), "nut_end")
        self.add_interface(Shaft(d=d), "axis")
        self.paint(STEEL)


@part(
    category="Fasteners/Threaded Rods",
    name="Threaded Rod DIN 976-1",
    standard="DIN 976-1 form A (supersedes DIN 975) · ISO 261 coarse",
    description="Fully threaded rod cut to length with both ends chamfered to the thread root; nuts run on from either end.",
    inputs=_THREAD_LABEL,
    configurations={
        "M6 x 100": dict(size="M6", length=100),
        "M10 x 250": dict(size="M10", length=250),
        "M16 x 500": dict(size="M16", length=500),
    },
    catalog_id="din976-threaded-rod",
    example={"size": "M10", "length": 250},
)
class DIN976Rod(Part):
    """DIN 976-1 form A threaded rod (full thread, chamfered ends). Pitch,
    major and root diameters from ISO 261 / ISO 724 (``standards.thread``);
    the ends are chamfered 45° to d3. Stock lengths are 1 m / 2 m / 3 m
    (DIN 976-1 §4); ``length`` is the cut length. ``MetricThreadedRod``
    (DIN 975 label, square ends) is kept for compatibility."""

    SIZES: ClassVar[list[str]] = [
        "M3", "M4", "M5", "M6", "M8", "M10", "M12", "M16", "M20", "M24", "M30",
    ]  # fmt: skip

    def __init__(
        self,
        size: OneOf[SIZES] = "M10",
        length: Num(min=10, max=3000, step=5) = 250,
        with_thread: bool = True,
    ):
        """Args:
        size: metric thread size (ISO 261 coarse).
        length: cut length.
        with_thread: model the helical thread (slower to render).
        """
        owner = "DIN976Rod"
        require_option({s: s for s in self.SIZES}, size, what="size", owner=owner)
        th = thread(size)
        d, P = th.major, th.pitch
        L = require_range(length, lo=max(10.0, 2 * d), hi=3000, what="length", owner=owner)
        lathe_revolve(self, _rod_profile(d, th.minor_external, L))
        if with_thread:
            add_thread_section(self, d=d, pitch=P, z0=0.0, z1=L)
        self.size, self.length, self.with_thread = size, L, with_thread
        self.nominal_diameter, self.thread_pitch, self.root_diameter = d, P, th.minor_external
        self.chamfer = (d - th.minor_external) / 2
        add_axial_anchors(self, L, ends=("end_a", "end_b"))
        for end in ("end_a", "end_b"):
            self.add_interface(ScrewTip(size=size), end)
        self.add_interface(Shaft(d=d), "axis")
        self.paint(STEEL)
