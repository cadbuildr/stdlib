"""Motion kits: manifest entries + widgets of the new parts and of the stdlib
parts the demos reuse, and the two demo layouts as connect sequences (every
part placed by one connect, check() clean, positions as the old coordinate
tables, consistent when rod / lengths / spacing change) and their bindings."""

import json
import os

import numpy as np
import pytest

from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.interference import _rotation, estimate_part_extents
from cadbuildr.foundation.interfaces import LoopMismatch
from cadbuildr.foundation.library import get_manifest
from cadbuildr.foundation.library.evaluate import evaluate
from cadbuildr.foundation.library.layout import build_layout, validate_layout
from cadbuildr.foundation.math_utils import tf_relative_to_frame
from cadbuildr.stdlib.motion_kits import demos
from cadbuildr.stdlib.motion_kits.parts import (
    Carriage,
    GantryCarriage,
    MotorMount,
    RodEndPlate,
)

MANIFEST = get_manifest("cadbuildr.stdlib")
ITEMS = {i["id"]: i for i in MANIFEST["items"]}
LAYOUTS = {
    "linear_stage": demos.linear_stage_layout(),
    "xy_gantry": demos.xy_gantry_layout(),
}


def _widgets(item_id):
    return {i["name"]: i["widget"] for i in ITEMS[item_id]["inputs"]}


# --------------------------------------------------------------------------- #
# Manifest
# --------------------------------------------------------------------------- #


def test_manifest_has_motion_kits_without_errors():
    assert "errors" not in MANIFEST
    sections = {s["label"]: s["items"] for s in MANIFEST["toolbar"]["sections"]}
    assert set(sections["Motion Kits"]) == {
        "stdlib:RodEndPlate",
        "stdlib:Carriage",
        "stdlib:GantryCarriage",
        "stdlib:MotorMount",
    }


def test_new_part_widgets():
    rod = {"kind": "enum", "options": ["8", "10", "12"], "default": "8"}
    nema = {
        "kind": "enum",
        "options": ["NEMA14", "NEMA17", "NEMA23"],
        "default": "NEMA17",
    }
    w = _widgets("stdlib:RodEndPlate")
    assert w["rod"] == rod and w["nema"] == nema
    assert w["motor"] == {"kind": "bool", "default": False}
    assert w["spacing"]["kind"] == "number" and w["spacing"]["min"] == 60
    w = _widgets("stdlib:Carriage")
    assert list(w) == [
        "rod",
        "spacing",
        "length",
        "belt_clamp",
        "lead_screw",
        "camera_mount",
    ]
    assert w["rod"] == rod
    assert w["belt_clamp"] == {"kind": "bool", "default": False}
    w = _widgets("stdlib:GantryCarriage")
    assert w["rod"] == rod and w["x_rod"] == rod
    assert w["lead_screw"] == {"kind": "bool", "default": True}
    w = _widgets("stdlib:MotorMount")
    assert w["nema"] == nema and w["motor"] == {"kind": "bool", "default": True}


@pytest.mark.parametrize(
    "item_id,expected",
    [
        ("stdlib:SmoothRod", {"diameter": "enum", "length": "number"}),
        ("stdlib:LinearBearing", {"model": "enum", "rod": "enum"}),
        (
            "stdlib:LeadScrewT8",
            {"length": "number", "with_thread": "bool", "trim": "number"},
        ),
        ("stdlib:LeadScrewNutT8", {"with_thread": "bool"}),
        (
            "stdlib:StepperMotor",
            {"frame": "enum", "body_length": "number", "shaft_length": "number"},
        ),
        (
            "stdlib:GT2Pulley",
            {"teeth": "number", "bore": "number", "belt_width": "number"},
        ),
        (
            "stdlib:ClampCoupling",
            {"bore_a": "number", "bore_b": "number", "length": "number"},
        ),
        (
            "stdlib:AluExtrusion",
            {"series": "enum", "length": "number", "trim": "number"},
        ),
    ],
)
def test_reused_parts_declare_typed_inputs(item_id, expected):
    w = _widgets(item_id)
    assert {k: v["kind"] for k, v in w.items()} == expected
    for widget in w.values():
        if widget["kind"] == "number":
            assert "min" in widget and "max" in widget
    item = ITEMS[item_id]
    assert item["anchors"]
    if any(v == "enum" for v in expected.values()):
        assert item["configurations"]  # table rows become configurations


def test_stepper_and_rod_tables_are_configurations():
    assert [c["name"] for c in ITEMS["stdlib:StepperMotor"]["configurations"]] == [
        "NEMA14",
        "NEMA17",
        "NEMA23",
    ]
    assert _widgets("stdlib:SmoothRod")["diameter"]["options"] == [
        "6",
        "8",
        "10",
        "12",
        "16",
    ]
    assert _widgets("stdlib:GT2Pulley")["teeth"]["integer"] is True


def test_backward_compatible_constructors():
    from cadbuildr.stdlib.linear_motion.smooth_rods.smooth_rod_part import SmoothRod
    from cadbuildr.stdlib.profiles.extrusions.alu_extrusion_part import AluExtrusion

    assert SmoothRod(8, 100).diameter == 8.0  # numbers still accepted
    assert SmoothRod("10", 100).diameter == 10.0
    assert AluExtrusion("2040", 50).series == "2040"


@pytest.mark.parametrize("rod", ["8", "10", "12"])
def test_new_parts_build_for_every_rod(rod):
    for part in (
        RodEndPlate(rod=rod, motor=True),
        RodEndPlate(rod=rod, motor=False),
        Carriage(rod=rod, belt_clamp=True, lead_screw=True),
        GantryCarriage(rod=rod, x_rod=rod),
    ):
        assert show_dag(part)["DAG"]


def test_part_validation():
    with pytest.raises(ValueError):
        RodEndPlate(rod="12", spacing=60, motor=True, nema="NEMA23")
    with pytest.raises(ValueError):
        Carriage(rod="12", length=50)
    with pytest.raises(ValueError):
        MotorMount(thickness=10, height=20)


def test_belt_clamp_adds_geometry_and_anchor():
    off, on = Carriage(camera_mount=False), Carriage(belt_clamp=True)
    names = lambda part: {a.name.value for a in part.anchors}  # noqa: E731
    assert "belt_clamp" in names(on) and "belt_clamp" not in names(off)
    assert len(on.operations) > len(off.operations)


def test_camera_mount_plate_unless_belt_clamp():
    names = lambda part: {a.name.value for a in part.anchors}  # noqa: E731
    assert "camera" in names(Carriage()) and "camera" not in names(
        Carriage(camera_mount=False)
    )
    assert "camera" not in names(Carriage(belt_clamp=True))


# --------------------------------------------------------------------------- #
# Layouts (connect sequences)
# --------------------------------------------------------------------------- #

BUILT = {name: build_layout(layout) for name, layout in LAYOUTS.items()}
REFERENCE = json.load(
    open(os.path.join(os.path.dirname(__file__), "data", "layouts_at_9466104.json"))
)


def test_layout_shape():
    assert len(LAYOUTS["linear_stage"]["items"]) == 27  # + a 4-screw fill_group
    assert len(BUILT["linear_stage"].components) == 30
    assert len(BUILT["xy_gantry"].components) == 80
    for layout in LAYOUTS.values():
        validate_layout(layout)  # JSON, names, grounded first, no positions
        for e in layout["items"]:
            assert e["item"] in ITEMS, e["item"]
            assert set(e["inputs"]) <= {i["name"] for i in ITEMS[e["item"]]["inputs"]}
        assert layout["items"][0]["connect"] is None
        assert all(e["connect"] for e in layout["items"][1:])


@pytest.mark.parametrize("name", list(LAYOUTS))
def test_every_part_placed_by_exactly_one_connect(name):
    asm = BUILT[name]
    # one grounded part (add_component at the origin), one joint per other part
    assert len(asm.joints) == len(asm.components) - 1
    children = [id(j.child_anchor) for j in asm.joints]
    assert len(set(children)) == len(children)
    issues = asm.check()
    assert [i for i in issues if i["severity"] != "info"] == [], issues
    # the loops really closed something
    assert len(LAYOUTS[name]["loops"]) >= 10


@pytest.mark.parametrize("name", list(LAYOUTS))
def test_show_dag_carries_a_clean_check(name):
    dag = show_dag(BUILT[name])
    assert dag["DAG"][dag["rootNodeId"]]["deps"]["components"]
    assert [c for c in dag["checks"] if c["severity"] != "info"] == []
    assert any(c["code"] == "moves" for c in dag["checks"])  # the carriage slides


def _unique_requests():
    seen = {}
    for layout in LAYOUTS.values():
        for e in layout["items"]:
            key = json.dumps([e["item"], e["inputs"]], sort_keys=True)
            seen.setdefault(key, pytest.param(e["item"], e["inputs"], id=e["name"]))
    return list(seen.values())


@pytest.mark.parametrize("item_id,inputs", _unique_requests())
def test_every_layout_item_evaluates(item_id, inputs):
    result = evaluate({"item": item_id, "inputs": inputs, "interfaces": True})
    assert result["ok"], result.get("error")
    dag = result["dag"]
    root = dag["DAG"][dag["rootNodeId"]]
    assert root["deps"].get("anchors"), item_id
    assert result["interfaces"], item_id


def _boxes(asm, ref):
    """{name: (lo, hi)} world boxes in the frame of part ``ref``."""
    roots = {r.name.value: r for r in asm.components}
    r0 = roots[ref]
    R0, P0 = _rotation(r0.frame.quaternion), np.array(r0.frame.position, float)
    out = {}
    for name, root in roots.items():
        ext = estimate_part_extents(root)
        R, P = _rotation(root.frame.quaternion), np.array(root.frame.position, float)
        corners = (np.vstack([b.corners() for b in ext.boxes]) @ R.T + P - P0) @ R0
        out[name] = (corners.min(axis=0), corners.max(axis=0))
    return out


# The X brackets are 0.5 mm taller than in the coordinate table: the pulleys
# now sit on them (the table floated them 0.5 mm above), so the bracket top,
# the motor under it, its screws and the idler nut move up 0.5 mm; the belt
# plane (pulleys) is unchanged.
_HALF_MM = (
    "x_motor_bracket",
    "x_idler_bracket",
    "x_motor",
    "x_motor_screw_",
    "x_idler_nut",
)


def _compare(asm, ref_key, ref_part):
    want = REFERENCE[ref_key]
    got = _boxes(asm, ref_part)
    assert set(got) == set(want)
    groups = {}
    for name, (lo, hi) in want.items():
        tol = 0.5 + 1e-3 if name.startswith(_HALF_MM) else 1e-3
        if name.startswith("x_motor_screw_") or name.startswith("motor_screw_"):
            groups.setdefault(name.rsplit("_", 1)[0], []).append((name, lo))
            continue  # a fill_group: same set of positions, numbered by the group
        assert np.allclose(got[name][0], lo, atol=tol), (name, got[name][0], lo)
        assert np.allclose(got[name][1], hi, atol=tol), (name, got[name][1], hi)
    for prefix, members in groups.items():
        want_set = sorted(tuple(np.round(lo, 3)) for _, lo in members)
        got_set = sorted(tuple(np.round(got[n][0], 3)) for n, _ in members)
        assert np.allclose(
            np.array(want_set)[:, :2], np.array(got_set)[:, :2], atol=1e-3
        ), prefix
        assert np.allclose(
            np.array(want_set)[:, 2], np.array(got_set)[:, 2], atol=0.6
        ), prefix


@pytest.mark.parametrize(
    "name,values,ref_key,ref_part",
    [
        ("linear_stage", {}, "linear_stage", "plate_motor"),
        (
            "linear_stage",
            {"rod": "12", "rail_length": 600, "spacing": 90},
            "linear_stage_12_600_90",
            "plate_motor",
        ),
        ("xy_gantry", {}, "xy_gantry", "left_plate_motor"),
        (
            "xy_gantry",
            {"rod": "10", "x_length": 500, "y_length": 300},
            "xy_gantry_10_500_300",
            "left_plate_motor",
        ),
    ],
)
def test_solved_positions_match_the_old_coordinate_tables(
    name, values, ref_key, ref_part
):
    """The joints put every part where the coordinate tables of git 9466104
    did (boxes relative to the grounded plate), for the defaults and for a
    changed rod / length / spacing (lengths drive positions through the chain)."""
    asm = getattr(demos, f"build_{name}")(**values)
    _compare(asm, ref_key, ref_part)


@pytest.mark.parametrize(
    "name,values",
    [
        ("linear_stage", {}),
        ("linear_stage", {"rod": "12", "rail_length": 600}),
        ("xy_gantry", {}),
        ("xy_gantry", {"rod": "10", "x_length": 500, "y_length": 300}),
    ],
)
def test_no_unintended_interference(name, values):
    layout = getattr(demos, f"{name}_layout")(**values)
    assert demos.check_layout_interference(layout) == []


def test_rail_length_moves_the_idler_end():
    a, b = demos.build_linear_stage(), demos.build_linear_stage(rail_length=550)

    def x_of(asm, part, anchor):
        t, _ = tf_relative_to_frame(asm.parts[part].anchor(anchor).frame, asm.frame)
        return t[0]

    assert x_of(b, "plate_idler", "outer_face") - x_of(
        a, "plate_idler", "outer_face"
    ) == pytest.approx(150)
    assert x_of(b, "idler_bearing", "top") - x_of(
        a, "idler_bearing", "top"
    ) == pytest.approx(150)


def test_carriage_rides_on_a_slider_dof():
    layout = demos.linear_stage_layout()
    first = next(e for e in layout["items"] if e["name"] == "bearing_0a")
    assert first["connect"]["dof"] == {"offset": 165.0}
    asm = build_layout(layout)
    slider = next(j for j in asm.joints if type(j).__name__ == "SliderJoint")
    slider.set_offset(60.0)  # the carriage (and its bearings, nut) follow
    t, _ = tf_relative_to_frame(asm.parts["carriage"].anchor("top").frame, asm.frame)
    assert t[0] == pytest.approx(60.0 + 35.0)
    # the loops on rod b still close (the slider moved along the rods)
    assert [i for i in asm.check() if i["code"] == "loop"] == []


def test_inconsistent_carriage_spacing_is_a_loop_mismatch():
    """Plate spacing 80 vs carriage spacing 70: the second rod's bearings miss."""
    layout = demos.linear_stage_layout()
    for e in layout["items"]:
        if e["name"] == "carriage":
            e["inputs"]["spacing"] = 70.0
    with pytest.raises(LoopMismatch) as err:
        build_layout(layout)
    e = err.value
    assert e.delta_mm == pytest.approx(10.0)
    assert abs(e.along[1]) == pytest.approx(1.0)  # across the rods
    assert "spacing" in e.hint and "80" in e.hint and "70" in e.hint


def test_belt_runs_through_the_clamp():
    """X pulleys' belt plane is the X carriage clamp slot centre height."""
    layout = demos.xy_gantry_layout()
    for e in layout["items"]:
        if e["name"] == "x_carriage":
            e["inputs"]["belt_clamp"] = True
    asm = build_layout(layout)

    def world(part, anchor):
        t, _ = tf_relative_to_frame(asm.parts[part].anchor(anchor).frame, asm.frame)
        return np.array(t)

    clamp = world("x_carriage", "belt_clamp")
    up = np.array(
        tf_relative_to_frame(asm.parts["x_carriage"].anchor("top").frame, asm.frame)[0]
    ) - np.array(
        tf_relative_to_frame(asm.parts["x_carriage"].anchor("bottom").frame, asm.frame)[
            0
        ]
    )
    up = up / np.linalg.norm(up)
    for pulley in ("x_pulley", "x_idler_pulley"):
        assert float((world(pulley, "belt_plane") - clamp) @ up) == pytest.approx(
            0.0, abs=1e-6
        )
    assert demos.check_layout_interference(layout) == []


# --------------------------------------------------------------------------- #
# Bindings (equal values only)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", list(LAYOUTS))
def test_bindings_are_equal_values(name):
    layout = LAYOUTS[name]
    items = {e["name"]: e for e in layout["items"]}
    for top, targets in layout["bindings"].items():
        assert targets, top
        for item, comp_input in targets:
            assert str(items[item]["inputs"][comp_input]) == str(
                layout["inputs"][top]["default"]
            ) or float(items[item]["inputs"][comp_input]) == float(
                layout["inputs"][top]["default"]
            ), (
                top,
                item,
                comp_input,
            )


@pytest.mark.parametrize("name", list(LAYOUTS))
def test_rod_binding_covers_rods_bearings_plates_carriages(name):
    layout = LAYOUTS[name]
    bound = {item for item, _ in layout["bindings"]["rod"]}
    for e in layout["items"]:
        cls = e["item"].split(":")[1]
        if cls in (
            "SmoothRod",
            "LinearBearing",
            "RodEndPlate",
            "Carriage",
            "GantryCarriage",
        ):
            assert e["name"] in bound, e["name"]


@pytest.mark.parametrize(
    "name,inp,classes",
    [
        ("linear_stage", "rail_length", {"SmoothRod", "AluExtrusion", "LeadScrewT8"}),
        ("xy_gantry", "y_length", {"SmoothRod", "AluExtrusion", "LeadScrewT8"}),
        ("xy_gantry", "x_length", {"SmoothRod", "AluExtrusion"}),
    ],
)
def test_length_bindings_reproduce_the_layout(name, inp, classes):
    """Applying a length binding (equal values) equals re-running the layout,
    inputs-wise; the positions follow through the joints."""
    fn = getattr(demos, f"{name}_layout")
    base = LAYOUTS[name]
    new = base["inputs"][inp]["default"] + 100
    expected = {e["name"]: e for e in fn(**{inp: new})["items"]}
    items = json.loads(json.dumps(base["items"]))
    by_name = {e["name"]: e for e in items}
    for item, comp_input in base["bindings"][inp]:
        by_name[item]["inputs"][comp_input] = new
    for e in items:
        assert e["inputs"] == expected[e["name"]]["inputs"], e["name"]
    assert {
        by_name[i]["item"].split(":")[1] for i, _ in base["bindings"][inp]
    } == classes
