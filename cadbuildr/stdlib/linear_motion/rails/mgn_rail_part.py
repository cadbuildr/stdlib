"""Miniature profile linear guides: MGN rails and carriages (HIWIN-style).

Frame convention (shared by rail and carriage, the ``datum`` anchor): +Z
runs along the rail, +X points up out of the rail's mounting face, the
origin is on the rail's bottom centre line — at the rail start for a rail,
at the block centre for a carriage. A carriage on its rail therefore shares
the rail's frame, offset along +Z: a ``SliderJoint`` (``mount_carriage`` or
``assembly.connect(carriage, rail)``) whose ``offset`` is the carriage centre
position along the rail.
"""

from __future__ import annotations

from typing import Any, Literal

from cadbuildr.foundation import (
    BoolParameter,
    Circle,
    Extrusion,
    FloatParameter,
    Part,
    SliderJoint,
    Sketch,
    anchor_plane,
    make_anchor,
)
from cadbuildr.foundation.interfaces import PlaneFace, ScrewHole
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import BLACK_OXIDE, STEEL, require_option, require_range
from cadbuildr.stdlib.interfaces import RailBlock, RailTrack

# Series -> rail section, hole pattern and carriage block (nominal HIWIN MGN).
# Rail: W width, H height, P hole pitch, d through hole, D / h counterbore.
# Carriage: Wc width, Hc assembly height (rail bottom to block top), H1 gap
# under the block, Lc / Lh block length (C / H type), B / Cc / Ch hole
# spacings (across / along, C / H type), bolt = thread size.
MGN_SERIES: dict[str, dict[str, Any]] = {
    "MGN7": dict(W=7, H=4.8, P=15, d=2.4, D=4.2, h=2.3, bolt="M2", Wc=17, Hc=8,
                 H1=1.5, Lc=22.5, Lh=30.8, B=12, Cc=8, Ch=13),
    "MGN9": dict(W=9, H=6.5, P=20, d=3.5, D=6.0, h=3.5, bolt="M3", Wc=20, Hc=10,
                 H1=2.0, Lc=28.9, Lh=39.9, B=15, Cc=10, Ch=16),
    "MGN12": dict(W=12, H=8.0, P=25, d=3.5, D=6.0, h=4.5, bolt="M3", Wc=27, Hc=13,
                  H1=3.0, Lc=34.7, Lh=45.4, B=20, Cc=15, Ch=20),
    "MGN15": dict(W=15, H=10.0, P=40, d=3.5, D=6.0, h=5.3, bolt="M3", Wc=32, Hc=16,
                  H1=4.0, Lc=42.1, Lh=58.8, B=25, Cc=20, Ch=25),
    # HIWIN HG series (HGR rail, HGH..CA / HA block), nominal.
    "HGR15": dict(W=15, H=15.0, P=60, d=4.5, D=7.5, h=5.3, bolt="M4", Wc=34, Hc=28,
                  H1=4.3, Lc=61.4, Lh=61.4, B=26, Cc=26, Ch=26),
    "HGR20": dict(W=20, H=17.5, P=60, d=6.0, D=9.5, h=8.5, bolt="M5", Wc=44, Hc=30,
                  H1=4.6, Lc=77.5, Lh=92.2, B=32, Cc=36, Ch=50),
}  # fmt: skip
# Every profile-rail series (MGN miniature and HG); MGN_SERIES is the
# historical name of the same table.
RAIL_SERIES = MGN_SERIES

Block = Literal["C", "H"]

_UP = (1.0, 0.0, 0.0)  # part +X: out of the rail's top / the block's top
_ALONG = (0.0, 0.0, 1.0)


def _section(sketch: Sketch, pts):
    sketch.pencil.move_to(*pts[0])
    for p in pts[1:]:
        sketch.pencil.line_to(*p)
    return sketch.pencil.close()


def _drill(part_, anchor, radius, depth):
    """Cut a hole of ``radius`` from ``anchor`` ``depth`` against its +Z."""
    circle = Circle(Sketch(anchor_plane(anchor)).origin, radius)
    part_.add_operation(Extrusion(circle, 0.0, -depth, cut=True))


@part(
    category="Linear Motion/Profile Rails",
    name="Profile Linear Rail (MGN / HGR)",
    standard="MGN7 / 9 / 12 / 15 · HGR15 / 20 · HIWIN-compatible",
    description="Profile linear guide rail with counterbored mounting holes at the series pitch; an MGN carriage runs along it.",
    configurations={
        "MGN12 x 300": dict(series="MGN12", length=300),
        "MGN9 x 200": dict(series="MGN9", length=200),
        "MGN15 x 500": dict(series="MGN15", length=500),
        "HGR20 x 600": dict(series="HGR20", length=600),
    },
    catalog_id="mgn-linear-rail",
    featured=True,
    example={"series": "MGN12", "length": 300},
)
class LinearRail(Part):
    def __init__(
        self,
        series: OneOf[MGN_SERIES] = "MGN12",
        length: Num(min=50, max=1500, step=5) = 300,
    ):
        """Args:
        series: rail size (section and hole pattern from ``MGN_SERIES``).
        length: rail length; holes are centred with equal end distances.
        """
        s = require_option(MGN_SERIES, series, what="series", owner="LinearRail")
        length = require_range(
            length, lo=s["P"], hi=1500, what="length", owner="LinearRail"
        )
        W, H = float(s["W"]), float(s["H"])
        groove_d, groove_h = 0.12 * W, 0.22 * H
        # Section in the part XY plane (X up, Y across), extruded along +Z.
        x0, x1 = 0.55 * H - groove_h / 2, 0.55 * H + groove_h / 2
        y, g = W / 2, W / 2 - groove_d
        section = _section(
            Sketch(self.xy()),
            [(0, -y), (x0, -y), (x0, -g), (x1, -g), (x1, -y), (H, -y),
             (H, y), (x1, y), (x1, g), (x0, g), (x0, y), (0, y)],
        )  # fmt: skip
        self.add_operation(Extrusion(section, 0.0, length))

        n = max(1, int(length // s["P"]))
        end = (length - (n - 1) * s["P"]) / 2
        self.series, self.length = series, length
        self.hole_pitch, self.hole_count, self.end_distance = s["P"], n, end
        self.height = H
        self.hole_grip = H - s["h"]  # rail material under a screw head
        self.bolt = s["bolt"]
        # Anchors + interfaces: datum (RailTrack), bottom mounting face,
        # one ScrewHole per hole at the counterbore floor (screw head seat).
        datum = self.add_anchor(make_anchor("datum", (0.0, 0.0, 0.0)))
        self.add_interface(RailTrack(series=series), datum)
        bottom = self.add_anchor(
            make_anchor(
                "bottom", (0.0, 0.0, length / 2), z_axis=(-1, 0, 0), x_axis=_ALONG
            )
        )
        self.add_interface(PlaneFace(), bottom)
        self.add_anchor(
            make_anchor("top", (H, 0.0, length / 2), z_axis=_UP, x_axis=_ALONG)
        )
        for i in range(n):
            z = end + i * s["P"]
            top = make_anchor(f"hole_top_{i}", (H, 0.0, z), z_axis=_UP, x_axis=_ALONG)
            self.add_anchor(top)
            _drill(self, top, s["D"] / 2, s["h"])
            seat = self.add_anchor(
                make_anchor(
                    f"mount_hole_{i}", (H - s["h"], 0.0, z), z_axis=_UP, x_axis=_ALONG
                )
            )
            _drill(self, seat, s["d"] / 2, H - s["h"])
            self.add_interface(
                ScrewHole(size=s["bolt"], depth=H - s["h"]), seat, group="mount"
            )
        self.paint(STEEL)


@part(
    category="Linear Motion/Profile Rails",
    name="Rail Carriage (MGN / HGH)",
    standard="MGN7 – 15 C / H · HGH15CA · HGH20CA / HA",
    description="Ball-recirculating carriage block for an MGN rail with four tapped mounting holes on top; runs along the rail on a slider joint.",
    configurations={
        "MGN12H": dict(series="MGN12", block="H"),
        "MGN12C": dict(series="MGN12", block="C"),
        "MGN9H": dict(series="MGN9", block="H"),
        "HGH20CA": dict(series="HGR20", block="C"),
    },
    catalog_id="mgn-rail-carriage",
    example={"series": "MGN12", "block": "H"},
)
class RailCarriage(Part):
    def __init__(self, series: OneOf[MGN_SERIES] = "MGN12", block: Block = "H"):
        """Args:
        series: rail size the carriage runs on (``MGN_SERIES`` key).
        block: ``C`` standard or ``H`` long block (length and hole spacing).
        """
        s = require_option(MGN_SERIES, series, what="series", owner="RailCarriage")
        if block not in ("C", "H"):
            raise ValueError(
                f"RailCarriage: unknown block {block!r} (choose from C, H)."
            )
        Lb = float(s["Lc"] if block == "C" else s["Lh"])
        C = float(s["Cc"] if block == "C" else s["Ch"])
        Wc, Hc, H1 = float(s["Wc"]), float(s["Hc"]), float(s["H1"])
        cw, ch = s["W"] / 2 + 0.3, s["H"] + 0.2  # channel over the rail
        section = _section(
            Sketch(self.xy()),
            [(H1, -Wc / 2), (Hc, -Wc / 2), (Hc, Wc / 2), (H1, Wc / 2),
             (H1, cw), (ch, cw), (ch, -cw), (H1, -cw)],
        )  # fmt: skip
        self.add_operation(Extrusion(section, -Lb / 2, Lb / 2))

        self.series, self.block = series, block
        self.hole_spacing = (float(s["B"]), C)
        self.length, self.width, self.height = Lb, Wc, Hc
        datum = self.add_anchor(make_anchor("datum", (0.0, 0.0, 0.0)))
        self.add_interface(RailBlock(series=series), datum)
        top = self.add_anchor(
            make_anchor("top", (Hc, 0.0, 0.0), z_axis=_UP, x_axis=_ALONG)
        )
        self.add_interface(PlaneFace(), top)
        depth = min(0.8 * (Hc - ch), 1.5 * float(s["bolt"][1:]))
        i = 0
        for sy in (-1, 1):
            for sz in (-1, 1):
                hole = make_anchor(
                    f"mount_hole_{i}",
                    (Hc, sy * s["B"] / 2, sz * C / 2),
                    z_axis=_UP,
                    x_axis=_ALONG,
                )
                self.add_anchor(hole)
                _drill(self, hole, float(s["bolt"][1:]) / 2, depth)
                self.add_interface(
                    ScrewHole(size=s["bolt"], depth=depth, thread=True),
                    hole,
                    group="mount",
                )
                i += 1
        self.paint(BLACK_OXIDE)


def mount_carriage(assembly: Any, rail: Any, carriage: Any, at: float | None = None):
    """Put ``carriage`` on ``rail`` (already placed) with a ``SliderJoint``.

    ``at`` is the carriage centre's position along the rail (default: mid
    rail). Raises ``ValueError`` when the series differ or the block would
    overhang an end. Returns the joint (``joint.set_offset(x)`` moves it).
    """
    if rail.series != carriage.series:
        raise ValueError(
            f"mount_carriage: {carriage.series} carriage on an {rail.series} rail."
        )
    half = carriage.length / 2
    at = rail.length / 2 if at is None else float(at)
    if not half <= at <= rail.length - half:
        raise ValueError(
            f"mount_carriage: at={at:g} mm puts the {carriage.length:g} mm block off "
            f"the {rail.length:g} mm rail (travel {half:g} .. {rail.length - half:g})."
        )
    joint = SliderJoint(
        parent_anchor=rail.anchor("datum"),
        child_anchor=carriage.anchor("datum"),
        offset=FloatParameter(value=at),
        flip=BoolParameter(value=False),
    )
    assembly.add_joint(joint)
    return joint


__all__ = ["LinearRail", "MGN_SERIES", "RAIL_SERIES", "RailCarriage", "mount_carriage"]
