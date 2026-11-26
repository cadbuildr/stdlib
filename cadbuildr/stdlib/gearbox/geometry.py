"""Dimensions and part placements of one spur gear stage between two plates.

Everything here is plain numbers (no CAD objects), shared by
:class:`~cadbuildr.stdlib.gearbox.plate_part.GearboxPlate`,
:class:`~cadbuildr.stdlib.gearbox.stage.GearStage` and the connect sequences
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
# The stage as a connect sequence (no positions)
# --------------------------------------------------------------------------- #

# plate B is plate A turned 180 deg about X: its corner hole k faces plate A's i.
MIRROR = {1: 4, 2: 3, 3: 2, 4: 1}


def _item(role, cls, inputs, connect=None, bind=None):
    return {
        "role": role,
        "item": f"stdlib:{cls}",
        "inputs": dict(inputs),
        "connect": connect,
        "bind": dict(bind or {}),
    }


def _to(own, role, iface, **dof):
    return {
        "own": own,
        "target": [role, iface],
        "dof": {k: float(v) for k, v in dof.items()},
    }


def stage_items(
    g: StageGeometry, threads: bool = False, root: str = "plate", entry: Any = None
) -> List[Dict[str, Any]]:
    """Every part of one stage as a connect sequence, in dependency order.

    Each entry: ``role``, ``item`` (``stdlib:<Cls>``), ``inputs``, ``connect``
    (``{own, target: [role, interface], dof}`` or None) and ``bind``
    ({component input: stage input}). ``root="plate"``: plate A is grounded
    (``connect`` None); ``root="input"``: the input shaft's ``end_a`` connects
    to ``entry`` (``[item, interface]`` outside the stage) and the stage
    hangs from it. Loop closures: :func:`stage_loops`.
    """
    g.check()
    cd, t, e = g.center_distance, g.thickness, g.shaft_extension
    plate_inputs = dict(
        module=g.module,
        z_pinion=g.z_pinion,
        z_gear=g.z_gear,
        bearing=g.bearing,
        screw=g.screw,
        thickness=g.thickness,
    )
    plate_bind = {k: k for k in ("module", "z_pinion", "z_gear", "bearing")}
    d = g.shaft_diameter
    bearing = dict(model=g.bearing)
    bbind = {"model": "bearing"}
    shaft_in = _item("shaft_in", "Shaft", dict(diameter=d, length=g.input_shaft_length))
    if root == "plate":
        out = [
            _item("plate_a", "GearboxPlate", plate_inputs, None, plate_bind),
            _item(
                "bearing_in_a",
                "DeepGrooveBearing",
                bearing,
                _to("top", "plate_a", "seat_in"),
                bbind,
            ),
            dict(shaft_in, connect=_to("axis", "bearing_in_a", "axis", offset=-e)),
        ]
    else:
        out = [
            dict(shaft_in, connect={"own": "end_a", "target": list(entry), "dof": {}}),
            # the bearing rides the shaft e from its end
            _item(
                "bearing_in_a",
                "DeepGrooveBearing",
                bearing,
                _to("axis", "shaft_in", "axis", offset=e),
                bbind,
            ),
            _item(
                "plate_a",
                "GearboxPlate",
                plate_inputs,
                _to("seat_in", "bearing_in_a", "top"),
                plate_bind,
            ),
        ]
    out += [
        _item(
            "bearing_out_a",
            "DeepGrooveBearing",
            bearing,
            _to("top", "plate_a", "seat_out"),
            bbind,
        ),
        _item(
            "shaft_out",
            "Shaft",
            dict(diameter=d, length=g.output_shaft_length),
            _to("axis", "bearing_out_a", "axis", offset=0.0),
        ),
    ]
    spacer = dict(screw=g.screw, length=g.bay, outer_diameter=g.spacer_od)
    for i in range(1, 5):
        out.append(
            _item(
                f"spacer_{i}",
                "Spacer",
                spacer,
                _to("bottom", "plate_a", f"hole_{i}_in"),
            )
        )
    out.append(
        _item(
            "plate_b",
            "GearboxPlate",
            plate_inputs,
            _to(f"hole_{MIRROR[1]}_in", "spacer_1", "top"),
            plate_bind,
        )
    )
    for side in ("in", "out"):
        out.append(
            _item(
                f"bearing_{side}_b",
                "DeepGrooveBearing",
                bearing,
                _to("top", "plate_b", f"seat_{side}"),
                bbind,
            )
        )
    gear_z = t + g.gear_gap
    gear = dict(module=g.module, face_width=g.face_width, bore=d)
    out.append(
        _item(
            "pinion",
            "SpurGear",
            dict(gear, teeth=g.z_pinion),
            _to("axis", "shaft_in", "axis", offset=gear_z + e, angle=0.0),
            {"module": "module", "teeth": "z_pinion"},
        )
    )
    out.append(
        _item(
            "gear",
            "SpurGear",
            dict(gear, teeth=g.z_gear),
            # mesh phase about the shaft: a joint value, not a rotation
            _to(
                "axis",
                "shaft_out",
                "axis",
                offset=gear_z,
                angle=math.radians(gear_mesh_phase_deg(g.z_gear)),
            ),
            {"module": "module", "teeth": "z_gear"},
        )
    )
    for i in range(1, 5):
        k = MIRROR[i]
        out += [
            _item(
                f"washer_head_{i}",
                "DIN125Washer",
                dict(size=g.screw),
                _to("bottom", "plate_b", f"hole_{k}"),
            ),
            _item(
                f"screw_{i}",
                "DIN912Screw",
                dict(size=g.screw, length=g.screw_length, with_thread=threads),
                _to("head_seat", f"washer_head_{i}", "top"),
            ),
            _item(
                f"washer_nut_{i}",
                "DIN125Washer",
                dict(size=g.screw),
                _to("bottom", "plate_a", f"hole_{i}"),
            ),
            _item(
                f"nut_{i}",
                "HexNut",
                dict(size=g.screw, with_thread=threads),
                _to("bottom", f"washer_nut_{i}", "top"),
            ),
        ]
    return out


def stage_loops(prefix: str = "") -> List[Dict[str, Any]]:
    """The redundant contacts a stage closes (checked): plate B on the other
    three spacers, both shafts in plate B's bearings, each nut on its bolt."""
    p = prefix
    loops = [
        {"a": [f"{p}plate_b", f"hole_{MIRROR[i]}_in"], "b": [f"{p}spacer_{i}", "top"]}
        for i in (2, 3, 4)
    ]
    loops += [
        {"a": [f"{p}shaft_in", "axis"], "b": [f"{p}bearing_in_b", "axis"]},
        {"a": [f"{p}shaft_out", "axis"], "b": [f"{p}bearing_out_b", "axis"]},
    ]
    loops += [
        {"a": [f"{p}screw_{i}", "tip"], "b": [f"{p}nut_{i}", "bottom"]}
        for i in range(1, 5)
    ]
    for loop in loops:
        loop["dof"] = {}
    return loops
