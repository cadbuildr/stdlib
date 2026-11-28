"""Wave 3: GT2 belts / idlers + belt_drive, gear trains on GearRelation,
servo horns, shaft collars, circlips, HGR rails, V-wheels."""

from __future__ import annotations

import math

import pytest

from cadbuildr.foundation import Assembly, BoolParameter, FloatParameter, RevoluteJoint
from cadbuildr.foundation.compute_functions import component_frames
from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.math_utils import (
    compose_tf,
    invert_tf,
    quaternion_rotate_vector,
    tf_relative_to_frame,
)

from cadbuildr.stdlib.actuators.servos import Servo, ServoHorn
from cadbuildr.stdlib.examples.basics import _plate
from cadbuildr.stdlib.fasteners.retaining_rings import ExternalCirclip, InternalCirclip
from cadbuildr.stdlib.linear_motion.rails import (
    LinearRail,
    RailCarriage,
    mount_carriage,
)
from cadbuildr.stdlib.linear_motion.rollers import VWheel
from cadbuildr.stdlib.power_transmission.gears import SpurGear, mesh_gears
from cadbuildr.stdlib.power_transmission.gears.spur_gear_part import spur_gear_outline
from cadbuildr.stdlib.power_transmission.pulleys import (
    GT2Belt,
    GT2Idler,
    GT2Pulley,
    belt_drive,
    gt2_center_distance,
    gt2_pitch_radius,
    open_belt_length,
)
from cadbuildr.stdlib.power_transmission.shafts.base_part import Shaft
from cadbuildr.stdlib.power_transmission.shafts.shaft_collar_part import ShaftCollar


def _world(anchor, assembly):
    return tf_relative_to_frame(anchor.frame, component_frames(assembly))


# --------------------------------------------------------------------------- #
# GT2 belts
# --------------------------------------------------------------------------- #


def test_open_belt_length_matches_the_closed_form():
    r = gt2_pitch_radius(20)
    assert open_belt_length(r, r, 100) == pytest.approx(200 + 40)
    # 20T / 40T: longer than the straight-line estimate, shorter than the hull.
    r1, r2 = gt2_pitch_radius(20), gt2_pitch_radius(40)
    est = 2 * 80 + math.pi * (r1 + r2)
    assert est < open_belt_length(r1, r2, 80) < est + 2


@pytest.mark.parametrize("length,za,zb", [(400, 20, 20), (610, 20, 60), (200, 16, 20)])
def test_center_distance_for_a_catalogue_belt_round_trips(length, za, zb):
    c = gt2_center_distance(length, za, zb)
    belt = GT2Belt(za, zb, c)
    assert belt.pitch_length == pytest.approx(length, abs=1e-6)
    assert belt.teeth == length // 2


def test_belt_teeth_follow_the_gt2_profile():
    from cadbuildr.stdlib.power_transmission.pulleys.gt2_belt_part import (
        PLD,
        TOOTH_HEIGHT,
        belt_loop,
        toothed_loop,
    )

    r = gt2_pitch_radius(20)
    land = belt_loop(r - PLD, r - PLD, 100, segments=96)
    pts = toothed_loop(land, 120)
    assert len(pts) == 120 * 8
    # Tooth tips on the pulley arcs reach 0.75 below the land (the groove
    # bottom of a GT2 pulley), never deeper.
    tips = [math.hypot(x, y) for x, y in pts if x < -1.0]
    assert min(tips) == pytest.approx(r - PLD - TOOTH_HEIGHT, abs=0.02)
    # Pulley OD = pitch diameter - 2 x PLD; its grooves are 0.75 deep.
    pulley = GT2Pulley(teeth=20)
    assert pulley.pitch_radius == pytest.approx(r)


def test_belt_rejects_touching_pulleys_and_impossible_lengths():
    with pytest.raises(ValueError, match="touch"):
        GT2Belt(40, 40, 20)
    with pytest.raises(ValueError, match="cannot wrap"):
        gt2_center_distance(60, 20, 40)
    with pytest.raises(ValueError, match="choose from"):
        GT2Belt(20, 20, 100, "8")


def test_belt_drive_places_pulley_and_belt_on_the_belt_plane():
    motor_pulley = GT2Pulley(teeth=20, bore=5)
    driven = GT2Pulley(teeth=40, bore=8)
    assembly = Assembly()
    assembly.add_component(motor_pulley)
    joint, belt = belt_drive(assembly, motor_pulley, driven, 80, angle=math.pi / 2)
    a, _ = _world(motor_pulley.anchor("belt_plane"), assembly)
    b, _ = _world(driven.anchor("belt_plane"), assembly)
    assert b[0] - a[0] == pytest.approx(0.0, abs=1e-9)
    assert b[1] - a[1] == pytest.approx(80.0)
    assert b[2] == pytest.approx(a[2])
    belt_b, _ = _world(belt.anchor("pulley_b"), assembly)
    assert belt_b == pytest.approx(b)
    assert belt.ratio == pytest.approx(2.0)
    show_dag(assembly)


def test_belt_drive_needs_gt2_pulleys():
    assembly = Assembly()
    p = GT2Pulley()
    assembly.add_component(p)
    with pytest.raises(TypeError, match="not a GT2 pulley"):
        belt_drive(assembly, p, Shaft(), 50)


def test_idlers_share_the_20t_pitch_circle():
    smooth, toothed = GT2Idler("smooth", "3"), GT2Idler("toothed", "5")
    assert (
        smooth.pitch_radius
        == toothed.pitch_radius
        == pytest.approx(gt2_pitch_radius(20))
    )
    assert smooth.teeth == 20  # belt_drive treats both as 20T


# --------------------------------------------------------------------------- #
# Gear train on GearRelation
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


def _train(z1, z2, flip=False, child="axis", angle=0.0):
    frame = _plate(80.0, 40.0, 4.0)
    a = SpurGear(module=1, teeth=z1, face_width=6, bore=5)
    b = SpurGear(module=1, teeth=z2, face_width=6, bore=5)
    assembly = Assembly()
    assembly.add_component(frame)
    spin = RevoluteJoint(
        parent_anchor=frame.anchor("hole").offset([0.0, 0.0, 10.0], name="axle"),
        child_anchor=a.anchor(child),
        flip=BoolParameter(value=flip),
    )
    assembly.add_joint(spin)
    driven = mesh_gears(assembly, a, b, angle=angle, driver_joint=spin)
    return assembly, a, b, spin, driven


@pytest.mark.parametrize("z1,z2", [(12, 30), (17, 20), (20, 13)])
@pytest.mark.parametrize("flip,child", [(False, "axis"), (True, "pitch_plane")])
def test_gear_train_turns_together_without_overlap(z1, z2, flip, child):
    assembly, a, b, spin, driven = _train(z1, z2, flip, child, angle=0.4)
    oa, ob = spur_gear_outline(1, z1), spur_gear_outline(1, z2)
    for step in range(7):
        spin.set_angle(step * (2 * math.pi / z1) / 6)
        ta, qa = _world(a.anchor("pitch_plane"), assembly)
        tb, qb = _world(b.anchor("pitch_plane"), assembly)
        ti, qi = invert_tf(ta, qa)
        t, q = compose_tf(ti, qi, tb, qb)
        assert abs(t[2]) == pytest.approx(0.0, abs=1e-9)  # mid planes aligned
        assert math.hypot(t[0], t[1]) == pytest.approx(a.pitch_radius + b.pitch_radius)
        pts = []
        for x, y in ob:
            p = quaternion_rotate_vector(q, [x, y, 0.0])
            pts.append((p[0] + t[0], p[1] + t[1]))
        assert not [p for p in pts if _inside(p, oa)], (z1, z2, step)


def test_gear_relation_ratio_and_direction():
    assembly, a, b, spin, driven = _train(12, 30)
    start = driven.angle.value
    spin.set_angle(1.0)
    assert driven.angle.value - start == pytest.approx(-12 / 30)
    show_dag(assembly)


def test_legacy_mesh_gears_is_unchanged():
    a = SpurGear(module=1, teeth=12)
    b = SpurGear(module=1, teeth=30)
    assembly = Assembly()
    assembly.add_component(a)
    joint = mesh_gears(assembly, a, b)
    assert joint.parent_anchor.name.value.endswith("_center")
    assert not getattr(assembly, "relations", [])


# --------------------------------------------------------------------------- #
# Servo horn, collars, circlips
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("servo", ["SG90", "MG996R"])
def test_horn_connects_onto_the_servo_spline(servo):
    s = Servo(servo)
    horn = ServoHorn(servo, "double")
    assembly = Assembly()
    assembly.ground(s)
    assembly.connect(s.interface("horn"), horn.interface("spline_stop"))
    tip, _ = _world(s.anchor("horn"), assembly)
    bottom, _ = _world(horn.anchor("bottom"), assembly)
    assert bottom[2] == pytest.approx(tip[2] - horn.spline_depth)
    assert bottom[2] >= _world(s.anchor("shaft"), assembly)[0][2] - 1e-9


def test_horn_kinds_have_their_arm_tips():
    assert len(ServoHorn("SG90", "single").arm_tips) == 1
    assert len(ServoHorn("SG90", "cross").arm_tips) == 4
    assert len(ServoHorn("MG996R", "disc").arm_tips) == 4
    with pytest.raises(ValueError, match="kind"):
        ServoHorn("SG90", "star")


def test_collar_slides_on_a_shaft_by_interface():
    shaft = Shaft(diameter=8, length=100)
    collar = ShaftCollar("8")
    assembly = Assembly()
    assembly.ground(shaft)
    assembly.connect(shaft.interface("axis"), collar.interface("axis"), offset=40)
    pos, _ = _world(collar.anchor("axis"), assembly)
    assert pos[2] == pytest.approx(40.0)
    with pytest.raises(Exception):
        Assembly().connect(
            Shaft(diameter=10).interface("axis"), ShaftCollar("8").interface("axis")
        )


def test_circlips():
    ext, inner = ExternalCirclip("8"), InternalCirclip("22")
    assert ext.groove_diameter < 8  # groove cut into the shaft
    assert inner.groove_diameter > 22
    with pytest.raises(ValueError, match="choose from"):
        ExternalCirclip("22")  # DIN 471 table stops at 25 but has no 22


# --------------------------------------------------------------------------- #
# HGR rails, V-wheels
# --------------------------------------------------------------------------- #


def test_hgr20_carriage_on_its_rail():
    rail = LinearRail("HGR20", 600)
    assert rail.hole_pitch == 60 and rail.hole_count == 10
    car = RailCarriage("HGR20", "H")
    assembly = Assembly()
    assembly.add_component(rail)
    mount_carriage(assembly, rail, car, at=300)
    with pytest.raises(ValueError, match="carriage on an"):
        mount_carriage(Assembly(), rail, RailCarriage("MGN12"))


def test_v_wheel_ridge():
    w = VWheel("solid")
    assert w.tip_radius == pytest.approx(11.95)
    assert VWheel("mini").tip_radius < w.tip_radius
