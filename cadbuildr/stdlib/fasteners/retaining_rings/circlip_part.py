"""Retaining rings (circlips): DIN 471 external (shaft) and DIN 472
internal (bore).

Flat ring in the XY plane from z=0 to the thickness ``s``, gap and lug
holes on +X. Modelled at its fitted (in-groove) size: an external ring's
bore is the groove diameter ``d2`` of a shaft ``d1``; an internal ring's
outside is the groove diameter in a bore ``d1``. Groove depth / width
tables for machining the grooves belong to ``cadbuildr.stdlib.standards``.
"""

from __future__ import annotations

import math

from cadbuildr.foundation import Circle, Extrusion, Part, Point, Sketch
from cadbuildr.foundation.interfaces import Bore, PlaneFace, Shaft
from cadbuildr.foundation.library import OneOf, part
from cadbuildr.stdlib.common import BLACK_OXIDE, add_axial_anchors, require_option

# d1 (shaft / bore) -> s thickness, d2 groove diameter, b radial section,
# lug hole diameter. Nominal DIN 471 / DIN 472 values.
DIN471: dict[str, dict[str, float]] = {
    "4": {"s": 0.4, "d2": 3.8, "b": 0.9, "hole": 1.0},
    "5": {"s": 0.6, "d2": 4.8, "b": 1.1, "hole": 1.0},
    "6": {"s": 0.7, "d2": 5.7, "b": 1.3, "hole": 1.2},
    "8": {"s": 0.8, "d2": 7.6, "b": 1.5, "hole": 1.2},
    "10": {"s": 1.0, "d2": 9.6, "b": 1.8, "hole": 1.5},
    "12": {"s": 1.0, "d2": 11.5, "b": 1.8, "hole": 1.7},
    "15": {"s": 1.0, "d2": 14.3, "b": 2.2, "hole": 1.7},
    "20": {"s": 1.2, "d2": 19.0, "b": 2.6, "hole": 2.0},
    "25": {"s": 1.2, "d2": 23.9, "b": 3.0, "hole": 2.0},
}
DIN472: dict[str, dict[str, float]] = {
    "10": {"s": 1.0, "d2": 10.4, "b": 1.4, "hole": 1.2},
    "12": {"s": 1.0, "d2": 12.5, "b": 1.7, "hole": 1.5},
    "16": {"s": 1.0, "d2": 16.8, "b": 2.0, "hole": 1.7},
    "19": {"s": 1.0, "d2": 20.0, "b": 2.2, "hole": 2.0},
    "22": {"s": 1.0, "d2": 23.0, "b": 2.5, "hole": 2.0},
    "26": {"s": 1.2, "d2": 27.2, "b": 2.8, "hole": 2.0},
    "32": {"s": 1.2, "d2": 33.7, "b": 3.2, "hole": 2.5},
}


class _Circlip(Part):
    """Shared geometry; ``kind`` is ``external`` or ``internal``.

    Sources: DIN 471 / DIN 472 (s, d2). Estimated: the radial section ``b``
    is constant (the real ring tapers from the lugs to the back) and the lugs
    are discs."""

    def _build(self, size: str, kind: str, table: dict) -> None:
        owner = type(self).__name__
        t = require_option(table, str(size), what="size", owner=owner)
        d1, s, b = float(size), t["s"], t["b"]
        if kind == "external":
            r_in, r_out = t["d2"] / 2, t["d2"] / 2 + b
        else:
            r_in, r_out = t["d2"] / 2 - b, t["d2"] / 2
        o = lambda: Point(Sketch(self.xy()), 0.0, 0.0)  # noqa: E731
        self.add_operation(Extrusion(Circle(o(), r_out), 0.0, s))
        self.add_operation(Extrusion(Circle(o(), r_in), 0.0, s, cut=True))
        # Opening on +X (about 30 degrees), two lugs with holes either side.
        gap = math.radians(15)
        cut = Sketch(self.xy())
        far = r_out + 1.0
        cut.pencil.move_to(0.0, 0.0)
        cut.pencil.line_to(far * math.cos(gap), -far * math.sin(gap))
        cut.pencil.line_to(far * math.cos(gap), far * math.sin(gap))
        self.add_operation(Extrusion(cut.pencil.close(), 0.0, s, cut=True))
        lug_r = 0.9 * t["hole"] + 0.4
        r_lug = r_out + lug_r * 0.6 if kind == "external" else r_in - lug_r * 0.6
        for sy in (-1, 1):
            a = sy * (gap + math.radians(14))
            c = (r_lug * math.cos(a), r_lug * math.sin(a))
            self.add_operation(
                Extrusion(Circle(Point(Sketch(self.xy()), *c), lug_r), 0.0, s)
            )
            hole = Circle(Point(Sketch(self.xy()), *c), t["hole"] / 2)
            self.add_operation(Extrusion(hole, 0.0, s, cut=True))

        self.size, self.kind, self.thickness = str(size), kind, s
        self.groove_diameter = t["d2"]
        add_axial_anchors(self, s)
        # Interfaces: an external ring rides its shaft (Bore d1), an internal
        # ring sits in its bore (Shaft d1); both faces are axial stops.
        spec = Bore(d=d1) if kind == "external" else Shaft(d=d1)
        self.add_interface(spec, "axis")
        self.add_interface(PlaneFace(), "bottom")
        self.add_interface(PlaneFace(), "top")
        self.paint(BLACK_OXIDE)


@part(
    category="Fasteners/Retaining Rings",
    name="External Circlip (shaft)",
    standard="DIN 471",
    description="Spring-steel retaining ring that snaps into a shaft groove to stop a bearing, gear or pulley sliding along the shaft.",
    catalog_id="din471-circlip",
    example={"size": "8"},
)
class ExternalCirclip(_Circlip):
    def __init__(self, size: OneOf[DIN471] = "8"):
        """Args:
        size: shaft diameter (thickness, groove and section from ``DIN471``).
        """
        self._build(size, "external", DIN471)


@part(
    category="Fasteners/Retaining Rings",
    name="Internal Circlip (bore)",
    standard="DIN 472",
    description="Spring-steel retaining ring that snaps into a bore groove to hold a bearing in its housing.",
    catalog_id="din472-circlip",
    example={"size": "22"},
)
class InternalCirclip(_Circlip):
    def __init__(self, size: OneOf[DIN472] = "22"):
        """Args:
        size: bore diameter (thickness, groove and section from ``DIN472``).
        """
        self._build(size, "internal", DIN472)
