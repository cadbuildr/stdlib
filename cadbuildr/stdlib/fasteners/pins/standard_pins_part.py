"""Standard pins and clips, each with the hole it goes in.

* :class:`ParallelPin` — ISO 2338 parallel pin, m6 or h8, chamfered ends.
* :class:`SpringPin` — ISO 8752 slotted spring pin, heavy duty (a split tube).
* :class:`CoiledPin` — ISO 8750 coiled spring pin, standard duty (a 2¼-turn
  spiral strip).
* :class:`CotterPin` — ISO 1234 split pin (two half-round legs and an eye).
* :class:`ClevisPin` — ISO 2341 clevis pin with head, form A (plain) or B
  (with a split-pin hole).
* :class:`RClip` — DIN 11024 spring cotter (R-clip / hitch pin clip).

Straight pins run along +Z from z=0 and carry ``Shaft`` / ``ShaftEnd`` of
their *nominal* diameter (= the hole diameter). :func:`pin_hole` drills the
matching hole — nominal diameter, the fit the standard prescribes
(``HOLE_FIT``) — and binds ``Bore(d, fit)`` so ``assembly.connect`` seats
the pin. ``ClevisPin`` form B exposes the split-pin hole as a ``Bore`` that
a :class:`CotterPin` or :class:`RClip` (``Shaft``) connects to.
"""

from __future__ import annotations

import math
from typing import Any, ClassVar, Literal

from cadbuildr.foundation import (
    Axis,
    Circle,
    Extrusion,
    Lathe,
    Line,
    Part,
    Point,
    Point3D,
    Sketch,
    Spline3D,
    Sweep,
    make_anchor,
)
from cadbuildr.foundation.interfaces import Bore, PivotPin, Shaft
from cadbuildr.foundation.interfaces.features import ShaftFeature
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import (
    STAINLESS,
    STEEL,
    add_axial_anchors,
    lathe_revolve,
    require_option,
    require_range,
)
from cadbuildr.stdlib.standards import fitted_bore, tolerance

__all__ = [
    "ClevisPin",
    "CoiledPin",
    "CotterPin",
    "ParallelPin",
    "RClip",
    "SpringPin",
    "pin_hole",
]


def pin_hole(face: Any, pin: Any, depth: float, *, fit: str | None = None):
    """Drill the hole ``pin`` goes in at ``face`` (an anchor, +Z out of the
    face): the pin's nominal diameter, toleranced ``fit`` (default: the fit
    the pin's standard prescribes, ``pin.hole_fit``), and ``Bore(d, fit)``
    bound on ``face``. Returns the :class:`~cadbuildr.stdlib.standards.HoleFeature`."""
    return fitted_bore(face, pin.nominal_diameter, fit or pin.hole_fit, depth)


def _chamfered_rod(r: float, length: float, c: float) -> list[tuple[float, float]]:
    return [(0.0, 0.0), (r - c, 0.0), (r, c), (r, length - c), (r - c, length), (0.0, length)]


# --------------------------------------------------------------------------- #
# ISO 2338 parallel pin
# --------------------------------------------------------------------------- #

Tol = Literal["m6", "h8"]


@part(
    category="Fasteners/Pins",
    name="Parallel Pin",
    standard="ISO 2338 (unhardened, m6 / h8)",
    description="Unhardened parallel pin with chamfered ends, ground to m6 (press fit in an H7 hole) or h8 (slide fit).",
    configurations={
        "4 m6 x 16": dict(diameter="4", length=16, tolerance="m6"),
        "6 m6 x 24": dict(diameter="6", length=24, tolerance="m6"),
        "8 h8 x 30": dict(diameter="8", length=30, tolerance="h8"),
    },
    catalog_id="iso2338-parallel-pin",
    example={"diameter": "6", "length": 24},
)
class ParallelPin(Part):
    """ISO 2338 parallel pin. End chamfer ``c`` from ISO 2338:1997 Table 1
    (d 2: 0.35 .. d 12: 2.5); the diameter is modeled at the middle of its
    ISO 286 zone (``standards.tolerance``: 6 m6 = 6.008). Hole: H7 for m6
    (``HOLE_FIT``), H8 for h8. Length range per ISO 2338 (2 d .. 20 d,
    capped at 100)."""

    TABLE: ClassVar[dict[str, float]] = {
        "2": 0.35, "3": 0.5, "4": 0.63, "5": 0.8, "6": 1.2, "8": 1.6, "10": 2.0, "12": 2.5,
    }  # fmt: skip
    HOLE_FIT: ClassVar[str] = "H7"

    def __init__(
        self,
        diameter: OneOf[TABLE] = "6",
        length: Num(min=4, max=100, step=1) = 24,
        tolerance: Tol = "m6",
    ):
        """Args:
        diameter: nominal diameter d (``TABLE`` key).
        length: overall length l.
        tolerance: ``m6`` (press fit) or ``h8``.
        """
        owner = "ParallelPin"
        c = require_option(self.TABLE, str(diameter), what="diameter", owner=owner)
        if tolerance not in ("m6", "h8"):
            raise ValueError(f"{owner}: unknown tolerance {tolerance!r} (choose from m6, h8).")
        d = float(diameter)
        L = require_range(length, lo=2 * d, hi=min(20 * d, 100.0), what="length", owner=owner)
        size = _zone(tolerance, d)
        lathe_revolve(self, _chamfered_rod(size / 2, L, c))
        self.nominal_diameter, self.diameter, self.length = d, size, L
        self.tolerance, self.chamfer = tolerance, c
        self.hole_fit = "H7" if tolerance == "m6" else "H8"
        add_axial_anchors(self, L, ends=("end_a", "end_b"))
        ShaftFeature(self, d=d, length=L)
        self.paint(STEEL)


def _zone(designation: str, d: float) -> float:
    return tolerance(designation, d).mean


# --------------------------------------------------------------------------- #
# ISO 8752 slotted spring pin
# --------------------------------------------------------------------------- #


@part(
    category="Fasteners/Pins",
    name="Slotted Spring Pin",
    standard="ISO 8752 (heavy duty)",
    description="Heavy-duty slotted spring pin: a split spring-steel tube, oversize before fitting, that grips its H12 hole.",
    configurations={
        "3 x 16": dict(diameter="3", length=16),
        "5 x 24": dict(diameter="5", length=24),
        "8 x 40": dict(diameter="8", length=40),
    },
    catalog_id="iso8752-spring-pin",
    example={"diameter": "5", "length": 24},
)
class SpringPin(Part):
    """ISO 8752 heavy-duty slotted spring pin, modeled in the free state:
    outside diameter d1 (mean of min / max), wall s and end taper length a
    from ISO 8752 (https://www.fasteners.eu/standards/ISO/8752/; 5: d1 5.4
    .. 5.6, s 1.0, a 0.9). Hole: nominal d, H12 (ISO 8752 §5).

    Estimated: the slot is as wide as the free-state oversize closes,
    pi (d1 - d) + 0.1 s; the ends taper over a to 0.9 d1."""

    # nominal: (d1 min, d1 max, s, a)
    TABLE: ClassVar[dict[str, tuple[float, float, float, float]]] = {
        "2": (2.3, 2.4, 0.4, 0.35), "3": (3.3, 3.5, 0.6, 0.5), "4": (4.4, 4.6, 0.8, 0.65),
        "5": (5.4, 5.6, 1.0, 0.9), "6": (6.4, 6.7, 1.25, 1.2), "8": (8.5, 8.8, 1.5, 2.0),
        "10": (10.5, 10.8, 2.0, 2.0),
    }  # fmt: skip
    HOLE_FIT: ClassVar[str] = "H12"

    def __init__(
        self,
        diameter: OneOf[TABLE] = "5",
        length: Num(min=4, max=120, step=1) = 24,
    ):
        """Args:
        diameter: nominal (hole) diameter d.
        length: pin length l.
        """
        owner = "SpringPin"
        lo, hi, s, a = require_option(self.TABLE, str(diameter), what="diameter", owner=owner)
        d = float(diameter)
        L = require_range(length, lo=max(4.0, d), hi=min(20 * d, 120.0), what="length", owner=owner)
        d1 = (lo + hi) / 2
        ro, ri = d1 / 2, d1 / 2 - s
        rt = 0.9 * ro
        lathe_revolve(
            self,
            [(ri, 0.0), (rt, 0.0), (ro, a), (ro, L - a), (rt, L), (ri, L)],
        )
        gap = math.pi * (d1 - d) + 0.1 * s
        sk = Sketch(self.xy())
        sk.pencil.move_to(ri - 0.2, -gap / 2)
        sk.pencil.line_to(ro + 0.2, -gap / 2)
        sk.pencil.line_to(ro + 0.2, gap / 2)
        sk.pencil.line_to(ri - 0.2, gap / 2)
        self.add_operation(Extrusion(sk.pencil.close(), start=-0.1, end=L + 0.1, cut=True))
        self.nominal_diameter, self.diameter, self.wall, self.length = d, d1, s, L
        self.slot_width, self.hole_fit = gap, self.HOLE_FIT
        add_axial_anchors(self, L, ends=("end_a", "end_b"))
        ShaftFeature(self, d=d, length=L)
        self.paint(STEEL)


# --------------------------------------------------------------------------- #
# ISO 8750 coiled spring pin
# --------------------------------------------------------------------------- #


@part(
    category="Fasteners/Pins",
    name="Coiled Spring Pin",
    standard="ISO 8750 (standard duty)",
    description="Coiled spring pin: a spring-steel strip rolled 2¼ turns into a spiral that keeps flexing evenly in its H10 hole.",
    configurations={
        "3 x 16": dict(diameter="3", length=16),
        "5 x 24": dict(diameter="5", length=24),
    },
    catalog_id="iso8750-coiled-pin",
    example={"diameter": "5", "length": 24},
)
class CoiledPin(Part):
    """ISO 8750 standard-duty coiled pin in the free state: outside diameter
    d1 (mean of min / max) and strip thickness s from ISO 8750
    (https://www.fasteners.eu/standards/ISO/8750/; 5: d1 5.25 .. 5.5, s
    0.42). Hole: nominal d, H10 (ISO 8750 §5).

    Estimated: 2¼ coils (typical for standard duty); the spiral layers keep
    a 5 % gap so the profile stays a simple polygon; square-cut ends (the
    standard's end chamfer is not modeled)."""

    TABLE: ClassVar[dict[str, tuple[float, float, float]]] = {
        "2": (2.13, 2.25, 0.17), "3": (3.15, 3.3, 0.25), "4": (4.2, 4.4, 0.33),
        "5": (5.25, 5.5, 0.42), "6": (6.25, 6.5, 0.5), "8": (8.3, 8.63, 0.67),
        "10": (10.35, 10.8, 0.84),
    }  # fmt: skip
    HOLE_FIT: ClassVar[str] = "H10"
    COILS: ClassVar[float] = 2.25

    def __init__(
        self,
        diameter: OneOf[TABLE] = "5",
        length: Num(min=4, max=120, step=1) = 24,
    ):
        """Args:
        diameter: nominal (hole) diameter d.
        length: pin length l.
        """
        owner = "CoiledPin"
        lo, hi, s = require_option(self.TABLE, str(diameter), what="diameter", owner=owner)
        d = float(diameter)
        L = require_range(length, lo=max(4.0, d), hi=min(20 * d, 120.0), what="length", owner=owner)
        d1 = (lo + hi) / 2
        outer, inner = self.spiral(d1 / 2, s, self.COILS)
        sk = Sketch(self.xy())
        sk.pencil.move_to(*outer[0])
        for p in outer[1:] + inner[::-1]:
            sk.pencil.line_to(*p)
        self.add_operation(Extrusion(sk.pencil.close(), end=L))
        self.nominal_diameter, self.diameter, self.strip, self.length = d, d1, s, L
        self.section_area = _polygon_area(outer + inner[::-1])
        self.hole_fit = self.HOLE_FIT
        add_axial_anchors(self, L, ends=("end_a", "end_b"))
        ShaftFeature(self, d=d, length=L)
        self.paint(STEEL)

    @staticmethod
    def spiral(r_out: float, s: float, coils: float, per_turn: int = 24):
        """Outer and inner edges of an Archimedean strip of thickness ``s``
        wound ``coils`` turns inward from ``r_out`` (layer pitch 1.05 s)."""
        n = int(round(coils * per_turn))
        outer, inner = [], []
        for i in range(n + 1):
            t = 2 * math.pi * coils * i / n
            r = r_out - 1.05 * s * t / (2 * math.pi)
            outer.append((r * math.cos(t), r * math.sin(t)))
            inner.append(((r - s) * math.cos(t), (r - s) * math.sin(t)))
        return outer, inner


def _polygon_area(pts) -> float:
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2


# --------------------------------------------------------------------------- #
# ISO 1234 split (cotter) pin
# --------------------------------------------------------------------------- #


def _half_disc(sketch, r: float, *, side: float, cx: float = 0.0, cy: float = 0.0, n: int = 12):
    """Closed half-disc of radius ``r`` (flat on x = cx, bulging to ``side``)."""
    pts = [
        (cx + side * r * math.sin(math.pi * k / n), cy - r * math.cos(math.pi * k / n))
        for k in range(n + 1)
    ]
    sketch.pencil.move_to(*pts[0])
    for p in pts[1:]:
        sketch.pencil.line_to(*p)
    return sketch.pencil.close()


@part(
    category="Fasteners/Pins",
    name="Split Pin",
    standard="ISO 1234",
    description="Split (cotter) pin: a half-round wire doubled into two legs and an eye; push it through a cross hole and bend the legs apart.",
    configurations={
        "2 x 16": dict(size="2", length=16),
        "3.2 x 25": dict(size="3.2", length=25),
        "4 x 32": dict(size="4", length=32),
    },
    catalog_id="iso1234-split-pin",
    example={"size": "3.2", "length": 25},
)
class CotterPin(Part):
    """ISO 1234 split pin. Nominal size = hole diameter; wire d (max), leg
    offset a (max), long-leg overhang b and eye width c (max) from ISO 1234
    (https://www.fasteners.eu/standards/ISO/1234/; 3.2: d 2.9, a 3.2, b 6.4,
    c 5.8). Length l is from under the eye to the short leg's end; the
    ``eye`` anchor (z=0, -Z) bears on the shaft, the legs run along +Z.
    ``SHAFT_RANGE``: bolt / clevis diameters the size suits (ISO 1234 Table
    1, "over .. up to").

    Estimated: the eye is a revolved half-round ring of outer width c; the
    legs are straight (no bend) and the long leg's end is square."""

    # nominal: (d, a, b, c)
    TABLE: ClassVar[dict[str, tuple[float, float, float, float]]] = {
        "1": (0.9, 1.6, 3.0, 1.8), "1.6": (1.4, 2.5, 3.2, 2.8), "2": (1.8, 2.5, 4.0, 3.6),
        "2.5": (2.3, 2.5, 5.0, 4.6), "3.2": (2.9, 3.2, 6.4, 5.8), "4": (3.7, 4.0, 8.0, 7.4),
        "5": (4.6, 4.0, 10.0, 9.2), "6.3": (5.9, 4.0, 12.6, 11.8), "8": (7.5, 4.0, 16.0, 15.0),
    }  # fmt: skip
    SHAFT_RANGE: ClassVar[dict[str, tuple[float, float]]] = {
        "1": (3.5, 4.5), "1.6": (5.5, 7.0), "2": (7.0, 9.0), "2.5": (9.0, 11.0),
        "3.2": (11.0, 14.0), "4": (14.0, 20.0), "5": (20.0, 27.0), "6.3": (27.0, 39.0),
        "8": (39.0, 56.0),
    }  # fmt: skip
    HOLE_FIT: ClassVar[str] = "H13"

    def __init__(
        self,
        size: OneOf[TABLE] = "3.2",
        length: Num(min=4, max=160, step=1) = 25,
    ):
        """Args:
        size: nominal size = hole diameter (``TABLE`` key).
        length: length l under the eye to the short leg's end.
        """
        owner = "CotterPin"
        d, a, b, c = require_option(self.TABLE, str(size), what="size", owner=owner)
        L = require_range(length, lo=c, hi=40 * d, what="length", owner=owner)
        r = d / 2
        # Legs: half-discs side by side, flats touching on x = 0.
        self.add_operation(Extrusion(_half_disc(Sketch(self.xy()), r, side=1.0), end=L + b))
        self.add_operation(Extrusion(_half_disc(Sketch(self.xy()), r, side=-1.0), end=L))
        # Eye: half-round ring in the XZ plane, outer width c, flats inward.
        rho = c / 2 - r / 2  # ring centre-line radius (radial thickness r)
        zc = -math.sqrt(max(rho**2 - (r / 2) ** 2, 1e-6))
        s = Sketch(self.xy().get_parallel_plane(zc))
        ring = _half_disc(s, r, side=-1.0, cx=-(rho - r / 2))
        self.add_operation(Lathe(ring, Axis(Line(s.origin, Point(s, 0.0, 1.0)))))
        self.nominal_diameter = float(size)
        self.wire_diameter, self.length, self.long_leg = d, L, L + b
        self.eye_width, self.eye_bottom = c, zc - rho - r / 2
        self.hole_fit = self.HOLE_FIT
        self.add_anchor(make_anchor("eye", (0.0, 0.0, 0.0), z_down=True))
        self.add_anchor(make_anchor("axis", (0.0, 0.0, 0.0)))
        self.add_anchor(make_anchor("tip", (0.0, 0.0, L)))
        self.add_interface(Shaft(d=self.nominal_diameter), "axis")
        self.paint(STEEL)

    def suits(self, shaft_diameter: float) -> bool:
        """True when ISO 1234 pairs this size with a ``shaft_diameter`` bolt."""
        lo, hi = self.SHAFT_RANGE[_key(self.nominal_diameter)]
        return lo < float(shaft_diameter) <= hi


def _key(x: float) -> str:
    return f"{x:g}"


# --------------------------------------------------------------------------- #
# ISO 2341 clevis pin
# --------------------------------------------------------------------------- #

ClevisForm = Literal["A", "B"]


@part(
    category="Fasteners/Pins",
    name="Clevis Pin",
    standard="ISO 2341 (form A / B)",
    description="Headed clevis pin; form B has a cross hole for a split pin or R-clip that keeps it in the clevis.",
    configurations={
        "6 x 20 B": dict(diameter="6", length=20, form="B"),
        "8 x 30 B": dict(diameter="8", length=30, form="B"),
        "10 x 40 A": dict(diameter="10", length=40, form="A"),
    },
    catalog_id="iso2341-clevis-pin",
    example={"diameter": "8", "length": 30, "form": "B"},
)
class ClevisPin(Part):
    """ISO 2341 clevis pin with head: dk (h14), k (js14), split-pin hole d1
    (H13), le (min, hole centre to the pin end) and end chamfer c (max) from
    ISO 2341 (https://www.fasteners.eu/standards/ISO/2341/; 8: dk 14, k 3,
    d1 2, le 3.5). Built like a screw: the shank from the tip (z=0) to the
    under-head face at z=l (``head_seat``, -Z), head above. ``split_pin``
    (form B) is the cross hole's axis (+Z along part +Y) with ``Bore(d1)``.
    ``SPLIT_PIN`` gives the matching ISO 1234 size (= d1).

    Estimated: tip chamfer c / 2 at 45°, head edge chamfer 0.1 k."""

    # d: (dk, k, d1, le, c)
    TABLE: ClassVar[dict[str, tuple[float, float, float, float, float]]] = {
        "4": (6.0, 1.0, 1.0, 2.2, 1.0), "5": (8.0, 1.6, 1.2, 2.9, 2.0),
        "6": (10.0, 2.0, 1.6, 3.2, 2.0), "8": (14.0, 3.0, 2.0, 3.5, 2.0),
        "10": (18.0, 4.0, 3.2, 4.5, 2.0), "12": (20.0, 4.0, 3.2, 5.5, 3.0),
    }  # fmt: skip
    HOLE_FIT: ClassVar[str] = "H11"

    def __init__(
        self,
        diameter: OneOf[TABLE] = "8",
        length: Num(min=6, max=120, step=1) = 30,
        form: ClevisForm = "B",
    ):
        """Args:
        diameter: pin diameter d (``TABLE`` key).
        length: length l under the head.
        form: ``A`` plain or ``B`` with a split-pin hole.
        """
        owner = "ClevisPin"
        dk, k, d1, le, c = require_option(self.TABLE, str(diameter), what="diameter", owner=owner)
        if form not in ("A", "B"):
            raise ValueError(f"{owner}: unknown form {form!r} (choose from A, B).")
        d = float(diameter)
        L = require_range(length, lo=max(2 * d, 2 * le + d1), hi=min(12 * d, 120.0), what="length", owner=owner)
        r, ch, hc = d / 2, c / 2, 0.1 * k
        lathe_revolve(
            self,
            [(0.0, 0.0), (r - ch, 0.0), (r, ch), (r, L), (dk / 2, L), (dk / 2, L + k - hc),
             (dk / 2 - hc, L + k), (0.0, L + k)],
        )  # fmt: skip
        self.nominal_diameter, self.length, self.head_height, self.form = d, L, k, form
        self.head_diameter, self.split_pin_hole = dk, d1 if form == "B" else None
        self.body_height, self.hole_fit = L, self.HOLE_FIT
        self.add_anchor(make_anchor("head_seat", (0.0, 0.0, L), z_down=True))
        self.add_anchor(make_anchor("tip", (0.0, 0.0, 0.0), z_down=True))
        self.add_anchor(make_anchor("axis", (0.0, 0.0, 0.0)))
        self.add_interface(Shaft(d=d), "axis")
        self.add_interface(PivotPin(d=d), "head_seat")
        if form == "B":
            hole = Circle(Point(Sketch(self.xz()), 0.0, le), d1 / 2)
            self.add_operation(Extrusion(hole, start=-d, end=d, cut=True))
            self.add_anchor(make_anchor("split_pin", (0.0, 0.0, le), z_axis=(0.0, 1.0, 0.0)))
            self.add_interface(Bore(d=float(_split_pin_size(d1)), fit=self.HOLE_FIT), "split_pin")
            self.split_pin_z = le
        self.paint(STEEL)

    @property
    def SPLIT_PIN(self) -> str | None:  # noqa: N802 - mirrors the table naming
        return _key(_split_pin_size(self.split_pin_hole)) if self.split_pin_hole else None


def _split_pin_size(d1: float) -> float:
    """ISO 1234 nominal size for a cross hole of ``d1`` (the sizes are the holes)."""
    return float(d1)


# --------------------------------------------------------------------------- #
# DIN 11024 R-clip
# --------------------------------------------------------------------------- #


@part(
    category="Fasteners/Pins",
    name="R-Clip (spring cotter)",
    standard="DIN 11024",
    description="R-clip / hitch pin clip: a straight spring-wire leg through the cross hole and a curved leg that snaps over the pin.",
    configurations={"2.5": dict(size="2.5"), "4": dict(size="4"), "6.3": dict(size="6.3")},
    catalog_id="din11024-r-clip",
    example={"size": "4"},
)
class RClip(Part):
    """DIN 11024 spring cotter (simple coil). Per nominal size (= cross-hole
    diameter d1): pin diameter range d2, wire d3 and overall length l from
    DIN 11024 (https://www.aspenfasteners.com/v/vspfiles/files/docs/Metric_DIN_11024_spec.pdf;
    4: d2 14..20, d3 3.6, l 64). Built in the XZ plane: the straight leg
    along +X from the loop (``leg`` anchor at the origin, +Z along part +X)
    through the hole; the curved leg above it bulges over a pin of up to
    d2 max.

    Estimated: loop inner diameter 2.5 d3; straight leg 0.85 l; the curved
    leg is a spline through five points (bulge at mid-length, d2 max / 2 +
    d3 above the straight leg)."""

    # nominal d1: (d2 min, d2 max, d3, l)
    TABLE: ClassVar[dict[str, tuple[float, float, float, float]]] = {
        "2.5": (9.0, 11.2, 2.25, 42.0), "3.2": (11.2, 14.0, 2.8, 48.0),
        "4": (14.0, 20.0, 3.6, 64.0), "5": (20.0, 26.0, 4.5, 80.0),
        "6.3": (26.0, 34.0, 5.6, 97.0), "7": (34.0, 45.0, 6.3, 125.0),
        "8": (45.0, 56.0, 7.0, 150.0),
    }  # fmt: skip

    def __init__(self, size: OneOf[TABLE] = "4"):
        """Args:
        size: nominal size = cross-hole diameter d1 (``TABLE`` key).
        """
        lo, hi, w, L = require_option(self.TABLE, str(size), what="size", owner="RClip")
        r = w / 2
        loop_r = 1.25 * w + r  # loop centre-line radius (inner diameter 2.5 w)
        zt = 2 * loop_r  # height of the curved leg's start above the straight leg
        leg = 0.85 * L
        # Straight leg along +X with a 30° pointed lead-in.
        yz = Sketch(self.yz())
        self.add_operation(Extrusion(Circle(Point(yz, 0.0, 0.0), r), end=leg))
        # Loop: two quarter turns about part Y through the loop centre, from
        # its leftmost point down to the straight leg and up to the curved one.
        s = Sketch(self.xy().get_parallel_plane(zt / 2))
        profile = lambda: Circle(Point(s, -loop_r, 0.0), r)  # noqa: E731
        for sign in (1.0, -1.0):
            axis = Axis(Line(s.origin, Point(s, 0.0, sign)))
            self.add_operation(Lathe(profile(), axis, angle=90.0))
        # Curved leg: spline from the loop top over the pin and back down.
        bulge = hi / 2 + w
        pts = [(0.0, zt), (0.3 * L, zt), (0.5 * L, zt + bulge - zt / 2), (0.72 * L, zt), (0.9 * L, zt - 0.3 * zt)]
        path = Spline3D(
            points=[Point3D(x, 0.0, z) for x, z in pts],
            start_tangent=Point3D(1.0, 0.0, 0.0),
        )
        start = Sketch(self.yz())
        self.add_operation(Sweep(Circle(Point(start, 0.0, zt), r), path))
        self.nominal_diameter, self.wire_diameter, self.length = float(size), w, L
        self.pin_range = (lo, hi)
        self.add_anchor(make_anchor("leg", (0.0, 0.0, 0.0), z_axis=(1.0, 0.0, 0.0)))
        self.add_interface(Shaft(d=self.nominal_diameter), "leg")
        self.paint(STAINLESS)

    def suits(self, pin_diameter: float) -> bool:
        lo, hi = self.pin_range
        return lo <= float(pin_diameter) <= hi
