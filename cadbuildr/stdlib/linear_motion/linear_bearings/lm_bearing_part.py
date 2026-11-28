"""LMxUU linear ball bearings (the cylindrical bushings that ride on smooth rod)."""

from typing import ClassVar

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion, make_anchor
from typing import Optional

from cadbuildr.foundation.interfaces import BearingFace
from cadbuildr.foundation.library import OneOf, part
from cadbuildr.stdlib.common import BLACK_OXIDE, add_axial_anchors


@part(
    category="Linear Motion/Linear Bearings",
    name="Linear Ball Bearing (LMxUU)",
    standard="LMxUU metric series",
    description="Closed-type linear ball bushing for round rod (LMxUU series sizing).",
    catalog_id="lm-uu-linear-bearing",
    featured=True,
    example={"model": "LM8UU"},
)
class LinearBearing(Part):
    # bore (d), outer diameter (D), length (L)
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "LM6UU": {"d": 6.0, "D": 12.0, "L": 19.0},
        "LM8UU": {"d": 8.0, "D": 15.0, "L": 24.0},
        "LM10UU": {"d": 10.0, "D": 19.0, "L": 29.0},
        "LM12UU": {"d": 12.0, "D": 21.0, "L": 30.0},
        "LM16UU": {"d": 16.0, "D": 28.0, "L": 37.0},
    }

    # rod diameter -> the bearing riding it
    BY_ROD: ClassVar[dict[str, str]] = {
        "6": "LM6UU",
        "8": "LM8UU",
        "10": "LM10UU",
        "12": "LM12UU",
        "16": "LM16UU",
    }

    def __init__(
        self, model: OneOf[TABLE] = "LM8UU", rod: Optional[OneOf[BY_ROD]] = None
    ):
        """Args:
        model: bearing designation (bore, outer diameter, length from ``TABLE``).
        rod: rod diameter; when given it picks the model (``"8"`` -> LM8UU), so
            one ``rod`` input can drive rods, plates and their bearings.
        """
        if rod is not None:
            key = f"{float(rod):g}" if not isinstance(rod, str) else rod
            if key not in self.BY_ROD:
                raise ValueError(f"No LMxUU bearing for a {rod} mm rod.")
            model = self.BY_ROD[key]
        if model not in self.TABLE:
            raise ValueError(f"Unknown linear bearing '{model}'.")
        b = self.TABLE[model]
        outer_r, bore_r, length = b["D"] / 2, b["d"] / 2, b["L"]

        body = Circle(Point(Sketch(self.xy()), 0, 0), outer_r)
        self.add_operation(Extrusion(body, length))
        bore = Circle(Point(Sketch(self.xy()), 0, 0), bore_r)
        self.add_operation(Extrusion(bore, length, cut=True))
        # Anchors: end faces, axis, and ``center`` (mid-length on the axis) —
        # the frame a SliderJoint against a rod's ``axis`` slides.
        self.bore_radius, self.outer_radius, self.length = bore_r, outer_r, length
        add_axial_anchors(self, length, ends=("end_a", "end_b"))
        self.add_anchor(make_anchor("center", (0.0, 0.0, length / 2)))
        # Interfaces: an end face in a carriage BearingPocket, or sliding on a
        # rod's RodAxis.
        for end in ("end_a", "end_b"):
            self.add_interface(BearingFace(model=model, d=b["d"]), end)
        self.paint(BLACK_OXIDE)
        self.model = model
