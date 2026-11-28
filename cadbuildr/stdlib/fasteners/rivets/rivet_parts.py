"""Rivets: blind (pop) rivets and solid rivets, with the hole they need.

* :class:`BlindRivet` — open-end blind rivet with break-pull mandrel and
  protruding (dome) head: ISO 15977 (AlA body / St mandrel) or ISO 15983
  (A2 / A2).
* :class:`SolidRivet` — DIN 660 round head or DIN 661 countersunk head.

Built like the screws: the shank tip (blind side) at z=0, the under-head
face at z=``body_height`` (``head_seat``, -Z), the head above. Each rivet
carries ``ScrewHead(size=key, length)`` on ``head_seat``; :func:`rivet_hole`
drills the clearance hole the standard prescribes and binds the matching
``ScrewHole`` so ``assembly.connect`` seats the rivet. ``grip`` (the
material thickness) feeds ``__checks__``: it must lie in the rivet's grip
range.
"""

from __future__ import annotations

import math
from typing import Any, ClassVar, Literal

from cadbuildr.foundation import Hole, Part, make_anchor
from cadbuildr.foundation.checks import issue
from cadbuildr.foundation.interfaces import ScrewHead, ScrewHole, ScrewTip
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import ALUMINIUM, STAINLESS, STEEL, lathe_revolve, require_option, require_range
from cadbuildr.stdlib.standards.features import HoleFeature, _owner

__all__ = ["BlindRivet", "SolidRivet", "rivet_hole"]


def rivet_hole(face: Any, rivet: Any, depth: float) -> HoleFeature:
    """Drill ``rivet``'s hole (``rivet.drill_diameter``) ``depth`` deep at
    ``face`` and bind ``ScrewHole(size=rivet.size_key, depth)`` there."""
    owner = _owner(face)
    d = rivet.drill_diameter
    op = Hole(anchor=face, radius=d / 2.0, depth=float(depth))
    owner.add_operation(op)
    node = owner.add_interface(ScrewHole(size=rivet.size_key, depth=float(depth)), face)
    return HoleFeature(op, node, face, None, d)


def _anchors(part, length: float, size_key: str) -> None:
    part.add_anchor(make_anchor("head_seat", (0.0, 0.0, length), z_down=True))
    part.add_anchor(make_anchor("tip", (0.0, 0.0, 0.0), z_down=True))
    part.add_interface(ScrewHead(size=size_key, length=length), "head_seat")
    part.add_interface(ScrewTip(size=size_key), "tip")


def _dome(r_in: float, r_out: float, z0: float, k: float, n: int = 8):
    """(r, z) points of a dome head from the rim (r_out, z0) up to the axis
    at z0 + k: a spherical cap through the rim and the apex."""
    R = (r_out**2 + k**2) / (2 * k)  # cap sphere radius
    zc = z0 + k - R
    pts = []
    for i in range(n + 1):
        r = r_out * (1 - i / n)
        pts.append((max(r, r_in), zc + math.sqrt(max(R**2 - r**2, 0.0))))
    return pts


Series = Literal["ISO 15977", "ISO 15983"]


@part(
    category="Fasteners/Rivets",
    name="Blind Rivet",
    standard="ISO 15977 (AlA/St) · ISO 15983 (A2/A2)",
    description="Open-end blind (pop) rivet with dome head and break-pull mandrel, set from one side; drill size and grip range included.",
    configurations={
        "3.2 x 8 AlA/St": dict(diameter="3.2", length=8, series="ISO 15977"),
        "4 x 10 AlA/St": dict(diameter="4", length=10, series="ISO 15977"),
        "4.8 x 12 A2": dict(diameter="4.8", length=12, series="ISO 15983"),
    },
    catalog_id="iso15977-blind-rivet",
    example={"diameter": "4", "length": 10},
)
class BlindRivet(Part):
    """Open-end blind rivet, unset (as supplied).

    Body d, head dk (max) and k (max), mandrel dm (max) and mandrel
    protrusion p (min) from ISO 15977:2002 Table 1 (3.2: dk 6.7, k 1.3,
    dm 2.0, p 25; 4.0: 8.4 / 1.7 / 2.45 / 27; 4.8: 10.1 / 2.0 / 2.95 / 27;
    https://cdn.standards.iteh.ai/samples/29619/49f14fd35d504f5eb7f34d3fa5cff250/ISO-15977-2002.pdf).
    Hole: ISO 15977 Table 2 clearance hole (3.2: 3.3..3.4); the drill is
    its minimum. ISO 15983 (A2/A2) covers d 3..5 with the same head and
    hole sizes here.

    Estimated: grip range ``l - 2.0 d .. l - 1.2 d`` (ISO 15977 leaves grip
    ranges to the manufacturer; this is the usual catalogue rule); the
    mandrel head is a d x 0.8 dm cylinder under the sleeve; ISO 15983 head
    and mandrel sizes are taken equal to ISO 15977.
    """

    # d: (dk max, k max, dm max, p min, hole min)
    TABLE: ClassVar[dict[str, tuple[float, float, float, float, float]]] = {
        "3.2": (6.7, 1.3, 2.0, 25.0, 3.3),
        "4": (8.4, 1.7, 2.45, 27.0, 4.1),
        "4.8": (10.1, 2.0, 2.95, 27.0, 4.9),
    }
    SERIES: ClassVar[dict[str, tuple[str, str]]] = {
        "ISO 15977": ("almg3", "spring_steel"),
        "ISO 15983": ("stainless_304", "stainless_304"),
    }

    def __init__(
        self,
        diameter: OneOf[TABLE] = "4",
        length: Num(min=4, max=30, step=1) = 10,
        series: Series = "ISO 15977",
        grip: Num(min=0, max=25, step=0.5) = 0.0,
    ):
        """Args:
        diameter: nominal body diameter d (``TABLE`` key).
        length: body length l under the head.
        series: ``ISO 15977`` (aluminium body, steel mandrel) or ``ISO 15983`` (A2 / A2).
        grip: thickness of the joined sheets (0: not checked).
        """
        owner = "BlindRivet"
        dk, k, dm, p, hole = require_option(self.TABLE, str(diameter), what="diameter", owner=owner)
        body_mat, _mandrel = require_option(self.SERIES, series, what="series", owner=owner)
        d = float(diameter)
        L = require_range(length, lo=1.5 * d, hi=8 * d, what="length", owner=owner)
        r, rb = d / 2, dm / 2 + 0.05
        # Sleeve: hollow body with the dome head (bore for the mandrel).
        pts = [(rb, 0.0), (r, 0.0), (r, L)] + _dome(rb, dk / 2, L, k)
        lathe_revolve(self, pts)
        # Mandrel: stem through the sleeve plus head under its tail.
        hm = 0.8 * dm
        lathe_revolve(
            self,
            [(0.0, -hm), (0.95 * r, -hm), (0.95 * r, 0.0), (dm / 2, 0.0), (dm / 2, L + k + p), (0.0, L + k + p)],
        )
        self.nominal_diameter, self.length, self.series = d, L, series
        self.head_diameter, self.head_height, self.mandrel_diameter = dk, k, dm
        self.mandrel_protrusion, self.drill_diameter = p, hole
        self.grip, self.grip_range = float(grip), (round(L - 2.0 * d, 2), round(L - 1.2 * d, 2))
        self.body_height, self.size_key = L, f"rivet-{diameter}"
        _anchors(self, L, self.size_key)
        self.paint(ALUMINIUM if body_mat == "almg3" else STAINLESS)

    def __checks__(self):
        lo, hi = self.grip_range
        if self.grip and not lo <= self.grip <= hi:
            return [issue(
                "warning", "rivet.grip",
                f"{self.nominal_diameter:g} x {self.length:g} rivet grips {lo:g}..{hi:g} mm, "
                f"the joint is {self.grip:g} mm.",
                fix="pick a length about grip + 1.5 d",
            )]
        return []


Head = Literal["round", "countersunk"]


@part(
    category="Fasteners/Rivets",
    name="Solid Rivet",
    standard="DIN 660 (round head) · DIN 661 (countersunk)",
    description="Solid rivet with a round (snap) head or a 75° countersunk head; the closing head is formed from the protruding shank.",
    configurations={
        "4 x 12 round": dict(diameter="4", length=12, head="round"),
        "5 x 16 countersunk": dict(diameter="5", length=16, head="countersunk"),
    },
    catalog_id="din660-solid-rivet",
    example={"diameter": "4", "length": 12},
)
class SolidRivet(Part):
    """Solid rivet. Round head (DIN 660): head diameter dk and height k from
    DIN 660 (https://www.fasteners.eu/standards/DIN/660/; 4: dk 7, k 2.4),
    the head a spherical cap through dk and k. Countersunk (DIN 661): dk and
    k from DIN 661 (https://www.fasteners.eu/standards/DIN/661/; 4: dk 7,
    k 2); the cone (dk - d) / 2k = tan 37.5° makes the 75° head. ``length``
    is l under the head (DIN 660) or overall (DIN 661, flush). Hole: DIN 101
    fine series (``HOLE``: 4 -> 4.3). Grip: DIN 101 allows ``l - 1.6 d ..
    l - 1.3 d`` for a round closing head.

    Estimated: no under-head fillet; the grip rule above is the usual
    DIN 101 guidance for a snap closing head."""

    # d: (dk round, k round, dk csk, k csk, hole)
    TABLE: ClassVar[dict[str, tuple[float, float, float, float, float]]] = {
        "2": (3.5, 1.2, 3.5, 1.0, 2.2), "3": (5.2, 1.8, 5.2, 1.4, 3.2),
        "4": (7.0, 2.4, 7.0, 2.0, 4.3), "5": (8.8, 3.0, 8.8, 2.5, 5.3),
        "6": (10.5, 3.6, 10.5, 3.0, 6.4), "8": (14.0, 4.8, 14.0, 4.0, 8.4),
    }  # fmt: skip

    def __init__(
        self,
        diameter: OneOf[TABLE] = "4",
        length: Num(min=3, max=60, step=1) = 12,
        head: Head = "round",
        grip: Num(min=0, max=50, step=0.5) = 0.0,
    ):
        """Args:
        diameter: nominal shank diameter d (``TABLE`` key).
        length: l (under the head for round, overall for countersunk).
        head: ``round`` (DIN 660) or ``countersunk`` (DIN 661).
        grip: thickness of the joined parts (0: not checked).
        """
        owner = "SolidRivet"
        dkr, kr, dkc, kc, hole = require_option(self.TABLE, str(diameter), what="diameter", owner=owner)
        if head not in ("round", "countersunk"):
            raise ValueError(f"{owner}: unknown head {head!r} (choose from round, countersunk).")
        d = float(diameter)
        L = require_range(length, lo=1.5 * d, hi=min(10 * d, 60.0), what="length", owner=owner)
        r = d / 2
        if head == "round":
            pts = [(0.0, 0.0), (r, 0.0), (r, L)] + _dome(0.0, dkr / 2, L, kr)
            dk, k, seat = dkr, kr, L
            self.grip_range = (round(L - 1.6 * d, 2), round(L - 1.3 * d, 2))
        else:
            pts = [(0.0, 0.0), (r, 0.0), (r, L - kc), (dkc / 2, L), (0.0, L)]
            dk, k, seat = dkc, kc, L
            self.grip_range = (round(L - 1.6 * d, 2), round(L - 1.3 * d, 2))
        lathe_revolve(self, pts)
        self.nominal_diameter, self.length, self.head = d, L, head
        self.head_diameter, self.head_height, self.drill_diameter = dk, k, hole
        self.grip, self.body_height, self.size_key = float(grip), seat, f"rivet-{diameter}"
        _anchors(self, seat, self.size_key)
        self.paint(STEEL)

    def __checks__(self):
        lo, hi = self.grip_range
        if self.grip and not lo <= self.grip <= hi:
            return [issue(
                "warning", "rivet.grip",
                f"rivet {self.nominal_diameter:g} x {self.length:g} suits a grip of {lo:g}..{hi:g} mm, "
                f"the joint is {self.grip:g} mm.",
                fix="choose l = grip + 1.3..1.6 d",
            )]
        return []
