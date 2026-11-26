"""Motion kits: manifest entries + widgets of the new parts and of the stdlib
parts the demos reuse, the two demo layouts (every item evaluates, placements
are one-rotation, parts sit on what they mate with) and their bindings."""

import json

import numpy as np
import pytest

from cadbuildr.foundation.compute_functions import _SOURCE_COMPONENT_ATTR
from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.library import get_manifest
from cadbuildr.foundation.library.evaluate import evaluate
from cadbuildr.foundation.math_utils import (
    quaternion_rotate_vector,
    tf_relative_to_frame,
)
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
    assert list(w) == ["rod", "spacing", "length", "belt_clamp", "lead_screw"]
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
        ("stdlib:LinearBearing", {"model": "enum"}),
        ("stdlib:LeadScrewT8", {"length": "number", "with_thread": "bool"}),
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
        ("stdlib:AluExtrusion", {"series": "enum", "length": "number"}),
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
    off, on = Carriage(), Carriage(belt_clamp=True)
    names = lambda part: {a.name.value for a in part.anchors}  # noqa: E731
    assert "belt_clamp" in names(on) and "belt_clamp" not in names(off)
    assert len(on.operations) > len(off.operations)


# --------------------------------------------------------------------------- #
# Layouts
# --------------------------------------------------------------------------- #


def test_layout_sizes_and_shape():
    assert 15 <= len(LAYOUTS["linear_stage"]["items"]) <= 32
    assert 50 <= len(LAYOUTS["xy_gantry"]["items"]) <= 80
    for layout in LAYOUTS.values():
        json.dumps(layout)
        names = [e["name"] for e in layout["items"]]
        assert len(names) == len(set(names))
        for e in layout["items"]:
            assert set(e) == {"name", "item", "inputs", "translate", "rotate", "mates"}
            assert e["item"] in ITEMS, e["item"]
            assert len(e["translate"]) == 3
            # the viewer places with ONE rotation about X, Y or Z
            assert e["rotate"] is None or (
                set(e["rotate"]) == {"axis", "angle"} and e["rotate"]["axis"] in "XYZ"
            )
            assert set(e["inputs"]) <= {i["name"] for i in ITEMS[e["item"]]["inputs"]}
            assert set(e["mates"]) <= set(names)


def _unique_requests():
    seen = {}
    for layout in LAYOUTS.values():
        for e in layout["items"]:
            key = json.dumps([e["item"], e["inputs"]], sort_keys=True)
            seen.setdefault(key, pytest.param(e["item"], e["inputs"], id=e["name"]))
    return list(seen.values())


@pytest.mark.parametrize("item_id,inputs", _unique_requests())
def test_every_layout_item_evaluates(item_id, inputs):
    result = evaluate({"item": item_id, "inputs": inputs})
    assert result["ok"], result.get("error")
    dag = result["dag"]
    root = dag["DAG"][dag["rootNodeId"]]
    assert root["deps"].get("anchors"), item_id


@pytest.mark.parametrize("name", list(LAYOUTS))
def test_no_floating_part(name):
    """Every part is connected (through ``mates``) to the rest of the build."""
    items = LAYOUTS[name]["items"]
    adj = {e["name"]: set() for e in items}
    for e in items:
        for m in e["mates"]:
            adj[e["name"]].add(m)
            adj[m].add(e["name"])
    seen, todo = set(), [items[0]["name"]]
    while todo:
        n = todo.pop()
        if n not in seen:
            seen.add(n)
            todo.extend(adj[n] - seen)
    assert seen == set(adj), sorted(set(adj) - seen)


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


def _placed(layout):
    asm = demos.build_from_layout(layout)
    comps = {
        root.name.value: getattr(root, _SOURCE_COMPONENT_ATTR)
        for root in asm.components
    }

    def world(name, anchor):
        a = comps[name].anchor(anchor)
        assert a is not None, (name, anchor)
        t, q = tf_relative_to_frame(a.frame, asm.frame)
        return np.array(t), np.array(quaternion_rotate_vector(list(q), [0.0, 0.0, 1.0]))

    return asm, comps, world


def _seated(world, comps, name, anchor, mates, on_axis=False):
    """``name.anchor`` coincides, facing it, with some anchor of a mate (or,
    ``on_axis``, some mate anchor lies on its axis, parallel: a screw in a hole)."""
    p, z = world(name, anchor)
    for m in mates:
        for a in comps[m].anchors:
            q, n = world(m, a.name.value)
            if on_axis:
                if np.allclose(np.cross(q - p, z), 0, atol=1e-6) and np.allclose(
                    np.cross(n, z), 0, atol=1e-6
                ):
                    return True
            elif np.allclose(p, q, atol=1e-6) and np.allclose(z, -n, atol=1e-6):
                return True
    return False


# (stdlib class, anchor that must sit on an anchor of one of its mates)
SEATS = {
    "SmoothRod": "end_a",
    "LinearBearing": "end_a",
    "DIN912Screw": "head_seat",
    "StepperMotor": "mount_face",
    "ClampCoupling": "bore_a_stop",
    "LeadScrewT8": "end_a",
    "LeadScrewNutT8": "flange_seat",
    "DeepGrooveBearing": "top",
    "MotorMount": "mount_hole_0",
}


@pytest.mark.parametrize("name", list(LAYOUTS))
def test_parts_sit_on_their_mates(name):
    layout = LAYOUTS[name]
    _, comps, world = _placed(layout)
    checked = 0
    for e in layout["items"]:
        cls = e["item"].split(":")[1]
        if cls in SEATS and e["mates"]:
            screw = cls == "DIN912Screw"
            assert _seated(
                world, comps, e["name"], SEATS[cls], e["mates"], on_axis=screw
            ), e["name"]
            checked += 1
    assert checked >= len(layout["items"]) // 2


def test_belt_runs_through_the_clamp():
    """X pulleys' belt plane is the X carriage clamp slot centre height."""
    layout = demos.xy_gantry_layout()
    for e in layout["items"]:
        if e["name"] == "x_carriage":
            e["inputs"]["belt_clamp"] = True
    _, _, world = _placed(layout)
    clamp, _ = world("x_carriage", "belt_clamp")
    for pulley in ("x_pulley", "x_idler_pulley"):
        p, _ = world(pulley, "belt_plane")
        assert p[2] == pytest.approx(clamp[2])
    assert demos.check_layout_interference(layout) == []


def test_build_functions_serialize():
    for build in (demos.build_linear_stage, demos.build_xy_gantry):
        dag = show_dag(build())
        assert dag["DAG"][dag["rootNodeId"]]["deps"]["components"]


# --------------------------------------------------------------------------- #
# Bindings
# --------------------------------------------------------------------------- #


def _binding(layout, name):
    return next(b for b in layout["bindings"] if b["input"] == name)


@pytest.mark.parametrize("name", list(LAYOUTS))
def test_rod_binding_covers_rods_bearings_plates_carriages(name):
    layout = LAYOUTS[name]
    b = _binding(layout, "rod")
    bound = {t["index"] for t in b["targets"]}
    for i, e in enumerate(layout["items"]):
        cls = e["item"].split(":")[1]
        if cls in (
            "SmoothRod",
            "LinearBearing",
            "RodEndPlate",
            "Carriage",
            "GantryCarriage",
        ):
            assert i in bound, e["name"]
    for t in b["targets"]:
        cls = layout["items"][t["index"]]["item"]
        if cls == "stdlib:LinearBearing":
            assert t["map"] == {"8": "LM8UU", "10": "LM10UU", "12": "LM12UU"}
        else:
            assert "map" not in t
    assert b["moves"] == []


@pytest.mark.parametrize(
    "name,inp",
    [
        ("linear_stage", "rail_length"),
        ("xy_gantry", "y_length"),
        ("xy_gantry", "x_length"),
    ],
)
def test_length_bindings_reproduce_the_layout(name, inp):
    """Applying a length binding by hand equals re-running the layout."""
    fn = getattr(demos, f"{name}_layout")
    base = LAYOUTS[name]
    b = _binding(base, inp)
    new = b["default"] + 100
    expected = fn(**{inp: new})["items"]
    items = json.loads(json.dumps(base["items"]))
    for t in b["targets"]:
        items[t["index"]]["inputs"][t["input"]] = new + t.get("offset", 0)
    for m in b["moves"]:
        tr = items[m["index"]]["translate"]
        items[m["index"]]["translate"] = [
            v + 100 * d for v, d in zip(tr, m["per_unit"])
        ]
    for got, want in zip(items, expected):
        assert got["inputs"] == want["inputs"], got["name"]
        assert got["translate"] == pytest.approx(want["translate"]), got["name"]
    # rods follow the length input directly
    direct = {items[t["index"]]["item"] for t in b["targets"] if "offset" not in t}
    assert "stdlib:SmoothRod" in direct
