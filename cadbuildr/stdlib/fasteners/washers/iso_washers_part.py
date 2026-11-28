"""Plain and lock washers beyond DIN 125 / DIN 9021 / DIN 127.

* :class:`ISO7090Washer` — plain washer, normal series, chamfered (ISO 7090).
* :class:`DIN433Washer` — small-series plain washer for cheese-head screws
  (DIN 433 / ISO 7092).
* :class:`ToothLockWasher` — serrated lock washer with external (form A) or
  internal (form J) teeth (DIN 6798).

ISO 7089 (plain, normal) is :class:`~.din125_part.DIN125Washer` and ISO 7093
(large) is :class:`~.washer_variants_part.FenderWasher`. Built along +Z from
z=0; ``bottom`` sits on a hole face (``NutSeat``), ``top`` offers a
``ScrewHole`` to the head / nut on it, like the other washers.
"""

from __future__ import annotations

import math
from typing import ClassVar, Literal

from cadbuildr.foundation import Extrusion, Part, Sketch
from cadbuildr.foundation.library import OneOf, part
from cadbuildr.stdlib.common import STEEL, add_axial_anchors, lathe_revolve, require_option
from cadbuildr.stdlib.fasteners.washers.washer_variants_part import _washer_interfaces


def _ring(part, ri, ro, h, chamfer=None):
    """Annulus ri..ro, 0..h; ``chamfer`` = (radial, axial) on the top outer edge."""
    if chamfer:
        cr, cz = chamfer
        pts = [(ri, 0.0), (ro, 0.0), (ro, h - cz), (ro - cr, h), (ri, h)]
    else:
        pts = [(ri, 0.0), (ro, 0.0), (ro, h), (ri, h)]
    lathe_revolve(part, pts)


class _PlainWasher(Part):
    TABLE: ClassVar[dict[str, tuple[float, float, float]]] = {}
    OWNER: ClassVar[str] = "washer"
    CHAMFER: ClassVar[bool] = False

    def _build(self, size: str) -> None:
        d1, d2, h = require_option(self.TABLE, size, what="size", owner=self.OWNER)
        ri, ro = d1 / 2, d2 / 2
        chamfer = None
        if self.CHAMFER:
            # ISO 7090 Fig. 1: 30° chamfer on the outer edge, h/4 .. h/2 high.
            cz = 0.375 * h
            chamfer = (cz / math.tan(math.radians(30.0)), cz)
        _ring(self, ri, ro, h, chamfer)
        self.size, self.inner_radius, self.outer_radius, self.thickness = size, ri, ro, h
        add_axial_anchors(self, h)
        _washer_interfaces(self, size, h)
        self.paint(STEEL)


@part(
    category="Fasteners/Washers",
    name="Chamfered Flat Washer",
    standard="ISO 7090 (normal series, 200 HV)",
    description="Plain washer of the ISO 7089 size with a 30° chamfer on the outer edge, for hex bolts and nuts.",
    configurations={"M6": dict(size="M6"), "M8": dict(size="M8"), "M12": dict(size="M12")},
    catalog_id="iso7090-chamfered-washer",
    example={"size": "M8"},
)
class ISO7090Washer(_PlainWasher):
    """ISO 7090: d1 (bore, min), d2 (outside, max), h (nominal) from ISO
    7090:2000 Table 1 (= ISO 7089 sizes; M8: 8.4 / 16 / 1.6). The standard
    covers M5 and up. Estimated: chamfer height 0.375 h (the standard gives
    h/4 .. h/2) at 30°."""

    TABLE: ClassVar[dict[str, tuple[float, float, float]]] = {
        "M5": (5.3, 10.0, 1.0), "M6": (6.4, 12.0, 1.6), "M8": (8.4, 16.0, 1.6),
        "M10": (10.5, 20.0, 2.0), "M12": (13.0, 24.0, 2.5), "M16": (17.0, 30.0, 3.0),
        "M20": (21.0, 37.0, 3.0), "M24": (25.0, 44.0, 4.0),
    }  # fmt: skip
    OWNER: ClassVar[str] = "ISO7090Washer"
    CHAMFER: ClassVar[bool] = True

    def __init__(self, size: OneOf[TABLE] = "M8"):
        """Args:
        size: metric size the washer fits (d1, d2, h from ``TABLE``).
        """
        self._build(size)


@part(
    category="Fasteners/Washers",
    name="Small Flat Washer",
    standard="DIN 433 / ISO 7092 (small series)",
    description="Small-diameter plain washer for cheese-head and socket screws where a DIN 125 washer is too wide.",
    configurations={"M3": dict(size="M3"), "M5": dict(size="M5"), "M8": dict(size="M8")},
    catalog_id="din433-small-washer",
    example={"size": "M5"},
)
class DIN433Washer(_PlainWasher):
    """DIN 433-1 / ISO 7092: d1 (min), d2 (max), h from ISO 7092:2000 Table 1
    (M3: 3.2 / 6 / 0.5; M8: 8.4 / 15 / 1.6)."""

    TABLE: ClassVar[dict[str, tuple[float, float, float]]] = {
        "M2": (2.2, 4.5, 0.3), "M2.5": (2.7, 5.0, 0.5), "M3": (3.2, 6.0, 0.5),
        "M4": (4.3, 8.0, 0.5), "M5": (5.3, 9.0, 1.0), "M6": (6.4, 11.0, 1.6),
        "M8": (8.4, 15.0, 1.6), "M10": (10.5, 18.0, 1.6), "M12": (13.0, 20.0, 2.0),
    }  # fmt: skip
    OWNER: ClassVar[str] = "DIN433Washer"

    def __init__(self, size: OneOf[TABLE] = "M5"):
        """Args:
        size: metric size the washer fits (d1, d2, h from ``TABLE``).
        """
        self._build(size)


Form = Literal["A", "J"]


@part(
    category="Fasteners/Washers",
    name="Serrated Lock Washer",
    standard="DIN 6798 A (external teeth) / J (internal teeth)",
    description="Thin spring-steel lock washer with a ring of teeth on the outside (A) or inside (J) that bite into the head and the seat.",
    configurations={"M4 A": dict(size="M4", form="A"), "M6 A": dict(size="M6", form="A"), "M6 J": dict(size="M6", form="J")},
    catalog_id="din6798-serrated-lock-washer",
    example={"size": "M6", "form": "A"},
)
class ToothLockWasher(Part):
    """DIN 6798 serrated lock washer: d1 (bore), d2 (outside), s (sheet
    thickness) from DIN 6798 (as listed e.g. at
    https://www.mcmaster.com/din-6798-lock-washers: M6 6.4 / 11 / 0.7).
    Teeth: V notches cut through the rim (form A) or the bore edge (form J)
    over 45 % of the ring width.

    Estimated: tooth counts (DIN 6798: 9..12 for M3..M12, form J one to two
    fewer); the teeth are flat — their alternating twist (which makes the
    free height about 2 s) is not modeled."""

    # size: (d1, d2, s, teeth A, teeth J)
    TABLE: ClassVar[dict[str, tuple[float, float, float, int, int]]] = {
        "M3": (3.2, 6.0, 0.4, 9, 7), "M4": (4.3, 8.0, 0.5, 9, 8),
        "M5": (5.3, 10.0, 0.6, 9, 8), "M6": (6.4, 11.0, 0.7, 9, 9),
        "M8": (8.4, 15.0, 0.8, 11, 10), "M10": (10.5, 18.0, 0.9, 11, 12),
        "M12": (13.0, 20.5, 1.0, 12, 12),
    }  # fmt: skip
    TOOTH_DEPTH: ClassVar[float] = 0.45

    def __init__(self, size: OneOf[TABLE] = "M6", form: Form = "A"):
        """Args:
        size: metric size the washer fits (d1, d2, s from ``TABLE``).
        form: ``A`` external teeth or ``J`` internal teeth.
        """
        owner = "ToothLockWasher"
        d1, d2, s, za, zj = require_option(self.TABLE, size, what="size", owner=owner)
        if form not in ("A", "J"):
            raise ValueError(f"{owner}: unknown form {form!r} (choose from A, J).")
        ri, ro = d1 / 2, d2 / 2
        _ring(self, ri, ro, s)
        z = za if form == "A" else zj
        depth = self.TOOTH_DEPTH * (ro - ri)
        # V notch: tip on the root circle, mouth (half a tooth pitch wide) past the edge.
        if form == "A":
            r_tip, r_mouth = ro - depth, ro + 0.5
        else:
            r_tip, r_mouth = ri + depth, ri - 0.5 if ri > 0.6 else 0.1
        half = math.pi / z / 2  # notch half-angle: notches take half the pitch
        for k in range(z):
            a = 2 * math.pi * k / z
            sk = Sketch(self.xy())
            sk.pencil.move_to(r_tip * math.cos(a), r_tip * math.sin(a))
            sk.pencil.line_to(r_mouth * math.cos(a - half), r_mouth * math.sin(a - half))
            sk.pencil.line_to(r_mouth * math.cos(a + half), r_mouth * math.sin(a + half))
            self.add_operation(Extrusion(sk.pencil.close(), start=-0.1, end=s + 0.1, cut=True))
        self.size, self.form, self.teeth = size, form, z
        self.inner_radius, self.outer_radius, self.thickness = ri, ro, s
        self.root_radius = r_tip
        add_axial_anchors(self, s)
        _washer_interfaces(self, size, s)
        self.paint(STEEL)
