"""LMxUU linear ball bearings (the cylindrical bushings that ride on smooth rod)."""

from typing import ClassVar

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import BLACK_OXIDE


@catalog_part(
    id="lm-uu-linear-bearing",
    category="Linear Motion",
    subcategory="Linear Bearings",
    name="Linear Ball Bearing (LMxUU)",
    standard="LMxUU metric series",
    description="Closed-type linear ball bushing for round rod (LMxUU series sizing).",
    params=[
        ParamSpec.enum("model", choices=["LM6UU", "LM8UU", "LM10UU", "LM12UU", "LM16UU"], default="LM8UU"),
    ],
    featured=True,
    example_config={"model": "LM8UU"},
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

    def __init__(self, model="LM8UU"):
        if model not in self.TABLE:
            raise ValueError(f"Unknown linear bearing '{model}'.")
        b = self.TABLE[model]
        outer_r, bore_r, length = b["D"] / 2, b["d"] / 2, b["L"]

        body = Circle(Point(Sketch(self.xy()), 0, 0), outer_r)
        self.add_operation(Extrusion(body, length))
        bore = Circle(Point(Sketch(self.xy()), 0, 0), bore_r)
        self.add_operation(Extrusion(bore, length, cut=True))
        self.paint(BLACK_OXIDE)
        self.model = model
