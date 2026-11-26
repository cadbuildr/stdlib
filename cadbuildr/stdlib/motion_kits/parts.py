"""Rod end plates, carriages and motor brackets for two-rod linear axes.

Every part is modelled in the pose it is installed in, Z up, so that a layout
places it with a translation plus at most one rotation about Z:

* the rods run along local **+X**, two of them ``spacing`` apart along Y, at
  height ``ROD_Z`` above the base a ``RodEndPlate`` stands on;
* a ``Carriage`` / ``GantryCarriage`` has its origin on the rod plane, centred
  between the rods (place it at ``z = ROD_Z``);
* a ``MotorMount`` is an L-bracket whose vertical leg bolts to a vertical face
  (its back at ``x = 0``) and whose horizontal leg holds a motor underneath,
  shaft up (or an idler pulley on top, ``motor=False``).

The outer envelope of every part is independent of the rod diameter (the
margins are sized for the largest rod), so switching ``rod`` between 8, 10 and
12 mm only changes holes and bores: nothing else in a layout has to move.
"""

from __future__ import annotations

import math
from typing import ClassVar

from cadbuildr.foundation import Circle, Extrusion, Part, Point, Sketch, make_anchor
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.actuators.stepper_motors.nema_stepper_part import StepperMotor
from cadbuildr.stdlib.common import oriented_rectangle_shape
from cadbuildr.stdlib.linear_motion.linear_bearings.lm_bearing_part import (
    LinearBearing,
)

PLATE_COLOR = "#3f6fb5"  # anodised aluminium plates
CARRIAGE_COLOR = "#d08a2e"
BRACKET_COLOR = "#5b6068"

# Rod sizes the kits support: rod diameter -> LMxUU bearing (LinearBearing.TABLE).
RODS: dict[str, dict] = {
    "8": {"d": 8.0, "bearing": "LM8UU"},
    "10": {"d": 10.0, "bearing": "LM10UU"},
    "12": {"d": 12.0, "bearing": "LM12UU"},
}
for _row in RODS.values():
    _row.update(
        {
            "D": LinearBearing.TABLE[_row["bearing"]]["D"],
            "L": LinearBearing.TABLE[_row["bearing"]]["L"],
        }
    )

NEMA: dict = StepperMotor.TABLE

ROD_Z = 30.0  # rod axis height above the plate base
PLATE_HEIGHT = 2 * ROD_Z
FOOT_LENGTH = 20.0  # foot of a RodEndPlate, on the carriage side
FOOT_THICKNESS = 8.0
EDGE = 16.0  # plate margin outside a rod axis (fits a 12 mm rod + wall)
CARRIAGE_BELOW = 16.0  # carriage block under the rod plane (fits LM12UU + wall)
CARRIAGE_ABOVE = 20.0  # carriage block over the rod plane
CARRIAGE_EDGE = 16.5  # carriage margin outside a rod axis
X_ROD_Z = 24.0  # GantryCarriage: X rods above its Y rod plane
SIDE_HOLE_X = 15.0  # GantryCarriage side holes / MotorMount holes: +-15 mm
BELT_Y = 20 * 2.0 / (2 * math.pi)  # belt run of a 20T GT2 pulley centred on y=0
BELT_Z = CARRIAGE_ABOVE + 7.0  # belt centre height in the clamp slot
NUT_PCD = 16.0  # LeadScrewNutT8 flange holes
NUT_BORE = 10.5  # clears the nut body (10.2) and the T8 screw
SEAT_608 = {"D": 22.0, "B": 7.0}  # idler bearing seat of a RodEndPlate
M3_CLEAR, M4_TAP, M5_CLEAR, M5_TAP = 1.7, 1.65, 2.75, 2.1  # hole radii


# --------------------------------------------------------------------------- #
# Geometry helpers (part frame)
# --------------------------------------------------------------------------- #


def _box(p, x0, x1, y0, y1, z0, z1, cut=False):
    shape = oriented_rectangle_shape(
        Sketch(p.xy()), (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, 0.0
    )
    p.add_operation(Extrusion(shape, z0, z1, cut=cut))


def _hole_x(p, y, z, r, x0, x1):
    """Cylinder along X (yz sketch: local x -> Y, local y -> Z, extrudes +X)."""
    p.add_operation(Extrusion(Circle(Point(Sketch(p.yz()), y, z), r), x0, x1, cut=True))


def _hole_y(p, x, z, r, y0, y1):
    """Cylinder along Y (xz sketch: local x -> X, local y -> Z, extrudes -Y)."""
    p.add_operation(
        Extrusion(Circle(Point(Sketch(p.xz()), x, z), r), -y1, -y0, cut=True)
    )


def _hole_z(p, x, y, r, z0, z1):
    p.add_operation(Extrusion(Circle(Point(Sketch(p.xy()), x, y), r), z0, z1, cut=True))


def _anchor(p, name, pos, normal):
    p.add_anchor(make_anchor(name, tuple(float(v) for v in pos), z_axis=normal))


PX, NX, PY, NY, PZ, NZ = (
    (1.0, 0.0, 0.0),
    (-1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, -1.0, 0.0),
    (0.0, 0.0, 1.0),
    (0.0, 0.0, -1.0),
)


def nut_hole_offsets():
    """(y, z) of the four LeadScrewNutT8 flange holes around the screw axis,
    for a nut whose axis is along X (holes at 45 deg on the 16 mm PCD)."""
    r = NUT_PCD / 2 / math.sqrt(2)
    return [(-r, -r), (-r, r), (r, -r), (r, r)]


def _check_rod(rod):
    if str(rod) not in RODS:
        raise ValueError(f"Unknown rod '{rod}' (choose from {list(RODS)}).")
    return RODS[str(rod)]


# --------------------------------------------------------------------------- #
# RodEndPlate
# --------------------------------------------------------------------------- #


@part(
    category="Motion Kits/Plates",
    name="Rod End Plate",
    description="Upright end plate holding two smooth rods, with a foot to bolt down and either a NEMA motor face or a 608 idler bearing seat for the lead screw.",
    catalog_id="rod-end-plate",
    example={"rod": "8", "spacing": 80, "motor": True},
)
class RodEndPlate(Part):
    """End plate of a two-rod axis.

    Frame: the plate stands on ``z = 0`` with its outer face at ``x = 0`` and
    its inner face at ``x = thickness``; the rods leave the inner face along +X
    at ``y = -+spacing/2``, ``z = ROD_Z``. The foot (``FOOT_LENGTH`` long,
    ``FOOT_THICKNESS`` thick) sticks out on the inner side, one M5 hole under
    each rod. The drive axis (``y = 0``, ``z = ROD_Z``) carries the motor face
    (``motor=True``: boss hole + 4 tapped holes on the outer face) or a 608
    bearing seat for the lead screw end (``motor=False``).

    Args:
        rod: smooth rod diameter (mm); bearings are the matching LMxUU.
        spacing: distance between the two rod axes.
        thickness: plate thickness along the rods.
        motor: True for the motor end (NEMA face), False for the idler end (608 seat).
        nema: NEMA frame of the motor face (motor end only).
        lightening: cut a window through the plate on each side of the drive axis.
    """

    RODS: ClassVar[dict] = RODS
    NEMA: ClassVar[dict] = NEMA
    ROD_Z: ClassVar[float] = ROD_Z

    def __init__(
        self,
        rod: OneOf[RODS] = "8",
        spacing: Num(min=60, max=200, step=1) = 80,
        thickness: Num(min=8, max=20, step=1) = 10,
        motor: bool = False,
        nema: OneOf[NEMA] = "NEMA17",
        lightening: bool = True,
    ):
        r = _check_rod(rod)
        d, t, s = r["d"], float(thickness), float(spacing)
        m = NEMA[nema]
        if motor and s / 2 - d / 2 - 1 < m["body"] / 2:
            raise ValueError(
                f"spacing {spacing} too narrow for a {nema} between {rod} mm rods"
            )
        if t < SEAT_608["B"] + 1:
            raise ValueError("thickness must exceed the 608 seat depth + 1 mm")
        half_w = s / 2 + EDGE
        self.rod, self.spacing, self.thickness = str(rod), s, t
        self.motor, self.nema, self.width = bool(motor), nema, 2 * half_w

        _box(self, 0, t, -half_w, half_w, 0, PLATE_HEIGHT)
        _box(self, t, t + FOOT_LENGTH, -half_w, half_w, 0, FOOT_THICKNESS)
        foot_x = t + FOOT_LENGTH / 2
        for y in (-s / 2, s / 2):
            _hole_x(self, y, ROD_Z, d / 2, 0, t)
            _hole_z(self, foot_x, y, M5_CLEAR, 0, FOOT_THICKNESS)
        if motor:
            _hole_x(self, 0, ROD_Z, m["boss_d"] / 2 + 0.5, 0, t)
            hp = m["pitch"] / 2
            self.motor_holes = [
                (sy * hp, ROD_Z + sz * hp) for sy in (-1, 1) for sz in (-1, 1)
            ]
            for y, z in self.motor_holes:
                _hole_x(self, y, z, m["hole_d"] / 2 + 0.2, 0, t)
        else:
            self.motor_holes = []
            seat = t - SEAT_608["B"]
            _hole_x(self, 0, ROD_Z, SEAT_608["D"] / 2, seat, t)
            _hole_x(self, 0, ROD_Z, 5.0, 0, seat)
        if lightening:
            # Windows between the drive axis and each rod hole (clear of both).
            inner = (m["pitch"] / 2 + m["hole_d"] if motor else SEAT_608["D"] / 2) + 3
            outer = s / 2 - d / 2 - 3
            if outer - inner >= 5:
                for sy in (-1, 1):
                    y0, y1 = sorted((sy * inner, sy * outer))
                    _box(self, 0, t, y0, y1, 10, PLATE_HEIGHT - 10, cut=True)

        # Anchors (+Z of each = outward normal / mate direction):
        _anchor(self, "outer_face", (0, 0, ROD_Z), NX)
        _anchor(self, "inner_face", (t, 0, ROD_Z), PX)
        _anchor(self, "bottom", (t / 2 + FOOT_LENGTH / 2, 0, 0), NZ)
        _anchor(self, "drive_axis", (0, 0, ROD_Z), PX)
        for tag, y in (("a", -s / 2), ("b", s / 2)):
            # rod hole axis on the outer face, +X into the axis (rod end_a here)
            _anchor(self, f"rod_hole_{tag}", (0, y, ROD_Z), PX)
            _anchor(self, f"foot_hole_{tag}", (foot_x, y, FOOT_THICKNESS), PZ)
        if motor:
            # motor mount face on the outer face (motor ``mount_face`` mates here)
            _anchor(self, "motor_face", (0, 0, ROD_Z), NX)
            for i, (y, z) in enumerate(self.motor_holes):
                # screw head seats on the inner face
                _anchor(self, f"motor_hole_{i}", (t, y, z), PX)
        else:
            # 608 seat shoulder (bearing ``bottom`` mates here, axis along +X)
            _anchor(self, "bearing_seat", (t - SEAT_608["B"], 0, ROD_Z), PX)
        self.paint(PLATE_COLOR)


# --------------------------------------------------------------------------- #
# Carriages
# --------------------------------------------------------------------------- #


def _carriage_body(p, rod, spacing, length, top, lead_screw):
    """Shared block of Carriage / GantryCarriage: bearing bores along X at
    ``y = -+spacing/2`` on the rod plane (z = 0), optional lead-screw nut mount."""
    r = _check_rod(rod)
    s, L = float(spacing), float(length)
    if L < 2 * r["L"] + 2:
        raise ValueError(f"length {length} too short for two {r['bearing']} per rod")
    half_w = s / 2 + CARRIAGE_EDGE
    p.rod, p.spacing, p.length, p.width, p.top = str(rod), s, L, 2 * half_w, top
    p.bearing = r["bearing"]
    _box(p, -L / 2, L / 2, -half_w, half_w, -CARRIAGE_BELOW, top)
    for y in (-s / 2, s / 2):
        _hole_x(p, y, 0, r["D"] / 2, -L / 2, L / 2)
    _anchor(p, "top", (0, 0, top), PZ)
    _anchor(p, "bottom", (0, 0, -CARRIAGE_BELOW), NZ)
    i = 0
    for x0, normal in ((-L / 2, PX), (L / 2, NX)):
        for y in (-s / 2, s / 2):
            # pocket mouth: a bearing's ``end_a`` mates here, axis into the block
            _anchor(p, f"bearing_pocket_{i}", (x0, y, 0), normal)
            i += 1
    for tag, y in (("a", -s / 2), ("b", s / 2)):
        _anchor(p, f"rod_axis_{tag}", (0, y, 0), PX)
    if lead_screw:
        _hole_x(p, 0, 0, NUT_BORE / 2, -L / 2, L / 2)
        _anchor(p, "nut_face", (-L / 2, 0, 0), NX)
        for j, (y, z) in enumerate(nut_hole_offsets()):
            _hole_x(p, y, z, M4_TAP, -L / 2, -L / 2 + 10)
            _anchor(p, f"nut_hole_{j}", (-L / 2, y, z), NX)


@part(
    category="Motion Kits/Carriages",
    name="Carriage",
    description="Carriage block riding two smooth rods on four LMxUU bearings, with top mounting holes, an optional lead-screw nut mount and an optional belt clamp.",
    catalog_id="motion-carriage",
    example={"rod": "8", "spacing": 80, "length": 70},
)
class Carriage(Part):
    """Carriage of a two-rod axis.

    Frame: origin on the rod plane, centred between the rods (place it at
    ``z = ROD_Z`` over the plates' base); rods along X. The block spans
    ``x = -+length/2``, ``z = -CARRIAGE_BELOW .. CARRIAGE_ABOVE``. Four bearing
    pockets (``bearing_pocket_0..3``) take one LMxUU from each end of each
    bore. ``lead_screw=True`` bores the centre for a T8 screw with the brass
    nut's four M4 holes on the -X face; ``belt_clamp=True`` adds a clamp block
    on top whose slot holds the belt run of 20T GT2 pulleys centred on
    ``y = 0`` (``belt_clamp`` anchor).

    Args:
        rod: smooth rod diameter (mm); bearings are the matching LMxUU.
        spacing: distance between the two rod axes.
        length: block length along the rods (fits two bearings per rod).
        belt_clamp: add the GT2 belt clamp on top.
        lead_screw: bore for a T8 lead screw + nut mount on the -X face.
        camera_mount: a camera plate on top (1/4"-20 hole), unless belt_clamp.
    """

    RODS: ClassVar[dict] = RODS

    def __init__(
        self,
        rod: OneOf[RODS] = "8",
        spacing: Num(min=40, max=200, step=1) = 80,
        length: Num(min=62, max=150, step=1) = 70,
        belt_clamp: bool = False,
        lead_screw: bool = False,
        camera_mount: bool = True,
    ):
        _carriage_body(self, rod, spacing, length, CARRIAGE_ABOVE, lead_screw)
        self.belt_clamp, self.lead_screw = bool(belt_clamp), bool(lead_screw)
        self.camera_mount = bool(camera_mount) and not self.belt_clamp
        L = self.length
        self.mount_holes = [
            (sx * (L / 2 - 10), sy * 15.0) for sx in (-1, 1) for sy in (-1, 1)
        ]
        for i, (x, y) in enumerate(self.mount_holes):
            _hole_z(self, x, y, M4_TAP, CARRIAGE_ABOVE - 8, CARRIAGE_ABOVE)
            _anchor(self, f"mount_hole_{i}", (x, y, CARRIAGE_ABOVE), PZ)
        if belt_clamp:
            top = CARRIAGE_ABOVE + 12
            _box(self, -12, 12, BELT_Y - 8, BELT_Y + 8, CARRIAGE_ABOVE, top)
            _box(
                self, -13, 13, BELT_Y - 1, BELT_Y + 1, CARRIAGE_ABOVE + 3, top, cut=True
            )
            for x in (-7.0, 7.0):
                _hole_z(self, x, BELT_Y + 5, M3_CLEAR, CARRIAGE_ABOVE, top)
            # belt centre line in the slot, +X along the belt
            _anchor(self, "belt_clamp", (0, BELT_Y, BELT_Z), PX)
        elif camera_mount:
            # Camera plate: 50 x 50 x 6 on top, 1/4"-20 clearance + two M3 pins.
            top = CARRIAGE_ABOVE + 6
            _box(self, -25, 25, -25, 25, CARRIAGE_ABOVE, top)
            _hole_z(self, 0, 0, 3.35, CARRIAGE_ABOVE, top)
            for y in (-16.0, 16.0):
                _hole_z(self, 0, y, M3_CLEAR, CARRIAGE_ABOVE, top)
            _anchor(self, "camera", (0, 0, top), PZ)
        self.paint(CARRIAGE_COLOR)


@part(
    category="Motion Kits/Carriages",
    name="Gantry Carriage",
    description="Y-axis carriage of an XY gantry: rides two Y rods on four LMxUU bearings, is driven by a T8 lead screw, and holds the two X rods plus side holes for a motor or idler bracket.",
    catalog_id="gantry-carriage",
    example={"rod": "8", "spacing": 60, "length": 90, "x_rod": "8", "x_spacing": 60},
)
class GantryCarriage(Part):
    """Gantry (Y) carriage that carries the X axis.

    Frame: like :class:`Carriage` (own rods along local X, origin on their
    plane); install it with a 90 deg rotation about Z to ride rods along Y.
    The X rods pass through it along local Y at ``x = -+x_spacing/2``,
    ``z = X_ROD_Z``; both side faces (``y = -+width/2``) carry two M5 holes
    ``SIDE_HOLE_X`` either side of centre at the X rod height, for a
    :class:`MotorMount`.

    Args:
        rod: Y rod diameter (mm); bearings are the matching LMxUU.
        spacing: distance between the two Y rod axes.
        length: block length along the Y rods.
        x_rod: X rod diameter (mm).
        x_spacing: distance between the two X rod axes.
        lead_screw: bore for a T8 lead screw + nut mount on the -X face.
    """

    RODS: ClassVar[dict] = RODS

    def __init__(
        self,
        rod: OneOf[RODS] = "8",
        spacing: Num(min=40, max=200, step=1) = 60,
        length: Num(min=80, max=160, step=1) = 90,
        x_rod: OneOf[RODS] = "8",
        x_spacing: Num(min=50, max=140, step=1) = 60,
        lead_screw: bool = True,
    ):
        xr = _check_rod(x_rod)
        top = X_ROD_Z + 6.0 + 8.0
        if float(length) < float(x_spacing) + 24:
            raise ValueError("length must exceed x_spacing + 24 mm")
        _carriage_body(self, rod, spacing, length, top, lead_screw)
        self.x_rod, self.x_spacing = str(x_rod), float(x_spacing)
        self.lead_screw = bool(lead_screw)
        hw = self.width / 2
        xs = self.x_spacing / 2
        for tag, x in (("a", -xs), ("b", xs)):
            _hole_y(self, x, X_ROD_Z, xr["d"] / 2, -hw, hw)
            # rod hole mouth on the +Y side face, axis into the block (-Y)
            _anchor(self, f"x_rod_hole_{tag}", (x, hw, X_ROD_Z), NY)
        self.side_holes = []
        for side, y0, y1, normal in (("p", hw - 10, hw, PY), ("n", -hw, -hw + 10, NY)):
            _anchor(self, f"side_face_{side}", (0, normal[1] * hw, X_ROD_Z), normal)
            for i, x in enumerate((-SIDE_HOLE_X, SIDE_HOLE_X)):
                _hole_y(self, x, X_ROD_Z, M5_TAP, y0, y1)
                _anchor(
                    self, f"side_hole_{side}{i}", (x, normal[1] * hw, X_ROD_Z), normal
                )
        self.paint(CARRIAGE_COLOR)


# --------------------------------------------------------------------------- #
# MotorMount
# --------------------------------------------------------------------------- #


@part(
    category="Motion Kits/Brackets",
    name="Motor Mount (L-bracket)",
    description="L-bracket holding a NEMA stepper shaft-up under its horizontal leg (or an idler pulley on an M5 screw), bolted by its vertical leg to a face.",
    catalog_id="motor-mount-l-bracket",
    example={"nema": "NEMA17"},
)
class MotorMount(Part):
    """NEMA motor L-bracket.

    Frame: vertical leg ``x = 0 .. thickness`` (its back at ``x = 0`` is the
    mounting face, two M5 clearance holes at ``y = -+SIDE_HOLE_X``,
    ``z = 10``), ``z = 0 .. height``; horizontal leg on top
    (``z = height - thickness .. height``) reaching out along +X. The motor
    hangs under it, axis at ``x = motor_x`` (clear of the mounting screw
    heads), shaft up through the boss hole. With ``motor=False`` the
    horizontal leg has an M5 hole on that axis for an idler pulley instead.

    Args:
        nema: NEMA frame size (``StepperMotor.TABLE``).
        thickness: plate thickness of both legs.
        height: vertical leg height (mounting holes 10 mm above its bottom).
        motor: True: motor boss + 4 holes; False: M5 idler hole.
    """

    NEMA: ClassVar[dict] = NEMA
    HOLE_Z: ClassVar[float] = 10.0

    def __init__(
        self,
        nema: OneOf[NEMA] = "NEMA17",
        thickness: Num(min=3, max=10, step=0.5) = 5,
        height: Num(min=25, max=80, step=0.5) = 32.5,
        motor: bool = True,
    ):
        m = NEMA[nema]
        t, H = float(thickness), float(height)
        if H < t + 15:
            raise ValueError("height must exceed thickness + 15 mm")
        body = m["body"]
        half_w = body / 2 + 4
        mx = t + 7 + body / 2
        reach = mx + body / 2 + 4
        self.nema, self.thickness, self.height, self.motor = nema, t, H, bool(motor)
        self.motor_x, self.reach, self.width = mx, reach, 2 * half_w

        _box(self, 0, t, -half_w, half_w, 0, H)
        _box(self, t, reach, -half_w, half_w, H - t, H)
        for y in (-SIDE_HOLE_X, SIDE_HOLE_X):
            _hole_x(self, y, self.HOLE_Z, M5_CLEAR, 0, t)
        hp = m["pitch"] / 2
        self.motor_holes = (
            [(mx + sx * hp, sy * hp) for sx in (-1, 1) for sy in (-1, 1)]
            if motor
            else []
        )
        if motor:
            _hole_z(self, mx, 0, m["boss_d"] / 2 + 0.5, H - t, H)
            for x, y in self.motor_holes:
                _hole_z(self, x, y, m["hole_d"] / 2 + 0.2, H - t, H)
        else:
            _hole_z(self, mx, 0, M5_CLEAR, H - t, H)

        _anchor(self, "mount_face", (0, 0, self.HOLE_Z), NX)
        for i, y in enumerate((-SIDE_HOLE_X, SIDE_HOLE_X)):
            _anchor(self, f"mount_hole_{i}", (0, y, self.HOLE_Z), NX)
            # screw head seat on the inner face of the leg
            _anchor(self, f"mount_screw_{i}", (t, y, self.HOLE_Z), PX)
        # shaft / idler axis on top of the horizontal leg (pulley ``bottom`` here)
        _anchor(self, "axis", (mx, 0, H), PZ)
        if motor:
            # underside: a StepperMotor's ``mount_face`` mates here
            _anchor(self, "motor_face", (mx, 0, H - t), NZ)
            for i, (x, y) in enumerate(self.motor_holes):
                _anchor(self, f"motor_hole_{i}", (x, y, H), PZ)
        else:
            _anchor(self, "nut_seat", (mx, 0, H - t), NZ)
        self.paint(BRACKET_COLOR)
