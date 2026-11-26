"""Aluminium T-slot extrusion profiles (2020 / 2040), 6 mm slot series."""

from typing import ClassVar

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion, make_anchor
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import (
    ALUMINIUM,
    add_axial_anchors,
    oriented_rectangle_shape,
    rectangle_shape,
)

_SLOT = 6.0  # slot opening width
_DEPTH = 6.0  # how far the slot channel reaches in
_BORE_R = 2.55  # central bore radius (~M5 tap / 5 mm)


@part(
    category="Profiles/Extrusions",
    name="Aluminium Extrusion (T-slot)",
    standard="2020 / 2040 · 6 mm slot",
    description="Open-builds style aluminium T-slot extrusion with face slots and centre bore(s). Pick the series and cut length.",
    catalog_id="alu-extrusion-tslot",
    featured=True,
    example={"series": "2020", "length": 120},
)
class AluExtrusion(Part):
    # series -> (width, height, cell centres on Y)
    GEOMETRY: ClassVar[dict[str, dict]] = {
        "2020": {"w": 20.0, "h": 20.0, "cells": [0.0]},
        "2040": {"w": 20.0, "h": 40.0, "cells": [-10.0, 10.0]},
    }

    def __init__(
        self,
        series: OneOf[GEOMETRY] = "2020",
        length: Num(min=20, max=1000, step=10) = 100,
    ):
        """Args:
        series: profile series (``2020`` or ``2040``, 6 mm slot).
        length: cut length along the profile (+Z).
        """
        if series not in self.GEOMETRY:
            raise ValueError(f"Unknown series '{series}'.")
        g = self.GEOMETRY[series]
        w, h, cells = g["w"], g["h"], g["cells"]

        # Solid bar.
        bar = rectangle_shape(Sketch(self.xy()), w, h)
        self.add_operation(Extrusion(bar, length))

        # Centre bore per 20 mm cell.
        for cy in cells:
            self.add_operation(
                Extrusion(
                    Circle(Point(Sketch(self.xy()), 0, cy), _BORE_R), length, cut=True
                )
            )

        # Left / right face slots, one per cell.
        for cy in cells:
            self._x_slot(+w / 2, cy, length)
            self._x_slot(-w / 2, cy, length)
        # Top / bottom face slots, centred on X.
        self._y_slot(0.0, +h / 2, length)
        self._y_slot(0.0, -h / 2, length)
        # Anchors: end_a / end_b on the cut ends, ``axis`` along the profile,
        # and one anchor per T-slot at its opening on the outer face, z=0:
        # +Z = outward face normal, +X = along the extrusion. A TSlotNut's
        # ``top`` mated there sits in the slot; slide it with slot_anchor().
        self.width, self.height, self.length = w, h, length
        add_axial_anchors(self, length, ends=("end_a", "end_b"))
        self.slot_names = []
        for i, cy in enumerate(cells):
            self._slot_anchor(f"slot_px_{i}", (w / 2, cy, 0.0), (1.0, 0.0, 0.0))
            self._slot_anchor(f"slot_nx_{i}", (-w / 2, cy, 0.0), (-1.0, 0.0, 0.0))
        self._slot_anchor("slot_py", (0.0, h / 2, 0.0), (0.0, 1.0, 0.0))
        self._slot_anchor("slot_ny", (0.0, -h / 2, 0.0), (0.0, -1.0, 0.0))
        self.paint(ALUMINIUM)
        self.series = series

    def _slot_anchor(self, name, position, normal):
        self.add_anchor(
            make_anchor(name, position, z_axis=normal, x_axis=(0.0, 0.0, 1.0))
        )
        self.slot_names.append(name)

    def slot_anchor(self, slot: str, at: float, name: str | None = None):
        """Anchor on T-slot ``slot`` (e.g. ``"slot_py"``) ``at`` mm along the
        extrusion from ``end_a``; same orientation as the slot anchor."""
        if slot not in self.slot_names:
            raise ValueError(f"Unknown slot '{slot}' (choose from {self.slot_names}).")
        return self.anchor(slot).offset(
            [float(at), 0.0, 0.0], name=name or f"at_{at:g}"
        )

    def _x_slot(self, face_x, cy, length):
        sign = 1 if face_x > 0 else -1
        cx = face_x - sign * (_DEPTH / 2 - 1)
        shape = oriented_rectangle_shape(
            Sketch(self.xy()), cx, cy, _DEPTH + 2, _SLOT, 0.0
        )
        self.add_operation(Extrusion(shape, length, cut=True))

    def _y_slot(self, cx, face_y, length):
        sign = 1 if face_y > 0 else -1
        cy = face_y - sign * (_DEPTH / 2 - 1)
        shape = oriented_rectangle_shape(
            Sketch(self.xy()), cx, cy, _SLOT, _DEPTH + 2, 0.0
        )
        self.add_operation(Extrusion(shape, length, cut=True))
