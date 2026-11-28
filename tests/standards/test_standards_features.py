"""Hole / bore helpers: geometry sized from the tables + connectable interfaces,
and the configurable demo parts / assemblies built from them."""

import json
import subprocess
import sys

import pytest

from cadbuildr.foundation import Assembly, Extrusion, Part, Sketch, Square, make_anchor
from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.math_utils import tf_relative_to_frame
from cadbuildr.stdlib.fasteners.screws_and_bolts.din912_part import DIN912Screw
from cadbuildr.stdlib.standards import (
    StandardsError,
    clearance_hole,
    counterbored_hole,
    countersunk_hole,
    fitted_bore,
    heat_set_insert_hole,
    self_tap_screw_hole,
    tapped_hole,
    tapped_holes,
)
from cadbuildr.stdlib.standards.demos import (
    FIT_COLORS,
    BearingFitDemo,
    BoltedJointDemo,
    ClampPlate,
    FitTestCoupon,
    FittedShaft,
    TappedBlock,
)


def _plate(thickness=10.0):
    p = Part()
    p.add_operation(
        Extrusion(Square.from_center_and_side(Sketch(p.xy()).origin, 60), thickness)
    )
    p.add_anchor(make_anchor("h", (10.0, 0.0, thickness)))
    return p


def _params(node):
    return json.loads(node.params.value)


def test_tapped_hole():
    p = _plate()
    ops = len(p.operations)
    f = tapped_hole(p.anchor("h"), "M5", 10)
    assert len(p.operations) == ops + 1
    assert f.diameter == 4.2 and f.operation.cut.value is True
    assert f.interface.type.value == "ScrewHole"
    assert _params(f.interface) == {"size": "M5", "depth": 10.0, "thread": True}
    show_dag(p)


def test_tapped_holes_on_a_pattern_share_a_group():
    p = _plate()
    anchors = p.anchor("h").linear_pattern(3, 12.0)
    p.add_anchors(anchors)
    tapped_holes(anchors, "M3", 6, group="mount")
    assert len(p.group("mount")) == 3


def test_clearance_and_countersunk_holes():
    p = _plate()
    f = clearance_hole(p.anchor("h"), "M6", 10, "close")
    assert f.diameter == 6.4 and _params(f.interface)["drilled"] is True
    q = _plate()
    c = countersunk_hole(q.anchor("h"), "M4", 10)
    assert c.operation.csink_radius.value == pytest.approx(4.48)
    show_dag(q)


def test_counterbore_seat_is_on_the_floor_and_a_screw_connects():
    p = _plate(10.0)
    f = counterbored_hole(p.anchor("h"), "M5", 10, group="bolts")
    assert f.seat.name.value == "h_seat"
    assert _params(f.interface)["depth"] == pytest.approx(10 - 5.4)
    asm = Assembly()
    asm.ground(p)
    screw = DIN912Screw("M5", 12, with_thread=False)
    asm.connect(screw, p.interface("h_seat"))
    t, _ = tf_relative_to_frame(screw.anchor("head_seat").frame, asm.frame)
    assert t == pytest.approx([10.0, 0.0, 10.0 - 5.4])
    assert asm.check() == []
    show_dag(asm)


def test_counterbore_needs_material():
    with pytest.raises(StandardsError, match="needs more than"):
        counterbored_hole(_plate(5.0).anchor("h"), "M5", 5)


def test_insert_and_self_tap_holes_are_threaded_screw_holes():
    p = _plate()
    f = heat_set_insert_hole(p.anchor("h"), "M3")
    assert f.diameter == 4.0 and f.operation.cut.value is True
    assert _params(f.interface) == {"size": "M3", "depth": 5.7, "thread": True}
    q = _plate()
    s = self_tap_screw_hole(q.anchor("h"), "M3", material="ABS")
    assert s.diameter == pytest.approx(2.4) and _params(s.interface)["thread"] is True


def test_fitted_bore_binds_bore_with_its_fit():
    p = _plate()
    f = fitted_bore(p.anchor("h"), 8, "H7", depth=10)
    assert f.diameter == pytest.approx(8.0075)
    assert _params(f.interface) == {"d": 8.0, "fit": "H7"}
    assert fitted_bore(
        _plate().anchor("h"), 8, "H7", model="max"
    ).diameter == pytest.approx(8.015)
    with pytest.raises(StandardsError, match="shaft tolerance"):
        fitted_bore(_plate().anchor("h"), 8, "g6")


def test_unregistered_anchor_fails_loudly():
    with pytest.raises(Exception):
        tapped_hole(make_anchor("loose"), "M5", 10)


# --------------------------------------------------------------------------- #
# Demo items
# --------------------------------------------------------------------------- #

STANDARD_ITEMS = {
    "BearingFitDemo",
    "FittedHousing",
    "FittedShaft",
    "FitTestCoupon",
    "BoltedJointDemo",
    "ClampPlate",
    "TappedBlock",
    "ParallelKey",
    "ORingSeal",
    "KeyedShaft",
    "CaptiveNutBlock",
    "CaptiveNutDemo",
}


# register() declares the demo items in this process only: run it in a
# subprocess so stdlib's catalog-wide tests in this session keep their view.
_MANIFEST_SCRIPT = """
import json, warnings
warnings.simplefilter("ignore")
from cadbuildr.stdlib.standards.demos import register
from cadbuildr.foundation.library import get_manifest
from cadbuildr.foundation.library.evaluate import evaluate
register()
m = get_manifest("cadbuildr.stdlib")
out = {"errors": m.get("errors"), "sections": {s["id"]: s["items"] for s in m["toolbar"]["sections"]}, "items": {}}
for i in m["items"]:
    if ".standards." not in i["module"]:
        continue
    out["items"][i["cls"]] = {
        "anchors": i["anchors"], "standard": i["standard"],
        "widgets": sorted({x["widget"]["kind"] for x in i["inputs"]}),
        "configurations": {
            c["name"]: evaluate({"item": i["id"], "inputs": c["values"]})["ok"]
            for c in i["configurations"]
        },
    }
print(json.dumps(out))
"""


@pytest.fixture(scope="module")
def manifest():
    proc = subprocess.run(
        [sys.executable, "-c", _MANIFEST_SCRIPT],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_demo_items_are_not_declared_at_import():
    from cadbuildr.foundation.library import item_for

    assert item_for(BoltedJointDemo) is None


def test_manifest_lists_the_standards_section(manifest):
    assert manifest["errors"] is None
    assert {f"stdlib:{c}" for c in STANDARD_ITEMS} == set(
        manifest["sections"]["standards"]
    )


@pytest.mark.parametrize("cls", sorted(STANDARD_ITEMS))
def test_every_configuration_evaluates(manifest, cls):
    item = manifest["items"][cls]
    assert item["configurations"] and item["anchors"] and item["standard"]
    assert set(item["widgets"]) <= {"enum", "number", "bool", "text"}
    assert all(item["configurations"].values()), item["configurations"]


def test_bolted_joint_screws_reach_into_the_tapped_holes():
    asm = BoltedJointDemo(size="M5", n=2, plate_thickness=10)
    assert asm.screw_length == 16 and len(asm.screws) == 2
    assert asm.check() == []
    for screw in asm.screws:
        head, _ = tf_relative_to_frame(screw.anchor("head_seat").frame, asm.frame)
        tip, _ = tf_relative_to_frame(screw.anchor("tip").frame, asm.frame)
        block_top = 20.0  # TappedBlock height
        assert head[2] == pytest.approx(block_top + 10 - 5.4)  # counterbore floor
        assert block_top - 12.5 < tip[2] < block_top  # inside the 11.5 mm tapped depth
    show_dag(asm)


def test_bolted_joint_clearance_variant():
    asm = BoltedJointDemo(size="M8", n=4, plate_thickness=12, holes="clearance")
    assert asm.screw_length == 25 and len(asm.screws) == 4
    assert asm.check() == []


def test_tapped_block_and_plate_validate():
    with pytest.raises(StandardsError, match="tapped depth"):
        TappedBlock(size="M8", height=10, depth=9)
    plate = ClampPlate(size="M4", n=3, thickness=8)
    assert len(plate.group("bolts")) == 3


@pytest.mark.parametrize(
    "tol,kind",
    [
        ("g6", "transition"),
        ("h6", "transition"),
        ("k6", "interference"),
        ("f6", "clearance"),
    ],
)
def test_fitted_shaft_colour_follows_the_fit(tol, kind):
    shaft = FittedShaft(d=8.0, tolerance=tol)
    assert shaft.fit.kind == kind


def test_bearing_fit_demo_exaggerates_the_fit():
    true = BearingFitDemo(shaft_tolerance="p6")
    big = BearingFitDemo(shaft_tolerance="p6", exaggerate=100)
    assert true.shaft_fit.kind == "interference"
    assert FIT_COLORS[true.shaft_fit.kind] == "#d0453c"
    # p6 on 8 mm: mean +0.0195 -> x100 = +1.95 mm on the modelled diameter.
    assert big.shaft.modeled_diameter == pytest.approx(8 + 1.95)
    assert true.shaft.modeled_diameter == pytest.approx(8.0195)
    show_dag(big)


def test_fit_test_coupon_holes():
    c = FitTestCoupon(pin=8, process="fdm")
    assert c.diameters == {"press": 8.0, "snug": 8.15, "sliding": 8.3, "loose": 8.5}
