"""Fixes from the fidelity review: flush countersinks, tapped_holes options,
one ISO 273 / 2306 source, blind-hole drill points, circlip rows."""

import math

import numpy as np
import pytest

from cadbuildr.foundation import holes as foundation_holes
from cadbuildr.foundation import Extrusion, Part, Sketch, Square, make_anchor
from cadbuildr.foundation.interference import _sketch_frame
from cadbuildr.stdlib.fasteners.screws_and_bolts.socket_head_screws_part import (
    CountersunkSocketScrew,
)
from cadbuildr.stdlib.standards import (
    circlip_bore,
    circlip_shaft,
    clearance_hole,
    counterbored_hole,
    countersink,
    tapped_holes,
)
from cadbuildr.stdlib.standards.threads import COUNTERSINK_HEADS, METRIC_COARSE

# ISO 7046-1 theoretical dk (= ISO 15065 countersink diameter), mm.
ISO7046_THEORETICAL_DK = {
    "M2": 4.4,
    "M2.5": 5.5,
    "M3": 6.3,
    "M4": 9.4,
    "M5": 10.4,
    "M6": 12.6,
    "M8": 17.3,
    "M10": 20.0,
}
# ISO 10642 theoretical dk = 2.24 d up to M12, then the table values.
ISO10642_THEORETICAL_DK = {
    "M3": 6.72,
    "M4": 8.96,
    "M5": 11.2,
    "M6": 13.44,
    "M8": 17.92,
    "M10": 22.4,
    "M12": 26.88,
    "M14": 30.8,
    "M16": 33.6,
    "M20": 40.32,
}


def _sink_depth(csink_d, head_d):
    """How far below the face a 90 degree head of ``head_d`` sits in a 90
    degree countersink of ``csink_d`` (negative = proud)."""
    return (csink_d - head_d) / 2.0


@pytest.mark.parametrize("size,dk", sorted(ISO7046_THEORETICAL_DK.items()))
def test_iso7046_countersink_is_flush(size, dk):
    assert COUNTERSINK_HEADS["ISO 7046"][size] == dk
    cs = countersink(size, "ISO 7046")
    assert _sink_depth(cs.diameter, dk) == pytest.approx(0.0)  # theoretical head: flush


@pytest.mark.parametrize("size,dk", sorted(ISO10642_THEORETICAL_DK.items()))
def test_iso10642_countersink_is_flush(size, dk):
    assert _sink_depth(countersink(size).diameter, dk) == pytest.approx(0.0)


@pytest.mark.parametrize("size", sorted(CountersunkSocketScrew.TABLE))
def test_stdlib_countersunk_screw_never_sits_proud(size):
    head = CountersunkSocketScrew.TABLE[size]["dk"]
    sink = _sink_depth(countersink(size).diameter, head)
    assert sink >= 0.0, (size, sink)  # never proud (smaller heads sink below)


def test_metric_table_is_read_from_foundation():
    for d, row in foundation_holes.ISO_METRIC_COARSE.items():
        assert METRIC_COARSE[f"M{d:g}"] == tuple(float(v) for v in row)
    sizes = [float(k[1:]) for k in METRIC_COARSE]
    assert sizes == sorted(sizes) and "M36" in METRIC_COARSE  # standards-only rows kept


def _plate(n=2, thickness=20.0):
    p = Part()
    p.add_operation(
        Extrusion(Square.from_center_and_side(Sketch(p.xy()).origin, 60), thickness)
    )
    p.add_anchor(make_anchor("h", (-10.0, 0.0, thickness)))
    anchors = p.anchor("h").linear_pattern(n, 20.0)
    p.add_anchors(anchors)
    return p, anchors


def _z_min(op, part):
    R, t = _sketch_frame(op.shape.sketch, part.frame)
    return min(
        (R @ np.array([q.x.value, q.y.value, 0.0]) + t)[2]
        for line in op.shape.primitives
        for q in (line.p1, line.p2)
    )


def _r_max(op):
    return max(
        abs(q.x.value) for line in op.shape.primitives for q in (line.p1, line.p2)
    )


def test_tapped_holes_passes_drill_depth():
    p, anchors = _plate()
    feats = tapped_holes(anchors, "M6", 10, drill_depth=15)
    point = 2.5 / math.tan(math.radians(59))
    assert all(_z_min(f.operation, p) == pytest.approx(20 - 15 - point) for f in feats)


def test_tapped_holes_passes_chamfer():
    p, anchors = _plate()
    feats = tapped_holes(anchors, "M6", 10, chamfer=False)
    assert all(_r_max(f.operation) == pytest.approx(2.5) for f in feats)
    p2, anchors2 = _plate()
    with_chamfer = tapped_holes(anchors2, "M6", 10)
    assert all(_r_max(f.operation) == pytest.approx(3.15) for f in with_chamfer)


def test_tapped_holes_passes_interface():
    p, anchors = _plate()
    feats = tapped_holes(anchors, "M6", 10, interface=False)
    assert all(f.interface is None for f in feats) and not p.interfaces
    p2, anchors2 = _plate()
    tapped_holes(anchors2, "M6", 10, group="g")
    assert len(p2.group("g")) == 2


def test_blind_clearance_and_counterbore_end_in_a_drill_point():
    p, (a, b) = _plate()
    c = clearance_hole(a, "M5", 12, blind=True)
    assert _z_min(c.operation, p) == pytest.approx(
        20 - 12 - 2.75 / math.tan(math.radians(59))
    )
    cb = counterbored_hole(b, "M5", 12, blind=True)
    assert _z_min(cb.operation, p) == pytest.approx(
        20 - 12 - 2.75 / math.tan(math.radians(59))
    )
    assert _r_max(cb.operation) == pytest.approx(5.0)  # DIN 974-1 M5: 10 mm
    # through holes keep the foundation wizards
    q, (a2, _b2) = _plate()
    assert type(clearance_hole(a2, "M5", 20).operation).__name__ == "Hole"


def test_added_circlip_rows():
    assert circlip_bore(18).groove == 19.0 and circlip_bore(18).width == 1.1
    assert circlip_shaft(11).groove == 10.5
    assert circlip_shaft(13).groove == 12.4
    assert (circlip_shaft(19).groove, circlip_shaft(19).width) == (18.0, 1.3)
