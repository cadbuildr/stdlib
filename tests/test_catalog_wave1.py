"""First content wave: set / pan head screws, heat-set inserts, dowel pins,
standoffs, flanged / thrust / pillow-block bearings, MGN rails, SK supports,
gear rack + mesh_rack, RC servos, and the new worked examples.

Every part also goes through test_catalog.py (each option builds) and
test_library_practices.py (typed inputs, configurations, interfaces)."""

from __future__ import annotations

import math

import pytest

from cadbuildr.foundation import Assembly, BoolParameter, FloatParameter, RevoluteJoint
from cadbuildr.foundation import make_anchor
from cadbuildr.foundation.compute_functions import component_frames
from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.interfaces import interfaces_of, spec_of
from cadbuildr.foundation.math_utils import (
    compose_tf,
    invert_tf,
    quaternion_rotate_vector,
    tf_relative_to_frame,
)

from cadbuildr.stdlib import examples
from cadbuildr.stdlib.actuators.servos import Servo
from cadbuildr.stdlib.bearings import FlangedBearing, PillowBlock, ThrustBearing
from cadbuildr.stdlib.examples.basics import _plate
from cadbuildr.stdlib.fasteners import (
    DIN912Screw,
    DowelPin,
    HeatSetInsert,
    HexStandoff,
    PanHeadScrew,
    SetScrew,
    connect_heat_set_insert,
    connect_with_screw,
)
from cadbuildr.stdlib.linear_motion.rails import (
    LinearRail,
    RailCarriage,
    mount_carriage,
)
from cadbuildr.stdlib.linear_motion.smooth_rods.shaft_support_part import ShaftSupport
from cadbuildr.stdlib.power_transmission.gears import GearRack, SpurGear, mesh_rack
from cadbuildr.stdlib.power_transmission.gears.rack_part import rack_outline
from cadbuildr.stdlib.power_transmission.gears.spur_gear_part import (
    spur_gear_outline,
)


def _world(anchor, assembly):
    return tf_relative_to_frame(anchor.frame, component_frames(assembly))


def _types(part):
    return sorted({spec_of(n).type_name for n in interfaces_of(part)})


# --------------------------------------------------------------------------- #
# Fasteners
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("point", ["flat", "cone", "dog", "cup"])
def test_set_screw_points_build_and_honour_the_fastener_contract(point):
    screw = SetScrew("M5", 10, point, with_thread=False)
    assert screw.body_height == 10 and screw.fastener_size == "M5"
    assert show_dag(screw)["DAG"]


def test_set_screw_too_short_fails_loudly():
    with pytest.raises(ValueError, match="too short"):
        SetScrew("M12", 4, "dog")
    with pytest.raises(ValueError, match="choose from"):
        SetScrew("M4", 10, "oval")


def test_pan_head_screw_is_a_fastener():
    screw = PanHeadScrew("M2", 6, with_thread=False)
    assert _types(screw) == ["ScrewHead", "ScrewTip"]
    assert screw.head_radius == pytest.approx(2.0)


def test_heat_set_insert_sits_flush_and_cuts_its_pocket():
    base = _plate(30.0, 30.0, 8.0)
    insert = HeatSetInsert("M3")
    assembly = Assembly()
    assembly.add_component(base)
    conn = connect_heat_set_insert(assembly, insert, base.anchor("hole"))
    assert conn is insert
    top, _ = _world(insert.anchor("top"), assembly)
    face, _ = _world(base.anchor("hole"), assembly)
    assert top == pytest.approx(face)  # flush
    bottom, _ = _world(insert.anchor("bottom"), assembly)
    assert bottom[2] == pytest.approx(face[2] - insert.length)
    assert "InsertBody" in _types(insert) and "ScrewHole" in _types(insert)
    show_dag(assembly)


def test_connect_heat_set_insert_rejects_a_non_insert():
    assembly = Assembly()
    base = _plate(30.0, 30.0, 8.0)
    assembly.add_component(base)
    with pytest.raises(TypeError, match="not a threaded insert"):
        connect_heat_set_insert(assembly, DowelPin("3", 10), base.anchor("hole"))


def test_connect_with_screw_into_needs_a_depth():
    assembly = Assembly()
    base = _plate(30.0, 30.0, 8.0)
    assembly.add_component(base)
    with pytest.raises(ValueError, match="into_depth"):
        connect_with_screw(
            assembly,
            DIN912Screw("M3", 8, with_thread=False),
            base.anchor("hole"),
            into=base.anchor("bottom"),
        )


def test_dowel_pin_length_bounds():
    pin = DowelPin("6", 20)
    assert _types(pin) == ["Shaft", "ShaftEnd"]
    with pytest.raises(ValueError, match="out of range"):
        DowelPin("10", 12)  # shorter than 2 x d


def test_standoff_kinds():
    ff = HexStandoff("M3", 10, "female-female")
    mf = HexStandoff("M3", 10, "male-female")
    assert _types(ff) == ["NutSeat"]
    assert _types(mf) == ["NutSeat", "ScrewTip"]
    assert "stud_tip" in {a.name.value for a in mf.anchors}
    with pytest.raises(ValueError, match="kind"):
        HexStandoff("M3", 10, "male-male")


# --------------------------------------------------------------------------- #
# Bearings, supports, servos
# --------------------------------------------------------------------------- #


def test_flanged_bearing_flange_seat_below_the_top():
    b = FlangedBearing("F608")
    assert b.flange_radius > b.outer_radius
    assert "flange_seat" in {a.name.value for a in b.anchors}
    assert _types(b) == ["BearingFace", "Bore"]
    assert _types(ThrustBearing("51104")) == ["BearingFace", "Bore"]


def test_pillow_block_and_shaft_support_carry_a_shaft_parallel_to_the_face():
    for part, axis, height in (
        (PillowBlock("KP08"), "axis", 15.0),
        (ShaftSupport("SK8"), "axis", 20.0),
    ):
        pos, q = tf_relative_to_frame(part.anchor(axis).frame)
        assert pos[2] == pytest.approx(height)
        assert quaternion_rotate_vector(q, [0, 0, 1]) == pytest.approx([0, 1, 0])
        assert "ScrewHole" in _types(part)
    assert "RodHole" in _types(ShaftSupport("SK12"))


def test_servo_spline_offset_and_mount_holes():
    s = Servo("MG996R")
    pos, _ = tf_relative_to_frame(s.anchor("horn").frame)
    assert pos[0] == pytest.approx(10.0)
    assert _types(s) == ["PlaneFace", "ScrewHole", "Shaft", "ShaftEnd"]


# --------------------------------------------------------------------------- #
# MGN rails
# --------------------------------------------------------------------------- #


def test_rail_holes_are_centred_at_the_series_pitch():
    rail = LinearRail("MGN12", 300)
    assert rail.hole_count == 12 and rail.end_distance == pytest.approx(12.5)
    names = {a.name.value for a in rail.anchors}
    assert {"datum", "bottom", "mount_hole_0", "mount_hole_11"} <= names


def test_carriage_slides_along_the_rail():
    rail = LinearRail("MGN9", 200)
    carriage = RailCarriage("MGN9", "C")
    assembly = Assembly()
    assembly.add_component(rail)
    slide = mount_carriage(assembly, rail, carriage, at=60)
    pos, _ = _world(carriage.anchor("datum"), assembly)
    assert pos == pytest.approx([0.0, 0.0, 60.0])
    slide.set_offset(120.0)
    pos, _ = _world(carriage.anchor("datum"), assembly)
    assert pos[2] == pytest.approx(120.0)


def test_carriage_connects_to_its_rail_by_interface():
    rail = LinearRail("MGN12", 300)
    carriage = RailCarriage("MGN12", "H")
    assembly = Assembly()
    assembly.add_component(rail)
    assembly.connect(carriage.interface("datum"), rail.interface("datum"), offset=100)
    pos, _ = _world(carriage.anchor("datum"), assembly)
    assert pos[2] == pytest.approx(100.0)


def test_mount_carriage_fails_loudly():
    rail = LinearRail("MGN12", 100)
    assembly = Assembly()
    assembly.add_component(rail)
    with pytest.raises(ValueError, match="MGN9 carriage on an MGN12 rail"):
        mount_carriage(assembly, rail, RailCarriage("MGN9"))
    with pytest.raises(ValueError, match="off"):
        mount_carriage(assembly, rail, RailCarriage("MGN12", "H"), at=5)


# --------------------------------------------------------------------------- #
# Rack and pinion
# --------------------------------------------------------------------------- #


def _inside(pt, poly):
    x, y = pt
    hit = False
    j = len(poly) - 1
    for i, (xi, yi) in enumerate(poly):
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def _rack_pinion(teeth, angle=0.0, flip=False, child="axis"):
    frame = _plate(60.0, 20.0, 4.0)
    pinion = SpurGear(module=1, teeth=teeth, face_width=6, bore=5)
    rack = GearRack(module=1, length=120, face_width=8, height=8)
    rack.add_anchor(make_anchor("probe", (0.0, 0.0, 0.0)))
    assembly = Assembly()
    assembly.add_component(frame)
    spin = RevoluteJoint(
        parent_anchor=frame.anchor("hole").offset([0.0, 0.0, 10.0], name="axle"),
        child_anchor=pinion.anchor(child),
        angle=FloatParameter(value=angle),
        flip=BoolParameter(value=flip),
    )
    assembly.add_joint(spin)
    slide, relation = mesh_rack(assembly, pinion, rack, spin)
    return assembly, pinion, rack, spin, slide


def _rack_in_pinion_frame(assembly, pinion, rack):
    tp, qp = _world(pinion.anchor("axis"), assembly)
    tr, qr = _world(rack.anchor("probe"), assembly)
    ti, qi = invert_tf(tp, qp)
    return compose_tf(ti, qi, tr, qr)


@pytest.mark.parametrize("teeth", [12, 17, 20])
@pytest.mark.parametrize("flip,child", [(False, "axis"), (True, "pitch_plane")])
def test_rack_meshes_without_overlap_while_the_pinion_turns(teeth, flip, child):
    assembly, pinion, rack, spin, slide = _rack_pinion(teeth, flip=flip, child=child)
    gear = spur_gear_outline(1, teeth)
    tooth = rack_outline(1, rack.teeth, rack.height)
    r = pinion.pitch_radius
    for step in range(9):
        spin.set_angle(step * (2 * math.pi / teeth) / 8)
        t, q = _rack_in_pinion_frame(assembly, pinion, rack)
        # Rack plane parallel to the gear, mid face widths aligned.
        # (antiparallel when the pinion joint flips it: the rack is symmetric)
        assert abs(quaternion_rotate_vector(q, [0, 0, 1])[2]) == pytest.approx(1.0)
        mid = quaternion_rotate_vector(q, [0, 0, rack.face_width / 2])
        assert t[2] + mid[2] == pytest.approx(pinion.face_width / 2)
        pts = []
        for x, y in tooth:
            p = quaternion_rotate_vector(q, [x, y, 0.0])
            pts.append((p[0] + t[0], p[1] + t[1]))
        near = [p for p in pts if math.hypot(*p) < r + 2]
        assert near, "rack is not at the pinion"
        # Engaged: rack tips reach the pinion's dedendum region...
        assert min(math.hypot(*p) for p in pts) == pytest.approx(r - 1.0, abs=0.2)
        # ...without any rack vertex inside a tooth, or tooth vertex in the rack.
        assert not [p for p in near if _inside(p, gear)], (teeth, step)
        assert not [g for g in gear if math.hypot(*g) > r - 1.3 and _inside(g, pts)]


def test_rack_follows_the_pinion_angle():
    assembly, pinion, rack, spin, slide = _rack_pinion(20)
    x0 = slide.offset.value
    spin.set_angle(0.5)
    assert slide.offset.value - x0 == pytest.approx(0.5 * pinion.pitch_radius)
    slide.set_offset(x0 - pinion.pitch_radius)
    assert spin.angle.value == pytest.approx(-1.0)


def test_mesh_rack_fails_loudly():
    frame = _plate(60.0, 20.0, 4.0)
    pinion = SpurGear(module=1, teeth=20)
    assembly = Assembly()
    assembly.add_component(frame)
    spin = RevoluteJoint(
        parent_anchor=frame.anchor("hole"), child_anchor=pinion.anchor("top")
    )
    assembly.add_joint(spin)
    with pytest.raises(ValueError, match="module"):
        mesh_rack(assembly, pinion, GearRack(module=1.5, length=100), spin)
    with pytest.raises(ValueError, match="'axis' or 'pitch_plane'"):
        mesh_rack(assembly, pinion, GearRack(module=1, length=100), spin)


def test_rack_length_rounds_to_an_even_tooth_count():
    rack = GearRack(module=1, length=100)
    assert rack.teeth % 2 == 0 and rack.length <= 100
    with pytest.raises(ValueError, match="no tooth pair"):
        GearRack(module=3, length=10)


# --------------------------------------------------------------------------- #
# Worked examples
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "build",
    [
        examples.build_rack_and_pinion,
        examples.build_rail_slide,
        examples.build_pcb_on_standoffs,
    ],
)
def test_new_examples_build_a_dag(build):
    assembly = build()[0]
    assert show_dag(assembly)["DAG"]


def test_rail_slide_screws_every_rail_hole():
    assembly, parts, joints = examples.build_rail_slide(at=100)
    assert len(parts["screws"]) == parts["rail"].hole_count
    pos, _ = _world(parts["carriage"].anchor("datum"), assembly)
    rail_start, _ = _world(parts["rail"].anchor("datum"), assembly)
    assert math.dist(pos, rail_start) == pytest.approx(100.0)


def test_pcb_sits_on_all_four_standoffs():
    assembly, parts = examples.build_pcb_on_standoffs(standoff_length=12)
    base_top = _world(parts["base"].anchor("corner_0_top"), assembly)[0][2]
    for i, standoff in enumerate(parts["standoffs"]):
        under_pcb = _world(parts["pcb"].anchor(f"corner_{i}_bottom"), assembly)[0]
        free_end = _world(standoff.anchor("bottom"), assembly)[0]
        assert under_pcb == pytest.approx(free_end), i
        assert free_end[2] == pytest.approx(base_top + 12)
