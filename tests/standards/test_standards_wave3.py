"""Tr / BSP / NPT threads, wood pilots, shaft / hub / seal cuts, captive nuts
and the parts built from them."""

import json

import pytest

from cadbuildr.foundation import (
    Circle,
    Extrusion,
    Part,
    Point,
    Sketch,
    Square,
    make_anchor,
)
from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.math_utils import tf_relative_to_frame
from cadbuildr.stdlib.standards import (
    StandardsError,
    UnknownSize,
    captive_nut_pocket,
    circlip_groove,
    d_flat,
    d_flat_size,
    hub_keyway,
    oring_groove,
    pipe_thread,
    shaft_keyway,
    trapezoidal,
    wood_pilot,
)
from cadbuildr.stdlib.standards.shaft_parts import (
    CaptiveNutBlock,
    CaptiveNutDemo,
    KeyedShaft,
    ORingSeal,
    ParallelKey,
)
from cadbuildr.stdlib.standards.special_threads import BSP, NPT, TRAPEZOIDAL

# --------------------------------------------------------------------------- #
# Threads
# --------------------------------------------------------------------------- #


def test_trapezoidal_iso_2904():
    t = trapezoidal("Tr8x2")
    assert (t.d, t.pitch, t.lead, t.starts) == (8, 2, 2, 1)
    assert t.pitch_diameter == 7.0
    assert t.minor_internal == 6.0 and t.tap_drill == 6.0
    assert t.minor_external == pytest.approx(5.5)  # 8 - (2 + 2 x 0.25)
    assert t.major_internal == pytest.approx(8.5)
    assert trapezoidal("Tr20x4").minor_external == pytest.approx(15.5)
    assert trapezoidal("Tr40x7").ac == 0.5


def test_trapezoidal_multi_start_printer_lead_screw():
    t = trapezoidal("Tr8x8(P2)")
    assert (t.lead, t.pitch, t.starts) == (8, 2, 4)
    with pytest.raises(StandardsError, match="multiple"):
        trapezoidal("Tr8x5(P2)")
    with pytest.raises(UnknownSize):
        trapezoidal("Tr9x2")
    with pytest.raises(UnknownSize):
        trapezoidal("M8")


@pytest.mark.parametrize("size", list(TRAPEZOIDAL))
def test_every_trapezoidal_size_is_consistent(size):
    t = trapezoidal(size)
    assert (
        t.minor_external < t.minor_internal < t.pitch_diameter < t.d < t.major_internal
    )


def test_pipe_threads():
    g = pipe_thread("G1/4")
    assert (g.major, g.tpi, g.tap_drill, g.tapered) == (13.157, 19, 11.8, False)
    assert g.pitch == pytest.approx(1.3368, abs=1e-4)
    assert pipe_thread("R1/2").tapered and pipe_thread("Rc1/2").taper == "1:16"
    assert pipe_thread("Rp3/8").tapered is False
    n = pipe_thread("1/4 NPT")
    assert (n.major, n.tpi, n.tap_drill_name) == (13.716, 18, "7/16")
    assert n.tap_drill == pytest.approx(11.112, abs=1e-3)
    with pytest.raises(UnknownSize):
        pipe_thread("G5/16")
    with pytest.raises(UnknownSize):
        pipe_thread("1/4")


@pytest.mark.parametrize("size", list(BSP))
def test_bsp_tap_drill_below_major(size):
    t = pipe_thread(f"G{size}")
    assert t.major - 2.5 * t.pitch < t.tap_drill < t.major


@pytest.mark.parametrize("size", list(NPT))
def test_npt_tap_drill_below_od(size):
    t = pipe_thread(f"{size} NPT")
    assert t.tap_drill < t.major


# --------------------------------------------------------------------------- #
# Wood
# --------------------------------------------------------------------------- #


def test_wood_pilots():
    hard = wood_pilot("#8", "hardwood")
    soft = wood_pilot("#8", "softwood")
    assert hard.pilot == pytest.approx(3.17, abs=0.01)
    assert soft.pilot < hard.pilot < hard.diameter < hard.clearance
    assert wood_pilot(5.0).pilot == 2.5 and wood_pilot("5").clearance == 5.5
    assert wood_pilot(4, "mdf").pilot == pytest.approx(2.8)
    assert wood_pilot("#10", "plywood").pilot == pytest.approx(
        0.55 * 0.190 * 25.4, abs=0.01
    )
    with pytest.raises(UnknownSize):
        wood_pilot("#9")
    with pytest.raises(UnknownSize):
        wood_pilot(5, "concrete")
    with pytest.raises(StandardsError):
        wood_pilot(30)
    with pytest.raises(StandardsError):
        wood_pilot("eight")


# --------------------------------------------------------------------------- #
# Cuts
# --------------------------------------------------------------------------- #


def _shaft(d=20.0, length=100.0):
    p = Part()
    p.add_operation(Extrusion(Circle(Point(Sketch(p.xy()), 0.0, 0.0), d / 2.0), length))
    return p


def test_shaft_cuts_add_operations_and_validate():
    s = _shaft()
    n = len(s.operations)
    assert shaft_keyway(s, 20, 10, 28).b == 6
    assert circlip_groove(s, 20, 50).groove == 19.0
    assert d_flat(s, 20, 80, 15) == pytest.approx(18.0)
    assert len(s.operations) == n + 3 + 2  # keyway = slot + 2 round ends
    show_dag(s)
    assert d_flat_size(5) == 4.5 and d_flat_size(6.35) == 5.8
    with pytest.raises(StandardsError):
        d_flat(_shaft(), 20, 0, 10, flat=9)
    with pytest.raises(StandardsError):
        shaft_keyway(_shaft(), 20, 0, 0)
    with pytest.raises(StandardsError, match="kind"):
        circlip_groove(_shaft(), 20, 0, kind="groove")


def test_hub_bore_cuts():
    hub = _shaft(50.0, 25.0)
    assert hub_keyway(hub, 20, 0, 25).t2 == 2.8
    assert circlip_groove(hub, 22, 10, kind="bore").groove == 23.0
    g = oring_groove(_shaft(19.9, 20), bore=20, cs=1.78, z=8)
    assert g.ring.name == "AS568-017"
    show_dag(hub)


def _plate(thickness=10.0):
    p = Part()
    p.add_operation(
        Extrusion(Square.from_center_and_side(Sketch(p.xy()).origin, 40), thickness)
    )
    p.add_anchor(make_anchor("under", (0.0, 0.0, 0.0), z_down=True))
    return p


def test_captive_nut_pocket():
    p = _plate()
    pocket = captive_nut_pocket(p.anchor("under"), "M3", hole_depth=4)
    assert pocket.across_flats == pytest.approx(5.9) and pocket.depth == pytest.approx(
        2.6
    )
    assert pocket.interface.type.value == "ScrewHole"
    assert json.loads(pocket.interface.params.value) == {"size": "M3", "depth": 2.6}
    assert pocket.interface.anchor.name.value == "under_nut"
    show_dag(p)
    with pytest.raises(UnknownSize):
        captive_nut_pocket(_plate().anchor("under"), "M14")


# --------------------------------------------------------------------------- #
# Parts
# --------------------------------------------------------------------------- #


def test_parallel_key_and_oring_parts():
    k = ParallelKey(shaft_d=20.0, length=27)
    assert k.length == 28 and (k.key.b, k.key.h) == (6, 6)
    assert {a.name.value for a in k.anchors} == {"bottom", "end_a", "end_b"}
    o = ORingSeal("AS568-010")
    assert o.ring.cs == pytest.approx(1.778)
    show_dag(k), show_dag(o)


def test_keyed_shaft():
    s = KeyedShaft(d=8.0, length=60, key_length=12, d_flat_end=True)
    assert s.key_length == 12 and s.flat == 7.5 and len(s.rings) == 2
    assert {i.type.value for i in s.interfaces} == {"Shaft", "ShaftEnd"}
    show_dag(s)
    with pytest.raises(StandardsError, match="does not fit"):
        KeyedShaft(d=20.0, length=40, key_length=28)


def test_captive_nut_demo_nuts_sit_in_their_pockets():
    a = CaptiveNutDemo(size="M3", n=2, height=12)
    assert a.check() == []
    assert len(a.nuts) == 2 and len(a.screws) == 2 and a.screw_length == 12
    depth = a.block.pockets[0].depth
    for nut in a.nuts:
        seat, _ = tf_relative_to_frame(nut.anchor("bottom").frame, a.frame)
        top, _ = tf_relative_to_frame(nut.anchor("top").frame, a.frame)
        assert seat[2] == pytest.approx(depth)  # on the pocket floor
        assert 0 <= top[2] < depth  # inside the pocket
    for screw in a.screws:
        head, _ = tf_relative_to_frame(screw.anchor("head_seat").frame, a.frame)
        tip, _ = tf_relative_to_frame(screw.anchor("tip").frame, a.frame)
        assert head[2] == pytest.approx(12.0) and tip[2] <= 0.2  # through the nut
    show_dag(a)
    with pytest.raises(StandardsError, match="too low"):
        CaptiveNutBlock(size="M6", height=6)
