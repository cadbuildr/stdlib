"""Standard cuts on shafts, hubs and printed parts: D-flats, keyways, circlip
grooves, O-ring grooves and captive-nut pockets.

Shaft / hub cuts work in the part's own frame on a body of revolution built
along +Z (the stdlib convention: ``Shaft``, ``FittedShaft``, bearings, hubs),
with ``z0`` the start of the cut along the axis::

    d_flat(shaft, d=5, z0=10, length=15)               # NEMA 17 D-cut (flat at 4.5)
    shaft_keyway(shaft, d=20, z0=5, length=28)         # DIN 6885 6 x 6, t1 = 3.5
    hub_keyway(hub, bore=20, z0=0, length=25)          # hub side, t2 = 2.8
    circlip_groove(shaft, d=8, z=30)                   # DIN 471 groove 7.6 x 0.9
    circlip_groove(housing, d=22, z=7, kind="bore")    # DIN 472 groove 23.0 x 1.1
    oring_groove(piston, bore=20, cs=1.78, z=10)       # piston gland + the AS568 ring
    captive_nut_pocket(face, "M3")                     # hex pocket + ScrewHole for HexNut

Every function returns the table row it used (``Key``, ``RetainingRing``,
``PistonGroove``, ``NutPocket``...) and raises ``StandardsError`` when the cut
does not fit the part (a groove deeper than the wall, a flat past the axis).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from cadbuildr.foundation import (
    Axis,
    Circle,
    Extrusion,
    Lathe,
    Line,
    Point,
    Rectangle,
    Sketch,
)
from cadbuildr.foundation.helpers import anchor_plane
from cadbuildr.foundation.interfaces import ScrewHole

from ._common import StandardsError, lookup, metric_diameter
from .seals import PistonGroove, piston_groove
from .shaft_features import Key, RetainingRing, circlip_bore, circlip_shaft, keyway
from .threads import thread

__all__ = [
    "D_FLATS",
    "HEX_NUTS",
    "NutPocket",
    "captive_nut_pocket",
    "circlip_groove",
    "d_flat",
    "d_flat_size",
    "hub_keyway",
    "oring_groove",
    "shaft_end_chamfer",
    "shaft_keyway",
]

# Motor-shaft D-cuts: shaft Ø -> flat-to-opposite-side dimension (mm).
# NEMA 17 / 14 (5 mm) and NEMA 23 (6.35 mm) stepper datasheets, 8 mm geared /
# pulley shafts; other diameters fall back to a 0.1 d deep set-screw flat.
D_FLATS: Dict[str, float] = {
    "3": 2.5,
    "4": 3.5,
    "5": 4.5,
    "6": 5.5,
    "6.35": 5.8,
    "8": 7.5,
    "10": 9.0,
}

# ISO 4032 hex nuts: size -> (width across flats s, height m), mm.
# fmt: off
HEX_NUTS: Dict[str, Tuple[float, float]] = {
    "M2": (4.0, 1.6), "M2.5": (5.0, 2.0), "M3": (5.5, 2.4), "M4": (7.0, 3.2),
    "M5": (8.0, 4.7), "M6": (10.0, 5.2), "M8": (13.0, 6.8), "M10": (16.0, 8.4),
    "M12": (18.0, 10.8),
}
# fmt: on


def _lathe_ring(
    part: Any, r_in: float, r_out: float, z0: float, z1: float, cut: bool
) -> Any:
    """Revolve the rectangle r_in..r_out x z0..z1 (part frame) about the part's Z axis."""
    if r_out <= r_in or z1 <= z0:
        raise StandardsError(f"empty ring r {r_in:g}..{r_out:g}, z {z0:g}..{z1:g}")
    s = Sketch(part.xz())
    s.pencil.move_to(r_in, z0)
    s.pencil.line_to(r_out, z0)
    s.pencil.line_to(r_out, z1)
    s.pencil.line_to(r_in, z1)
    shape = s.pencil.close()
    axis = Axis(Line(s.origin, Point(s, 0.0, 1.0)))
    op = Lathe(shape, axis, cut=cut)
    part.add_operation(op)
    return op


def _box_cut(
    part: Any, x0: float, x1: float, width: float, z0: float, z1: float
) -> Any:
    """Cut the box x0..x1, |y| <= width / 2, z0..z1 (part frame)."""
    sketch = Sketch(part.xy())
    center = Point(sketch, (x0 + x1) / 2.0, 0.0)
    shape = Rectangle.from_center_and_sides(center, x1 - x0, width)
    op = Extrusion(shape, start=float(z0), end=float(z1), cut=True)
    part.add_operation(op)
    return op


def _span(z0: float, length: float, what: str) -> Tuple[float, float]:
    if length <= 0:
        raise StandardsError(f"{what}: length must be > 0, got {length!r}")
    return float(z0), float(z0) + float(length)


def d_flat_size(d: float) -> float:
    """Flat-to-opposite-side dimension of a D-cut on a shaft of diameter ``d``."""
    key = f"{float(d):g}"
    return D_FLATS[key] if key in D_FLATS else round(0.9 * float(d), 3)


def d_flat(
    part: Any, d: float, z0: float, length: float, *, flat: Optional[float] = None
) -> float:
    """Cut a D-flat on the +X side of a shaft of diameter ``d`` from ``z0`` for
    ``length``. ``flat`` = flat-to-opposite-side (default :func:`d_flat_size`).
    Returns ``flat``."""
    flat = d_flat_size(d) if flat is None else float(flat)
    r = float(d) / 2.0
    if not 0 < flat < float(d) or flat <= r:
        raise StandardsError(f"d_flat: flat {flat:g} must be between d/2 and d ({d:g})")
    z_a, z_b = _span(z0, length, "d_flat")
    x0 = flat - r
    _box_cut(part, x0, r + 1.0, float(d) + 2.0, z_a, z_b)
    return flat


def shaft_keyway(part: Any, d: float, z0: float, length: float) -> Key:
    """DIN 6885-1 keyway for a form A (round-ended) key on the +X side of a
    shaft of diameter ``d``, from ``z0`` for ``length``: width b, floor at
    ``d - t1`` across the shaft, ends rounded with radius b / 2 as an end
    mill cuts them. ``length`` is the key length (:func:`key_length`)."""
    key = keyway(d)
    z_a, z_b = _span(z0, length, "shaft_keyway")
    if z_b - z_a < key.b:
        raise StandardsError(
            f"shaft_keyway: length {length:g} is shorter than the key width {key.b:g}"
        )
    r, half = float(d) / 2.0, key.b / 2.0
    floor = r - key.t1
    if z_b - z_a > key.b:
        _box_cut(part, floor, r + 1.0, key.b, z_a + half, z_b - half)
    for zc in (z_a + half, z_b - half):
        sketch = Sketch(part.yz())  # u = Y, v = Z, normal = +X
        part.add_operation(
            Extrusion(
                Circle(Point(sketch, 0.0, zc), half), start=floor, end=r + 1.0, cut=True
            )
        )
    return key


def hub_keyway(part: Any, bore: float, z0: float, length: float) -> Key:
    """DIN 6885-1 hub keyway (width b, depth t2 beyond the bore) on +X of a
    bore of diameter ``bore`` along the part's Z axis."""
    key = keyway(bore)
    z_a, z_b = _span(z0, length, "hub_keyway")
    r = float(bore) / 2.0
    _box_cut(part, r - 0.5, r + key.t2, key.b, z_a, z_b)
    return key


def shaft_end_chamfer(
    part: Any, d: float, z: float, size: float, end: str = "top"
) -> None:
    """45 degree chamfer of ``size`` on the shaft end at ``z`` (``end="top"``:
    the material is below z; ``"bottom"``: above)."""
    r, c = float(d) / 2.0, float(size)
    if not 0 < c < r:
        raise StandardsError(f"shaft_end_chamfer: size {size!r} must be in (0, d/2)")
    sgn = -1.0 if end == "top" else 1.0
    if end not in ("top", "bottom"):
        raise StandardsError(
            f"shaft_end_chamfer: end must be 'top' or 'bottom', got {end!r}"
        )
    s = Sketch(part.xz())
    pts = [(r - c, z), (r + 1.0, z), (r + 1.0, z + sgn * (c + 1.0))]
    s.pencil.move_to(*pts[0])
    for p in pts[1:]:
        s.pencil.line_to(*p)
    part.add_operation(
        Lathe(s.pencil.close(), Axis(Line(s.origin, Point(s, 0.0, 1.0))), cut=True)
    )


def circlip_groove(part: Any, d: float, z: float, kind: str = "shaft") -> RetainingRing:
    """DIN 471 (``kind="shaft"``, shaft diameter ``d``) or DIN 472 (``"bore"``,
    bore ``d``) retaining-ring groove, width m starting at ``z``."""
    if kind == "shaft":
        ring = circlip_shaft(d)
        _lathe_ring(
            part, ring.groove / 2.0, float(d) / 2.0 + 0.5, z, z + ring.width, cut=True
        )
    elif kind == "bore":
        ring = circlip_bore(d)
        _lathe_ring(
            part, float(d) / 2.0 - 0.5, ring.groove / 2.0, z, z + ring.width, cut=True
        )
    else:
        raise StandardsError(
            f"circlip_groove: kind must be 'shaft' or 'bore', got {kind!r}"
        )
    return ring


def oring_groove(
    part: Any, bore: float, cs: float, z: float, application: str = "static_radial"
) -> PistonGroove:
    """Piston (male) O-ring gland on a body of diameter ~``bore`` that slides
    in a bore of ``bore``: groove-bottom diameter and width from
    :func:`piston_groove`, starting at ``z``. Returns the groove + chosen AS568 ring."""
    g = piston_groove(bore, cs, application)
    _lathe_ring(
        part, g.groove_d / 2.0, float(bore) / 2.0 + 0.5, z, z + g.gland.width, cut=True
    )
    return g


@dataclass(frozen=True)
class NutPocket:
    """A hex pocket for a captive ISO 4032 nut (mm): ``across_flats`` and
    ``depth`` include the print / machining ``clearance``."""

    size: str
    across_flats: float
    depth: float
    hole: float
    interface: Any = None


def captive_nut_pocket(
    face: Any,
    size: str = "M3",
    *,
    depth: Optional[float] = None,
    clearance: float = 0.2,
    hole_depth: float = 0.0,
    group: Optional[str] = None,
    interface: bool = True,
) -> NutPocket:
    """Hex pocket for an ISO 4032 nut sunk into ``face`` (an anchor, +Z out of
    the face), flats along the anchor's X axis, plus an optional ISO 273
    clearance hole ``hole_depth`` deeper. Binds ``ScrewHole(size)`` on the
    pocket floor (anchor ``<face>_nut``) so a stdlib ``HexNut`` connects
    (NutSeat <-> ScrewHole). ``depth`` defaults to the nut height + clearance."""
    from .features import _owner

    d, _ = metric_diameter(size)
    key = f"M{d:g}"
    s, m = lookup(HEX_NUTS, key, "ISO 4032 nut size")
    af = s + 2.0 * float(clearance)
    depth = (m + float(clearance)) if depth is None else float(depth)
    if depth <= 0:
        raise StandardsError(f"captive_nut_pocket: depth must be > 0, got {depth!r}")
    owner = _owner(face)
    sketch = Sketch(anchor_plane(face))
    r = af / math.sqrt(3.0)
    for i in range(6):
        a = math.radians(60 * i)
        (sketch.pencil.move_to if i == 0 else sketch.pencil.line_to)(
            r * math.cos(a), r * math.sin(a)
        )
    owner.add_operation(
        Extrusion(sketch.pencil.close(), start=-depth, end=0.0, cut=True)
    )
    hole = thread(key).clearance("normal")
    if hole_depth > 0:
        s2 = Sketch(anchor_plane(face))
        owner.add_operation(
            Extrusion(
                Circle(Point(s2, 0.0, 0.0), hole / 2.0),
                -depth - float(hole_depth),
                -depth,
                cut=True,
            )
        )
    node = None
    if interface:
        floor = face.offset([0.0, 0.0, -depth], name="nut")
        node = owner.add_interface(ScrewHole(size=key, depth=depth), floor, group=group)
    return NutPocket(key, round(af, 3), round(depth, 3), hole, node)
