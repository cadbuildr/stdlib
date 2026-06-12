"""Aluminium T-slot extrusion profiles (2020 / 2040), 6 mm slot series."""

from typing import ClassVar

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import ALUMINIUM, oriented_rectangle_shape, rectangle_shape

_SLOT = 6.0       # slot opening width
_DEPTH = 6.0      # how far the slot channel reaches in
_BORE_R = 2.55    # central bore radius (~M5 tap / 5 mm)


@catalog_part(
    id="alu-extrusion-tslot",
    category="Profiles",
    subcategory="Extrusions",
    name="Aluminium Extrusion (T-slot)",
    standard="2020 / 2040 · 6 mm slot",
    description="Open-builds style aluminium T-slot extrusion with face slots and centre bore(s). Pick the series and cut length.",
    params=[
        ParamSpec.enum("series", choices=["2020", "2040"], default="2020"),
        ParamSpec.number("length", min=20, max=600, default=100, step=10),
    ],
    featured=True,
    example_config={"series": "2020", "length": 120},
)
class AluExtrusion(Part):
    # series -> (width, height, cell centres on Y)
    GEOMETRY: ClassVar[dict[str, dict]] = {
        "2020": {"w": 20.0, "h": 20.0, "cells": [0.0]},
        "2040": {"w": 20.0, "h": 40.0, "cells": [-10.0, 10.0]},
    }

    def __init__(self, series="2020", length=100):
        if series not in self.GEOMETRY:
            raise ValueError(f"Unknown series '{series}'.")
        g = self.GEOMETRY[series]
        w, h, cells = g["w"], g["h"], g["cells"]

        # Solid bar.
        bar = rectangle_shape(Sketch(self.xy()), w, h)
        self.add_operation(Extrusion(bar, length))

        # Centre bore per 20 mm cell.
        for cy in cells:
            self.add_operation(Extrusion(Circle(Point(Sketch(self.xy()), 0, cy), _BORE_R), length, cut=True))

        # Left / right face slots, one per cell.
        for cy in cells:
            self._x_slot(+w / 2, cy, length)
            self._x_slot(-w / 2, cy, length)
        # Top / bottom face slots, centred on X.
        self._y_slot(0.0, +h / 2, length)
        self._y_slot(0.0, -h / 2, length)
        self.paint(ALUMINIUM)
        self.series = series

    def _x_slot(self, face_x, cy, length):
        sign = 1 if face_x > 0 else -1
        cx = face_x - sign * (_DEPTH / 2 - 1)
        shape = oriented_rectangle_shape(Sketch(self.xy()), cx, cy, _DEPTH + 2, _SLOT, 0.0)
        self.add_operation(Extrusion(shape, length, cut=True))

    def _y_slot(self, cx, face_y, length):
        sign = 1 if face_y > 0 else -1
        cy = face_y - sign * (_DEPTH / 2 - 1)
        shape = oriented_rectangle_shape(Sketch(self.xy()), cx, cy, _SLOT, _DEPTH + 2, 0.0)
        self.add_operation(Extrusion(shape, length, cut=True))
