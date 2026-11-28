"""Configurable parts and assemblies whose sizes come from the standards tables.

* :class:`FittedHousing`, :class:`FittedShaft` and :class:`BearingFitDemo` —
  a 6xx bearing in a housing on a shaft, bore / shaft diameters from ISO 286
  (``fit()`` / ``bearing_fit()``), the shaft painted by fit kind, with an
  ``exaggerate`` input that scales the deviations so microns become visible.
* :class:`TappedBlock`, :class:`ClampPlate` and :class:`BoltedJointDemo` — a
  plate bolted onto a block: tapped holes (ISO 2306 tap drill), counterbored /
  clearance holes (DIN 974 / ISO 273) and DIN 912 screws whose length comes
  from :func:`screw_length`, all placed by ``connect``.
* :class:`FitTestCoupon` — a printable calibration plate: one hole per fit
  intent (press / snug / sliding / loose) for a nominal pin.

They are plain classes at import; :func:`register` declares them as library
items (``stdlib:<Class>``, toolbar section "Standards") for the viewer.
"""

from __future__ import annotations

import math
from typing import Literal

from cadbuildr.foundation import (
    Assembly,
    Circle,
    Extrusion,
    Part,
    Point,
    Sketch,
    Rectangle,
    make_anchor,
)
from cadbuildr.foundation.interfaces import PlaneFace
from cadbuildr.foundation.interfaces.features import BearingPocket, ShaftFeature
from cadbuildr.foundation.library import Num, OneOf, assembly, item_for, part

from cadbuildr.stdlib.bearings.ball_bearings.deep_groove_part import DeepGrooveBearing
from cadbuildr.stdlib.fasteners.screws_and_bolts.din912_part import DIN912Screw

from ._common import StandardsError
from .features import clearance_hole, counterbored_hole, tapped_hole
from .fits import PRINTED_CLEARANCE, bearing_fit
from .threads import screw_length

__all__ = [
    "register",
    "BearingFitDemo",
    "BoltedJointDemo",
    "ClampPlate",
    "FitTestCoupon",
    "FittedHousing",
    "FittedShaft",
    "TappedBlock",
]

BEARINGS = list(DeepGrooveBearing.TABLE)
HOUSING_TOLERANCES = ["G7", "H7", "JS7", "K7", "M7", "N7", "P7"]
SHAFT_TOLERANCES = ["f6", "g6", "h6", "js6", "k6", "m6", "n6", "p6"]
FIT_COLORS = {
    "clearance": "#3a9d5d",
    "transition": "#e0a526",
    "interference": "#d0453c",
}
BOLT_SIZES = ["M3", "M4", "M5", "M6", "M8"]

# Library declarations, applied by :func:`register` (not at import): stdlib's
# catalog-wide tests (tests/test_anchors.py EXPECTED table, catalog ==
# manifest) would otherwise have to list these demo items first. TODO(stdlib):
# once those tests accept the Standards section, decorate at import.
_DECLARED: list = []


def _declare(kind: str, **kwargs):
    def wrap(cls):
        _DECLARED.append((kind, cls, kwargs))
        return cls

    return wrap


def register() -> list:
    """Declare the demo parts / assemblies as library items (``stdlib:<Class>``,
    toolbar section "Standards") so the viewer shows their configuration bar.
    Idempotent; returns the classes."""
    from . import shaft_parts  # noqa: F401 - declares its items into _DECLARED

    out = []
    for kind, cls, kwargs in _DECLARED:
        if item_for(cls) is None:
            (part if kind == "part" else assembly)(**dict(kwargs))(cls)
        out.append(cls)
    return out


ALUMINIUM = "#c7ccd1"
STEEL = "#9ea4ab"


def _box(part: Part, length: float, width: float, height: float) -> None:
    """A length x width x height block on the XY plane (z 0 .. height), centred in XY."""
    sketch = Sketch(part.xy())
    shape = Rectangle.from_center_and_sides(sketch.origin, length, width)
    part.add_operation(Extrusion(shape, height))


@_declare(
    "part",
    category="Standards/Fits",
    name="Fitted bearing housing",
    standard="ISO 286 / ISO 492",
    description="Block with a rolling-bearing pocket toleranced to an ISO 286 hole class (BearingSeat).",
    configurations={
        "608 H7 (stationary outer ring)": dict(
            bearing="608", tolerance="H7", exaggerate=1
        ),
        "608 N7 (rotating housing)": dict(bearing="608", tolerance="N7", exaggerate=1),
    },
)
class FittedHousing(Part):
    """A square housing block with a bearing pocket on its top face.

    Args:
        bearing: the 6xx bearing the pocket takes (outer diameter D, width B).
        tolerance: ISO 286 hole class of the pocket (H7 = normal stationary outer ring).
        exaggerate: multiply the deviations (1 = true size) so the fit is visible.
    """

    def __init__(
        self,
        bearing: OneOf[BEARINGS] = "608",
        tolerance: OneOf[HOUSING_TOLERANCES] = "H7",
        exaggerate: Num(min=1, max=300, step=1, unit=None) = 1,
    ):
        b = DeepGrooveBearing.TABLE[bearing]
        f = bearing_fit(tolerance, b["D"], ring="outer")
        side = b["D"] + 16.0
        height = b["B"] + 5.0
        self.pocket_diameter = round(
            b["D"] + (f.hole.mean - b["D"]) * float(exaggerate), 4
        )
        _box(self, side, side, height)
        top = self.add_anchor(make_anchor("top", (0.0, 0.0, height)))
        self.add_anchor(make_anchor("bottom", (0.0, 0.0, 0.0), z_down=True))
        BearingPocket(
            top,
            bearing,
            name="seat",
            D=self.pocket_diameter,
            B=b["B"],
            depth=height,
            through_d=b["d"] + 4.0,
        )
        self.add_interface(PlaneFace(name="bottom"), "bottom")
        self.fit = f
        self.bearing, self.tolerance = bearing, tolerance
        self.paint(ALUMINIUM)


@_declare(
    "part",
    category="Standards/Fits",
    name="Fitted shaft",
    standard="ISO 286",
    description="Plain shaft toleranced to an ISO 286 shaft class, painted by its fit in a bearing bore.",
    configurations={
        "8 k6 (rotating inner ring)": dict(
            d=8.0, tolerance="k6", length=40, exaggerate=1
        ),
        "8 g6 (sliding)": dict(d=8.0, tolerance="g6", length=40, exaggerate=1),
    },
)
class FittedShaft(Part):
    """A plain round shaft along +Z (``axis``, ``end_a``, ``end_b`` anchors).

    Args:
        d: nominal diameter (a 6xx bearing bore: 3..12 mm).
        tolerance: ISO 286 shaft class (k6 = normal rotating inner ring).
        length: shaft length.
        exaggerate: multiply the deviations (1 = true size) so the fit is visible.
    """

    def __init__(
        self,
        d: OneOf[[3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0]] = 8.0,
        tolerance: OneOf[SHAFT_TOLERANCES] = "k6",
        length: Num(min=10, max=200, step=1) = 40,
        exaggerate: Num(min=1, max=300, step=1, unit=None) = 1,
    ):
        f = bearing_fit(tolerance, float(d), ring="inner")
        self.modeled_diameter = round(
            float(d) + (f.shaft.mean - float(d)) * float(exaggerate), 4
        )
        sketch = Sketch(self.xy())
        self.add_operation(
            Extrusion(
                Circle(Point(sketch, 0.0, 0.0), self.modeled_diameter / 2.0),
                float(length),
            )
        )
        ShaftFeature(self, d=float(d), length=float(length))
        self.fit = f
        self.paint(FIT_COLORS[f.kind])


@_declare(
    "assembly",
    category="Standards/Fits",
    name="Bearing fit demo",
    standard="ISO 286 / ISO 492",
    description="608-style bearing in a housing on a shaft; ISO 286 classes size the bore and the shaft live.",
    configurations={
        "Rotating shaft H7 / k6": dict(
            bearing="608", housing_tolerance="H7", shaft_tolerance="k6", exaggerate=1
        ),
        "Floating bearing G7 / k6": dict(
            bearing="608", housing_tolerance="G7", shaft_tolerance="k6", exaggerate=1
        ),
        "Sliding shaft g6, x100": dict(
            bearing="608", housing_tolerance="H7", shaft_tolerance="g6", exaggerate=100
        ),
        "Press-fit p6, x100": dict(
            bearing="608", housing_tolerance="H7", shaft_tolerance="p6", exaggerate=100
        ),
    },
)
class BearingFitDemo(Assembly):
    """Housing, deep-groove bearing and shaft, connected seat-to-face and
    shaft-in-bore. The housing and shaft diameters come from
    ``bearing_fit()``; the shaft is green / amber / red for a clearance /
    transition / interference fit on the bearing bore.

    Args:
        bearing: bearing model (sizes the pocket, the bearing and the shaft).
        housing_tolerance: ISO 286 hole class of the housing pocket.
        shaft_tolerance: ISO 286 shaft class of the shaft.
        exaggerate: deviation multiplier (1 = true size; 100 makes 10 µm a millimetre).
    """

    def __init__(
        self,
        bearing: OneOf[BEARINGS] = "608",
        housing_tolerance: OneOf[HOUSING_TOLERANCES] = "H7",
        shaft_tolerance: OneOf[SHAFT_TOLERANCES] = "k6",
        exaggerate: Num(min=1, max=300, step=1, unit=None) = 1,
    ):
        b = DeepGrooveBearing.TABLE[bearing]
        housing = FittedHousing(
            bearing=bearing, tolerance=housing_tolerance, exaggerate=exaggerate
        )
        self.ground(housing)
        brg = DeepGrooveBearing(model=bearing)
        self.connect(brg.interface("bottom"), housing.interface("seat"))
        length = b["B"] * 3 + 10.0
        shaft = FittedShaft(
            d=b["d"], tolerance=shaft_tolerance, length=length, exaggerate=exaggerate
        )
        self.connect(
            shaft.interface("axis"),
            brg.interface("axis"),
            offset=-(length - b["B"]) / 2.0,
        )
        self.add_anchor(make_anchor("origin", (0.0, 0.0, 0.0)))
        self.housing, self.shaft = housing, shaft
        self.housing_fit, self.shaft_fit = housing.fit, shaft.fit
        self.bearing = bearing


@_declare(
    "part",
    category="Standards/Threads",
    name="Tapped block",
    standard="ISO 261 / ISO 2306",
    description="Block with a row of tapped holes (tap-drill bores + threaded ScrewHole interfaces).",
    configurations={
        "2 x M5": dict(size="M5", n=2, pitch=30, height=20, depth=12),
        "4 x M3": dict(size="M3", n=4, pitch=15, height=12, depth=8),
    },
)
class TappedBlock(Part):
    """A block with ``n`` tapped holes along X on its top face.

    Args:
        size: metric thread of the holes (tap drill from the ISO 2306 table).
        n: number of holes.
        pitch: hole spacing along X.
        height: block height.
        depth: tapped depth (blind; at least 1 x d, at most height - 2 mm).
    """

    def __init__(
        self,
        size: OneOf[BOLT_SIZES] = "M5",
        n: Num(min=1, max=6, step=1, integer=True, unit=None) = 2,
        pitch: Num(min=10, max=80, step=1) = 30,
        height: Num(min=8, max=60, step=1) = 20,
        depth: Num(min=3, max=58, step=0.5) = 12,
    ):
        d = float(size[1:])
        n = int(n)
        length = pitch * (n - 1) + 4 * d + 12.0
        width = 4 * d + 12.0
        depth = float(depth)
        if depth < d or depth > float(height) - 2.0:
            raise StandardsError(
                f"TappedBlock: {size} tapped depth {depth:g} mm must be >= {d:g} (1 x d) and"
                f" <= height - 2 = {float(height) - 2:g} mm"
            )
        _box(self, length, width, height)
        top = self.add_anchor(make_anchor("top", (0.0, 0.0, float(height))))
        self.add_anchor(make_anchor("bottom", (0.0, 0.0, 0.0), z_down=True))
        self.add_interface(PlaneFace(name="top"), top)
        first = top.offset([-(n - 1) * pitch / 2.0, 0.0, 0.0], name="hole")
        for i, anchor in enumerate(
            first.linear_pattern(n, float(pitch), direction=(1, 0, 0))
        ):
            self.add_anchor(anchor)
            tapped_hole(anchor, size, depth, group="tapped")
        self.size, self.length, self.width, self.height = (
            size,
            length,
            width,
            float(height),
        )
        self.paint(STEEL)


@_declare(
    "part",
    category="Standards/Threads",
    name="Clamp plate",
    standard="ISO 273 / DIN 974-1",
    description="Plate with counterbored or clearance holes for socket cap screws (ScrewHole group 'bolts').",
    configurations={
        "2 x M5 counterbored": dict(
            size="M5", n=2, pitch=30, thickness=10, holes="counterbore", fit="normal"
        ),
        "2 x M5 clearance": dict(
            size="M5", n=2, pitch=30, thickness=6, holes="clearance", fit="normal"
        ),
    },
)
class ClampPlate(Part):
    """A plate matching :class:`TappedBlock`'s hole row.

    Args:
        size: screw size (clearance from ISO 273, counterbore from DIN 974-1).
        n: number of holes.
        pitch: hole spacing along X.
        thickness: plate thickness.
        holes: counterbore (head below the face) or clearance (head on the face).
        fit: ISO 273 clearance series.
    """

    def __init__(
        self,
        size: OneOf[BOLT_SIZES] = "M5",
        n: Num(min=1, max=6, step=1, integer=True, unit=None) = 2,
        pitch: Num(min=10, max=80, step=1) = 30,
        thickness: Num(min=3, max=40, step=0.5) = 10,
        holes: Literal["counterbore", "clearance"] = "counterbore",
        fit: Literal["close", "normal", "loose"] = "normal",
    ):
        d = float(size[1:])
        n = int(n)
        length = pitch * (n - 1) + 4 * d + 12.0
        width = 4 * d + 12.0
        _box(self, length, width, thickness)
        top = self.add_anchor(make_anchor("top", (0.0, 0.0, float(thickness))))
        self.add_anchor(make_anchor("bottom", (0.0, 0.0, 0.0), z_down=True))
        self.add_interface(PlaneFace(name="bottom"), "bottom")
        first = top.offset([-(n - 1) * pitch / 2.0, 0.0, 0.0], name="hole")
        drill = counterbored_hole if holes == "counterbore" else clearance_hole
        self.grip = 0.0
        for anchor in first.linear_pattern(n, float(pitch), direction=(1, 0, 0)):
            self.add_anchor(anchor)
            feature = drill(anchor, size, float(thickness), fit, group="bolts")
            self.grip = feature.interface.spec.depth
        self.size, self.thickness, self.holes = size, float(thickness), holes
        self.paint(ALUMINIUM)


@_declare(
    "assembly",
    category="Standards/Threads",
    name="Bolted joint demo",
    standard="ISO 4762 / ISO 273 / ISO 2306",
    description="Clamp plate bolted onto a tapped block with DIN 912 screws sized by screw_length().",
    configurations={
        "2 x M5, counterbored": dict(
            size="M5", n=2, plate_thickness=10, holes="counterbore", engagement=1.5
        ),
        "4 x M8, clearance": dict(
            size="M8", n=4, plate_thickness=12, holes="clearance", engagement=1.5
        ),
        "3 x M4 into aluminium (2 d)": dict(
            size="M4", n=3, plate_thickness=8, holes="counterbore", engagement=2.0
        ),
    },
)
class BoltedJointDemo(Assembly):
    """A clamp plate face-to-face on a tapped block, one DIN 912 screw per
    hole. The screw length is the shortest ISO 4762 length that clamps the
    plate and engages ``engagement`` x d of thread in the block.

    Args:
        size: screw / thread size (holes, counterbores and screws follow).
        n: number of screws.
        plate_thickness: clamp plate thickness.
        holes: counterbored or plain clearance holes in the plate.
        engagement: thread engagement in the block, in screw diameters.
    """

    def __init__(
        self,
        size: OneOf[BOLT_SIZES] = "M5",
        n: Num(min=1, max=6, step=1, integer=True, unit=None) = 2,
        plate_thickness: Num(min=4, max=30, step=0.5) = 10,
        holes: Literal["counterbore", "clearance"] = "counterbore",
        engagement: Num(min=1, max=2, step=0.25, unit=None) = 1.5,
    ):
        plate = ClampPlate(size=size, n=n, thickness=plate_thickness, holes=holes)
        length = screw_length(size, plate.grip, engagement=float(engagement))
        # Tap 1 mm (rounded up to 0.5) past the screw tip; the block is 4 mm deeper.
        depth = math.ceil((length - plate.grip + 1.0) * 2.0) / 2.0
        block = TappedBlock(
            size=size, n=n, height=max(20.0, math.ceil(depth) + 4.0), depth=depth
        )
        self.ground(block)
        self.connect(plate.interface("bottom"), block.interface("top"))
        self.screws = self.connect_all(
            lambda: DIN912Screw(size=size, length=length, with_thread=False),
            plate.group("bolts"),
        )
        self.add_anchor(make_anchor("origin", (0.0, 0.0, 0.0)))
        self.screw_length = length
        self.size = size


@_declare(
    "part",
    category="Standards/Fits",
    name="Print fit test coupon",
    standard="FDM / SLA / SLS design allowances",
    description="Printable plate with one hole per fit intent (press, snug, sliding, loose) for a nominal pin.",
    configurations={
        "8 mm pin, FDM": dict(pin=8, process="fdm", thickness=5),
        "608 bearing (22 mm), FDM": dict(pin=22, process="fdm", thickness=7),
        "3 mm pin, SLA": dict(pin=3, process="sla", thickness=3),
    },
)
class FitTestCoupon(Part):
    """A calibration plate: holes of ``pin`` + the printed clearance of each
    intent, left to right press / snug / sliding / loose.

    Args:
        pin: nominal pin (or bearing / magnet) diameter.
        process: print process (sets the clearance per intent).
        thickness: plate thickness.
    """

    def __init__(
        self,
        pin: Num(min=2, max=30, step=0.5) = 8,
        process: OneOf[list(PRINTED_CLEARANCE)] = "fdm",
        thickness: Num(min=2, max=20, step=0.5) = 5,
    ):
        intents = list(PRINTED_CLEARANCE[process])
        pitch = float(pin) + 8.0
        length = pitch * len(intents) + 4.0
        width = float(pin) + 12.0
        _box(self, length, width, thickness)
        self.add_anchor(make_anchor("top", (0.0, 0.0, float(thickness))))
        self.add_anchor(make_anchor("bottom", (0.0, 0.0, 0.0), z_down=True))
        self.diameters = {}
        for i, intent in enumerate(intents):
            x = (i - (len(intents) - 1) / 2.0) * pitch
            dia = float(pin) + PRINTED_CLEARANCE[process][intent]
            sketch = Sketch(self.xy())
            self.add_operation(
                Extrusion(
                    Circle(Point(sketch, x, 0.0), dia / 2.0), float(thickness), cut=True
                )
            )
            self.add_anchor(make_anchor(f"hole_{intent}", (x, 0.0, float(thickness))))
            self.diameters[intent] = round(dia, 3)
        self.paint("#e0e0e0")
