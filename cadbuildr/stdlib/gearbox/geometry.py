"""Dimensions and part placements of one spur gear stage between two plates.

Everything here is plain numbers (no CAD objects), shared by
:class:`~cadbuildr.stdlib.gearbox.plate_part.GearboxPlate`,
:class:`~cadbuildr.stdlib.gearbox.stage.GearStage` and the placement tables
in :mod:`cadbuildr.stdlib.gearbox.demos`, so all three agree by construction.

Stage frame (mm): shafts along +Z, the input (pinion) axis on the origin, the
output (gear) axis at ``x = centre distance``. Plate A (input side) spans
``z = 0 .. t`` with its outer face on ``z = 0``; the bay between the plates is
``t .. t + bay``; plate B spans ``t + bay .. 2t + bay`` and is plate A flipped
180° about X. Bearings are seated from the outer faces (shoulders inside), so
their placement does not depend on the bearing width. Through-bolts at the
four corners clamp a spacer tube between the plates: socket head on plate B,
washer + hex nut under plate A.

Hole and outline positions depend on the centre distance, the module and the
screw size only (not on the bearing, nor on how the teeth split the centre
distance), so a click-built gearbox keeps every placement valid when the
bearing changes, or when the tooth counts change at a constant
``z_pinion + z_gear``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from cadbuildr.stdlib.bearings.ball_bearings.deep_groove_part import (
    DeepGrooveBearing,
)
from cadbuildr.stdlib.fasteners.nuts.hex_din934_part import HexNut
from cadbuildr.stdlib.fasteners.screws_and_bolts.din912_part import DIN912Screw
from cadbuildr.stdlib.fasteners.washers.din125_part import DIN125Washer
from cadbuildr.stdlib.power_transmission.gears.spur_gear_part import (
    ADDENDUM,
    DEDENDUM,
)

# DIN EN 20273 medium-series clearance holes for the corner through-bolts.
CLEARANCE: Dict[str, float] = {
    "M3": 3.4,
    "M4": 4.5,
    "M5": 5.5,
    "M6": 6.6,
    "M8": 9.0,
}

MIN_TEETH = 8
FACE_WIDTH = 12.0  # gear face width
GEAR_GAP = 4.0  # axial clearance between a gear face and a plate's inner face
PLATE_THICKNESS = 8.0
SHAFT_EXTENSION = 20.0  # input / output shaft beyond the plates
SHOULDER = 1.0  # minimum plate material behind a bearing seat
MAX_BEARING_OD = max(b["D"] for b in DeepGrooveBearing.TABLE.values())


def gear_mesh_phase_deg(z_gear: int) -> float:
    """Rotation (deg, about the gear axis) that puts a gap of the gear in front
    of tooth 0 of the pinion, with the gear on the pinion's +X: 0 for an odd
    tooth count, half a tooth pitch for an even one (as ``mesh_phase``)."""
    return 0.0 if int(z_gear) % 2 else 180.0 / int(z_gear)


def _round_up(value: float, step: float = 5.0) -> float:
    return float(math.ceil(value / step - 1e-9) * step)


@dataclass(frozen=True)
class StageGeometry:
    module: float
    z_pinion: int
    z_gear: int
    bearing: str = "608"
    screw: str = "M5"
    thickness: float = PLATE_THICKNESS
    face_width: float = FACE_WIDTH
    gear_gap: float = GEAR_GAP
    shaft_extension: float = SHAFT_EXTENSION

    def __post_init__(self) -> None:
        if self.bearing not in DeepGrooveBearing.TABLE:
            raise ValueError(f"Unknown bearing '{self.bearing}'.")
        if self.screw not in CLEARANCE:
            raise ValueError(
                f"Unsupported screw '{self.screw}' (one of {', '.join(CLEARANCE)})."
            )
        if min(self.z_pinion, self.z_gear) < MIN_TEETH:
            raise ValueError(f"Gears need at least {MIN_TEETH} teeth.")
        if self.z_pinion > self.z_gear:
            raise ValueError("A reducer stage needs z_pinion <= z_gear.")
        if self.module <= 0:
            raise ValueError("module must be positive")
        if self.thickness < self.bearing_width + SHOULDER:
            raise ValueError(
                f"Plate thickness {self.thickness} too thin for a {self.bearing} seat "
                f"(width {self.bearing_width} + {SHOULDER} shoulder)."
            )

    # -- gears ------------------------------------------------------------ #
    @property
    def center_distance(self) -> float:
        """Standard centre distance: module x (z_pinion + z_gear) / 2."""
        return self.module * (self.z_pinion + self.z_gear) / 2.0

    @property
    def ratio(self) -> float:
        return self.z_gear / self.z_pinion

    @property
    def pinion_pitch_radius(self) -> float:
        return self.module * self.z_pinion / 2.0

    @property
    def gear_pitch_radius(self) -> float:
        return self.module * self.z_gear / 2.0

    def outer_radius(self, teeth: int) -> float:
        return self.module * teeth / 2.0 + ADDENDUM * self.module

    def root_radius(self, teeth: int) -> float:
        return self.module * teeth / 2.0 - DEDENDUM * self.module

    @property
    def max_gear_radius(self) -> float:
        """Largest gear tip radius any split of this centre distance can have
        (the other gear at ``MIN_TEETH``): sizes the plate and its holes."""
        return self.center_distance - self.module * MIN_TEETH / 2.0 + self.module

    @property
    def max_pinion_radius(self) -> float:
        """Largest pinion tip radius with ``z_pinion <= z_gear``."""
        return self.center_distance / 2.0 + self.module

    # -- bearings / shafts ------------------------------------------------ #
    @property
    def bearing_spec(self) -> Dict[str, float]:
        return DeepGrooveBearing.TABLE[self.bearing]

    @property
    def bearing_width(self) -> float:
        return float(self.bearing_spec["B"])

    @property
    def shaft_diameter(self) -> float:
        return float(self.bearing_spec["d"])

    @property
    def shoulder_hole(self) -> float:
        """Shaft clearance through the shoulder behind a bearing seat."""
        return self.shaft_diameter + 2.0

    # -- plates, spacers, bolts -------------------------------------------- #
    @property
    def bay(self) -> float:
        """Inner gap between the plates (= spacer length)."""
        return self.face_width + 2.0 * self.gear_gap

    @property
    def height(self) -> float:
        """Plate A outer face to plate B outer face."""
        return 2.0 * self.thickness + self.bay

    @property
    def washer(self) -> Dict[str, float]:
        return DIN125Washer.DIN_SPECS[self.screw]

    @property
    def washer_thickness(self) -> float:
        return float(self.washer["thickness"])

    @property
    def nut_thickness(self) -> float:
        return float(HexNut.dimension_table[self.screw]["thickness"])

    @property
    def spacer_od(self) -> float:
        return float(self.washer["outer_diameter"])

    @property
    def edge(self) -> float:
        """Hole centre to plate edge."""
        return self.spacer_od / 2.0 + 2.0

    @property
    def hole_y(self) -> float:
        """Corner holes at ±hole_y: spacers clear the largest possible gear."""
        return self.max_gear_radius + self.spacer_od / 2.0 + 2.0

    @property
    def x_min(self) -> float:
        return -(max(self.max_pinion_radius, MAX_BEARING_OD / 2.0) + self.edge)

    @property
    def x_max(self) -> float:
        return self.center_distance + self.max_gear_radius + self.edge

    @property
    def y_half(self) -> float:
        return self.hole_y + self.edge

    def hole_positions(self) -> List[tuple]:
        """hole_1..4 counter-clockwise from the (-x, -y) corner."""
        xl, xr = self.x_min + self.edge, self.x_max - self.edge
        y = self.hole_y
        return [(xl, -y), (xr, -y), (xr, y), (xl, y)]

    def mount_positions(self) -> List[tuple]:
        """Two extra DIN912 mounting holes, mid-length on the long edges."""
        xm = (self.x_min + self.x_max) / 2.0
        return [(xm, -self.hole_y), (xm, self.hole_y)]

    @property
    def screw_pitch(self) -> float:
        return float(DIN912Screw.dimension_table[self.screw]["thread_pitch"])

    @property
    def screw_length(self) -> float:
        """Through-bolt: both plates, the spacer, two washers, the nut and two
        pitches of thread past the nut, rounded up to 5 mm."""
        grip = self.height + 2.0 * self.washer_thickness + self.nut_thickness
        return _round_up(grip + 2.0 * self.screw_pitch)

    @property
    def input_shaft_length(self) -> float:
        return self.shaft_extension + self.height

    @property
    def output_shaft_length(self) -> float:
        return self.height + self.shaft_extension

    def check(self) -> None:
        """Raise if the parts would not fit together."""
        d = self.shaft_diameter
        if self.root_radius(self.z_pinion) < d / 2.0 + 1.0:
            raise ValueError(
                f"Pinion root (r={self.root_radius(self.z_pinion):.2f}) too small for "
                f"a {d:g} mm shaft: use more teeth, a larger module or a smaller bearing."
            )
        if self.screw_length > 80:
            raise ValueError(f"Through-bolt length {self.screw_length} > 80 mm")


# --------------------------------------------------------------------------- #
# Placements (stage frame)
# --------------------------------------------------------------------------- #

FLIP_X = {"axis": "X", "angle": 180.0}


def _item(
    role: str,
    cls: str,
    inputs: Dict[str, Any],
    translate: tuple,
    rotate: Optional[Dict[str, Any]] = None,
    bind: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    return {
        "role": role,
        "item": f"stdlib:{cls}",
        "inputs": dict(inputs),
        "translate": [float(v) for v in translate],
        "rotate": dict(rotate) if rotate else None,
        "bind": dict(bind or {}),
    }


def stage_items(g: StageGeometry, threads: bool = False) -> List[Dict[str, Any]]:
    """Every part of one stage, placed in the stage frame.

    Each entry: ``role``, ``item`` (``stdlib:<Cls>``), ``inputs``,
    ``translate`` [x, y, z], ``rotate`` ({axis, angle} about the part's own
    origin, applied before the translation) or None, and ``bind``:
    {component input: stage input} for the inputs that follow the stage's
    ``module`` / ``z_pinion`` / ``z_gear`` / ``bearing``.
    """
    g.check()
    cd, t, h = g.center_distance, g.thickness, g.height
    plate_inputs = dict(
        module=g.module,
        z_pinion=g.z_pinion,
        z_gear=g.z_gear,
        bearing=g.bearing,
        screw=g.screw,
        thickness=g.thickness,
    )
    plate_bind = {k: k for k in ("module", "z_pinion", "z_gear", "bearing")}
    out = [
        _item("plate_a", "GearboxPlate", plate_inputs, (0, 0, 0), None, plate_bind),
        _item("plate_b", "GearboxPlate", plate_inputs, (0, 0, h), FLIP_X, plate_bind),
    ]
    d = g.shaft_diameter
    out.append(
        _item(
            "shaft_in",
            "Shaft",
            dict(diameter=d, length=g.input_shaft_length),
            (0, 0, -g.shaft_extension),
        )
    )
    out.append(
        _item(
            "shaft_out",
            "Shaft",
            dict(diameter=d, length=g.output_shaft_length),
            (cd, 0, 0),
        )
    )
    gear_z = t + g.gear_gap
    out.append(
        _item(
            "pinion",
            "SpurGear",
            dict(module=g.module, teeth=g.z_pinion, face_width=g.face_width, bore=d),
            (0, 0, gear_z),
            None,
            {"module": "module", "teeth": "z_pinion"},
        )
    )
    phase = gear_mesh_phase_deg(g.z_gear)
    out.append(
        _item(
            "gear",
            "SpurGear",
            dict(module=g.module, teeth=g.z_gear, face_width=g.face_width, bore=d),
            (cd, 0, gear_z),
            {"axis": "Z", "angle": phase} if phase else None,
            {"module": "module", "teeth": "z_gear"},
        )
    )
    # Bearings: plate A seats open on z=0 (bearing z = 0 .. B); plate B seats
    # open on z=h (bearing flipped, z = h - B .. h).
    for side, x in (("in", 0.0), ("out", cd)):
        out.append(
            _item(
                f"bearing_{side}_a",
                "DeepGrooveBearing",
                dict(model=g.bearing),
                (x, 0, 0),
                None,
                {"model": "bearing"},
            )
        )
        out.append(
            _item(
                f"bearing_{side}_b",
                "DeepGrooveBearing",
                dict(model=g.bearing),
                (x, 0, h),
                FLIP_X,
                {"model": "bearing"},
            )
        )
    tw, tn = g.washer_thickness, g.nut_thickness
    for i, (x, y) in enumerate(g.hole_positions(), start=1):
        out.append(
            _item(
                f"spacer_{i}",
                "Spacer",
                dict(screw=g.screw, length=g.bay, outer_diameter=g.spacer_od),
                (x, y, t),
            )
        )
        out.append(
            _item(
                f"screw_{i}",
                "DIN912Screw",
                dict(size=g.screw, length=g.screw_length, with_thread=threads),
                (x, y, h + tw - g.screw_length),
            )
        )
        out.append(
            _item(f"washer_head_{i}", "DIN125Washer", dict(size=g.screw), (x, y, h))
        )
        out.append(
            _item(f"washer_nut_{i}", "DIN125Washer", dict(size=g.screw), (x, y, -tw))
        )
        out.append(
            _item(
                f"nut_{i}",
                "HexNut",
                dict(size=g.screw, with_thread=threads),
                (x, y, -tw - tn),
            )
        )
    return out
