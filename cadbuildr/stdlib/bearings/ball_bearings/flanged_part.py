"""Flanged deep-groove ball bearings (F6xx / F68x) — the flange locates the
bearing axially in a through-bored plate, no shoulder needed."""

from __future__ import annotations

from typing import ClassVar

from cadbuildr.foundation import Circle, Extrusion, Part, Point, Sketch, make_anchor
from cadbuildr.foundation.interfaces import BearingFace, Bore
from cadbuildr.foundation.library import OneOf, part
from cadbuildr.stdlib.common import STEEL, add_axial_anchors, require_option


def _disc(part_, radius, z0, z1, cut=False):
    part_.add_operation(
        Extrusion(Circle(Point(Sketch(part_.xy()), 0, 0), radius), z0, z1, cut=cut)
    )


@part(
    category="Bearings/Ball Bearings",
    name="Flanged Ball Bearing",
    standard="ISO 15 · F6xx / F68x flanged series",
    description="Shielded deep-groove ball bearing with an outer-ring flange: press it into a through bore and the flange sets its depth.",
    catalog_id="flanged-ball-bearing",
    example={"model": "F608"},
)
class FlangedBearing(Part):
    # d = bore, D = outer, B = width, Df = flange diameter, Bf = flange thickness
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "F623": {"d": 3.0, "D": 10.0, "B": 4.0, "Df": 11.5, "Bf": 1.0},
        "F624": {"d": 4.0, "D": 13.0, "B": 5.0, "Df": 15.0, "Bf": 1.0},
        "F625": {"d": 5.0, "D": 16.0, "B": 5.0, "Df": 18.0, "Bf": 1.0},
        "F695": {"d": 5.0, "D": 13.0, "B": 4.0, "Df": 15.0, "Bf": 1.0},
        "F688": {"d": 8.0, "D": 16.0, "B": 5.0, "Df": 18.0, "Bf": 1.1},
        "F608": {"d": 8.0, "D": 22.0, "B": 7.0, "Df": 25.0, "Bf": 1.5},
    }

    def __init__(self, model: OneOf[TABLE] = "F608"):
        """Args:
        model: bearing designation (bore, outer, width and flange from ``TABLE``).
        """
        b = require_option(self.TABLE, model, what="model", owner="FlangedBearing")
        bore_r, outer_r, width = b["d"] / 2, b["D"] / 2, b["B"]
        flange_r, flange_t = b["Df"] / 2, b["Bf"]
        race = outer_r - bore_r
        shield = min(0.5, width * 0.1)
        # Outer ring body, the flange at the top face, the bore.
        _disc(self, outer_r, 0.0, width)
        _disc(self, flange_r, width - flange_t, width)
        _disc(self, bore_r, 0.0, width, cut=True)
        # Recessed shield annulus on the bottom face (inner ring stays proud).
        _disc(self, outer_r - race * 0.28, 0.0, shield, cut=True)
        _disc(self, bore_r + race * 0.28, 0.0, shield)
        _disc(self, bore_r, 0.0, shield, cut=True)

        self.model = model
        self.bore_radius, self.outer_radius, self.width = bore_r, outer_r, width
        self.flange_radius, self.flange_thickness = flange_r, flange_t
        # Anchors: ring faces, axis, and the flange underside (+Z = -part Z,
        # the face that lands on the plate around the bore).
        add_axial_anchors(self, width)
        seat = self.add_anchor(
            make_anchor("flange_seat", (0.0, 0.0, width - flange_t), z_down=True)
        )
        # Interfaces: ring faces / flange on a BearingSeat, the bore on a Shaft.
        self.add_interface(BearingFace(model=model, d=b["d"]), "bottom")
        self.add_interface(BearingFace(model=model, d=b["d"]), "top")
        self.add_interface(BearingFace(model=model, d=b["d"]), seat)
        self.add_interface(Bore(d=b["d"]), "axis")
        self.paint(STEEL)


@part(
    category="Bearings/Thrust Bearings",
    name="Thrust Ball Bearing",
    standard="ISO 104 · 511xx single-direction",
    description="Single-direction thrust ball bearing: shaft washer, ball cage and housing washer, carrying axial load (turntables, lead-screw ends).",
    catalog_id="thrust-ball-bearing",
    example={"model": "51100"},
)
class ThrustBearing(Part):
    # d = bore, D = outer, T = height
    TABLE: ClassVar[dict[str, dict[str, float]]] = {
        "F8-16M": {"d": 8.0, "D": 16.0, "T": 5.0},
        "51100": {"d": 10.0, "D": 24.0, "T": 9.0},
        "51101": {"d": 12.0, "D": 26.0, "T": 9.0},
        "51102": {"d": 15.0, "D": 28.0, "T": 9.0},
        "51104": {"d": 20.0, "D": 35.0, "T": 10.0},
        "51105": {"d": 25.0, "D": 42.0, "T": 11.0},
    }

    def __init__(self, model: OneOf[TABLE] = "51100"):
        """Args:
        model: bearing designation (bore, outer diameter and height from ``TABLE``).
        """
        b = require_option(self.TABLE, model, what="model", owner="ThrustBearing")
        bore_r, outer_r, h = b["d"] / 2, b["D"] / 2, b["T"]
        washer = 0.3 * h
        # Housing washer (bottom) and shaft washer (top), with a recessed
        # cage band between them.
        mid_out = outer_r - 0.12 * (outer_r - bore_r)
        mid_in = bore_r + 0.12 * (outer_r - bore_r)
        _disc(self, outer_r, 0.0, washer)
        _disc(self, mid_out, washer, h - washer)
        _disc(self, outer_r, h - washer, h)
        _disc(self, bore_r, 0.0, h, cut=True)
        _disc(self, mid_in, washer, h - washer, cut=True)
        self.model = model
        self.bore_radius, self.outer_radius, self.height = bore_r, outer_r, h
        add_axial_anchors(self, h)
        # Interfaces: the housing washer on a BearingSeat, the shaft washer
        # under a shaft shoulder, the bore on a Shaft.
        self.add_interface(BearingFace(model=model, d=b["d"]), "bottom")
        self.add_interface(BearingFace(model=model, d=b["d"]), "top")
        self.add_interface(Bore(d=b["d"]), "axis")
        self.paint(STEEL)


__all__ = ["FlangedBearing", "ThrustBearing"]
