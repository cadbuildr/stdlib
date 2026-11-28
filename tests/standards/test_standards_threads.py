"""Thread, clearance, counterbore, countersink and screw-length tables."""

import pytest

from cadbuildr.foundation import holes as foundation_holes
from cadbuildr.stdlib.standards import (
    StandardsError,
    UnknownSize,
    clearance_diameter,
    counterbore,
    countersink,
    metric_sizes,
    screw_length,
    tap_drill,
    thread,
)
from cadbuildr.stdlib.standards.threads import METRIC_COARSE, METRIC_FINE, UNIFIED


def test_m6_basic_dimensions_iso_724():
    t = thread("M6")
    assert (t.pitch, t.tap_drill) == (1.0, 5.0)
    assert t.pitch_diameter == pytest.approx(5.350, abs=1e-3)
    assert t.minor_internal == pytest.approx(4.917, abs=1e-3)
    assert t.minor_external == pytest.approx(4.773, abs=1e-3)
    assert t.stress_area == pytest.approx(20.1, abs=0.05)  # ISO 898-1: 20.1 mm²
    assert [t.clearance(f) for f in ("close", "normal", "loose")] == [6.4, 6.6, 7.0]
    assert t.clearance("medium") == 6.6 and t.clearance("fine") == 6.4


@pytest.mark.parametrize("size", list(METRIC_COARSE))
def test_coarse_tap_drill_is_d_minus_p(size):
    t = thread(size)
    # ISO 2306 rounds d - P to a stock drill (M8: 6.75 -> 6.8).
    assert t.tap_drill == pytest.approx(t.major - t.pitch, abs=0.051)
    assert t.clearance_close < t.clearance_normal < t.clearance_loose
    assert t.clearance_close > t.major


@pytest.mark.parametrize(
    "size",
    [s for s in METRIC_COARSE if float(s[1:]) in foundation_holes.ISO_METRIC_COARSE],
)
def test_matches_foundation_hole_wizard(size):
    """foundation's TappedHole / ClearanceHole must agree with the standards table."""
    d = float(size[1:])
    assert foundation_holes.tap_drill_diameter(d) == tap_drill(size)
    for fit in ("CLOSE", "NORMAL", "LOOSE"):
        assert foundation_holes.clearance_diameter(d, fit) == clearance_diameter(
            size, fit.lower()
        )


@pytest.mark.parametrize("designation", list(METRIC_FINE))
def test_fine_threads(designation):
    t = thread(designation)
    assert t.series == "fine"
    assert t.screw_size == designation.split("x")[0]
    assert t.tap_drill == pytest.approx(t.major - t.pitch)


def test_coarse_designation_with_its_own_pitch_is_coarse():
    assert thread("M8x1.25").series == "coarse"
    assert thread(8).designation == "M8"


@pytest.mark.parametrize("designation", list(UNIFIED))
def test_unified(designation):
    t = thread(designation)
    series, major_in, tpi, tap, close, free = UNIFIED[designation]
    assert t.major == pytest.approx(major_in * 25.4, abs=1e-3)
    assert t.pitch == pytest.approx(25.4 / tpi, abs=1e-3)
    assert t.minor_internal < t.tap_drill < t.major
    assert t.major < t.clearance("close") < t.clearance("normal")
    with pytest.raises(StandardsError, match="loose"):
        t.clearance("loose")


def test_unified_aliases_and_errors():
    assert thread("1/4-20 UNC").tap_drill_name == "#7"
    assert thread("#10-32").series == "UNF"
    with pytest.raises(UnknownSize, match="unified"):
        thread("1/4-21")
    with pytest.raises(UnknownSize, match="M8, M6"):
        thread("M7")
    with pytest.raises(UnknownSize, match="fine"):
        thread("M8x0.75")
    with pytest.raises(UnknownSize):
        thread("M6").clearance("snug")


def test_counterbore_and_countersink():
    cb = counterbore("M5")
    assert (cb.diameter, cb.depth, cb.hole) == (10.0, 5.4, 5.5)
    assert counterbore("M8", "close").hole == 8.4
    assert counterbore("M12").depth == pytest.approx(12.6)
    cs = countersink("M4")
    assert (cs.diameter, cs.angle, cs.hole) == (8.96, 90.0, 4.5)
    assert countersink("M4", "ISO 7046").diameter == 9.4
    with pytest.raises(UnknownSize):
        countersink("M2", "ISO 10642")
    with pytest.raises(StandardsError):
        counterbore("1/4-20")


def test_screw_length():
    assert screw_length("M5", 8) == 16  # 8 + 7.5 -> 16
    assert screw_length("M5", 8, engagement=1.0) == 16  # 13 -> 16
    assert screw_length("M3", 3, engagement=1.0) == 6
    assert screw_length("M8", 12) == 25  # 12 + 12 -> 25
    with pytest.raises(StandardsError, match="longer than the series"):
        screw_length("M8", 250)


def test_metric_sizes_are_ordered():
    sizes = [float(s[1:]) for s in metric_sizes()]
    assert sizes == sorted(sizes)
