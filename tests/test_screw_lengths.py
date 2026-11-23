"""Nominal screw length follows each standard's convention, checked on geometry.

* Under the head (ISO 4762 socket cap, ISO 7380 button, ISO 1207 cheese
  head, ISO 4017/4014 hex bolt): the shank is ``length``, the head sits on
  top, so the part spans ``length + k``.
* Overall incl. head (ISO 10642 / ISO 2009 countersunk, wood screws): the
  part spans exactly ``length`` and the head top is flush at ``length``.

The z-span is measured from foundation's bounding-volume estimate of the
built solid, not from the class attributes.
"""

import pytest

from cadbuildr.foundation.interference import estimate_part_extents
from cadbuildr.stdlib.fasteners import (
    ButtonHeadSocketScrew,
    CheeseHeadSlottedScrew,
    CountersunkSlottedScrew,
    CountersunkSocketScrew,
    DIN912Screw,
    HexBolt,
    HexNut,
    WoodScrew,
)


def _z_span(part):
    ext = estimate_part_extents(part)
    assert ext.known, ext.unknown
    # z half-extent of an oriented box = sum over its axes of |axis_z| * half.
    spans = [
        (b.center[2], sum(abs(b.axes[2, i]) * b.half[i] for i in range(3)))
        for b in ext.boxes
    ]
    return min(c - h for c, h in spans), max(c + h for c, h in spans)


def _seat_z(part):
    return part.anchor("head_seat").frame.position[2]


UNDER_HEAD = [
    (lambda: DIN912Screw("M3", 10, with_thread=False), 10, 3.0),
    (lambda: DIN912Screw("M8", 30, with_thread=False), 30, 8.0),
    (lambda: ButtonHeadSocketScrew("M4", 12, with_thread=False), 12, 2.2),
    (lambda: CheeseHeadSlottedScrew("M4", 16, with_thread=False), 16, 2.6),
    (lambda: HexBolt("M8", 30, with_thread=False), 30, 5.3),
]

OVERALL = [
    (lambda: CountersunkSocketScrew("M6", 20, with_thread=False), 20),
    (lambda: CountersunkSlottedScrew("M4", 16, with_thread=False), 16),
    (lambda: WoodScrew("8", 32), 32),
]


@pytest.mark.parametrize("make,length,k", UNDER_HEAD)
def test_under_head_length(make, length, k):
    screw = make()
    lo, hi = _z_span(screw)
    assert lo == pytest.approx(0.0, abs=1e-6)
    assert hi == pytest.approx(length + k, abs=1e-6)  # shank = length, head above
    assert _seat_z(screw) == pytest.approx(length)
    assert screw.body_height == pytest.approx(length)


@pytest.mark.parametrize("make,length", OVERALL)
def test_overall_length_includes_head(make, length):
    screw = make()
    lo, hi = _z_span(screw)
    assert lo == pytest.approx(0.0, abs=1e-6)
    assert hi == pytest.approx(length, abs=1e-6)  # head is part of the length
    assert _seat_z(screw) == pytest.approx(length)  # flush head top


def test_m3x10_cap_screw_has_a_10mm_shank():
    """Regression: DIN912Screw('M3', 10) used to get a 7 mm shank."""
    screw = DIN912Screw("M3", 10, with_thread=False)
    assert screw.body_height == 10
    assert _seat_z(screw) - screw.anchor("tip").frame.position[2] == 10


@pytest.mark.parametrize(
    "size,dk,k,s,t",
    [("M2", 3.8, 2.0, 1.5, 1.0), ("M2.5", 4.5, 2.5, 2.0, 1.1)],
)
def test_small_cap_screws_iso4762(size, dk, k, s, t):
    screw = DIN912Screw(size, 3)  # min length 3 mm, threaded
    assert screw.head_radius * 2 == dk
    assert screw.head_height == k
    assert screw.hexagon_width == s
    assert screw.hexagon_depth == t
    assert screw.body_height == 3


@pytest.mark.parametrize("size,s,m", [("M2", 4.0, 1.6), ("M2.5", 5.0, 2.0)])
def test_small_hex_nuts_iso4032(size, s, m):
    nut = HexNut(size)
    assert nut.width_across_flats == s
    assert nut.thickness == m
    assert nut.anchor("top").frame.position[2] == m
