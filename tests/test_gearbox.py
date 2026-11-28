"""Spur gear reducer: library parts, the GearStage assembly and the click-demo
connect sequences (single and two stage)."""

import json
import math
import os

import numpy as np
import pytest

from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.interference import _rotation, estimate_part_extents
from cadbuildr.foundation.interfaces import IncompatibleInterfaces
from cadbuildr.foundation.library.layout import build_layout, validate_layout
from cadbuildr.foundation.library import get_manifest
from cadbuildr.foundation.library.evaluate import evaluate
from cadbuildr.foundation.math_utils import tf_relative_to_frame
from cadbuildr.stdlib.bearings.ball_bearings.deep_groove_part import DeepGrooveBearing
from cadbuildr.stdlib.gearbox import (
    GearboxPlate,
    GearStage,
    StageGeometry,
    build_single_stage,
    build_two_stage,
    ratio_presets,
    single_stage_layout,
    two_stage_layout,
)
from cadbuildr.stdlib.power_transmission.gears.spur_gear_part import (
    spur_gear_outline,
)

MANIFEST = get_manifest("cadbuildr.stdlib")
ITEMS = {i["cls"]: i for i in MANIFEST["items"]}


def _widgets(cls):
    return {i["name"]: i["widget"] for i in ITEMS[cls]["inputs"]}


# --------------------------------------------------------------------------- #
# Manifest / widgets
# --------------------------------------------------------------------------- #


def test_decorated_stdlib_parts_have_typed_widgets():
    gear = _widgets("SpurGear")
    assert list(gear) == ["module", "teeth", "face_width", "bore", "hub_length"]
    assert gear["teeth"]["kind"] == "number" and gear["teeth"]["integer"] is True
    assert gear["module"]["min"] == 0.5 and gear["module"]["unit"] == "mm"
    assert gear["face_width"]["default"] == 6 and gear["bore"]["default"] == 5
    shaft = _widgets("Shaft")
    assert shaft["diameter"]["kind"] == "number" and shaft["length"]["max"] == 400
    washer = _widgets("DIN125Washer")["size"]
    assert washer["kind"] == "enum" and "M5" in washer["options"]
    assert _widgets("HexNut")["size"]["kind"] == "enum"


def test_gearbox_manifest_items():
    plate = ITEMS["GearboxPlate"]
    assert plate["id"] == "stdlib:GearboxPlate" and plate["kind"] == "part"
    w = _widgets("GearboxPlate")
    assert w["bearing"] == {
        "kind": "enum",
        "options": list(DeepGrooveBearing.TABLE),
        "default": "608",
    }
    assert w["z_gear"]["integer"] is True and w["module"]["kind"] == "number"
    assert {"bore_in", "bore_out", "hole_1", "hole_2", "hole_3", "hole_4"} <= set(
        plate["anchors"]
    )
    assert set(_widgets("Spacer")) == {"screw", "length", "outer_diameter"}
    stage = ITEMS["GearStage"]
    assert stage["kind"] == "assembly"
    assert [i["name"] for i in stage["inputs"]] == [
        "module",
        "z_pinion",
        "z_gear",
        "bearing",
    ]
    assert {"input", "output"} <= set(stage["anchors"])
    exposed = {i["name"]: i["type"] for i in stage["interfaces"]}
    assert exposed == {"input": "ShaftEnd", "output": "ShaftEnd"}
    sections = {s["id"]: s["items"] for s in MANIFEST["toolbar"]["sections"]}
    assert {"stdlib:GearboxPlate", "stdlib:Spacer", "stdlib:GearStage"} <= set(
        sections["gearbox"]
    )


# --------------------------------------------------------------------------- #
# Geometry
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "module,z1,z2,bearing",
    [(2, 11, 33, "608"), (1.5, 12, 40, "688"), (1, 20, 21, "623")],
)
def test_plate_bores_at_centre_distance(module, z1, z2, bearing):
    plate = GearboxPlate(module=module, z_pinion=z1, z_gear=z2, bearing=bearing)
    t_in, _ = tf_relative_to_frame(plate.anchor("bore_in").frame, plate.frame)
    t_out, _ = tf_relative_to_frame(plate.anchor("bore_out").frame, plate.frame)
    assert np.linalg.norm(np.array(t_out) - np.array(t_in)) == pytest.approx(
        module * (z1 + z2) / 2
    )
    seat, _ = tf_relative_to_frame(plate.anchor("seat_in").frame, plate.frame)
    assert seat[2] == pytest.approx(DeepGrooveBearing.TABLE[bearing]["B"])


def test_holes_do_not_depend_on_bearing_or_tooth_split():
    base = StageGeometry(module=2, z_pinion=11, z_gear=33, bearing="608")
    for other in (
        StageGeometry(module=2, z_pinion=11, z_gear=33, bearing="6800"),
        StageGeometry(module=2, z_pinion=15, z_gear=29, bearing="688"),
    ):
        assert other.hole_positions() == base.hole_positions()
        assert (other.x_min, other.x_max, other.y_half) == (
            base.x_min,
            base.x_max,
            base.y_half,
        )


def test_ratio_presets_keep_centre_distance():
    presets = ratio_presets()
    assert presets["3.00:1"] == {"z_pinion": 11, "z_gear": 33}
    for p in presets.values():
        assert p["z_pinion"] + p["z_gear"] == 44 and p["z_gear"] % 2 == 1


# --------------------------------------------------------------------------- #
# Layouts (connect sequences)
# --------------------------------------------------------------------------- #

LAYOUTS = {
    "single": single_stage_layout(),
    "two": two_stage_layout(),
    "two_live": two_stage_layout(stage2_as_assembly=True),
}
REFERENCE = json.load(
    open(os.path.join(os.path.dirname(__file__), "data", "layouts_at_9466104.json"))
)


def test_part_counts():
    assert LAYOUTS["single"]["part_count"] == 30
    assert LAYOUTS["two"]["part_count"] == 61
    assert len(LAYOUTS["two"]["items"]) == 61
    assert LAYOUTS["two_live"]["part_count"] == 61
    assert len(LAYOUTS["two_live"]["items"]) == 32
    counts = {}
    for it in LAYOUTS["single"]["items"]:
        counts[it["item"]] = counts.get(it["item"], 0) + 1
    assert counts == {
        "stdlib:GearboxPlate": 2,
        "stdlib:Spacer": 4,
        "stdlib:Shaft": 2,
        "stdlib:SpurGear": 2,
        "stdlib:DeepGrooveBearing": 4,
        "stdlib:DIN912Screw": 4,
        "stdlib:DIN125Washer": 8,
        "stdlib:HexNut": 4,
    }


@pytest.mark.parametrize("name", sorted(LAYOUTS))
def test_layout_shape(name):
    layout = LAYOUTS[name]
    validate_layout(layout)
    assert layout["items"][0]["connect"] is None
    for it in layout["items"]:
        assert it["item"].startswith("stdlib:")


@pytest.mark.parametrize("name", sorted(LAYOUTS))
def test_every_part_placed_by_exactly_one_connect(name):
    asm = build_layout(LAYOUTS[name])
    assert len(asm.joints) == len(asm.components) - 1
    assert [i for i in asm.check() if i["severity"] != "info"] == []
    dag = show_dag(asm)
    assert [c for c in dag["checks"] if c["severity"] != "info"] == []


@pytest.mark.parametrize("name", ["single", "two_live"])
def test_bindings(name):
    layout = LAYOUTS[name]
    b = layout["bindings"]
    assert set(b) == {"module", "z_pinion", "z_gear", "bearing"}
    items = {it["name"]: it for it in layout["items"]}
    by_target = {(items[n]["item"], inp) for n, inp in b["bearing"]}
    assert ("stdlib:DeepGrooveBearing", "model") in by_target
    assert ("stdlib:GearboxPlate", "bearing") in by_target
    for top, targets in b.items():
        for n, inp in targets:
            assert (
                items[n]["inputs"][inp] == layout["inputs"][top]["default"]
            )  # equal values
    gear_items = {items[n]["item"] for n, _ in b["z_gear"]}
    assert "stdlib:GearboxPlate" in gear_items
    if name == "single":
        assert len(b["bearing"]) == 6 and len(b["module"]) == 4
    assert layout["inputs"]["bearing"]["widget"]["kind"] == "enum"


def _unique_requests():
    seen = {}
    for layout in LAYOUTS.values():
        for it in layout["items"]:
            key = (it["item"], json.dumps(it["inputs"], sort_keys=True))
            seen.setdefault(key, {"item": it["item"], "inputs": it["inputs"]})
    return list(seen.values())


@pytest.mark.parametrize(
    "request_", _unique_requests(), ids=lambda r: r["item"].split(":")[1]
)
def test_every_layout_item_evaluates(request_):
    result = evaluate(dict(request_, interfaces=True))
    assert result["ok"], result.get("error")
    assert result["dag"]["DAG"] and result["interfaces"]


def _boxes(asm, ref):
    roots = {r.name.value: r for r in asm.components}
    r0 = roots[ref]
    R0, P0 = _rotation(r0.frame.quaternion), np.array(r0.frame.position, float)
    out = {}
    for name, root in roots.items():
        if type(root).__name__ == "AssemblyRoot":
            continue
        ext = estimate_part_extents(root)
        R, P = _rotation(root.frame.quaternion), np.array(root.frame.position, float)
        corners = (np.vstack([b.corners() for b in ext.boxes]) @ R.T + P - P0) @ R0
        out[name] = (corners.min(axis=0), corners.max(axis=0))
    return out


@pytest.mark.parametrize(
    "values,ref_key",
    [
        ({}, "single_stage"),
        (
            {"module": 1.5, "z_pinion": 12, "z_gear": 40, "bearing": "688"},
            "single_stage_15_12_40_688",
        ),
    ],
)
def test_solved_positions_match_the_old_coordinate_tables(values, ref_key):
    """Boxes relative to plate A equal the coordinate tables of git 9466104,
    also with another module / tooth split / bearing (the joints re-space)."""
    got = _boxes(build_single_stage(**values), "plate_a")
    want = REFERENCE[ref_key]
    assert set(got) == set(want)
    for name, (lo, hi) in want.items():
        assert np.allclose(got[name][0], lo, atol=1e-3), name
        assert np.allclose(got[name][1], hi, atol=1e-3), name


def test_two_stage_live_matches_the_old_table():
    asm = build_two_stage(stage2_as_assembly=True)
    got = _boxes(asm, "s1.plate_a")
    want = REFERENCE["two_stage_live"]
    assert set(got) == set(want)
    for name, (lo, hi) in want.items():
        assert np.allclose(got[name][0], lo, atol=1e-3), name
    roots = {r.name.value: r for r in asm.components}
    p0, stage = roots["s1.plate_a"].frame, roots["s2.stage"].frame
    from cadbuildr.foundation.math_utils import compose_tf, invert_tf

    t, q = compose_tf(
        *invert_tf(p0.position, p0.quaternion), stage.position, stage.quaternion
    )
    ref = REFERENCE["two_stage_live_stage_frame"]
    assert t == pytest.approx(ref["position"], abs=1e-3)
    assert (
        min(
            np.abs(np.array(q) - ref["quaternion"]).max(),
            np.abs(np.array(q) + ref["quaternion"]).max(),
        )
        < 1e-6
    )


def test_output_shaft_at_centre_distance():
    asm = build_single_stage()

    def world(part, anchor):
        t, _ = tf_relative_to_frame(asm.parts[part].anchor(anchor).frame, asm.frame)
        return np.array(t)

    d = world("shaft_out", "axis") - world("shaft_in", "axis")
    assert d[0] == pytest.approx(44) and d[1] == pytest.approx(0)
    two = build_two_stage()
    p = {
        n: np.array(
            tf_relative_to_frame(two.parts[n].anchor("axis").frame, two.frame)[0]
        )
        for n in ("s1.shaft_out", "s2.shaft_in")
    }
    assert p["s1.shaft_out"][:2] == pytest.approx(p["s2.shaft_in"][:2])  # coaxial


@pytest.mark.parametrize(
    "module,z1,z2,bearing",
    [(2, 11, 33, "608"), (1.5, 12, 40, "688"), (1, 20, 21, "623")],
)
def test_changing_module_teeth_bearing_stays_consistent(module, z1, z2, bearing):
    asm = build_single_stage(module=module, z_pinion=z1, z_gear=z2, bearing=bearing)
    assert [i for i in asm.check() if i["severity"] != "info"] == []
    boxes = _world_boxes(asm)
    assert _connected(boxes)


def test_a_stale_component_input_is_refused_at_its_connect():
    """Switch the bearing but not the shafts: the shaft no longer fits."""
    layout = single_stage_layout()
    for it in layout["items"]:
        if it["item"] == "stdlib:DeepGrooveBearing":
            it["inputs"]["model"] = "6800"  # 10 mm bore, the shafts stay 8 mm
    with pytest.raises(IncompatibleInterfaces):
        build_layout(layout)


# 2D tooth overlap at the solved positions (stage frame).


def _poly(points, angle_deg, dx):
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    return [(x * c - y * s + dx, x * s + y * c) for x, y in points]


def _inside(pt, poly):
    x, y = pt
    hit, j = False, len(poly) - 1
    for i, (xi, yi) in enumerate(poly):
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def _overlap(a, b, centre, zone):
    def near(poly):
        return [
            p
            for p in poly
            if (p[0] - centre[0]) ** 2 + (p[1] - centre[1]) ** 2 < zone**2
        ]

    return any(_inside(p, b) for p in near(a)) or any(_inside(p, a) for p in near(b))


def _yaw_deg(q):
    return math.degrees(2 * math.atan2(q[3], q[0]))


@pytest.mark.parametrize("z1,z2", [(11, 33), (12, 40), (13, 31), (12, 32)])
def test_gears_mesh_without_overlap_at_solved_positions(z1, z2):
    asm = build_single_stage(z_pinion=z1, z_gear=z2)
    roots = {r.name.value: r for r in asm.components}
    pin, gear = roots["pinion"].frame, roots["gear"].frame
    m = 2.0
    cd = gear.position[0] - pin.position[0]
    assert cd == pytest.approx(m * (z1 + z2) / 2)
    assert pin.position[1:] == pytest.approx(gear.position[1:])
    a = _poly(spur_gear_outline(m, z1), _yaw_deg(pin.quaternion), 0.0)
    phase = _yaw_deg(gear.quaternion)
    b = _poly(spur_gear_outline(m, z2), phase, cd)
    assert not _overlap(a, b, (m * z1 / 2, 0.0), 4 * m)
    bad = _poly(spur_gear_outline(m, z2), phase + 180.0 / z2, cd)
    assert _overlap(a, bad, (m * z1 / 2, 0.0), 4 * m)


# No floating part: the contact graph of world bounding boxes is connected.


def _world_boxes(assembly):
    boxes = []
    for root in assembly.components:
        ext = estimate_part_extents(root)
        assert not ext.unknown, ext.unknown
        rot = _rotation(root.frame.quaternion)
        pos = np.array(root.frame.position, dtype=float)
        corners = np.vstack([b.corners() for b in ext.boxes]) @ rot.T + pos
        boxes.append((corners.min(axis=0), corners.max(axis=0)))
    return boxes


def _connected(boxes, tol=0.05):
    n = len(boxes)
    seen, todo = {0}, [0]
    while todo:
        i = todo.pop()
        lo_i, hi_i = boxes[i]
        for j in range(n):
            if j in seen:
                continue
            lo_j, hi_j = boxes[j]
            if np.all(lo_i <= hi_j + tol) and np.all(lo_j <= hi_i + tol):
                seen.add(j)
                todo.append(j)
    return len(seen) == n


@pytest.mark.parametrize("builder", [build_single_stage, build_two_stage])
def test_no_floating_part(builder):
    asm = builder()
    boxes = _world_boxes(asm)
    assert len(boxes) == asm.layout["part_count"]
    assert _connected(boxes)
    lo, hi = boxes[0]
    assert not _connected(boxes[:1] + [(lo + 500, hi + 500)] + boxes[1:])


# --------------------------------------------------------------------------- #
# GearStage
# --------------------------------------------------------------------------- #


def test_gear_stage_evaluates():
    result = evaluate(
        {
            "item": "stdlib:GearStage",
            "inputs": {"module": 2, "z_pinion": 13, "z_gear": 31, "bearing": "688"},
        }
    )
    assert result["ok"], result.get("error")


def test_gear_stage_matches_layout_and_binds_its_inputs():
    stage = GearStage()
    asm = build_single_stage()
    assert len(stage.components) == len(asm.components) == 30
    for a, b in zip(stage.components, asm.components):
        assert a.frame.position == pytest.approx(b.frame.position)
        assert a.frame.quaternion == pytest.approx(b.frame.quaternion)
    assert stage.center_distance == pytest.approx(44) and stage.ratio == 3

    dag = show_dag(stage)
    names = {v: k for k, v in dag["serializableNodes"].items()}
    nodes = dag["DAG"]
    refs = [
        {k: nodes[v]["params"]["value"] for k, v in n["deps"].items()}
        for n in nodes.values()
        if names[n["type"]] == "LibraryRef"
    ]
    plate = next(r for r in refs if r["cls"] == "GearboxPlate")
    assert json.loads(plate["bindings"]) == {
        "module": "module",
        "z_pinion": "z_pinion",
        "z_gear": "z_gear",
        "bearing": "bearing",
    }
    teeth = {
        json.loads(r["inputs"])["teeth"]: json.loads(r["bindings"])
        for r in refs
        if r["cls"] == "SpurGear"
    }
    assert teeth[33] == {"module": "module", "teeth": "z_gear"}
    assert teeth[11] == {"module": "module", "teeth": "z_pinion"}
    bearing = next(r for r in refs if r["cls"] == "DeepGrooveBearing")
    assert json.loads(bearing["bindings"]) == {"model": "bearing"}
    root = nodes[dag["rootNodeId"]]
    stage_ref = nodes[root["deps"]["library"]]
    assert nodes[stage_ref["deps"]["item"]]["params"]["value"] == "stdlib:GearStage"


def test_gear_stage_phases_an_even_gear():
    stage = GearStage(z_pinion=12, z_gear=32)
    gear = stage.stage_parts["gear"]
    from cadbuildr.foundation.compute_functions import _SOURCE_COMPONENT_ATTR

    root = next(
        c for c in stage.components if getattr(c, _SOURCE_COMPONENT_ATTR) is gear
    )
    assert gear.teeth == 32
    # 180/32 deg about Z
    w = abs(root.frame.quaternion[0])  # q and -q are the same rotation
    assert math.degrees(2 * math.acos(w)) == pytest.approx(180 / 32)


def test_gear_stage_rejects_a_pinion_too_small_for_the_shaft():
    with pytest.raises(ValueError, match="Pinion root"):
        GearStage(module=0.5, z_pinion=10, z_gear=30, bearing="6801")
