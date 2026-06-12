"""Deep-groove ball bearings (the 6xx / 68xx metric series)."""

from typing import ClassVar

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion
from cadbuildr.stdlib.catalog import catalog_part, ParamSpec
from cadbuildr.stdlib.common import STEEL, BLACK_OXIDE


@catalog_part(
    id="deep-groove-ball-bearing",
    category="Bearings",
    subcategory="Ball Bearings",
    name="Deep Groove Ball Bearing",
    standard="ISO 15 · 6xx / 68xx series",
    description="Shielded deep-groove ball bearing modeled as inner + outer races with a recessed shield face.",
    params=[
        ParamSpec.enum("model", choices=["623", "624", "625", "626", "688", "608", "6800", "6801"], default="608"),
    ],
    featured=True,
    example_config={"model": "608"},
)
class DeepGrooveBearing(Part):
    # bore (d), outer diameter (D), width (B)
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "623": {"d": 3.0, "D": 10.0, "B": 4.0},
        "624": {"d": 4.0, "D": 13.0, "B": 5.0},
        "625": {"d": 5.0, "D": 16.0, "B": 5.0},
        "626": {"d": 6.0, "D": 19.0, "B": 6.0},
        "688": {"d": 8.0, "D": 16.0, "B": 5.0},
        "608": {"d": 8.0, "D": 22.0, "B": 7.0},
        "6800": {"d": 10.0, "D": 19.0, "B": 5.0},
        "6801": {"d": 12.0, "D": 21.0, "B": 5.0},
    }

    def __init__(self, model="608"):
        if model not in self.TABLE:
            raise ValueError(f"Unknown bearing '{model}'.")
        b = self.TABLE[model]
        outer_r, bore_r, width = b["D"] / 2, b["d"] / 2, b["B"]
        # Race band geometry: rings occupy the outer/inner thirds, shield recessed between.
        race = (outer_r - bore_r)
        outer_race_r = outer_r - race * 0.28
        inner_race_r = bore_r + race * 0.28
        shield_recess = min(0.6, width * 0.12)

        # Solid ring body.
        self.add_operation(Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), outer_r), width))
        self.add_operation(Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), bore_r), width, cut=True))

        # Recess the shield band on both faces by cutting the mid annulus, then
        # refilling the inner core so the bore stays open.
        for z0, z1 in ((0, shield_recess), (width - shield_recess, width)):
            self.add_operation(
                Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), outer_race_r), z0, z1, cut=True)
            )
            self.add_operation(
                Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), inner_race_r), z0, z1)
            )
            self.add_operation(
                Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), bore_r), z0, z1, cut=True)
            )
        self.paint(STEEL)
        self.shield_color = BLACK_OXIDE
        self.model = model
