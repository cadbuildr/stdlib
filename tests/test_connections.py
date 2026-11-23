"""Fastener contract, bolt-and-nut stacks, gear meshing and the example assemblies."""

import math

import pytest

from cadbuildr.foundation import Assembly, Part, make_anchor
from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.math_utils import (
    quaternion_rotate_vector,
    tf_relative_to_frame,
)

from cadbuildr.stdlib.examples import (
    _plate,
    bolted_plate,
    build_bolted_plate,
    build_gear_pair,
    build_motor_leadscrew_stack,
    gear_pair,
    motor_leadscrew_stack,
)
from cadbuildr.stdlib.fasteners import (
    ButtonHeadSocketScrew,
    CheeseHeadSlottedScrew,
    CountersunkSlottedScrew,
    CountersunkSocketScrew,
    DIN125Washer,
    DIN912Screw,
    Fastener,
    HexBolt,
    HexNut,
    is_fastener,
    WoodScrew,
    connect_with_bolt_and_nut,
    connect_with_screw,
)
from cadbuildr.stdlib.power_transmission.gears import (
    SpurGear,
    center_distance,
    mesh_gears,
    mesh_phase,
)


def _world(anchor, assembly):
    t, q = tf_relative_to_frame(anchor.frame, assembly.frame)
    return t, quaternion_rotate_vector(q, [0.0, 0.0, 1.0])


SCREWS = [
    lambda: DIN912Screw("M4", 16, with_thread=False),
    lambda: HexBolt("M4", 16, with_thread=False),
    lambda: CheeseHeadSlottedScrew("M4", 16, with_thread=False),
    lambda: CountersunkSlottedScrew("M4", 16, with_thread=False),
    lambda: CountersunkSocketScrew("M4", 16, with_thread=False),
    lambda: ButtonHeadSocketScrew("M4", 16, with_thread=False),
    lambda: WoodScrew("8", 32),
]


@pytest.mark.parametrize("make", SCREWS)
def test_every_screw_honours_the_contract(make):
    screw = make()
    assert isinstance(screw, Fastener)
    assert is_fastener(screw)
    assert not is_fastener(Part())
    assert screw.body_radius > 0 and screw.body_height > 0


@pytest.mark.parametrize("make", SCREWS)
def test_connect_with_screw_works_for_every_screw(make):
    screw = make()
    plate = _plate(40, 40, 6)
    assembly = Assembly()
    assembly.add_component(plate)
    connect_with_screw(assembly, screw, plate.anchor("hole"))
    seat, _ = _world(screw.anchor("head_seat"), assembly)
    tip, tip_z = _world(screw.anchor("tip"), assembly)
    assert seat == pytest.approx([0, 0, 6])
    assert tip == pytest.approx([0, 0, 6 - screw.body_height])
    assert tip_z == pytest.approx(
        [0, 0, -1], abs=1e-9
    )  # tip points down, into the plate


def test_connect_with_screw_rejects_non_fasteners():
    plate = _plate(40, 40, 6)
    assembly = Assembly()
    assembly.add_component(plate)
    with pytest.raises(TypeError, match="not a fastener"):
        connect_with_screw(assembly, Part(), plate.anchor("hole"))


def test_bolt_and_nut_stack_positions():
    assembly, p = build_bolted_plate(with_thread=False)
    plate, washer_h, bolt, washer_n, nut = (
        p["plate"],
        p["head_washer"],
        p["bolt"],
        p["nut_washer"],
        p["nut"],
    )
    w = 1.6  # DIN 125 M8 thickness
    # Bolt head washer on top of the plate, bolt seated on the washer.
    assert _world(washer_h.anchor("top"), assembly)[0] == pytest.approx([0, 0, 8 + w])
    seat, seat_z = _world(bolt.anchor("head_seat"), assembly)
    assert seat == pytest.approx([0, 0, 8 + w])
    assert seat_z == pytest.approx([0, 0, -1], abs=1e-9)
    # Nut washer under the plate, nut under the washer, nut points away.
    assert _world(washer_n.anchor("bottom"), assembly)[0] == pytest.approx([0, 0, 0])
    nut_bottom, nut_normal = _world(nut.anchor("bottom"), assembly)
    assert nut_bottom == pytest.approx([0, 0, -w])
    assert nut_normal == pytest.approx([0, 0, 1], abs=1e-9)
    assert _world(nut.anchor("top"), assembly)[0] == pytest.approx([0, 0, -w - 6.5])
    # Tip passes through the nut.
    assert _world(bolt.anchor("tip"), assembly)[0][2] < -w - 6.5
    # Clearance hole was drilled through the plate (box + bore).
    assert len(plate.operations) == 2
    assert len(assembly.joints) == 4


def test_bolt_and_nut_with_exit_anchor_and_no_washers():
    plate = _plate(40, 40, 8)
    plate.add_anchor(make_anchor("under", (0.0, 0.0, 0.0), z_down=True))
    assembly = Assembly()
    assembly.add_component(plate)
    nut = HexNut("M8", with_thread=False)
    connect_with_bolt_and_nut(
        assembly,
        HexBolt("M8", 20, with_thread=False),
        nut,
        plate.anchor("hole"),
        exit_anchor=plate.anchor("under"),
        drill=False,
    )
    assert _world(nut.anchor("bottom"), assembly)[0] == pytest.approx([0, 0, 0])
    assert _world(nut.anchor("top"), assembly)[0] == pytest.approx([0, 0, -6.5])


def test_bolt_too_short_raises():
    plate = _plate(40, 40, 20)
    assembly = Assembly()
    assembly.add_component(plate)
    with pytest.raises(ValueError, match="too short"):
        connect_with_bolt_and_nut(
            assembly,
            HexBolt("M8", 16, with_thread=False),
            HexNut("M8", with_thread=False),
            plate.anchor("hole"),
            grip=20,
        )


def test_bolt_and_nut_needs_grip_or_exit():
    plate = _plate(40, 40, 8)
    assembly = Assembly()
    assembly.add_component(plate)
    with pytest.raises(ValueError, match="grip"):
        connect_with_bolt_and_nut(
            assembly,
            HexBolt("M8", 30, with_thread=False),
            HexNut("M8", with_thread=False),
            plate.anchor("hole"),
        )


def test_gear_mesh_center_distance_and_phase():
    pinion, wheel = SpurGear(1, 12, 6, 5), SpurGear(1, 30, 6, 8)
    assert center_distance(pinion, wheel) == pytest.approx(21.0)
    assert mesh_phase(pinion, wheel) == pytest.approx(
        math.pi / 30
    )  # even -> half tooth
    assert mesh_phase(pinion, SpurGear(1, 31, 6, 8)) == pytest.approx(0.0)

    assembly, p = build_gear_pair()
    pinion, wheel = p["pinion"], p["wheel"]
    c, z = _world(wheel.anchor("axis"), assembly)
    assert c == pytest.approx([21.0, 0.0, 0.0])
    assert z == pytest.approx([0, 0, 1], abs=1e-9)  # parallel axes, same side up
    pp_p, _ = _world(pinion.anchor("pitch_plane"), assembly)
    pp_w, _ = _world(wheel.anchor("pitch_plane"), assembly)
    assert pp_p[2] == pytest.approx(pp_w[2])  # coplanar pitch planes


def test_gear_mesh_at_angle_and_module_check():
    pinion, wheel = SpurGear(2, 10, 6, 5), SpurGear(2, 20, 6, 8)
    assembly = Assembly()
    assembly.add_component(pinion)
    mesh_gears(assembly, pinion, wheel, angle=math.pi / 2)
    c, _ = _world(wheel.anchor("axis"), assembly)
    assert c == pytest.approx([0.0, 30.0, 0.0], abs=1e-9)
    with pytest.raises(ValueError, match="module"):
        mesh_gears(Assembly(), SpurGear(1, 10, 6, 5), SpurGear(2, 10, 6, 5))


def test_motor_coupling_leadscrew_stack():
    assembly, p = build_motor_leadscrew_stack(with_thread=False)
    coupling, lead, nut = p["coupling"], p["lead_screw"], p["nut"]
    shaft_tip = 40 + 24
    # Shaft inserted half the coupling; screw starts at mid-coupling.
    assert _world(coupling.anchor("end_a"), assembly)[0] == pytest.approx(
        [0, 0, shaft_tip - 12.5]
    )
    assert _world(lead.anchor("end_a"), assembly)[0] == pytest.approx([0, 0, shaft_tip])
    end_b, end_b_z = _world(lead.anchor("end_b"), assembly)
    assert end_b == pytest.approx([0, 0, shaft_tip + 200])
    assert end_b_z == pytest.approx([0, 0, 1], abs=1e-9)
    assert _world(nut.anchor("axis"), assembly)[0] == pytest.approx(
        [0, 0, shaft_tip + 120]
    )


@pytest.mark.parametrize("build", [bolted_plate, motor_leadscrew_stack, gear_pair])
def test_examples_serialize(build):
    dag = show_dag(build())
    root = dag["DAG"][dag["rootNodeId"]]
    assert root["deps"]["components"]
    assert root["deps"].get("joints")
