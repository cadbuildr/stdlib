"""Tests for RoundTube and the cope-cut tube_tee connection."""

import math

import pytest

from cadbuildr.foundation import Assembly
from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.math_utils import (
    quaternion_rotate_vector,
    tf_relative_to_frame,
)

from cadbuildr.stdlib.profiles.tubes import RoundTube, tube_tee


def _axis_of(assembly, tube):
    _, q = tf_relative_to_frame(tube.frame, assembly.frame)
    return quaternion_rotate_vector(q, [0, 0, 1])


def test_round_tube_builds_and_has_anchors():
    tube = RoundTube(outer_diameter=26.9, wall=2.3, length=500)
    assert tube.anchor("end_b").frame.position[2] == pytest.approx(500)
    dag = show_dag(tube)
    assert dag["DAG"]


def test_radial_anchor_sits_on_surface():
    tube = RoundTube(outer_diameter=30.0, wall=2.0, length=400)
    assembly = Assembly()
    assembly.add_component(tube)
    anchor = tube.radial_anchor(at=100.0, angle=math.pi / 2.0)
    t, q = tf_relative_to_frame(anchor.frame, assembly.frame)
    assert t == pytest.approx([0.0, 15.0, 100.0], abs=1e-9)
    # +Z of the anchor points radially outward (here +Y)
    z = quaternion_rotate_vector(q, [0, 0, 1])
    assert z == pytest.approx([0, 1, 0], abs=1e-9)


def test_tube_tee_places_perpendicular_and_copes():
    main = RoundTube(outer_diameter=26.9, wall=2.3, length=800)
    branch = RoundTube(outer_diameter=26.9, wall=2.3, length=400)
    assembly = Assembly()
    assembly.add_component(main)

    ops_before = len(branch.operations)
    tube_tee(assembly, branch, main, at=400)

    # Cope cut landed on the branch.
    assert len(branch.operations) == ops_before + 1
    assert len(assembly.components) == 2
    assert len(assembly.joints) == 1

    # Branch is perpendicular to the main tube and points at its axis.
    axis_main = _axis_of(assembly, main)
    axis_branch = _axis_of(assembly, branch)
    dot = sum(a * b for a, b in zip(axis_main, axis_branch))
    assert dot == pytest.approx(0.0, abs=1e-9)

    # The branch end sits sunk into the main tube: distance from the main
    # axis to the branch end is (main radius - sink) < main radius.
    t_end, _ = tf_relative_to_frame(branch.anchor("end_b").frame, assembly.frame)
    radial = math.hypot(t_end[0], t_end[1])
    assert radial < main.outer_radius
    assert radial > main.outer_radius - branch.outer_radius
    assert t_end[2] == pytest.approx(400.0)


def test_tube_tee_serializes_with_joint():
    main = RoundTube(length=800)
    branch = RoundTube(length=300)
    assembly = Assembly()
    assembly.add_component(main)
    tube_tee(assembly, branch, main)
    dag = show_dag(assembly)
    root = dag["DAG"][dag["rootNodeId"]]
    assert len(root["deps"].get("joints", [])) == 1
