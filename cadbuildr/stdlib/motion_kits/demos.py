"""Placement tables for two click-built demos: a linear stage and an XY gantry.

Each ``*_layout()`` returns::

    {
      "inputs":   {name: {"widget": {...}, "default": value}},   # promotable inputs
      "items":    [{"name", "item": "stdlib:<Cls>", "inputs": {...},
                    "translate": [x, y, z],
                    "rotate": {"axis": "X" | "Y" | "Z", "angle": deg} | None,
                    "mates": [names of items it is meant to sit in / bolt into]}],
      "bindings": [{"input", "widget", "default", "targets": [...], "moves": [...]}],
    }

A placement is what the viewer's Library panel can do: rotate the component
about its own origin by ONE angle about X, Y or Z, then translate it (assembly
frame, mm). Parts are either axisymmetric stdlib parts built along +Z (the
rotation only picks the axis direction, see :func:`axis_rotation`) or motion
kit parts modelled in their installed pose (a rotation about Z at most).

``bindings`` say which component inputs follow a promoted top-level input and
are derived by re-running the layout with that input changed:

* ``targets``: ``{"index", "name", "input"}`` -- the component input takes the
  promoted value; ``"offset": k`` means value + k (a lead screw is the rail
  length minus the coupling stick-out); ``"map": {option: value}`` means the
  value is looked up (``rod: "8"`` -> bearing ``model: "LM8UU"``).
* ``moves``: ``{"index", "name", "per_unit": [dx, dy, dz]}`` -- the
  component's translation changes by that much per unit of the input (the far
  end plate follows ``rail_length``). Viewers that only bind equal values can
  use the direct targets and treat the rest as a checklist.

``build_linear_stage()`` / ``build_xy_gantry()`` construct the same assembly in
code from the table (``add_component(part, at=..., rot_deg=...)``).
"""

from __future__ import annotations

import copy
from typing import Any, Callable, Dict, List, Optional

from cadbuildr.foundation import Assembly, StringParameter
from cadbuildr.foundation.library import find_item
from cadbuildr.foundation.library.evaluate import resolve_item
from cadbuildr.foundation.library.registry import call_configurable

from .parts import (
    BELT_Z,
    CARRIAGE_EDGE,
    FOOT_LENGTH,
    FOOT_THICKNESS,
    NEMA,
    ROD_Z,
    RODS,
    SIDE_HOLE_X,
    X_ROD_Z,
    nut_hole_offsets,
)

__all__ = [
    "axis_rotation",
    "build_from_layout",
    "build_linear_stage",
    "build_xy_gantry",
    "check_layout_interference",
    "linear_stage_layout",
    "xy_gantry_layout",
]

# Rotation taking a part's +Z axis onto a direction (one axis, one angle).
_AXIS_ROT = {
    "+Z": None,
    "-Z": {"axis": "X", "angle": 180.0},
    "+X": {"axis": "Y", "angle": 90.0},
    "-X": {"axis": "Y", "angle": -90.0},
    "+Y": {"axis": "X", "angle": -90.0},
    "-Y": {"axis": "X", "angle": 90.0},
}

# Hardware constants of the stdlib parts the layouts use.
MOTOR_BODY = 40.0  # StepperMotor body_length
MOTOR_SHAFT = 24.0  # StepperMotor shaft_length
COUPLING = {"bore_a": 5, "bore_b": 8, "length": 25}
SCREW_START = MOTOR_SHAFT  # lead screw end_a sits mid-coupling = at the shaft tip
NUT_FLANGE = 3.5  # LeadScrewNutT8.FLANGE_H
T_NUT_H = 3.2  # TSlotNut flange + neck
PULLEY = {"teeth": 20, "bore": 5, "belt_width": 6}
PULLEY_BELT = 4.0  # GT2Pulley belt_plane height above its bottom
PULLEY_H = 8.0  # GT2Pulley total height
M5_NUT_H = 4.0  # HexNut M5 thickness
BRACKET_T = 5.0  # MotorMount thickness


def axis_rotation(direction: str) -> Optional[Dict[str, Any]]:
    """The single rotation pointing a +Z-built part along ``direction``."""
    return copy.deepcopy(_AXIS_ROT[direction])


def _rz(angle: float) -> Optional[Dict[str, Any]]:
    angle = (float(angle) + 180.0) % 360.0 - 180.0  # (-180, 180]
    if angle == -180.0:
        angle = 180.0
    return {"axis": "Z", "angle": angle} if angle else None


class _Layout:
    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []

    def add(self, name, cls, inputs, translate, rotate=None, mates=()):
        self.items.append(
            {
                "name": name,
                "item": f"stdlib:{cls}",
                "inputs": dict(inputs),
                "translate": [round(float(v), 6) + 0.0 for v in translate],
                "rotate": rotate,
                "mates": list(mates),
            }
        )
        return name

    def screw(self, name, size, length, seat, direction, mates=()):
        """A DIN912 whose head seat is at ``seat`` and whose shank points along
        ``direction`` (the screw's own +Z, tip -> head, is the opposite)."""
        back = {"+X": "-X", "-X": "+X", "+Y": "-Y", "-Y": "+Y", "+Z": "-Z", "-Z": "+Z"}
        axis = back[direction]
        sign = -1.0 if axis[0] == "-" else 1.0
        i = "XYZ".index(axis[1])
        tip = list(seat)
        tip[i] -= sign * length  # tip = seat - length along the screw's +Z
        return self.add(
            name,
            "DIN912Screw",
            {"size": size, "length": length, "with_thread": False},
            tip,
            axis_rotation(axis),
            mates,
        )


# --------------------------------------------------------------------------- #
# A two-rod lead-screw axis (the linear stage; also each gantry Y side)
# --------------------------------------------------------------------------- #


def _rod_axis(
    lay: _Layout,
    prefix: str,
    rod: str,
    length: float,
    spacing: float,
    origin: tuple,
    along: str,
    carriage: Dict[str, Any],
    carriage_at: float,
    base_rails: bool,
    motor_screws: int = 4,
) -> str:
    """Plates, rods, motor, coupling, lead screw, idler bearing, carriage,
    bearings and nut of one axis running from ``origin`` along ``along``
    (``"X"`` or ``"Y"``). Returns the carriage's item name."""
    ox, oy, oz = origin
    t = 10.0
    s = float(spacing)
    bearing = RODS[rod]["bearing"]

    def at(u, v, z):
        """Axis frame (u along the rods, v across, z up) -> assembly."""
        if along == "X":
            return (ox + u, oy + v, oz + z)
        return (ox - v, oy + u, oz + z)

    fwd = "+" + along
    rev = "-" + along
    plate_rz = 0.0 if along == "X" else 90.0  # parts modelled along +X

    near = lay.add(
        f"{prefix}plate_motor",
        "RodEndPlate",
        {"rod": rod, "spacing": s, "thickness": t, "motor": True, "nema": "NEMA17"},
        at(0, 0, 0),
        _rz(plate_rz),
    )
    far = lay.add(
        f"{prefix}plate_idler",
        "RodEndPlate",
        {"rod": rod, "spacing": s, "thickness": t, "motor": False, "nema": "NEMA17"},
        at(length, 0, 0),
        _rz(plate_rz + 180.0),
    )
    for tag, v in (("a", -s / 2), ("b", s / 2)):
        lay.add(
            f"{prefix}rod_{tag}",
            "SmoothRod",
            {"diameter": rod, "length": length},
            at(0, v, ROD_Z),
            axis_rotation(fwd),
            mates=[near, far],
        )
    motor = lay.add(
        f"{prefix}motor",
        "StepperMotor",
        {"frame": "NEMA17", "body_length": MOTOR_BODY, "shaft_length": MOTOR_SHAFT},
        at(-MOTOR_BODY, 0, ROD_Z),
        axis_rotation(fwd),
        mates=[near],
    )
    hp = NEMA["NEMA17"]["pitch"] / 2
    i = 0
    for sv in (-1, 1):
        for sz in (-1, 1):
            if motor_screws == 2 and sv != sz:
                i += 1
                continue  # two diagonal screws
            lay.screw(
                f"{prefix}motor_screw_{i}",
                "M3",
                12,
                at(t, sv * hp, ROD_Z + sz * hp),
                rev,
                mates=[near, motor],
            )
            i += 1
    coupling_at = MOTOR_SHAFT - COUPLING["length"] / 2
    coupling = lay.add(
        f"{prefix}coupling",
        "ClampCoupling",
        COUPLING,
        at(coupling_at, 0, ROD_Z),
        axis_rotation(fwd),
        mates=[motor],
    )
    lay.add(
        f"{prefix}idler_bearing",
        "DeepGrooveBearing",
        {"model": "608"},
        at(length - t, 0, ROD_Z),
        axis_rotation(fwd),
        mates=[far],
    )
    screw = lay.add(
        f"{prefix}lead_screw",
        "LeadScrewT8",
        {"length": length - SCREW_START, "with_thread": False},
        at(SCREW_START, 0, ROD_Z),
        axis_rotation(fwd),
        mates=[coupling, far, f"{prefix}idler_bearing"],
    )

    # Carriage on the rods, nut on its motor-side face.
    cls = carriage.pop("cls")
    c_len = float(carriage["length"])
    car = lay.add(
        f"{prefix}carriage",
        cls,
        carriage,
        at(carriage_at, 0, ROD_Z),
        _rz(plate_rz),
        mates=[screw, f"{prefix}rod_a", f"{prefix}rod_b"],
    )
    for k, (u, d) in enumerate(((-c_len / 2, fwd), (c_len / 2, rev))):
        for tag, v in (("a", -s / 2), ("b", s / 2)):
            lay.add(
                f"{prefix}bearing_{k}{tag}",
                "LinearBearing",
                {"model": bearing},
                at(carriage_at + u, v, ROD_Z),
                axis_rotation(d),
                mates=[car, f"{prefix}rod_{tag}"],
            )
    nut_u = carriage_at - c_len / 2 - NUT_FLANGE
    nut = lay.add(
        f"{prefix}nut",
        "LeadScrewNutT8",
        {"with_thread": False},
        at(nut_u, 0, ROD_Z),
        axis_rotation(fwd),
        mates=[car, screw],
    )
    for j, (v, z) in enumerate(nut_hole_offsets()):
        if j not in (0, 3):  # two diagonal screws hold a T8 nut
            continue
        lay.screw(
            f"{prefix}nut_screw_{j}",
            "M4",
            10,
            at(nut_u, v, ROD_Z + z),
            fwd,
            # bounding boxes of the heads graze the screw's (0.5 mm real gap)
            mates=[nut, car, screw],
        )

    # Foot screws into T-nuts in the 2020 rail under each rod.
    foot_u = t + FOOT_LENGTH / 2
    for end, u, plate in (("m", foot_u, near), ("i", length - foot_u, far)):
        for tag, v in (("a", -s / 2), ("b", s / 2)):
            rail = f"{prefix}rail_{tag}" if base_rails else None
            tnut = lay.add(
                f"{prefix}t_nut_{end}{tag}",
                "TSlotNut",
                {"size": "M5", "with_thread": False},
                at(u, v, -T_NUT_H),
                _rz(90.0) if along == "X" else None,  # flange across the slot
                mates=[rail] if rail else [],
            )
            lay.screw(
                f"{prefix}foot_screw_{end}{tag}",
                "M5",
                10,
                at(u, v, FOOT_THICKNESS),
                "-Z",
                mates=[plate, tnut] + ([rail] if rail else []),
            )
    return car


def _rail(lay, name, length, start, along, mates=()):
    """A 2020 rail whose top face is at the ``start`` z, running along ``along``."""
    x, y, z = start
    if along == "X":  # Ry(90): profile x -> -Z
        return lay.add(
            name,
            "AluExtrusion",
            {"series": "2020", "length": length},
            (x, y, z - 10),
            axis_rotation("+X"),
            mates,
        )
    return lay.add(  # Rx(-90): profile y -> -Z
        name,
        "AluExtrusion",
        {"series": "2020", "length": length},
        (x, y, z - 10),
        axis_rotation("+Y"),
        mates,
    )


# --------------------------------------------------------------------------- #
# Layouts
# --------------------------------------------------------------------------- #

_ROD_WIDGET = {"kind": "enum", "options": list(RODS), "default": "8"}


def _num(default, lo, hi, step=1):
    return {
        "kind": "number",
        "integer": False,
        "default": default,
        "unit": "mm",
        "min": lo,
        "max": hi,
        "step": step,
    }


STAGE_INPUTS = {
    "rod": _ROD_WIDGET,
    "rail_length": _num(400, 200, 1000, 10),
    "spacing": _num(80, 58, 200, 1),
}


def _stage_items(rod="8", rail_length=400, spacing=80) -> List[Dict[str, Any]]:
    lay = _Layout()
    L, s = float(rail_length), float(spacing)
    for tag, v in (("a", -s / 2), ("b", s / 2)):
        _rail(lay, f"rail_{tag}", L, (0, v, 0), "X")
    _rod_axis(
        lay,
        "",
        str(rod),
        L,
        s,
        (0.0, 0.0, 0.0),
        "X",
        {
            "cls": "Carriage",
            "rod": str(rod),
            "spacing": s,
            "length": 70,
            "belt_clamp": False,
            "lead_screw": True,
        },
        L / 2,
        base_rails=True,
    )
    return lay.items


GANTRY_INPUTS = {
    "rod": _ROD_WIDGET,
    "y_length": _num(400, 250, 1000, 10),
    "x_length": _num(400, 250, 1000, 10),
    "spacing": _num(60, 58, 200, 1),
    "x_spacing": _num(60, 50, 66, 1),
}


def _gantry_items(
    rod="8", y_length=400, x_length=400, spacing=60, x_spacing=60
) -> List[Dict[str, Any]]:
    lay = _Layout()
    rod = str(rod)
    Ly, Lx, s, xs = float(y_length), float(x_length), float(spacing), float(x_spacing)
    gc_len = 90.0
    gc_w = s + 2 * CARRIAGE_EDGE  # GantryCarriage width across its Y rods
    xL, xR = 0.0, Lx - gc_w  # Y side centre lines
    yc = Ly / 2  # gantry position along Y
    zx = ROD_Z + X_ROD_Z  # X rod height

    # Frame: two 2020 cross rails under four Y rails (one under each Y rod).
    x0, x1 = xL - s / 2 - 10, xR + s / 2 + 10
    for tag, y in (("front", 10.0), ("back", Ly - 10.0)):
        _rail(lay, f"cross_rail_{tag}", x1 - x0, (x0, y, -20.0), "X")
    sides = {}
    for side, xc in (("left", xL), ("right", xR)):
        for tag, dx in (("a", s / 2), ("b", -s / 2)):
            _rail(
                lay,
                f"{side}_rail_{tag}",
                Ly,
                (xc + dx, 0.0, 0.0),
                "Y",
                mates=["cross_rail_front", "cross_rail_back"],
            )
        sides[side] = _rod_axis(
            lay,
            f"{side}_",
            rod,
            Ly,
            s,
            (xc, 0.0, 0.0),
            "Y",
            {
                "cls": "GantryCarriage",
                "rod": rod,
                "spacing": s,
                "length": gc_len,
                "x_rod": rod,
                "x_spacing": xs,
                "lead_screw": True,
            },
            yc,
            base_rails=True,
            motor_screws=2,
        )

    # X axis: two rods through both gantry carriages, belt-driven carriage.
    for tag, y in (("a", yc - xs / 2), ("b", yc + xs / 2)):
        lay.add(
            f"x_rod_{tag}",
            "SmoothRod",
            {"diameter": rod, "length": Lx},
            (xL - gc_w / 2, y, zx),
            axis_rotation("+X"),
            mates=[sides["left"], sides["right"]],
        )
    xc = (xL + xR) / 2
    c_len = 70.0
    car = lay.add(
        "x_carriage",
        "Carriage",
        {
            "rod": rod,
            "spacing": xs,
            "length": c_len,
            "belt_clamp": False,
            "lead_screw": False,
        },
        (xc, yc, zx),
        None,
        mates=["x_rod_a", "x_rod_b"],
    )
    for k, (u, d) in enumerate(((-c_len / 2, "+X"), (c_len / 2, "-X"))):
        for tag, v in (("a", -xs / 2), ("b", xs / 2)):
            lay.add(
                f"x_bearing_{k}{tag}",
                "LinearBearing",
                {"model": RODS[rod]["bearing"]},
                (xc + u, yc + v, zx),
                axis_rotation(d),
                mates=[car, f"x_rod_{tag}"],
            )

    # Belt plane = the carriage clamp slot centre; pulleys sit on the bracket.
    belt_z = zx + BELT_Z
    plate_top = belt_z - PULLEY_BELT - 0.5
    bracket_h = plate_top - (zx - 10.0)  # mounting holes at the X rod height
    body = NEMA["NEMA17"]["body"]
    motor_x = BRACKET_T + 7 + body / 2  # MotorMount.motor_x
    for side, sign in (("left", -1.0), ("right", 1.0)):
        face_x = (xL if side == "left" else xR) + sign * gc_w / 2
        motor = side == "left"
        bracket = lay.add(
            f"x_{'motor' if motor else 'idler'}_bracket",
            "MotorMount",
            {
                "nema": "NEMA17",
                "thickness": BRACKET_T,
                "height": bracket_h,
                "motor": motor,
            },
            (face_x, yc, zx - 10.0),
            _rz(180.0) if side == "left" else None,
            mates=[sides[side]],
        )
        for i, dy in enumerate((-SIDE_HOLE_X, SIDE_HOLE_X)):
            lay.screw(
                f"x_{side}_bracket_screw_{i}",
                "M5",
                12,
                (face_x + sign * BRACKET_T, yc + dy, zx),
                "-X" if side == "right" else "+X",
                mates=[bracket, sides[side]],
            )
        ax = face_x + sign * motor_x
        if motor:
            m = lay.add(
                "x_motor",
                "StepperMotor",
                {
                    "frame": "NEMA17",
                    "body_length": MOTOR_BODY,
                    "shaft_length": MOTOR_SHAFT,
                },
                (ax, yc, plate_top - BRACKET_T - MOTOR_BODY),
                None,
                mates=[bracket],
            )
            hp = NEMA["NEMA17"]["pitch"] / 2
            i = 0
            for sx in (-1, 1):
                for sy in (-1, 1):
                    lay.screw(
                        f"x_motor_screw_{i}",
                        "M3",
                        8,
                        (ax + sx * hp, yc + sy * hp, plate_top),
                        "-Z",
                        mates=[bracket, m],
                    )
                    i += 1
            lay.add(
                "x_pulley",
                "GT2Pulley",
                PULLEY,
                (ax, yc, plate_top + 0.5),
                None,
                mates=[m],
            )
        else:
            pulley = lay.add(
                "x_idler_pulley", "GT2Pulley", PULLEY, (ax, yc, plate_top + 0.5)
            )
            nut = lay.add(
                "x_idler_nut",
                "HexNut",
                {"size": "M5", "with_thread": False},
                (ax, yc, plate_top - BRACKET_T - M5_NUT_H),
                None,
            )
            lay.screw(
                "x_idler_screw",
                "M5",
                20,
                (ax, yc, plate_top + 0.5 + PULLEY_H),
                "-Z",
                mates=[pulley, bracket, nut],
            )
    return lay.items


# --------------------------------------------------------------------------- #
# Bindings
# --------------------------------------------------------------------------- #


def _derive_bindings(
    fn: Callable[..., List[Dict[str, Any]]], spec: Dict[str, Dict[str, Any]], values
) -> List[Dict[str, Any]]:
    base = fn(**values)
    out = []
    for name, widget in spec.items():
        targets: Dict[tuple, Dict[str, Any]] = {}
        moves: List[Dict[str, Any]] = []
        if widget["kind"] == "enum":
            for option in widget["options"]:
                other = fn(**{**values, name: option})
                for i, (a, b) in enumerate(zip(base, other)):
                    for key, bv in b["inputs"].items():
                        if a["inputs"].get(key) != bv:
                            t = targets.setdefault(
                                (i, key),
                                {
                                    "index": i,
                                    "name": a["name"],
                                    "input": key,
                                    "map": {},
                                },
                            )
                            t["map"][option] = bv
                    if a["translate"] != b["translate"]:
                        raise ValueError(f"{name}={option} moves {a['name']}")
            for (i, key), t in targets.items():
                t["map"][values[name]] = base[i]["inputs"][key]
                if all(str(k) == str(v) for k, v in t["map"].items()):
                    del t["map"]  # the component input takes the value as is
        else:
            delta = 1.0
            v0 = float(values[name])
            other = fn(**{**values, name: v0 + delta})
            for i, (a, b) in enumerate(zip(base, other)):
                for key, bv in b["inputs"].items():
                    av = a["inputs"].get(key)
                    if av == bv:
                        continue
                    if abs((float(bv) - float(av)) - delta) > 1e-9:
                        raise ValueError(f"{a['name']}.{key} is not {name} + k")
                    t = {"index": i, "name": a["name"], "input": key}
                    offset = round(float(av) - v0, 6)
                    if offset:
                        t["offset"] = offset
                    targets[(i, key)] = t
                if a["translate"] != b["translate"]:
                    per = [
                        round((q - p) / delta, 6) + 0.0
                        for p, q in zip(a["translate"], b["translate"])
                    ]
                    moves.append({"index": i, "name": a["name"], "per_unit": per})
        out.append(
            {
                "input": name,
                "widget": widget,
                "default": values[name],
                "targets": list(targets.values()),
                "moves": moves,
            }
        )
    return out


def _layout(fn, spec, values):
    values = {k: values.get(k, w["default"]) for k, w in spec.items()}
    return {
        "inputs": {k: {"widget": w, "default": values[k]} for k, w in spec.items()},
        "items": fn(**values),
        "bindings": _derive_bindings(fn, spec, values),
    }


def linear_stage_layout(**values) -> Dict[str, Any]:
    """Lead-screw linear stage (camera slider): two 2020 base rails, motor and
    idler end plates, two rods, a carriage on four LMxUU, NEMA 17 + coupling +
    T8 screw, 608 idler bearing and the screws / T-nuts holding it together.

    Keyword overrides: ``rod`` ("8" | "10" | "12"), ``rail_length`` (rod and
    rail length, mm), ``spacing`` (rod spacing, mm)."""
    return _layout(_stage_items, STAGE_INPUTS, values)


def xy_gantry_layout(**values) -> Dict[str, Any]:
    """XY gantry / small CNC frame: a 2020 frame, two lead-screw Y sides
    (the linear stage, turned along Y) whose GantryCarriages hold the two X
    rods, and a belt-driven X carriage (NEMA 17 + GT2 pulley on a MotorMount,
    idler pulley on a second MotorMount).

    Keyword overrides: ``rod``, ``y_length`` (Y rods / rails), ``x_length``
    (X rods), ``spacing`` (Y rod spacing), ``x_spacing`` (X rod spacing)."""
    return _layout(_gantry_items, GANTRY_INPUTS, values)


# --------------------------------------------------------------------------- #
# Build in code
# --------------------------------------------------------------------------- #


def _rot_deg(rotate: Optional[Dict[str, Any]]):
    if not rotate:
        return None
    angles = [0.0, 0.0, 0.0]
    angles["XYZ".index(rotate["axis"])] = float(rotate["angle"])
    return tuple(angles)


def build_from_layout(layout: Dict[str, Any]) -> Assembly:
    """An Assembly with every layout item built (``Cls(**inputs)``) and placed."""
    asm = Assembly()
    for entry in layout["items"]:
        item = find_item(entry["item"]) or resolve_item(entry["item"])
        component = call_configurable(item, entry["inputs"])
        component.name = StringParameter(value=entry["name"])
        asm.add_component(
            component, at=tuple(entry["translate"]), rot_deg=_rot_deg(entry["rotate"])
        )
    return asm


def build_linear_stage(**values) -> Assembly:
    return build_from_layout(linear_stage_layout(**values))


def build_xy_gantry(**values) -> Assembly:
    return build_from_layout(xy_gantry_layout(**values))


def check_layout_interference(
    layout: Dict[str, Any], assembly: Optional[Assembly] = None
):
    """Bounding-box interference of a layout's assembly, with the intended
    contacts (each item's ``mates``: a rod in its plate, a bearing in its
    carriage, a screw in what it bolts) allowed. Call it before serialising the
    assembly. Returns the remaining overlaps (should be empty)."""
    asm = assembly or build_from_layout(layout)
    allow = [(e["name"], m) for e in layout["items"] for m in e["mates"]]
    found = asm.check_interference(allow=allow, include_unknown=False)
    return [i for i in found if i.status == "overlap"]
