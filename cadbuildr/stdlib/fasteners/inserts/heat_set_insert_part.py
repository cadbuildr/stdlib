"""Heat-set threaded inserts for 3D-printed parts (brass, knurled).

Melted into a printed pocket, an insert gives plastic a reusable metal
thread. Built along +Z from the bottom (z=0) to the top face (z=``length``),
which sits flush with the part face. Place it with
:func:`cadbuildr.stdlib.fasteners.connect_heat_set_insert` — it seats the
insert on a face anchor and cuts the pocket in one call.
"""

from __future__ import annotations

from typing import ClassVar

from cadbuildr.foundation import Part, make_anchor
from cadbuildr.foundation.interfaces import ScrewHole
from cadbuildr.foundation.library import OneOf, part
from cadbuildr.stdlib.common import (
    BRASS,
    ISO_COARSE_PITCH,
    add_axial_anchors,
    add_internal_thread,
    lathe_revolve,
    nominal_diameter,
    require_option,
)
from cadbuildr.stdlib.interfaces import InsertBody


@part(
    category="Fasteners/Threaded Inserts",
    name="Heat-Set Insert (brass)",
    standard="Ruthex RX-series style · M2 – M6",
    description="Knurled brass insert melted into a 3D-printed pocket to give plastic a metal thread; sits flush with the face.",
    inputs={"with_thread": {"label": "Modeled thread"}},
    catalog_id="heat-set-insert",
    featured=True,
    example={"size": "M3"},
)
class HeatSetInsert(Part):
    # od = outer (knurl) diameter, l = length, hole = recommended pocket
    # diameter in printed plastic (typical RX-series values).
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "M2": {"od": 3.6, "l": 3.0, "hole": 3.2},
        "M2.5": {"od": 4.0, "l": 4.0, "hole": 3.6},
        "M3": {"od": 4.6, "l": 5.7, "hole": 4.0},
        "M4": {"od": 6.3, "l": 8.1, "hole": 5.6},
        "M5": {"od": 7.1, "l": 9.5, "hole": 6.4},
        "M6": {"od": 8.7, "l": 12.7, "hole": 8.0},
    }

    def __init__(self, size: OneOf[TABLE] = "M3", with_thread: bool = False):
        """Args:
        size: thread of the insert (knurl diameter, length and pocket from ``TABLE``).
        with_thread: model the internal thread (off by default: tiny, slow).
        """
        d = require_option(self.TABLE, size, what="size", owner="HeatSetInsert")
        bore_r = nominal_diameter(size) / 2
        r_out, length = d["od"] / 2, d["l"]
        r_groove = r_out - 0.12 * d["od"]
        r_lead = d["hole"] / 2 - 0.05
        z = [length * f for f in (0.15, 0.4, 0.55, 0.85)]
        # Lead-in, two knurl bands separated by a groove, a top band.
        lathe_revolve(
            self,
            [
                (bore_r, 0.0),
                (r_lead, 0.0),
                (r_lead, z[0]),
                (r_out, z[0]),
                (r_out, z[1]),
                (r_groove, z[1]),
                (r_groove, z[2]),
                (r_out, z[2]),
                (r_out, z[3]),
                (r_groove, z[3]),
                (r_groove, length - 0.2),
                (r_out, length - 0.2),
                (r_out, length),
                (bore_r, length),
            ],
        )
        if with_thread:
            add_internal_thread(
                self, nominal_radius=bore_r, length=length, pitch=ISO_COARSE_PITCH[size]
            )
        self.size, self.length = size, length
        self.outer_radius = r_out
        self.pocket_diameter = d["hole"]
        self.pocket_depth = length + 0.5
        # Anchors: bottom / top (flush with the face) / axis.
        add_axial_anchors(self, length)
        # Interfaces (one per anchor): ``seat`` (same pose as ``top``) sits
        # flush in an InsertPocket; ``top`` is the tapped face a screw lands on.
        seat = self.add_anchor(make_anchor("seat", (0.0, 0.0, length)))
        self.add_interface(InsertBody(size=size), seat)
        self.add_interface(ScrewHole(size=size, depth=length, thread=True), "top")
        self.paint(BRASS)
