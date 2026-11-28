"""ISO 286 limits and fits against published ISO 286-2 table values."""

import pytest

from cadbuildr.stdlib.standards import (
    PREFERRED_FITS,
    OutOfRange,
    StandardsError,
    UnknownSize,
    bearing_fit,
    fit,
    it_grade,
    printed_clearance,
    tolerance,
)
from cadbuildr.stdlib.standards.fits import HOLE_LETTERS, SHAFT_LETTERS, SIZE_STEPS

# (designation, nominal mm, upper µm, lower µm) — ISO 286-2 tables.
PUBLISHED = [
    ("H7", 10, 15, 0),
    ("H7", 22, 21, 0),
    ("H8", 25, 33, 0),
    ("H11", 45, 160, 0),
    ("g6", 10, -5, -14),
    ("f7", 25, -20, -41),
    ("h6", 8, 0, -9),
    ("k6", 8, 10, 1),
    ("k6", 25, 15, 2),
    ("m6", 25, 21, 8),
    ("n6", 15, 23, 12),
    ("p6", 30, 35, 22),
    ("r6", 60, 60, 41),
    ("s6", 25, 48, 35),
    ("c11", 45, -130, -290),
    ("d9", 20, -65, -117),
    ("e8", 40, -50, -89),
    ("js6", 15, 5.5, -5.5),
    ("js7", 25, 10, -10),  # IT7 = 21: odd -> rounded down to 20 (ISO 286-1 5.3.1)
    ("G7", 20, 28, 7),
    ("F8", 12, 43, 16),
    ("K6", 25, 2, -11),
    ("K7", 15, 6, -12),
    ("K8", 25, 10, -23),
    ("M6", 15, -4, -15),
    ("M7", 25, 0, -21),
    ("N7", 15, -5, -23),
    ("N9", 2, -4, -29),
    ("P7", 15, -11, -29),
    ("P7", 25, -14, -35),
    ("R7", 15, -16, -34),
    ("S7", 25, -27, -48),
    ("JS7", 25, 10, -10),
]


@pytest.mark.parametrize("designation,size,upper,lower", PUBLISHED)
def test_published_deviations(designation, size, upper, lower):
    t = tolerance(designation, size)
    assert t.upper * 1000 == pytest.approx(upper, abs=1e-6)
    assert t.lower * 1000 == pytest.approx(lower, abs=1e-6)
    assert t.max == pytest.approx(size + upper / 1000)
    assert t.min == pytest.approx(size + lower / 1000)


def test_it_grades_and_range_boundaries():
    assert it_grade(7, 10) == pytest.approx(0.015)  # 10 is in "over 6 up to 10"
    assert it_grade(7, 10.001) == pytest.approx(0.018)
    assert it_grade(6, 3) == pytest.approx(0.006)
    assert it_grade(16, 500) == pytest.approx(4.0)
    with pytest.raises(OutOfRange):
        it_grade(7, 600)
    with pytest.raises(UnknownSize):
        it_grade(17, 10)


def test_fit_h7_g6_at_10():
    f = fit("H7/g6", 10)
    assert f.hole.limits == (10.0, 10.015)
    assert f.shaft.limits == (9.986, 9.995)
    assert f.min_clearance == pytest.approx(0.005)
    assert f.max_clearance == pytest.approx(0.029)
    assert f.kind == "clearance"
    assert "sliding" in f.purpose
    assert str(f).startswith("Ø10 H7/g6 clearance")


@pytest.mark.parametrize(
    "designation,size,kind",
    [
        ("H7/h6", 20, "clearance"),
        ("H7/k6", 8, "transition"),
        ("H7/n6", 20, "transition"),
        ("H7/p6", 30, "interference"),
        ("H7/s6", 30, "interference"),
        ("H11/c11", 50, "clearance"),
    ],
)
def test_fit_kinds(designation, size, kind):
    assert fit(designation, size).kind == kind


@pytest.mark.parametrize("designation", sorted(PREFERRED_FITS))
@pytest.mark.parametrize("size", [1, 3, 5, 10, 18, 30, 64, 100, 150, 250, 400, 500])
def test_every_preferred_fit_covers_the_table(designation, size):
    f = fit(designation, size)
    assert f.hole.width > 0 and f.shaft.width > 0
    assert f.max_clearance > f.min_clearance


@pytest.mark.parametrize("letter", SHAFT_LETTERS + HOLE_LETTERS)
@pytest.mark.parametrize("grade", [5, 6, 7, 8, 9, 11])
def test_every_letter_and_grade_resolves_at_every_step(letter, grade):
    for upper in SIZE_STEPS[1:]:
        t = tolerance(f"{letter}{grade}", upper)
        # js / JS 7..11 round an odd IT down to an even micrometre.
        assert (
            it_grade(grade, upper) - 0.001 - 1e-9
            <= t.width
            <= it_grade(grade, upper) + 1e-9
        )


def test_bad_designations_fail_loudly():
    with pytest.raises(UnknownSize, match="not covered"):
        tolerance("x6", 10)
    with pytest.raises(UnknownSize, match="designation"):
        tolerance("H", 10)
    with pytest.raises(StandardsError, match="hole first"):
        fit("g6/H7", 10)
    with pytest.raises(StandardsError, match="hole/shaft"):
        fit("H7", 10)


def test_bearing_fits_use_iso_492_rings():
    inner = bearing_fit("k6", 8)  # bore 0/-8, k6 +10/+1 -> interference
    assert inner.hole.limits == (7.992, 8.0)
    assert inner.kind == "interference"
    assert bearing_fit("g6", 8).kind == "transition"
    outer = bearing_fit("H7", 22, ring="outer")  # OD 0/-9 in H7 +21/0
    assert outer.min_clearance == pytest.approx(0.0)
    assert outer.max_clearance == pytest.approx(0.030)
    with pytest.raises(StandardsError):
        bearing_fit("H7", 8)  # a hole letter on the inner ring


def test_printed_clearance():
    assert printed_clearance() == pytest.approx(0.3)
    assert printed_clearance("press", "sls") == pytest.approx(0.1)
    with pytest.raises(UnknownSize):
        printed_clearance("wobbly")
