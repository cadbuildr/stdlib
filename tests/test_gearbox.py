"""Spur gear reducer: library parts, the GearStage assembly and the click-demo
placement tables (single and two stage)."""

import json
import math

import numpy as np
import pytest

from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.interference import estimate_part_extents
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
    assert list(gear) == ["module", "teeth", "face_width", "bore"]
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
# Layouts
# --------------------------------------------------------------------------- #

LAYOUTS = {
    "single": single_stage_layout(),
    "single_vertical": single_stage_layout(horizontal=False),
    "two": two_stage_layout(),
    "two_live": two_stage_layout(stage2_as_assembly=True),
}


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
def test_layout_shape_and_single_axis_rotations(name):
    layout = LAYOUTS[name]
    json.dumps(layout)
    assert layout["warnings"] == []
    for it in layout["items"]:
        assert set(it) >= {"item", "inputs", "translate", "rotate"}
        assert it["item"].startswith("stdlib:") and len(it["translate"]) == 3
        rot = it["rotate"]
        assert rot is None or (set(rot) == {"axis", "angle"} and rot["axis"] in "XYZ")


@pytest.mark.parametrize("name", ["single", "two_live"])
def test_bindings(name):
    layout = LAYOUTS[name]
    b = layout["bindings"]
    assert set(b) == {"module", "z_pinion", "z_gear", "bearing"}
    items = layout["items"]
    by_target = {(items[i]["item"], inp) for i, inp in b["bearing"]}
    assert ("stdlib:DeepGrooveBearing", "model") in by_target
    assert ("stdlib:GearboxPlate", "bearing") in by_target
    for top, targets in b.items():
        for i, inp in targets:
            assert items[i]["bindings"][inp] == top
            assert items[i]["inputs"][inp] == layout["inputs"][top]
    gear_items = {items[i]["item"] for i, _ in b["z_gear"]}
    assert "stdlib:GearboxPlate" in gear_items
    if name == "single":
        assert len(b["bearing"]) == 6 and len(b["module"]) == 4
    assert layout["widgets"]["bearing"]["kind"] == "enum"


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
    result = evaluate(request_)
    assert result["ok"], result.get("error")
    assert result["dag"]["DAG"]


def _world_items(layout):
    """{name: (translate, rotate)} of a layout."""
    return {it["name"]: it for it in layout["items"]}


def test_output_shaft_at_centre_distance():
    for layout in (LAYOUTS["single"], LAYOUTS["single_vertical"]):
        items = _world_items(layout)
        for a, b in (("shaft_in", "shaft_out"), ("bearing_in_b", "bearing_out_b")):
            d = np.array(items[b]["translate"]) - np.array(items[a]["translate"])
            assert d[0] == pytest.approx(layout["center_distance"]) == pytest.approx(44)
        assert d[1] == d[2] == 0
    two = _world_items(LAYOUTS["two"])
    # stage 2 input axis is coaxial with stage 1 output.
    s1, s2 = two["s1.shaft_out"]["translate"], two["s2.shaft_in"]["translate"]
    assert (s1[0], s1[2]) == pytest.approx((s2[0], s2[2]))


# 2D tooth overlap at the placed positions (stage frame, vertical layout).


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


@pytest.mark.parametrize("z1,z2", [(11, 33), (12, 40), (13, 31)])
def test_gears_mesh_without_overlap_at_layout_positions(z1, z2):
    layout = single_stage_layout(z_pinion=z1, z_gear=z2, horizontal=False)
    items = _world_items(layout)
    pin, gear = items["pinion"], items["gear"]
    m = 2.0
    cd = gear["translate"][0] - pin["translate"][0]
    assert cd == pytest.approx(m * (z1 + z2) / 2)
    assert pin["translate"][1:] == gear["translate"][1:]
    phase = (gear["rotate"] or {"angle": 0.0})["angle"]
    a = _poly(spur_gear_outline(m, z1), 0.0, 0.0)
    b = _poly(spur_gear_outline(m, z2), phase, cd)
    assert not _overlap(a, b, (m * z1 / 2, 0.0), 4 * m)
    # Control: half a tooth off overlaps.
    bad = _poly(spur_gear_outline(m, z2), phase + 180.0 / z2, cd)
    assert _overlap(a, bad, (m * z1 / 2, 0.0), 4 * m)
    # Tips reach into the other gear's tooth space (they actually mesh).
    assert m * z1 / 2 + m + m * z2 / 2 + m > cd + m


def test_even_gear_horizontal_warns():
    layout = single_stage_layout(z_pinion=12, z_gear=40)
    assert layout["warnings"] and "even" in layout["warnings"][0]


# No floating part: the contact graph of world bounding boxes is connected.


def _world_boxes(assembly):
    from cadbuildr.foundation.interference import _rotation

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
    # Control: a part moved away is detected.
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
    asm = build_single_stage(horizontal=False)
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
    root = stage.components[[c for c in stage.stage_parts].index("gear")]
    assert gear.teeth == 32
    # 180/32 deg about Z
    w = root.frame.quaternion[0]
    assert math.degrees(2 * math.acos(w)) == pytest.approx(180 / 32)


def test_gear_stage_rejects_a_pinion_too_small_for_the_shaft():
    with pytest.raises(ValueError, match="Pinion root"):
        GearStage(module=0.5, z_pinion=10, z_gear=30, bearing="6801")
