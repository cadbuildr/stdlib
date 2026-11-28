"""ISO / DIN hexagon nuts with the 30° bearing-face chamfer.

* :class:`ISO4032Nut` — regular hex nut, style 1 (ISO 4032:2012).
* :class:`ISO4035Nut` — thin (jam) hex nut (ISO 4035:2012).
* :class:`NylonInsertNut` — prevailing-torque nut with a non-metallic insert,
  regular (ISO 7040) or thin (ISO 10511).
* :class:`CapNut` — hexagon domed cap nut (DIN 1587), blind thread.
* :class:`FlangeNut` — hexagon nut with a conical flange (DIN 6923 / ISO 4161).

All are built along +Z from the bearing face (z=0, anchor ``bottom``) and
carry ``NutSeat`` on ``bottom`` like :class:`HexNut`. Thread pitch, minor
diameter and the ``size`` key come from :mod:`cadbuildr.stdlib.standards`
(ISO 261 / ISO 724).
"""

from __future__ import annotations

import math
from typing import ClassVar, Literal

from cadbuildr.foundation import (
    Circle,
    Extrusion,
    Part,
    Point,
    Sketch,
    Sphere,
)
from cadbuildr.foundation.interfaces import NutSeat
from cadbuildr.foundation.library import OneOf, part
from cadbuildr.stdlib.common import (
    STEEL,
    add_axial_anchors,
    add_internal_thread,
    hexagon_shape,
    lathe_revolve,
    require_option,
)
from cadbuildr.stdlib.fasteners.nuts.hex_din934_part import HexNut
from cadbuildr.stdlib.standards import thread

_THREAD_LABEL = {"with_thread": {"label": "Modeled thread"}}
#: Bearing-face chamfer angle of hex nuts (ISO 4032 Fig. 1: 15..30°; 30° used).
CHAMFER_DEG = 30.0


def chamfer_hex_face(part, s: float, z_face: float, *, up: bool) -> None:
    """Cut the conical corner chamfer of a hex face at ``z_face``: the cone
    starts on the across-flats circle (dw ~ s) and rises at 30° to the
    corners (``up``: the face looks down, the cone rises into +Z)."""
    e = s / math.sqrt(3.0)  # across-corners radius
    r0, r1 = s / 2.0, e + 0.5
    h = (r1 - r0) * math.tan(math.radians(CHAMFER_DEG))
    sign = 1.0 if up else -1.0
    _ring_cut(part, [(r0, z_face), (r1, z_face), (r1, z_face + sign * h)])


def _ring_cut(part, pts) -> None:
    """Revolve a closed (r, z) polygon away from the axis about Z, as a cut."""
    from cadbuildr.foundation import Axis, Lathe, Line

    s = Sketch(part.xz())
    s.pencil.move_to(*pts[0])
    for p in pts[1:]:
        s.pencil.line_to(*p)
    shape = s.pencil.close()
    axis = Axis(Line(s.origin, Point(s, 0.0, 1.0)))
    part.add_operation(Lathe(shape, axis, cut=True))


def _pitch(size: str) -> float:
    return thread(size).pitch


def _dims(table):
    """``HexNut.dimension_table`` rows from a (s, m) table; pitch from ISO 261."""
    return {
        size: {
            "width_across_flats": s,
            "thickness": m,
            "nominal_diameter": thread(size).major,
            "thread_pitch": thread(size).pitch,
        }
        for size, (s, m) in table.items()
    }


class _TableHexNut(HexNut):
    """A ``HexNut`` with its own (s, m) table (pitch from standards) and both
    faces chamfered."""

    OWNER: ClassVar[str] = "nut"

    def _init(self, size: str, with_thread: bool) -> None:
        s, m = require_option(self.TABLE, size, what="size", owner=self.OWNER)
        HexNut.__init__(self, size=size, with_thread=with_thread)
        chamfer_hex_face(self, s, 0.0, up=True)
        chamfer_hex_face(self, s, m, up=False)


@part(
    category="Fasteners/Nuts",
    name="Hex Nut ISO 4032",
    standard="ISO 4032 (style 1) · ISO 261 coarse",
    description="Regular hexagon nut, style 1, with both bearing faces chamfered at 30° and an optional modeled thread.",
    inputs=_THREAD_LABEL,
    configurations={"M5": dict(size="M5"), "M8": dict(size="M8"), "M12": dict(size="M12")},
    catalog_id="iso4032-hex-nut",
    example={"size": "M8"},
)
class ISO4032Nut(_TableHexNut):
    """ISO 4032 hexagon nut: s = width across flats, m = height (max) from
    ISO 4032:2012 Table 1 (M5 m 4.7, M8 m 6.8, M10 s 16). Pitch from
    ISO 261 (``standards.thread``).

    Estimated: the 30° chamfer starts on the across-flats circle (the
    standard allows dw min .. s); no thread countersink at the bore."""

    TABLE: ClassVar[dict[str, tuple[float, float]]] = {
        "M2": (4.0, 1.6), "M2.5": (5.0, 2.0), "M3": (5.5, 2.4), "M4": (7.0, 3.2),
        "M5": (8.0, 4.7), "M6": (10.0, 5.2), "M8": (13.0, 6.8), "M10": (16.0, 8.4),
        "M12": (18.0, 10.8), "M14": (21.0, 12.8), "M16": (24.0, 14.8),
        "M20": (30.0, 18.0), "M24": (36.0, 21.5),
    }  # fmt: skip
    dimension_table: ClassVar[dict[str, dict[str, float]]] = _dims(TABLE)
    OWNER: ClassVar[str] = "ISO4032Nut"

    def __init__(self, size: OneOf[TABLE] = "M6", with_thread: bool = True):
        """Args:
        size: metric thread size (s and m from ``TABLE``).
        with_thread: model the helical thread (slower to render).
        """
        self._init(size, with_thread)


@part(
    category="Fasteners/Nuts",
    name="Thin Hex Nut ISO 4035",
    standard="ISO 4035 · ISO 261 coarse",
    description="Thin (jam) hexagon nut, chamfered both sides, used as a lock nut or where height is short.",
    inputs=_THREAD_LABEL,
    configurations={"M6": dict(size="M6"), "M10": dict(size="M10")},
    catalog_id="iso4035-thin-nut",
    example={"size": "M8"},
)
class ISO4035Nut(_TableHexNut):
    """ISO 4035 thin hexagon nut: s and m (max) from ISO 4035:2012 Table 1
    (M8 m 4, M10 s 16 m 5). Estimated: chamfer as :class:`ISO4032Nut`."""

    TABLE: ClassVar[dict[str, tuple[float, float]]] = {
        "M3": (5.5, 1.8), "M4": (7.0, 2.2), "M5": (8.0, 2.7), "M6": (10.0, 3.2),
        "M8": (13.0, 4.0), "M10": (16.0, 5.0), "M12": (18.0, 6.0),
        "M16": (24.0, 8.0), "M20": (30.0, 10.0), "M24": (36.0, 12.0),
    }  # fmt: skip
    dimension_table: ClassVar[dict[str, dict[str, float]]] = _dims(TABLE)
    OWNER: ClassVar[str] = "ISO4035Nut"

    def __init__(self, size: OneOf[TABLE] = "M6", with_thread: bool = True):
        """Args:
        size: metric thread size (s and m from ``TABLE``).
        with_thread: model the helical thread (slower to render).
        """
        self._init(size, with_thread)


Series = Literal["ISO 7040", "ISO 10511"]


@part(
    category="Fasteners/Nuts",
    name="Nylon Insert Lock Nut (ISO)",
    standard="ISO 7040 (regular) · ISO 10511 (thin)",
    description="Prevailing-torque hex nut: a wrenching hex plus a crimped collar holding a nylon ring whose bore is the thread minor diameter.",
    inputs=_THREAD_LABEL,
    configurations={
        "M6 ISO 7040": dict(size="M6", series="ISO 7040"),
        "M8 ISO 10511": dict(size="M8", series="ISO 10511"),
    },
    catalog_id="iso7040-nylon-insert-nut",
    example={"size": "M8", "series": "ISO 7040"},
)
class NylonInsertNut(Part):
    """Nylon-insert lock nut.

    ISO 7040 (regular, style 1): s / h max from ISO 7040:2012 Table 1
    (M10 s 16, h 11.9 — e.g. https://eshop.wuerth.de, ISO 7040 product
    data). ISO 10511 (thin): s from ISO 4035, h max from ISO 10511:2012
    (= DIN 985 heights, https://www.fasteners.eu/standards/ISO/10511/), hex
    height m_w = DIN 985 m min. The insert bore is the internal minor
    diameter D1 (ISO 724), so a bolt cuts its own thread in it.

    Estimated: ISO 7040 hex height = ISO 4032 m (the standard only gives a
    minimum wrenching height); collar diameter 0.9 s (about dw min); the
    collar top is chamfered 45° over half the collar height.
    """

    TABLE: ClassVar[dict[str, dict[str, tuple[float, float, float]]]] = {
        # size: (s, h max, hex height)
        "ISO 7040": {
            "M3": (5.5, 4.5, 2.4), "M4": (7.0, 6.0, 3.2), "M5": (8.0, 6.8, 4.7),
            "M6": (10.0, 8.0, 5.2), "M8": (13.0, 9.5, 6.8), "M10": (16.0, 11.9, 8.4),
            "M12": (18.0, 14.9, 10.8),
        },
        "ISO 10511": {
            "M3": (5.5, 3.9, 2.4), "M4": (7.0, 5.0, 2.9), "M5": (8.0, 5.0, 3.2),
            "M6": (10.0, 6.0, 4.0), "M8": (13.0, 8.0, 5.5), "M10": (16.0, 10.0, 6.5),
            "M12": (18.0, 12.0, 8.0),
        },
    }  # fmt: skip
    SIZES: ClassVar[list[str]] = ["M3", "M4", "M5", "M6", "M8", "M10", "M12"]

    def __init__(
        self,
        size: OneOf[SIZES] = "M6",
        series: Series = "ISO 7040",
        with_thread: bool = True,
    ):
        """Args:
        size: metric thread size.
        series: ``ISO 7040`` (regular height) or ``ISO 10511`` (thin).
        with_thread: model the thread in the steel hex (slower to render).
        """
        owner = "NylonInsertNut"
        table = require_option(self.TABLE, series, what="series", owner=owner)
        s, h, m = require_option(table, size, what="size", owner=owner)
        th = thread(size)
        d, D1 = th.major, th.minor_internal
        sk = Sketch(self.xy())
        self.add_operation(Extrusion(hexagon_shape(sk, s), end=m))
        rc = 0.45 * s
        top_ch = 0.5 * (h - m)
        # Collar (steel, crimped over the insert) with a chamfered top.
        lathe_revolve(
            self,
            [(0.0, m), (rc, m), (rc, h - top_ch), (rc - top_ch, h), (0.0, h)],
        )
        # Bores: thread major through the hex, insert minor through the collar.
        self.add_operation(Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), d / 2), end=m, cut=True))
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), D1 / 2), start=m, end=h, cut=True)
        )
        if with_thread:
            add_internal_thread(self, nominal_radius=d / 2, length=m, pitch=th.pitch)
        chamfer_hex_face(self, s, 0.0, up=True)
        self.size, self.series, self.with_thread = size, series, with_thread
        self.width_across_flats, self.thickness, self.hex_height = s, h, m
        self.insert_bore, self.nominal_diameter, self.thread_pitch = D1, d, th.pitch
        add_axial_anchors(self, h)
        self.add_interface(NutSeat(size=size), "bottom")
        self.paint(STEEL)


@part(
    category="Fasteners/Nuts",
    name="Domed Cap Nut",
    standard="DIN 1587",
    description="Hexagon domed cap (acorn) nut: a hex, a collar and a hemispherical dome over a blind thread.",
    inputs=_THREAD_LABEL,
    configurations={"M5": dict(size="M5"), "M8": dict(size="M8")},
    catalog_id="din1587-cap-nut",
    example={"size": "M6"},
)
class CapNut(Part):
    """DIN 1587 domed cap nut: s, h (total height), m (hex height), t
    (thread depth, mean of min / max), dk (dome diameter) from DIN 1587
    (https://www.fasteners.eu/standards/DIN/1587/; M6: s 10, h 12, m 5,
    t 7.71..8.29, dk 9.5).

    Estimated: the dome is a hemisphere of dk on a cylinder of dk; the
    blind bore is cut to t with a flat floor (no drill point)."""

    # size: (s, h, m, t, dk)
    TABLE: ClassVar[dict[str, tuple[float, float, float, float, float]]] = {
        "M4": (7.0, 8.0, 3.2, 5.5, 6.5), "M5": (8.0, 10.0, 4.0, 7.5, 7.5),
        "M6": (10.0, 12.0, 5.0, 8.0, 9.5), "M8": (13.0, 15.0, 6.5, 11.0, 12.5),
        "M10": (16.0, 18.0, 8.8, 13.0, 15.0), "M12": (18.0, 22.0, 10.0, 16.0, 17.0),
    }  # fmt: skip

    def __init__(self, size: OneOf[TABLE] = "M6", with_thread: bool = True):
        """Args:
        size: metric thread size (dimensions from ``TABLE``).
        with_thread: model the blind internal thread (slower to render).
        """
        s, h, m, t, dk = require_option(self.TABLE, size, what="size", owner="CapNut")
        th = thread(size)
        rk = dk / 2
        zc = h - rk  # dome centre
        self.add_operation(Extrusion(hexagon_shape(Sketch(self.xy()), s), end=m))
        self.add_operation(Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), rk), start=m, end=zc))
        self.add_operation(Sphere(Point(Sketch(self.xz()), 0.0, zc), rk))
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), th.major / 2), end=t, cut=True)
        )
        if with_thread:
            add_internal_thread(self, nominal_radius=th.major / 2, length=t, pitch=th.pitch)
        chamfer_hex_face(self, s, 0.0, up=True)
        self.size, self.with_thread = size, with_thread
        self.width_across_flats, self.thickness, self.hex_height = s, h, m
        self.thread_depth, self.dome_diameter = t, dk
        self.nominal_diameter, self.thread_pitch = th.major, th.pitch
        add_axial_anchors(self, h)
        self.add_interface(NutSeat(size=size), "bottom")
        self.paint(STEEL)


@part(
    category="Fasteners/Nuts",
    name="Hex Flange Nut",
    standard="DIN 6923 (ISO 4161)",
    description="Hexagon nut with an integral conical flange that spreads the load like a captive washer.",
    inputs=_THREAD_LABEL,
    configurations={"M6": dict(size="M6"), "M8": dict(size="M8")},
    catalog_id="din6923-flange-nut",
    example={"size": "M8"},
)
class FlangeNut(Part):
    """DIN 6923 hexagon flange nut: s, m (height, max), dc (flange diameter,
    max), c (flange thickness at the rim, min) from DIN 6923
    (https://www.fasteners.eu/standards/DIN/6923/; M8: s 13, m 8, dc 17.9,
    c 1.2).

    Estimated: the flange top rises as a 25° cone from the rim to the hex;
    the bearing face is plain (the serrated option of DIN 6923 is not
    modeled)."""

    # size: (s, m, dc, c)
    TABLE: ClassVar[dict[str, tuple[float, float, float, float]]] = {
        "M5": (8.0, 5.0, 11.8, 1.0), "M6": (10.0, 6.0, 14.2, 1.1),
        "M8": (13.0, 8.0, 17.9, 1.2), "M10": (15.0, 10.0, 21.8, 1.5),
        "M12": (18.0, 12.0, 26.0, 1.8),
    }  # fmt: skip
    FLANGE_CONE_DEG: ClassVar[float] = 25.0

    def __init__(self, size: OneOf[TABLE] = "M8", with_thread: bool = True):
        """Args:
        size: metric thread size (dimensions from ``TABLE``).
        with_thread: model the helical thread (slower to render).
        """
        s, m, dc, c = require_option(self.TABLE, size, what="size", owner="FlangeNut")
        th = thread(size)
        rf, rh = dc / 2, s / 2
        zf = c + (rf - rh) * math.tan(math.radians(self.FLANGE_CONE_DEG))
        lathe_revolve(self, [(0.0, 0.0), (rf, 0.0), (rf, c), (rh, zf), (0.0, zf)])
        self.add_operation(Extrusion(hexagon_shape(Sketch(self.xy()), s), start=zf, end=m))
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), th.major / 2), end=m, cut=True)
        )
        if with_thread:
            add_internal_thread(self, nominal_radius=th.major / 2, length=m, pitch=th.pitch)
        chamfer_hex_face(self, s, m, up=False)
        self.size, self.with_thread = size, with_thread
        self.width_across_flats, self.thickness = s, m
        self.flange_diameter, self.flange_thickness, self.flange_top = dc, c, zf
        self.nominal_diameter, self.thread_pitch = th.major, th.pitch
        add_axial_anchors(self, m)
        self.add_interface(NutSeat(size=size), "bottom")
        self.paint(STEEL)
