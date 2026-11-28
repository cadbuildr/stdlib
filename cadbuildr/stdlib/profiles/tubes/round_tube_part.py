"""Round steel tube with mating anchors for tube joinery."""

from __future__ import annotations

import math

from cadbuildr.foundation import Circle, Extrusion, Part, Sketch, make_anchor
from cadbuildr.foundation.interfaces.features import ShaftFeature
from cadbuildr.foundation.library import Num, part


@part(
    category="Profiles/Tubes",
    name="Round Tube",
    standard="EN 10255 / handrail sizes",
    description="Round hollow tube (handrail / structural). Ends carry mating anchors; use tube_tee to cope-join tubes at right angles.",
    configurations={
        "Handrail 26.9 x 2.3": dict(outer_diameter=26.9, wall=2.3),
        "Handrail 33.7 x 2.6": dict(outer_diameter=33.7, wall=2.6),
        "Balustrade 42.4 x 2.6": dict(outer_diameter=42.4, wall=2.6),
    },
    catalog_id="round-steel-tube",
    example={"outer_diameter": 26.9, "wall": 2.3, "length": 500},
)
class RoundTube(Part):
    """A tube extruded along +Z from 0 to ``length``.

    Anchors: ``end_a`` / ``end_b`` on the end faces and ``axis`` at the origin
    (+Z along the tube), the base for :meth:`radial_anchor`.
    """

    def __init__(
        self,
        outer_diameter: Num(min=10, max=80, step=0.1) = 26.9,
        wall: Num(min=1, max=6, step=0.1) = 2.3,
        length: Num(min=50, max=3000, step=10) = 1000.0,
        color: str | None = "#2e8b6e",
    ):
        """Args:
        outer_diameter: tube outside diameter.
        wall: wall thickness.
        length: tube length (along +Z from z=0).
        color: paint colour (``None`` leaves the part unpainted).
        """
        if wall * 2.0 >= outer_diameter:
            raise ValueError(
                f"RoundTube: wall {wall:g} mm leaves no bore in a "
                f"{outer_diameter:g} mm tube."
            )
        self.outer_diameter = float(outer_diameter)
        self.outer_radius = self.outer_diameter / 2.0
        self.wall = float(wall)
        self.length = float(length)

        sketch = Sketch(self.xy())
        self.add_operation(
            Extrusion(Circle(sketch.origin, self.outer_radius), self.length)
        )
        bore_sketch = Sketch(self.xy())
        self.add_operation(
            Extrusion(
                Circle(bore_sketch.origin, self.outer_radius - self.wall),
                self.length,
                cut=True,
            )
        )

        self.add_anchor(make_anchor("end_a", (0.0, 0.0, 0.0), z_down=True))
        self.add_anchor(make_anchor("end_b", (0.0, 0.0, self.length)))
        self.add_anchor(make_anchor("axis", (0.0, 0.0, 0.0)))
        # Interfaces: the outside is a Shaft (clamps / bores ride it), each
        # end a ShaftEnd (it stops in a socket Bore).
        ShaftFeature(self, d=self.outer_diameter, length=self.length)

        if color is not None:
            self.paint(color)

    def radial_anchor(self, at: float, angle: float = 0.0, name: str | None = None):
        """Anchor on the tube surface: +Z radially outward, at ``at`` mm along
        the tube, rotated ``angle`` around it. The anchor X axis runs along
        the tube (toward ``end_a``)."""
        label = name or f"radial_{at:g}_{angle:g}"
        return (
            self.anchor("axis")
            .rotated(angle, axis=[0.0, 0.0, 1.0], name=f"{label}_spin")
            .offset([self.outer_radius, 0.0, at], name=f"{label}_pt")
            .rotated(math.pi / 2.0, axis=[0.0, 1.0, 0.0], name=label)
        )
