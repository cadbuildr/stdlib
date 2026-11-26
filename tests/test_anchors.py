"""Every catalogued part exposes mate anchors, and every anchor is where it says.

``EXPECTED`` is the anchor contract per catalog id: name -> (position, +Z axis)
in part space, as a function of the built part. A new catalog part must add
an entry here (``test_every_catalog_part_declares_anchors`` fails otherwise).
"""

import math

import pytest

from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.math_utils import quaternion_rotate_vector
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
    },
    "gt2-pulley": lambda p: {
        **_axial(p.height),
        "belt_plane": ((0, 0, p.height / 2), UP),
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
        frame = anchor.frame
        assert frame.top_frame is part.frame, anchor.name.value
        assert list(frame.position) == pytest.approx(
            list(pos), abs=1e-9
        ), anchor.name.value
        z_axis = quaternion_rotate_vector(list(frame.quaternion), [0.0, 0.0, 1.0])
        assert z_axis == pytest.approx(list(z), abs=1e-9), anchor.name.value


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
