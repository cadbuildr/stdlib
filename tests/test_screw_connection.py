"""Tests for the connect_with_screw one-liner (anchors + Connection hook)."""

import pytest

from cadbuildr.foundation import (
    Assembly,
    Extrusion,
    Part,
    Sketch,
    Square,
    make_anchor,
)
from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.math_utils import (
    quaternion_rotate_vector,
    tf_relative_to_frame,
)

from cadbuildr.stdlib.fasteners.connections import connect_with_screw
from cadbuildr.stdlib.fasteners.screws_and_bolts.din912_part import DIN912Screw


def _make_plate(size=40.0, thickness=6.0):
    plate = Part()
    sketch = Sketch(plate.xy())
    square = Square.from_center_and_side(sketch.origin, size)
    plate.add_operation(Extrusion(square, thickness))
    plate.add_anchor(make_anchor("mount_1", (10.0, 10.0, thickness)))
    return plate


def test_screw_has_mating_anchors():
    screw = DIN912Screw("M4", 16, with_thread=False)
    seat = screw.anchor("head_seat")
    assert seat.frame.position[2] == pytest.approx(screw.body_height)
    assert screw.anchor("tip").frame.position[2] == pytest.approx(0.0)


def test_connect_with_screw_places_and_drills():
    plate = _make_plate(thickness=6.0)
    screw = DIN912Screw("M4", 16, with_thread=False)
    assembly = Assembly()
    assembly.add_component(plate)

    ops_before = len(plate.operations)
    connect_with_screw(assembly, screw, plate.anchor("mount_1"))

    # One-liner effects: the plate gained the clearance bore...
    assert len(plate.operations) == ops_before + 1
    # ...the screw was placed by a joint...
    assert len(assembly.components) == 2
    assert len(assembly.joints) == 1

    # ...seated head-up: the under-head seat sits exactly on the anchor and
    # the shank points down into the plate.
    seat_t, seat_q = tf_relative_to_frame(
        screw.anchor("head_seat").frame, assembly.frame
    )
    assert seat_t == pytest.approx([10.0, 10.0, 6.0])
    tip_t, _ = tf_relative_to_frame(screw.anchor("tip").frame, assembly.frame)
    assert tip_t == pytest.approx([10.0, 10.0, 6.0 - screw.body_height])
    # The screw's own +Z (tip toward head) points up in assembly space.
    screw_root = assembly.components[-1]
    z_axis = quaternion_rotate_vector(screw_root.frame.quaternion, [0, 0, 1])
    assert z_axis == pytest.approx([0, 0, 1], abs=1e-9)


def test_connect_without_drilling():
    plate = _make_plate()
    screw = DIN912Screw("M4", 16, with_thread=False)
    assembly = Assembly()
    assembly.add_component(plate)
    ops_before = len(plate.operations)
    connect_with_screw(assembly, screw, plate.anchor("mount_1"), drill=False)
    assert len(plate.operations) == ops_before
    assert len(assembly.joints) == 1


def test_connection_serializes():
    plate = _make_plate()
    screw = DIN912Screw("M4", 16, with_thread=False)
    assembly = Assembly()
    assembly.add_component(plate)
    connect_with_screw(assembly, screw, plate.anchor("mount_1"))

    dag = show_dag(assembly)
    root = dag["DAG"][dag["rootNodeId"]]
    assert len(root["deps"].get("joints", [])) == 1
    # the drilled bore serializes with the plate
    plate_root_id = root["deps"]["components"][0]
    plate_ops = dag["DAG"][plate_root_id]["deps"]["operations"]
    assert len(plate_ops) == 2
