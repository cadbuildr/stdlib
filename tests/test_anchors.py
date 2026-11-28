"""Every catalogued part exposes mate anchors, and every anchor is where it says.

``EXPECTED`` is the anchor contract per catalog id: name -> (position, +Z axis)
in part space, as a function of the built part. A new catalog part must add
an entry here (``test_every_catalog_part_declares_anchors`` fails otherwise).
"""

import math

import pytest

from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.math_utils import (
    quaternion_rotate_vector,
    tf_relative_to_frame,
)
from cadbuildr.stdlib.catalog import get_catalog_entries

UP, DOWN = (0.0, 0.0, 1.0), (0.0, 0.0, -1.0)


def _axial(length, ends=("bottom", "top")):
    return {
        ends[0]: ((0, 0, 0), DOWN),
        ends[1]: ((0, 0, length), UP),
        "axis": ((0, 0, 0), UP),
    }


def _screw(p):
    return {"head_seat": ((0, 0, p.body_height), DOWN), "tip": ((0, 0, 0), DOWN)}


def _stepper(p):
    L, r = p.body_length, p.hole_pitch / 2
    out = {
        "mount_face": ((0, 0, L), UP),
        "shaft": ((0, 0, L), UP),
        "shaft_tip": ((0, 0, L + p.shaft_length), UP),
        "back": ((0, 0, 0), DOWN),
    }
    corners = [(-r, -r), (-r, r), (r, -r), (r, r)]
    out.update({f"mount_hole_{i}": ((x, y, L), UP) for i, (x, y) in enumerate(corners)})
    return out


def _lead_nut(p):
    out = _axial(p.FLANGE_H + p.BODY_H)
    out["flange_seat"] = ((0, 0, p.FLANGE_H), UP)
    r = p.HOLE_PCD / 2
    for i in range(4):
        a = math.radians(45 + 90 * i)
        out[f"mount_hole_{i}"] = ((r * math.cos(a), r * math.sin(a), p.FLANGE_H), UP)
        out[f"flange_hole_{i}"] = ((r * math.cos(a), r * math.sin(a), 0), DOWN)
    return out


def _extrusion(p):
    out = _axial(p.length, ("end_a", "end_b"))
    cells = p.GEOMETRY[p.series]["cells"]
    for i, cy in enumerate(cells):
        out[f"slot_px_{i}"] = ((p.width / 2, cy, 0), (1, 0, 0))
        out[f"slot_nx_{i}"] = ((-p.width / 2, cy, 0), (-1, 0, 0))
    out["slot_py"] = ((0, p.height / 2, 0), (0, 1, 0))
    out["slot_ny"] = ((0, -p.height / 2, 0), (0, -1, 0))
    return out


# motion kits (frames documented in cadbuildr.stdlib.motion_kits.parts)
PX, NX, PY, NY = (1.0, 0.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, -1.0, 0.0)
_ROD_Z, _NEMA_PITCH = 30.0, {"NEMA14": 26.0, "NEMA17": 31.0, "NEMA23": 47.14}
_NEMA_BODY = {"NEMA14": 35.2, "NEMA17": 42.3, "NEMA23": 56.4}


def _rod_end_plate(p):
    t, s = p.thickness, p.spacing
    out = {
        "outer_face": ((0, 0, _ROD_Z), NX),
        "inner_face": ((t, 0, _ROD_Z), PX),
        "bottom": ((t / 2 + 10, 0, 0), DOWN),
        "drive_axis": ((0, 0, _ROD_Z), PX),
    }
    for tag, y in (("a", -s / 2), ("b", s / 2)):
        out[f"rod_hole_{tag}"] = ((0, y, _ROD_Z), PX)
        out[f"foot_hole_{tag}"] = ((t + 10, y, 8), UP)
        out[f"foot_nut_{tag}"] = ((t + 10, y, 0), DOWN)
        out[f"rail_seat_{tag}"] = ((0, y, 0), DOWN)
    if p.motor:
        hp = _NEMA_PITCH[p.nema] / 2
        out["motor_face"] = ((0, 0, _ROD_Z), NX)
        holes = [(sy * hp, _ROD_Z + sz * hp) for sy in (-1, 1) for sz in (-1, 1)]
        out.update(
            {f"motor_hole_{i}": ((t, y, z), PX) for i, (y, z) in enumerate(holes)}
        )
    else:
        out["bearing_seat"] = ((t - 7, 0, _ROD_Z), PX)
    return out


def _carriage_common(p):
    L, s = p.length, p.spacing
    out = {"top": ((0, 0, p.top), UP), "bottom": ((0, 0, -16), DOWN)}
    pockets = [
        (-L / 2, -s / 2, PX),
        (-L / 2, s / 2, PX),
        (L / 2, -s / 2, NX),
        (L / 2, s / 2, NX),
    ]
    for i, (x, y, n) in enumerate(pockets):
        out[f"bearing_pocket_{i}"] = ((x, y, 0), n)
    out["rod_axis_a"] = ((0, -s / 2, 0), PX)
    out["rod_axis_b"] = ((0, s / 2, 0), PX)
    if p.lead_screw:
        r = 8 / math.sqrt(2)
        out["nut_face"] = ((-L / 2, 0, 0), NX)
        for j, (y, z) in enumerate([(-r, -r), (-r, r), (r, -r), (r, r)]):
            out[f"nut_hole_{j}"] = ((-L / 2, y, z), NX)
    return out


def _carriage(p):
    out = _carriage_common(p)
    L = p.length
    holes = [(sx * (L / 2 - 10), sy * 15) for sx in (-1, 1) for sy in (-1, 1)]
    out.update({f"mount_hole_{i}": ((x, y, 20), UP) for i, (x, y) in enumerate(holes)})
    if p.belt_clamp:
        out["belt_clamp"] = ((0, 40 / (2 * math.pi), 27), PX)
    elif p.camera_mount:
        out["camera"] = ((0, 0, 26), UP)
    return out


def _gantry_carriage(p):
    out = _carriage_common(p)
    hw, xs = p.width / 2, p.x_spacing / 2
    out["x_rod_hole_a"] = ((-xs, hw, 24), NY)
    out["x_rod_hole_b"] = ((xs, hw, 24), NY)
    out["x_rod_exit_a"] = ((-xs, -hw, 24), PY)
    out["x_rod_exit_b"] = ((xs, -hw, 24), PY)
    for side, sign, n in (("p", 1, PY), ("n", -1, NY)):
        out[f"side_face_{side}"] = ((0, sign * hw, 24), n)
        out[f"side_hole_{side}0"] = ((-15, sign * hw, 24), n)
        out[f"side_hole_{side}1"] = ((15, sign * hw, 24), n)
    return out


def _motor_mount(p):
    t, H = p.thickness, p.height
    mx = t + 7 + _NEMA_BODY[p.nema] / 2
    out = {"mount_face": ((0, 0, 10), NX), "axis": ((mx, 0, H), UP)}
    for i, y in enumerate((-15, 15)):
        out[f"mount_hole_{i}"] = ((0, y, 10), NX)
        out[f"mount_screw_{i}"] = ((t, y, 10), PX)
    if p.motor:
        hp = _NEMA_PITCH[p.nema] / 2
        out["motor_face"] = ((mx, 0, H - t), DOWN)
        holes = [(mx + sx * hp, sy * hp) for sx in (-1, 1) for sy in (-1, 1)]
        out.update(
            {f"motor_hole_{i}": ((x, y, H), UP) for i, (x, y) in enumerate(holes)}
        )
    else:
        out["nut_seat"] = ((mx, 0, H - t), DOWN)
    return out


def _with(base, **extra):
    return lambda p: {**base(p), **extra}


EXPECTED = {
    # fasteners: screws & bolts
    "din912-socket-cap-screw": _screw,
    "hex-bolt": _screw,
    "din84-cheese-head-slotted": _screw,
    "din963-countersunk-slotted": _screw,
    "din7991-countersunk-socket": _screw,
    "din7380-button-head-socket": _screw,
    "wood-screw-countersunk": _screw,
    # nuts
    "din934-hex-nut": lambda p: _axial(p.thickness),
    "din439-thin-hex-nut": lambda p: _axial(p.thickness),
    "din985-nylon-lock-nut": lambda p: _axial(p.thickness),
    "din557-square-nut": lambda p: _axial(p.thickness),
    "din315-wing-nut": lambda p: _axial(p.thickness),
    "t-slot-nut-6mm": lambda p: {
        **_axial(p.thickness),
        "flange_seat": ((0, 0, p.FLANGE_H), UP),
        "slot_seat": ((0, 0, p.thickness), UP),
    },
    # washers
    "din125-flat-washer": lambda p: _axial(p.thickness),
    "din9021-fender-washer": lambda p: _axial(p.thickness),
    "din127-split-lock-washer": lambda p: _axial(p.thickness),
    # rods / shafts
    "threaded-rod-generic": lambda p: _axial(p.length, ("end_a", "end_b")),
    "threaded-rod-metric": lambda p: _axial(p.length, ("end_a", "end_b")),
    "shaft-plain": lambda p: _axial(p.LENGTH, ("end_a", "end_b")),
    "smooth-rod": lambda p: _axial(p.length, ("end_a", "end_b")),
    "lead-screw-t8": lambda p: _axial(p.length, ("end_a", "end_b")),
    "round-steel-tube": lambda p: _axial(p.length, ("end_a", "end_b")),
    # bearings / linear
    "deep-groove-ball-bearing": lambda p: _axial(p.width),
    "lm-uu-linear-bearing": lambda p: {
        **_axial(p.length, ("end_a", "end_b")),
        "center": ((0, 0, p.length / 2), UP),
    },
    "lead-screw-nut-t8": _lead_nut,
    # power transmission
    "spur-gear": lambda p: {
        **_axial(p.face_width),
        "pitch_plane": ((0, 0, p.face_width / 2), UP),
        **(
            {
                "hub_end": ((0, 0, p.face_width + p.hub_length), UP),
                "set_screw": (
                    (p.hub_diameter / 2, 0, p.face_width + p.hub_length / 2),
                    PX,
                ),
            }
            if p.hub_length
            else {}
        ),
    },
    "gt2-pulley": lambda p: {
        **_axial(p.height),
        "belt_plane": ((0, 0, p.belt_z), UP),
        **(
            {
                "set_screw_0": (
                    (p.hub_diameter / 2, 0, p.height - p.hub_length / 2),
                    PX,
                ),
                "set_screw_1": (
                    (0, p.hub_diameter / 2, p.height - p.hub_length / 2),
                    PY,
                ),
            }
            if p.hub_length
            else {}
        ),
    },
    "clamp-shaft-coupling": lambda p: {
        **_axial(p.length, ("end_a", "end_b")),
        "bore_a_stop": ((0, 0, p.length / 2), DOWN),
        "bore_b_stop": ((0, 0, p.length / 2), UP),
    },
    "nema-stepper-motor": _stepper,
    "alu-extrusion-tslot": _extrusion,
    # motion kits
    "rod-end-plate": _rod_end_plate,
    "motion-carriage": _carriage,
    "gantry-carriage": _gantry_carriage,
    "motor-mount-l-bracket": _motor_mount,
}


def _gearbox_plate(p):
    g = p.geometry
    cd, B, t = g.center_distance, g.bearing_width, g.thickness
    out = {
        "bore_in": ((0, 0, 0), UP),
        "bore_out": ((cd, 0, 0), UP),
        "seat_in": ((0, 0, B), DOWN),
        "seat_out": ((cd, 0, B), DOWN),
        "outer": ((0, 0, 0), DOWN),
        "inner": ((0, 0, t), UP),
    }
    for i, (x, y) in enumerate(g.hole_positions(), start=1):
        out[f"hole_{i}"] = ((x, y, 0), DOWN)
        out[f"hole_{i}_in"] = ((x, y, t), UP)
    for i, (x, y) in enumerate(g.mount_positions(), start=1):
        out[f"mount_{i}"] = ((x, y, 0), DOWN)
    return out


def _gear_stage(p):
    g = p.geometry
    cd, h, e = g.center_distance, g.height, g.shaft_extension
    return {
        "input": ((0, 0, -e), DOWN),
        "output": ((cd, 0, h + e), UP),
        "input_axis": ((0, 0, 0), UP),
        "output_axis": ((cd, 0, 0), UP),
        "face_a": ((0, 0, 0), DOWN),
        "face_b": ((0, 0, h), UP),
    }


EXPECTED.update(
    {
        "gearbox-plate": _gearbox_plate,
        "spacer": lambda p: _axial(p.length),
        "gear-stage": _gear_stage,
    }
)


# --- first content wave (Nov-27) ------------------------------------------ #


def _standoff(p):
    out = _axial(p.length)
    if p.kind == "male-female":
        out["stud_tip"] = ((0, 0, p.length + p.stud_length), UP)
    return out


def _flanged(p):
    out = _axial(p.width)
    out["flange_seat"] = ((0, 0, p.width - p.flange_thickness), DOWN)
    return out


def _pillow(p):
    h, a, j, t = p.center_height, p.width, p.bolt_spacing, p.base_thickness
    return {
        "bottom": ((0, 0, 0), DOWN),
        "axis": ((0, 0, h), PY),
        "face_a": ((0, -a / 2, h), NY),
        "face_b": ((0, a / 2, h), PY),
        "mount_hole_0": ((-j / 2, 0, t), UP),
        "mount_hole_1": ((j / 2, 0, t), UP),
    }


def _shaft_support(p):
    h, t, b, f = p.center_height, p.thickness, p.bolt_spacing, p.foot_height
    return {
        "bottom": ((0, 0, 0), DOWN),
        "axis": ((0, 0, h), PY),
        "face_b": ((0, t / 2, h), PY),
        "rod_hole": ((0, t / 2, h), NY),
        "mount_hole_0": ((-b / 2, 0, f), UP),
        "mount_hole_1": ((b / 2, 0, f), UP),
    }


def _rail(p):
    H, L = p.height, p.length
    out = {
        "datum": ((0, 0, 0), UP),
        "bottom": ((0, 0, L / 2), NX),
        "top": ((H, 0, L / 2), PX),
    }
    for i in range(p.hole_count):
        z = p.end_distance + i * p.hole_pitch
        out[f"hole_top_{i}"] = ((H, 0, z), PX)
        out[f"mount_hole_{i}"] = ((p.hole_grip, 0, z), PX)
    return out


def _rail_carriage(p):
    b, c = p.hole_spacing
    out = {"datum": ((0, 0, 0), UP), "top": ((p.height, 0, 0), PX)}
    corners = [(sy * b / 2, sz * c / 2) for sy in (-1, 1) for sz in (-1, 1)]
    out.update(
        {f"mount_hole_{i}": ((p.height, y, z), PX) for i, (y, z) in enumerate(corners)}
    )
    return out


def _rack(p):
    w, L = p.face_width, p.length
    return {
        "slide": ((0, 0, w / 2), PX),
        "back": ((0, -p.height, w / 2), NY),
        "end_a": ((-L / 2, 0, w / 2), NX),
        "end_b": ((L / 2, 0, w / 2), PX),
    }


def _servo(p):
    x, top = p.spline_offset, p.top_z
    ear_top = p.ear_z + p.ear_thickness
    return {
        "bottom": ((0, 0, 0), DOWN),
        "mount_face": ((0, 0, p.ear_z), DOWN),
        "shaft": ((x, 0, top), UP),
        "horn": ((x, 0, top + p.spline_length), UP),
        "mount_hole_0": ((-p.hole_spacing / 2, 0, ear_top), UP),
        "mount_hole_1": ((p.hole_spacing / 2, 0, ear_top), UP),
    }


EXPECTED.update(
    {
        "iso4029-set-screw": _screw,
        "iso7045-pan-head-phillips": _screw,
        "heat-set-insert": lambda p: {
            **_axial(p.length),
            "seat": ((0, 0, p.length), UP),
        },
        "iso8734-dowel-pin": lambda p: _axial(p.length, ("end_a", "end_b")),
        "hex-standoff": _standoff,
        "flanged-ball-bearing": _flanged,
        "thrust-ball-bearing": lambda p: _axial(p.height),
        "pillow-block-kp": _pillow,
        "sk-shaft-support": _shaft_support,
        "mgn-linear-rail": _rail,
        "mgn-rail-carriage": _rail_carriage,
        "gear-rack": _rack,
        "rc-servo": _servo,
    }
)

ENTRIES = get_catalog_entries()


def _config(entry, **override):
    cfg = {p.name: p.default for p in entry.params}
    cfg.update(entry.example_config)
    cfg.update(override)
    return cfg


def _cases():
    """Example config of every entry, plus each enum variant (sizes/models)."""
    cases = []
    for entry in ENTRIES:
        cases.append(pytest.param(entry, _config(entry), id=f"{entry.id}"))
        for param in entry.params:
            if param.kind == "enum":
                for value in param.choices:
                    cfg = _config(entry, **{param.name: value})
                    if "with_thread" in cfg:
                        cfg["with_thread"] = False  # anchors don't depend on threads
                    cases.append(pytest.param(entry, cfg, id=f"{entry.id}-{value}"))
    return cases


def test_every_catalog_part_declares_anchors():
    missing = sorted(e.id for e in ENTRIES if e.id not in EXPECTED)
    assert not missing, f"add anchor expectations for: {missing}"


@pytest.mark.parametrize("entry,config", _cases())
def test_anchor_positions_and_normals(entry, config):
    part = entry.load_class()(**config)
    expected = EXPECTED[entry.id](part)
    names = [a.name.value for a in part.anchors]
    assert sorted(names) == sorted(expected), f"{entry.id}: {names}"
    for anchor in part.anchors:
        pos, z = expected[anchor.name.value]
        position, quaternion = _pose_in_part(anchor, part)
        assert position == pytest.approx(list(pos), abs=1e-9), anchor.name.value
        z_axis = quaternion_rotate_vector(quaternion, [0.0, 0.0, 1.0])
        assert z_axis == pytest.approx(list(z), abs=1e-9), anchor.name.value


def _pose_in_part(anchor, part):
    """(position, quaternion) of ``anchor`` in part space. Anchors made with
    ``make_anchor`` hang directly off the part frame; derived anchors
    (``anchor.offset`` / ``rotated`` / ``linear_pattern``...) chain through
    their base anchor — both must resolve to the part frame."""
    frame = anchor.frame
    if frame.top_frame is part.frame:
        return list(frame.position), list(frame.quaternion)
    position, quaternion = tf_relative_to_frame(frame, part.frame)
    f = frame
    while f is not None and f is not part.frame:
        f = getattr(f, "top_frame", None)
    assert f is part.frame, f"{anchor.name.value}: frame does not root in the part"
    return list(position), list(quaternion)


def test_derived_anchors_are_checked_in_part_space():
    """A part may publish anchors derived from others (patterns, offsets)."""
    from cadbuildr.foundation import Part, make_anchor

    p = Part()
    base = p.add_anchor(make_anchor("base", (1.0, 2.0, 3.0), z_axis=(1, 0, 0)))
    p.add_anchor(base.offset([0.0, 0.0, 5.0], name="ahead"))
    pos, q = _pose_in_part(p.anchor("base_ahead"), p)
    assert pos == pytest.approx([6.0, 2.0, 3.0])
    assert quaternion_rotate_vector(q, [0, 0, 1]) == pytest.approx([1, 0, 0])


def test_anchors_serialize():
    for entry in ENTRIES:
        part = entry.load_class()(**_config(entry))
        if "with_thread" in _config(entry):
            part = entry.load_class()(**_config(entry, with_thread=False))
        dag = show_dag(part)
        root = dag["DAG"][dag["rootNodeId"]]
        assert len(root["deps"].get("anchors", [])) == len(part.anchors), entry.id


def test_slot_anchor_runs_along_extrusion():
    from cadbuildr.stdlib.profiles.extrusions.alu_extrusion_part import AluExtrusion

    bar = AluExtrusion("2040", 200)
    assert bar.slot_names == [
        "slot_px_0",
        "slot_nx_0",
        "slot_px_1",
        "slot_nx_1",
        "slot_py",
        "slot_ny",
    ]
    a = bar.slot_anchor("slot_py", 50.0)
    # Derived anchor: +X of the slot anchor is along the extrusion (+Z part).
    assert a.frame.position == pytest.approx([50.0, 0.0, 0.0])
    x_axis = quaternion_rotate_vector(
        list(bar.anchor("slot_py").frame.quaternion), [1, 0, 0]
    )
    assert x_axis == pytest.approx([0, 0, 1], abs=1e-9)
    with pytest.raises(ValueError):
        bar.slot_anchor("slot_top", 10.0)


# --- wave 3 ----------------------------------------------------------------- #


def _horn(p):
    out = _axial(p.hub_height)
    out["spline_stop"] = ((0, 0, p.spline_depth), DOWN)
    for i, (x, y) in enumerate(p.arm_tips):
        out[f"arm_tip_{i}"] = ((x, y, p.hub_height), UP)
    return out


def _collar(p):
    out = _axial(p.width)
    d, D, w = p.bore, p.outer_diameter, p.width
    if p.kind == "set-screw":
        out["set_screw"] = ((D / 2, 0, w / 2), PX)
    else:
        out["clamp_screw"] = (((d / 2 + D / 2) / 2, D / 2, w / 2), PY)
    return out


EXPECTED.update(
    {
        "gt2-belt-loop": lambda p: {
            "pulley_a": ((0, 0, 0), UP),
            "pulley_b": ((p.center_distance, 0, 0), UP),
            "back": ((p.center_distance / 2, p.back_offset, 0), PY),
        },
        "gt2-idler": lambda p: {
            **_axial(p.height),
            "belt_plane": ((0, 0, p.height / 2), UP),
        },
        "servo-horn": _horn,
        "shaft-collar": _collar,
        "din471-circlip": lambda p: _axial(p.thickness),
        "din472-circlip": lambda p: _axial(p.thickness),
        "v-wheel": lambda p: {
            **_axial(p.width),
            "contact": ((p.tip_radius, 0, p.width / 2), PX),
        },
    }
)
