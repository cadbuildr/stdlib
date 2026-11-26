"""Two click-built demos as connect sequences: a linear stage and an XY gantry.

Each ``*_layout()`` returns::

    {
      "inputs":   {name: {"widget": {...}, "default": value}},   # promotable inputs
      "bindings": {name: [[item, component input], ...]},       # equal values only
      "items":    [{"name", "item": "stdlib:<Cls>", "inputs": {...},
                    "connect": {"own": <interface>, "target": [<earlier item>, <interface>],
                                "dof": {...}} | None,
                    "fill_group"?: <group of the target: one part per member>}],
      "loops":    [{"a": [item, interface], "b": [item, interface], "dof": {}}],
    }

That is what the viewer's *insert & connect* records: no positions. The
first item (the motor end plate) is grounded; every other part is placed by
the joint its interfaces' mate rule gives (``RodEnd`` into a ``RodHole``, a
``BearingFace`` sliding on a ``RodAxis``, a ``ScrewHead`` on a
``ScrewHole``...), so lengths drive positions through the chain: the idler
plate hangs from the rods' ``end_b``, so ``rail_length`` moves it, and the
carriage rides its first bearing, whose slider offset is a joint value.
``loops`` are the redundant contacts, checked when the assembly is built
(the idler plate on the second rod and on the rails, bearings on the second
rod, the nut on the lead screw...): a size that does not fit raises
``LoopMismatch`` naming the inputs that disagree.

``build_linear_stage()`` / ``build_xy_gantry()`` build them with
``ground`` / ``connect`` / ``connect_all`` (:func:`build_layout`).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from cadbuildr.foundation import Assembly
from cadbuildr.foundation.library.layout import build_layout, derive_bindings

from .parts import BELT_Z, CARRIAGE_EDGE, FOOT_LENGTH, ROD_Z, RODS, X_ROD_Z

__all__ = [
    "build_from_layout",
    "build_linear_stage",
    "build_xy_gantry",
    "check_layout_interference",
    "linear_stage_layout",
    "xy_gantry_layout",
]

# Hardware of the stdlib parts the layouts use.
MOTOR = {"frame": "NEMA17", "body_length": 40.0, "shaft_length": 24.0}
COUPLING = {"bore_a": 5, "bore_b": 8, "length": 25}
SCREW_TRIM = MOTOR["shaft_length"]  # lead screw: rail length minus the shaft stick-out
PULLEY = {"teeth": 20, "bore": 5, "belt_width": 6}
PULLEY_BELT = 4.0  # GT2Pulley belt_plane above its bottom
BRACKET_T = 5.0  # MotorMount thickness
PLATE_T = 10.0
CARRIAGE_LEN = 70.0
GANTRY_LEN = 90.0
# Cross rails span both Y sides: x_length - (gantry carriage width - spacing) + 2 x 10.
CROSS_TRIM = 2 * CARRIAGE_EDGE - 20.0


class _Layout:
    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []
        self.loops: List[Dict[str, Any]] = []

    def add(self, name, cls, inputs, own=None, target=None, fill_group=None, **dof):
        entry = {
            "name": name,
            "item": f"stdlib:{cls}",
            "inputs": dict(inputs),
            "connect": (
                None
                if target is None
                else {
                    "own": own,
                    "target": list(target),
                    "dof": {k: float(v) for k, v in dof.items()},
                }
            ),
        }
        if fill_group:
            entry["fill_group"] = fill_group
        self.items.append(entry)
        return name

    def loop(self, a, b, **dof):
        self.loops.append({"a": list(a), "b": list(b), "dof": dict(dof)})


def _screw(size, length):
    return {"size": size, "length": length, "with_thread": False}


# --------------------------------------------------------------------------- #
# One two-rod lead-screw axis (the linear stage; each gantry Y side)
# --------------------------------------------------------------------------- #


def _drive_and_feet(lay, p, rod, length, plate_m, plate_i, rail, motor_screws):
    """Motor, coupling, lead screw, idler bearing, and the foot screws into
    T-nuts in the rails under the plates."""
    motor = lay.add(
        f"{p}motor", "StepperMotor", MOTOR, "mount_face", [plate_m, "motor_face"]
    )
    if motor_screws == 4:
        lay.add(
            f"{p}motor_screw",
            "DIN912Screw",
            _screw("M3", 12),
            "head_seat",
            [plate_m, None],
            "motor",
        )
    else:  # two diagonal screws
        for k in (0, 3):
            lay.add(
                f"{p}motor_screw_{k}",
                "DIN912Screw",
                _screw("M3", 12),
                "head_seat",
                [plate_m, f"motor_hole_{k}"],
            )
    coupling = lay.add(
        f"{p}coupling", "ClampCoupling", COUPLING, "bore_a_stop", [motor, "shaft_tip"]
    )
    screw = lay.add(
        f"{p}lead_screw",
        "LeadScrewT8",
        {"length": length, "trim": SCREW_TRIM, "with_thread": False},
        "end_a",
        [coupling, "bore_b_stop"],
    )
    bearing = lay.add(
        f"{p}idler_bearing",
        "DeepGrooveBearing",
        {"model": "608"},
        "top",
        [plate_i, "bearing_seat"],
    )
    lay.loop([screw, "axis"], [bearing, "axis"])
    # Feet: the idler plate faces the motor plate, so its "b" side is over rail "a".
    for end, plate, flip in (("m", plate_m, False), ("i", plate_i, True)):
        for tag in ("a", "b"):
            hole = {"a": "b", "b": "a"}[tag] if flip else tag
            tnut = lay.add(
                f"{p}t_nut_{end}{tag}",
                "TSlotNut",
                {"size": "M5", "with_thread": False},
                "top",
                [plate, f"foot_nut_{hole}"],
            )
            lay.add(
                f"{p}foot_screw_{end}{tag}",
                "DIN912Screw",
                _screw("M5", 10),
                "head_seat",
                [plate, f"foot_hole_{hole}"],
            )
            lay.loop([tnut, "slot_seat"], [rail[tag], "slot_nx_0"])
    return screw


def _carriage_on_bearings(
    lay, p, rod, rod_names, cls, inputs, first_offset, rods_placed=True
):
    """Bearing 0a on rod a (slider), the carriage on it, the other three
    bearings in the carriage; loops: each bearing on its rod."""
    b0 = lay.add(
        f"{p}bearing_0a",
        "LinearBearing",
        {"rod": rod},
        "end_a",
        [rod_names["a"], "axis"],
        offset=first_offset,
    )
    car = lay.add(f"{p}carriage", cls, inputs, "bearing_pocket_0", [b0, "end_a"])
    for name, pocket, tag in (("0b", 1, "b"), ("1a", 2, "a"), ("1b", 3, "b")):
        b = lay.add(
            f"{p}bearing_{name}",
            "LinearBearing",
            {"rod": rod},
            "end_a",
            [car, f"bearing_pocket_{pocket}"],
        )
        lay.loop([b, "end_a"], [rod_names[tag], "axis"])
    return car


def _nut(lay, p, car, screw):
    nut = lay.add(
        f"{p}nut",
        "LeadScrewNutT8",
        {"with_thread": False},
        "flange_seat",
        [car, "nut_face"],
    )
    lay.loop([nut, "axis"], [screw, "axis"])
    for j, hole in ((0, 1), (3, 3)):  # two diagonal screws hold a T8 nut
        lay.add(
            f"{p}nut_screw_{j}",
            "DIN912Screw",
            _screw("M4", 10),
            "head_seat",
            [nut, f"flange_hole_{hole}"],
        )


def _plates_rods_rails(lay, p, rod, length, s, nema="NEMA17"):
    plate = {"rod": rod, "spacing": s, "thickness": PLATE_T, "nema": nema}
    pm = lay.add(f"{p}plate_motor", "RodEndPlate", dict(plate, motor=True))
    return pm, plate


# --------------------------------------------------------------------------- #
# Inputs
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

GANTRY_INPUTS = {
    "rod": _ROD_WIDGET,
    "y_length": _num(400, 250, 1000, 10),
    "x_length": _num(400, 250, 1000, 10),
    "spacing": _num(60, 58, 200, 1),
    "x_spacing": _num(60, 50, 66, 1),
}


# --------------------------------------------------------------------------- #
# Linear stage
# --------------------------------------------------------------------------- #


def _stage(rod="8", rail_length=400, spacing=80) -> Dict[str, Any]:
    lay = _Layout()
    rod, L, s = str(rod), float(rail_length), float(spacing)
    plate = {"rod": rod, "spacing": s, "thickness": PLATE_T, "nema": "NEMA17"}
    pm = lay.add("plate_motor", "RodEndPlate", dict(plate, motor=True))
    rods = {}
    for tag in ("a", "b"):
        rods[tag] = lay.add(
            f"rod_{tag}",
            "SmoothRod",
            {"diameter": rod, "length": L},
            "end_a",
            [pm, f"rod_hole_{tag}"],
        )
    pi = lay.add(
        "plate_idler",
        "RodEndPlate",
        dict(plate, motor=False),
        "rod_hole_b",
        [rods["a"], "end_b"],
    )
    lay.loop([pi, "rod_hole_a"], [rods["b"], "end_b"])
    rails = {}
    for tag in ("a", "b"):
        rails[tag] = lay.add(
            f"rail_{tag}",
            "AluExtrusion",
            {"series": "2020", "length": L},
            "slot_nx_0",
            [pm, f"rail_seat_{tag}"],
        )
    lay.loop([pi, "rail_seat_b"], [rails["a"], "slot_nx_0"])
    lay.loop([pi, "rail_seat_a"], [rails["b"], "slot_nx_0"])
    screw = _drive_and_feet(lay, "", rod, L, pm, pi, rails, motor_screws=4)
    car = _carriage_on_bearings(
        lay,
        "",
        rod,
        rods,
        "Carriage",
        {
            "rod": rod,
            "spacing": s,
            "length": CARRIAGE_LEN,
            "belt_clamp": False,
            "lead_screw": True,
        },
        first_offset=L / 2 - CARRIAGE_LEN / 2,
    )
    _nut(lay, "", car, screw)
    return {"items": lay.items, "loops": lay.loops}


# --------------------------------------------------------------------------- #
# XY gantry
# --------------------------------------------------------------------------- #


def _gantry(
    rod="8", y_length=400, x_length=400, spacing=60, x_spacing=60
) -> Dict[str, Any]:
    lay = _Layout()
    rod = str(rod)
    Ly, Lx, s, xs = float(y_length), float(x_length), float(spacing), float(x_spacing)
    plate = {"rod": rod, "spacing": s, "thickness": PLATE_T, "nema": "NEMA17"}
    gantry = {
        "rod": rod,
        "spacing": s,
        "length": GANTRY_LEN,
        "x_rod": rod,
        "x_spacing": xs,
        "lead_screw": True,
    }
    offset = Ly / 2 - GANTRY_LEN / 2  # gantry half way along Y (a joint value)

    # Left Y side, from the grounded motor plate.
    pm = lay.add("left_plate_motor", "RodEndPlate", dict(plate, motor=True))
    rods = {}
    for tag in ("a", "b"):
        rods[tag] = lay.add(
            f"left_rod_{tag}",
            "SmoothRod",
            {"diameter": rod, "length": Ly},
            "end_a",
            [pm, f"rod_hole_{tag}"],
        )
    pi = lay.add(
        "left_plate_idler",
        "RodEndPlate",
        dict(plate, motor=False),
        "rod_hole_b",
        [rods["a"], "end_b"],
    )
    lay.loop([pi, "rod_hole_a"], [rods["b"], "end_b"])
    rails = {}
    for tag in ("a", "b"):
        rails[tag] = lay.add(
            f"left_rail_{tag}",
            "AluExtrusion",
            {"series": "2020", "length": Ly},
            "slot_nx_0",
            [pm, f"rail_seat_{tag}"],
        )
    lay.loop([pi, "rail_seat_b"], [rails["a"], "slot_nx_0"])
    lay.loop([pi, "rail_seat_a"], [rails["b"], "slot_nx_0"])
    # Frame: two cross rails under the Y rails (profile on profile, crossed).
    for tag, dx in (("front", 10.0), ("back", Ly - 10.0)):
        lay.add(
            f"cross_rail_{tag}",
            "AluExtrusion",
            {"series": "2020", "length": Lx, "trim": CROSS_TRIM},
            "slot_nx_0",
            [rails["a"], "slot_px_0"],
            dx=dx,
            dy=-(s + 10.0),
            angle=1.5707963267948966,
        )
        lay.loop([rails["b"], "slot_px_0"], [f"cross_rail_{tag}", "slot_nx_0"])
    screw = _drive_and_feet(lay, "left_", rod, Ly, pm, pi, rails, motor_screws=2)
    left = _carriage_on_bearings(
        lay, "left_", rod, rods, "GantryCarriage", gantry, first_offset=offset
    )
    _nut(lay, "left_", left, screw)

    # X rods through the left gantry carriage; the right one on their far ends.
    for tag in ("a", "b"):
        lay.add(
            f"x_rod_{tag}",
            "SmoothRod",
            {"diameter": rod, "length": Lx},
            "end_a",
            [left, f"x_rod_hole_{tag}"],
        )
    right = lay.add(
        "right_carriage", "GantryCarriage", gantry, "x_rod_exit_a", ["x_rod_a", "end_b"]
    )
    lay.loop([right, "x_rod_exit_b"], ["x_rod_b", "end_b"])

    # Right Y side, hanging from its carriage: bearings, then the rods slide in them.
    rrods = {"a": "right_rod_a", "b": "right_rod_b"}
    for name, pocket, tag in (
        ("0a", 0, "a"),
        ("0b", 1, "b"),
        ("1a", 2, "a"),
        ("1b", 3, "b"),
    ):
        b = lay.add(
            f"right_bearing_{name}",
            "LinearBearing",
            {"rod": rod},
            "end_a",
            [right, f"bearing_pocket_{pocket}"],
        )
        if name.startswith("0"):
            lay.add(
                rrods[tag],
                "SmoothRod",
                {"diameter": rod, "length": Ly},
                "axis",
                [b, "end_a"],
                offset=offset,
            )
        else:
            lay.loop([b, "end_a"], [rrods[tag], "axis"])
    rpm = lay.add(
        "right_plate_motor",
        "RodEndPlate",
        dict(plate, motor=True),
        "rod_hole_a",
        [rrods["a"], "end_a"],
    )
    lay.loop([rpm, "rod_hole_b"], [rrods["b"], "end_a"])
    rpi = lay.add(
        "right_plate_idler",
        "RodEndPlate",
        dict(plate, motor=False),
        "rod_hole_b",
        [rrods["a"], "end_b"],
    )
    lay.loop([rpi, "rod_hole_a"], [rrods["b"], "end_b"])
    rrails = {}
    for tag in ("a", "b"):
        rrails[tag] = lay.add(
            f"right_rail_{tag}",
            "AluExtrusion",
            {"series": "2020", "length": Ly},
            "slot_nx_0",
            [rpm, f"rail_seat_{tag}"],
        )
        for cross in ("front", "back"):
            lay.loop([rrails[tag], "slot_px_0"], [f"cross_rail_{cross}", "slot_nx_0"])
    lay.loop([rpi, "rail_seat_b"], [rrails["a"], "slot_nx_0"])
    lay.loop([rpi, "rail_seat_a"], [rrails["b"], "slot_nx_0"])
    rscrew = _drive_and_feet(lay, "right_", rod, Ly, rpm, rpi, rrails, motor_screws=2)
    _nut(lay, "right_", right, rscrew)

    # X carriage on the X rods (belt plane = its clamp slot centre).
    xb0 = lay.add(
        "x_bearing_0a",
        "LinearBearing",
        {"rod": rod},
        "end_a",
        ["x_rod_a", "axis"],
        offset=Lx / 2 - CARRIAGE_LEN / 2,
    )
    car = lay.add(
        "x_carriage",
        "Carriage",
        {
            "rod": rod,
            "spacing": xs,
            "length": CARRIAGE_LEN,
            "belt_clamp": False,
            "lead_screw": False,
        },
        "bearing_pocket_0",
        [xb0, "end_a"],
    )
    for name, pocket, tag in (("0b", 1, "b"), ("1a", 2, "a"), ("1b", 3, "b")):
        b = lay.add(
            f"x_bearing_{name}",
            "LinearBearing",
            {"rod": rod},
            "end_a",
            [car, f"bearing_pocket_{pocket}"],
        )
        lay.loop([b, "end_a"], [f"x_rod_{tag}", "axis"])

    # Brackets on the gantry carriages' outer faces: motor + pulley on the
    # left, idler pulley on the right; the pulleys sit on the brackets.
    bracket_h = BELT_Z - PULLEY_BELT + 10.0  # mounting holes at the X rod height
    bracket = {"nema": "NEMA17", "thickness": BRACKET_T, "height": bracket_h}
    mb = lay.add(
        "x_motor_bracket",
        "MotorMount",
        dict(bracket, motor=True),
        "mount_face",
        [left, "side_face_p"],
    )
    ib = lay.add(
        "x_idler_bracket",
        "MotorMount",
        dict(bracket, motor=False),
        "mount_face",
        [right, "side_face_n"],
    )
    for side, b, order in (("left", mb, (1, 0)), ("right", ib, (0, 1))):
        for i, hole in enumerate(order):  # the left bracket is turned round
            lay.add(
                f"x_{side}_bracket_screw_{i}",
                "DIN912Screw",
                _screw("M5", 12),
                "head_seat",
                [b, f"mount_screw_{hole}"],
            )
    motor = lay.add("x_motor", "StepperMotor", MOTOR, "mount_face", [mb, "motor_face"])
    lay.add(
        "x_motor_screw",
        "DIN912Screw",
        _screw("M3", 8),
        "head_seat",
        [mb, None],
        "motor",
    )
    lay.add(
        "x_pulley",
        "GT2Pulley",
        PULLEY,
        "axis",
        [motor, "shaft"],
        offset=BRACKET_T,
        angle=0.0,
    )
    pulley = lay.add("x_idler_pulley", "GT2Pulley", PULLEY, "bottom", [ib, "axis"])
    screw = lay.add(
        "x_idler_screw", "DIN912Screw", _screw("M5", 20), "head_seat", [pulley, "top"]
    )
    nut = lay.add(
        "x_idler_nut",
        "HexNut",
        {"size": "M5", "with_thread": False},
        "bottom",
        [ib, "nut_seat"],
    )
    lay.loop([nut, "bottom"], [screw, "tip"])
    return {"items": lay.items, "loops": lay.loops}


# --------------------------------------------------------------------------- #
# Layouts
# --------------------------------------------------------------------------- #

_PROBES = {
    "rod": ["10", "12"],
    "rail_length": [500.0],
    "y_length": [500.0],
    "x_length": [500.0],
    "spacing": [90.0],
    "x_spacing": [64.0],
}


def _layout(fn, spec, values):
    values = {k: values.get(k, w["default"]) for k, w in spec.items()}
    out = fn(**values)

    def run(**v):
        return fn(**v)

    return {
        "inputs": {k: {"widget": w, "default": values[k]} for k, w in spec.items()},
        "bindings": derive_bindings(run, values, {k: _PROBES[k] for k in spec}),
        "items": out["items"],
        "loops": out["loops"],
    }


def linear_stage_layout(**values) -> Dict[str, Any]:
    """Lead-screw linear stage (camera slider): motor and idler end plates
    on two rods, two 2020 base rails, a carriage on four LMxUU, NEMA 17 +
    coupling + T8 screw, 608 idler bearing, and the screws / T-nuts holding
    it together.

    Keyword overrides: ``rod`` ("8" | "10" | "12"), ``rail_length`` (rod,
    rail and lead screw length, mm), ``spacing`` (rod spacing, mm)."""
    return _layout(_stage, STAGE_INPUTS, values)


def xy_gantry_layout(**values) -> Dict[str, Any]:
    """XY gantry / small CNC frame: two lead-screw Y sides whose
    GantryCarriages hold the two X rods, a 2020 frame of four Y rails on two
    cross rails, and a belt-driven X carriage (NEMA 17 + GT2 pulley on a
    MotorMount, idler pulley on a second MotorMount).

    Keyword overrides: ``rod``, ``y_length`` (Y rods / rails / lead screws),
    ``x_length`` (X rods and cross rails), ``spacing`` (Y rod spacing),
    ``x_spacing`` (X rod spacing)."""
    return _layout(_gantry, GANTRY_INPUTS, values)


# --------------------------------------------------------------------------- #
# Build in code
# --------------------------------------------------------------------------- #


def build_from_layout(layout: Dict[str, Any]) -> Assembly:
    """The assembly of a layout, placed by ``ground`` / ``connect`` only."""
    return build_layout(layout)


def build_linear_stage(**values) -> Assembly:
    return build_layout(linear_stage_layout(**values))


def build_xy_gantry(**values) -> Assembly:
    return build_layout(xy_gantry_layout(**values))


def check_layout_interference(
    layout: Dict[str, Any], assembly: Optional[Assembly] = None
):
    """Overlaps left in a layout's assembly (should be empty). Connected parts
    (every connect, loops included) are intended contacts; so are a screw and
    the part behind the one it seats on (it bolts into it), and a rod / lead
    screw and the part its bearing or nut sits in (it passes through)."""
    asm = assembly or build_layout(layout)
    allow = _allowed_contacts(layout)
    found = asm.check_interference(allow=allow, include_unknown=False)
    return [i for i in found if i.status == "overlap"]


def _allowed_contacts(layout):
    pairs = []
    expanded = []
    for e in layout["items"]:
        if e.get("fill_group"):  # the layouts only fill 4-hole motor groups
            expanded += [(f"{e['name']}_{i}", e) for i in range(4)]
        else:
            expanded.append((e["name"], e))
    all_names = [n for n, _ in expanded]
    for name, e in expanded:
        if e.get("connect") is None:
            continue
        if "screw" in name and "lead" not in name:
            prefix = (
                name.split("_")[0] + "_"
                if name.split("_")[0] in ("left", "right")
                else ""
            )
            # what is behind the part the screw goes into
            if "foot_screw" in name:
                suffix = name.rsplit("_", 1)[1]  # e.g. "ma"
                pairs.append((name, f"{prefix}t_nut_{suffix}"))
                pairs.append((name, f"{prefix}rail_{suffix[1]}"))
            elif "nut_screw" in name:
                pairs += [(name, f"{prefix}carriage"), (name, f"{prefix}lead_screw")]
            elif name.startswith("x_motor_screw"):
                pairs.append((name, "x_motor"))
            elif "motor_screw" in name:
                pairs.append((name, f"{prefix}motor"))
            elif "bracket_screw" in name:
                pairs.append(
                    (name, "left_carriage" if "left" in name else "right_carriage")
                )
            elif name == "x_idler_screw":
                pairs += [(name, "x_idler_bracket"), (name, "x_idler_nut")]
    # A rod / lead screw passes through the part its bearing or nut sits in.
    through = {
        "stdlib:LinearBearing",
        "stdlib:DeepGrooveBearing",
        "stdlib:LeadScrewNutT8",
    }
    edges = [(n, e["connect"]["target"][0]) for n, e in expanded if e.get("connect")]
    edges += [(lp["a"][0], lp["b"][0]) for lp in layout.get("loops") or []]
    near: Dict[str, set] = {}
    for x, y in edges:
        near.setdefault(x, set()).add(y)
        near.setdefault(y, set()).add(x)
    for middle, e in expanded:
        if e["item"] in through:
            for x in near.get(middle, ()):
                for y in near.get(middle, ()):
                    if x < y:
                        pairs.append((x, y))
    return [(a, b) for a, b in pairs if a in all_names and b in all_names]
