"""Geometry of the standards features, mapped into the part frame and checked
against hand-computed values (drill point, runout, countersink, form A key,
torus, keyway floor)."""

import math

import numpy as np
import pytest

from cadbuildr.foundation import Extrusion, Part, Sketch, Square, make_anchor
from cadbuildr.foundation.interference import _sketch_frame, estimate_part_extents
from cadbuildr.stdlib.standards import (
    StandardsError,
    heat_set_insert_hole,
    shaft_keyway,
    tapped_hole,
)
from cadbuildr.stdlib.standards.shaft_parts import KeyedShaft, ORingSeal, ParallelKey


def _profile_in_part(op, part):
    """The (x, y, z) vertices of a Lathe profile in the part frame."""
    R, t = _sketch_frame(op.shape.sketch, part.frame)
    pts = [
        R @ np.array([p.x.value, p.y.value, 0.0]) + t
        for line in op.shape.primitives
        for p in (line.p1, line.p2)
    ]
    return np.unique(np.round(np.array(pts), 6), axis=0)


def _top_plate(thickness=20.0):
    p = Part()
    p.add_operation(
        Extrusion(Square.from_center_and_side(Sketch(p.xy()).origin, 40), thickness)
    )
    p.add_anchor(make_anchor("h", (5.0, 0.0, thickness)))
    return p


def _radial(pts):
    return np.hypot(pts[:, 0] - 5.0, pts[:, 1])


def test_tapped_hole_runout_drill_point_and_countersink():
    p = _top_plate()
    f = tapped_hole(p.anchor("h"), "M6", 10)
    pts = _profile_in_part(f.operation, p)
    r, rc = 2.5, 1.05 * 3.0  # tap drill 5.0; countersink 1.05 d
    drill = 10 + 3 * 1.0  # thread depth + 3 P runout
    tip = 20 - drill - r / math.tan(math.radians(59))  # 118 deg point
    rad = _radial(pts)
    assert rad.max() == pytest.approx(rc)
    assert pts[:, 2].max() == pytest.approx(20.0)  # starts at the face
    assert pts[:, 2].min() == pytest.approx(tip)
    # 90 deg countersink: the chamfer drops (rc - r) while closing (rc - r)
    assert any(
        abs(z - (20 - (rc - r))) < 1e-6 and abs(x - r) < 1e-6
        for x, z in zip(rad, pts[:, 2])
    )
    # full-diameter bore down to the drill depth
    assert any(
        abs(z - (20 - drill)) < 1e-6 and abs(x - r) < 1e-6
        for x, z in zip(rad, pts[:, 2])
    )


def test_tapped_hole_options():
    p = _top_plate()
    plain = tapped_hole(p.anchor("h"), "M6", 10, chamfer=False, drill_depth=12)
    pts = _profile_in_part(plain.operation, p)
    assert _radial(pts).max() == pytest.approx(2.5)
    assert pts[:, 2].min() == pytest.approx(20 - 12 - 2.5 / math.tan(math.radians(59)))
    with pytest.raises(StandardsError, match="shorter"):
        tapped_hole(_top_plate().anchor("h"), "M6", 10, drill_depth=8)


def test_heat_set_hole_profile():
    p = _top_plate()
    f = heat_set_insert_hole(p.anchor("h"), "M3")
    pts = _profile_in_part(f.operation, p)
    assert pts[:, 2].min() == pytest.approx(20 - 6.7)  # insert 5.7 + 1 mm
    assert _radial(pts).max() == pytest.approx(2.0 + 0.3)  # hole 4.0 + lead-in


def _extent(part):
    ext = estimate_part_extents(part)
    assert not ext.unknown, ext.unknown
    corners = np.vstack([b.corners() for b in ext.boxes])
    return corners.min(axis=0), corners.max(axis=0)


def test_parallel_key_is_form_a_with_rounded_ends():
    k = ParallelKey(shaft_d=20.0, length=28)
    lo, hi = _extent(k)
    assert lo == pytest.approx([0, -3, 0]) and hi == pytest.approx([6, 3, 28])
    circles = [op for op in k.operations if type(op.shape[0]).__name__ == "Circle"]
    assert len(circles) == 2
    assert all(c.shape[0].radius.value == pytest.approx(3.0) for c in circles)


def test_oring_torus_extent():
    o = ORingSeal("AS568-214")
    lo, hi = _extent(o)
    assert hi[0] - lo[0] == pytest.approx(o.ring.id + 2 * o.ring.cs, abs=1e-3)
    assert hi[2] - lo[2] == pytest.approx(o.ring.cs, abs=1e-3)


def _circle_cuts(part):
    return [
        op
        for op in part.operations
        if type(op).__name__ == "Extrusion"
        and op.cut.value
        and type(op.shape[0]).__name__ == "Circle"
    ]


def test_shaft_keyway_floor_and_rounded_ends():
    shaft = Part()
    sk = Sketch(shaft.xy())
    from cadbuildr.foundation import Circle, Point

    shaft.add_operation(Extrusion(Circle(Point(sk, 0, 0), 10.0), 100))
    key = shaft_keyway(shaft, 20, 10, 28)
    ends = _circle_cuts(shaft)
    assert len(ends) == 2
    for op in ends:
        assert op.shape[0].radius.value == pytest.approx(key.b / 2)
        assert min(op.start.value, op.end.value) == pytest.approx(
            10.0 - key.t1
        )  # d - t1
        R, t = _sketch_frame(op.shape[0].center.sketch, shaft.frame)
        assert (R @ [0, 0, 1]) == pytest.approx([1, 0, 0])  # cut along +X
    zs = sorted(op.shape[0].center.y.value for op in ends)
    assert zs == pytest.approx([10 + 3, 10 + 28 - 3])  # round ends inside 28 mm
    with pytest.raises(StandardsError, match="shorter than the key width"):
        shaft_keyway(shaft, 20, 0, 4)


def test_keyed_shaft_layout():
    s = KeyedShaft(d=20.0, length=120, key_length=28)
    assert s.chamfer == 1.0 and len(s.rings) == 2
    assert s.rings[0].groove == 19.0 and s.rings[0].width == 1.3  # DIN 471 d1 = 20
