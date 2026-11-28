"""Inserts, keys, circlips, O-rings, preferred numbers, surfaces, materials."""

import pytest

from cadbuildr.stdlib.standards import (
    MATERIALS,
    OutOfRange,
    StandardsError,
    UnknownSize,
    circlip_bore,
    circlip_shaft,
    flatness_tolerance,
    general_angle_tolerance,
    general_tolerance,
    gland,
    heat_set_insert,
    key_length,
    keyway,
    material,
    materials_for,
    oring,
    piston_groove,
    preferred,
    processes_for_ra,
    ra_grade,
    radius_tolerance,
    self_tap_hole,
    sheet_gauge,
    stock_size,
)
from cadbuildr.stdlib.standards.seals import AS568
from cadbuildr.stdlib.standards.shaft_features import DIN471, DIN472, DIN6885_KEYS


def test_heat_set_inserts():
    m3 = heat_set_insert("M3")
    assert (m3.hole, m3.length, m3.depth) == (4.0, 5.7, 6.7)
    assert m3.boss > m3.outer
    assert heat_set_insert("M3", "short").length == 3.0
    with pytest.raises(UnknownSize):
        heat_set_insert("M6", "short")
    with pytest.raises(UnknownSize):
        heat_set_insert("M7")


def test_self_tap_into_plastic():
    h = self_tap_hole(3.0, "PC")
    assert (h.pilot, h.boss, h.engagement) == (2.55, 7.5, 6.0)
    assert self_tap_hole("M4", "PP").pilot == pytest.approx(2.8)
    with pytest.raises(UnknownSize):
        self_tap_hole(3, "steel")


def test_keyways_din_6885():
    k = keyway(20)
    assert (k.b, k.h, k.t1, k.t2) == (6, 6, 3.5, 2.8)
    assert keyway(22).b == 6 and keyway(22.01).b == 8  # "over 17 up to 22"
    assert k.designation == "DIN 6885 A 6 x 6"
    assert key_length(20, 27) == 28
    with pytest.raises(OutOfRange):
        keyway(5)
    with pytest.raises(StandardsError):
        key_length(20, 500)
    widths = [row[2][0] for row in DIN6885_KEYS]
    assert widths == sorted(widths)


def test_circlips():
    assert circlip_shaft(8).groove == 7.6
    ring = circlip_bore(22)  # 608 bearing outer ring retained in its bore
    assert (ring.groove, ring.width, ring.thickness) == (23.0, 1.1, 1.0)
    assert ring.groove_depth == pytest.approx(0.5)
    with pytest.raises(UnknownSize, match="DIN 471"):
        circlip_shaft(21)
    for d, (groove, m, s) in DIN471.items():
        assert groove < float(d) and m > s
    for d, (groove, m, s) in DIN472.items():
        assert groove > float(d) and m > s


def test_orings_and_glands():
    o = oring("AS568-010")
    assert (o.id, o.cs) == (pytest.approx(6.071), pytest.approx(1.778))
    assert oring("-214").id == pytest.approx(0.984 * 25.4, abs=1e-3)
    assert AS568["AS568-012"] == (0.364, 0.070)  # generated 1/16 in step
    g = gland(1.78)
    assert g.depth == pytest.approx(1.78 * 0.78, abs=1e-3)
    assert 0.6 < g.fill <= 0.85
    with pytest.raises(StandardsError, match="squeeze"):
        gland(1.78, "dynamic_radial", squeeze=0.3)
    p = piston_groove(20, 1.78)
    assert p.groove_d == pytest.approx(20 - 2 * g.depth)
    assert 0 <= p.stretch <= 0.05 and p.ring.name == "AS568-017"
    with pytest.raises(StandardsError, match="No AS568"):
        piston_groove(200, 1.78)


def test_preferred_numbers():
    assert preferred(37, "R20") == 35.5
    assert preferred(37, "R10", "up") == 40.0
    assert preferred(37, "R10", "down") == 31.5
    assert preferred(4700, "E12") == 4700.0
    assert preferred(0.05, "R5") == pytest.approx(0.04)
    with pytest.raises(UnknownSize):
        preferred(10, "R7")


def test_gauges_and_stock():
    assert sheet_gauge(16) == pytest.approx(1.519)
    assert sheet_gauge(16, "aluminium") == pytest.approx(1.291)
    with pytest.raises(OutOfRange):
        sheet_gauge(2)
    assert stock_size(13) == 15.0
    assert stock_size(13, "plywood", "down") == 12.0
    with pytest.raises(OutOfRange):
        stock_size(30)


def test_surface_and_general_tolerances():
    assert ra_grade(1.6) == "N7" and ra_grade(1.0) == "N7" and ra_grade(0.8) == "N6"
    assert "grinding" in processes_for_ra(0.8) and "fdm print" not in processes_for_ra(
        0.8
    )
    assert general_tolerance(45, "m") == 0.3
    assert general_tolerance(3, "f") == 0.05
    assert general_tolerance(2500, "c") == 4.0
    with pytest.raises(StandardsError, match="no general tolerance"):
        general_tolerance(3000, "f")
    with pytest.raises(OutOfRange):
        general_tolerance(0.2)
    assert radius_tolerance(4, "c") == 1.0
    assert general_angle_tolerance(30, "m") == 0.5
    assert general_angle_tolerance(5, "v") == 3.0
    assert flatness_tolerance(200, "K") == 0.4


def test_materials():
    al = material("6061-T6")
    assert al.key == "6061_t6" and al.density == 2700 and al.machinable
    assert al.mass_kg(1e6) == pytest.approx(2.7)
    assert al.cost(1e6) == pytest.approx(2.7 * al.cost_per_kg)
    assert material("stainless steel A2").key == "stainless_304"
    assert material("Aluminium 6082").key == "6082_t6"
    assert material("steel 8.8").family == "steel"
    assert material("PETG").printable and not material("PETG").machinable
    assert {m.key for m in materials_for("fdm")} >= {"pla", "petg", "abs"}
    with pytest.raises(UnknownSize):
        material("unobtainium")
    with pytest.raises(UnknownSize):
        materials_for("knitting")


def test_material_sheet_keys_match_foundation():
    from cadbuildr.foundation.sheet_metal_materials import MATERIALS as SHEET

    for m in MATERIALS.values():
        if m.sheet_metal:
            assert m.sheet_metal in SHEET, m.key
            assert abs(SHEET[m.sheet_metal].density - m.density) <= 100, m.key
        assert m.density > 0 and m.E > 0 and m.cost_per_kg > 0
        assert (
            m.yield_mpa is None or m.uts_mpa is None or m.yield_mpa <= m.uts_mpa
        ), m.key
