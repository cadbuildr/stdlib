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
}

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
