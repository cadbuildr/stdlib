"""Standard parts wave 2: geometry and numbers against the cited tables.

Kernel-free: volumes come from the DAG's own operations (Pappus on lathe
profiles, wire length x section on swept coils, polygon areas on extrusions)
and are compared with hand-computed or published values; bounding boxes use
foundation's operation-level extents. Sizes are representative, not every
row (the catalog / anchor suites build every option).
"""

from __future__ import annotations

import math

import pytest

from cadbuildr.foundation import Assembly, Extrusion, Part, Sketch, Square, make_anchor
from cadbuildr.foundation.compute_functions import component_frames
from cadbuildr.foundation.interference import estimate_part_extents
from cadbuildr.foundation.math_utils import tf_relative_to_frame
from cadbuildr.stdlib.fasteners import (
    BlindRivet,
    CapNut,
    ClevisPin,
    CoiledPin,
    CotterPin,
    DIN433Washer,
    DIN976Rod,
    FlangeNut,
    ISO4032Nut,
    ISO4035Nut,
    ISO7090Washer,
    NylonInsertNut,
    ParallelPin,
    RClip,
    SolidRivet,
    SpringPin,
    StudBolt,
    ToothLockWasher,
    WireThreadInsert,
    pin_hole,
    rivet_hole,
    wire_thread_insert_hole,
)
from cadbuildr.stdlib.hardware import BallKnob, FixedHandle, LevellingFoot
from cadbuildr.stdlib.springs import (
    CompressionSpring,
    ExtensionSpring,
    SpringError,
    TorsionSpring,
    compression_rate,
    torsion_rate,
)
from cadbuildr.stdlib.standards import material, thread

# --------------------------------------------------------------------------- #
# DAG geometry helpers
# --------------------------------------------------------------------------- #


def _ops(part, name):
    return [op for op in part.operations if type(op).__name__ == name]


def _profile(op):
    """(x, y) sketch vertices of a pencil-drawn closed shape."""
    return [(ln.p1.x.value, ln.p1.y.value) for ln in op.shape.primitives]


def _frame_name(op):
    return op.shape.primitives[0].p1.sketch.plane.frame.name.value


def _pappus(pts):
    """Volume of the (r, z) polygon revolved about z (exact for polygons)."""
    v = 0.0
    for (r0, z0), (r1, z1) in zip(pts, pts[1:] + pts[:1]):
        v += (z1 - z0) * (r0 * r0 + r0 * r1 + r1 * r1)
    return abs(v) * math.pi / 3


def lathe_volume(part, *, include_cuts=False):
    """Net volume of the part's xz-plane lathe operations (adds minus cuts)."""
    total = 0.0
    for op in _ops(part, "Lathe"):
        if _frame_name(op) != "xz_frame" or op.angle is not None:
            continue
        v = _pappus(_profile(op))
        if op.cut.value:
            total -= v if include_cuts else 0.0
        else:
            total += v
    return total


def helices(part):
    """Helix paths of the part's sweeps (``Thread`` expands into a Sweep
    along a ``Helix3D``), in build order."""
    return [
        op.path
        for op in _ops(part, "Sweep")
        if type(op.path).__name__ == "Helix3D"
    ]


def coil_volume(part):
    """Swept round-wire volume of the helical sweeps: area x helix length."""
    v = 0.0
    for op in _ops(part, "Sweep"):
        if type(op.path).__name__ != "Helix3D":
            continue
        r_wire = op.profile.radius.value
        h = op.path
        p, H, R = h.pitch.value, h.height.value, h.radius.value
        v += math.pi * r_wire**2 * (H / p) * math.hypot(2 * math.pi * R, p)
    return v


def bbox(part):
    ext = estimate_part_extents(part)
    assert ext.known, ext.unknown
    lo = [min(c[i] for b in ext.boxes for c in b.corners()) for i in range(3)]
    hi = [max(c[i] for b in ext.boxes for c in b.corners()) for i in range(3)]
    return lo, hi


def codes(part):
    return {i["code"] for i in part.check()}


def _plate(thickness=20.0):
    p = Part()
    p.add_operation(Extrusion(Square.from_center_and_side(Sketch(p.xy()).origin, 60), thickness))
    p.add_anchor(make_anchor("h", (5.0, 0.0, thickness)))
    return p


def _world(anchor, asm):
    return tf_relative_to_frame(anchor.frame, component_frames(asm))[0]


# --------------------------------------------------------------------------- #
# Springs (EN 13906-1 / -2 / -3)
# --------------------------------------------------------------------------- #


def test_rate_formulas_hand_computed():
    # R = G d^4 / (8 D^3 n): d 2, D 16, n 8, G 81500 -> 1304000 / 262144
    assert compression_rate(81500, 2.0, 16.0, 8) == pytest.approx(4.9744, abs=1e-4)
    # R_M = E d^4 / (3667 D n): d 1.5, D 12, n 6.5, E 206000
    assert torsion_rate(206000, 1.5, 12.0, 6.5) == pytest.approx(
        206000 * 5.0625 / (3667 * 12 * 6.5)
    )


@pytest.mark.parametrize(
    "d,D,L0,n,ends,ls",
    [
        (1.0, 10.0, 30.0, 6, "ground", 8 * 1.0),  # Ls = nt d
        (1.6, 12.0, 40.0, 7, "ground", 9 * 1.6),
        (2.0, 16.0, 50.0, 8, "closed", (10 + 1.5) * 2.0),  # (nt + 1.5) d
    ],
)
def test_compression_spring_geometry(d, D, L0, n, ends, ls):
    s = CompressionSpring(d, D, L0, n, ends=ends)
    assert s.total_coils == n + 2
    assert s.solid_length == pytest.approx(ls)
    assert s.rate == pytest.approx(81500 * d**4 / (8 * D**3 * n))
    coils = helices(s)
    assert [round(c.height.value / c.pitch.value, 9) for c in coils] == [1, n, 1]
    assert all(c.radius.value == pytest.approx(D / 2) for c in coils)
    wires = [op.profile.radius.value for op in _ops(s, "Sweep")]
    assert wires == pytest.approx([d / 2] * 3)
    # Wire centre line spans the free length (ground) or L0 - d (closed).
    z0 = coils[0].center.z.value
    top = coils[-1].center.z.value + coils[-1].height.value
    assert top - z0 == pytest.approx(L0 if ends == "ground" else L0 - d)
    # Wire volume ~ pi^2 D d^2 nt / 4 (open coils add the pitch slope).
    approx = math.pi**2 * D * d**2 * (n + 2) / 4
    assert coil_volume(s) == pytest.approx(approx, rel=0.02)
    # Ground ends: two flat cuts at the seats.
    assert len(_ops(s, "Extrusion")) == (2 if ends == "ground" else 0)
    assert s.interface("axis") is not None


def test_compression_spring_stroke_check():
    base = dict(wire_diameter=1.6, mean_diameter=12.0, free_length=40.0, active_coils=7)
    sh = CompressionSpring(**base).travel_to_solid  # 40 - 9 x 1.6 = 25.6
    assert sh == pytest.approx(25.6)
    assert codes(CompressionSpring(**base, stroke=0.5 * sh)) == set()
    assert "spring.stroke_over_80pct" in codes(CompressionSpring(**base, stroke=0.85 * sh))
    assert "spring.stroke_beyond_solid" in codes(CompressionSpring(**base, stroke=sh + 1))
    assert "spring.index" in codes(CompressionSpring(1.0, 3.5, 20.0, 4))
    assert "spring.buckling" in codes(CompressionSpring(1.0, 8.0, 60.0, 12))


def test_compression_spring_bad_inputs():
    with pytest.raises(SpringError, match="too short"):
        CompressionSpring(2.0, 16.0, 15.0, 8)
    with pytest.raises(SpringError, match="cannot be coiled"):
        CompressionSpring(2.0, 5.0, 40.0, 6)
    with pytest.raises(ValueError, match="choose from"):
        CompressionSpring(wire="piano")


@pytest.mark.parametrize("hook", ["german", "hook"])
def test_extension_spring_loops(hook):
    d, D, nt = 1.5, 12.0, 16
    s = ExtensionSpring(d, D, nt, hook=hook)
    assert s.body_length == pytest.approx((nt + 1) * d)  # EN 13906-2 eq. (15)
    assert s.loop_height == pytest.approx(D - d)  # LH = Di
    # Loop centres 1.02 d nt + D apart; free length inside the loops.
    assert s.pin_distance == pytest.approx(1.02 * d * nt + D)
    assert s.free_length == pytest.approx(s.pin_distance + D - d)
    loops = [op for op in _ops(s, "Lathe")]
    assert len(loops) == 2
    sweep = None if hook == "german" else 270.0
    assert all((op.angle.value if op.angle is not None else None) == sweep for op in loops)
    assert s.rate == pytest.approx(81500 * d**4 / (8 * D**3 * nt))
    assert s.force(10) == pytest.approx(10 * s.rate)
    assert "spring.overstressed" in codes(ExtensionSpring(d, D, nt, extension=400))


@pytest.mark.parametrize("coils,leg_angle", [(5.0, 0.0), (5.25, 90.0), (6.5, 180.0), (6.75, 270.0)])
def test_torsion_spring_legs(coils, leg_angle):
    s = TorsionSpring(1.5, 12.0, coils, 25.0)
    assert s.leg_angle == leg_angle
    legs = [op for op in _ops(s, "Extrusion")]
    assert len(legs) == 2 and all(abs(op.end.value) == 25.0 for op in legs)
    n = coils + 2 * 25.0 / (3 * math.pi * 12.0)
    assert s.rate == pytest.approx(206000 * 1.5**4 / (3667 * 12.0 * n))
    assert s.body_length == pytest.approx((coils + 1) * 1.5)


def test_torsion_spring_checks():
    assert codes(TorsionSpring(1.5, 12.0, 6.5, 25.0, angle=30)) == set()
    found = codes(TorsionSpring(1.5, 12.0, 6.5, 25.0, angle=300, arbor=10.0))
    assert {"spring.overstressed", "spring.arbor_bind"} <= found
    with pytest.raises(SpringError, match="quarter"):
        TorsionSpring(coils=6.3)


# --------------------------------------------------------------------------- #
# Nuts
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "cls,size,s,m",
    [
        (ISO4032Nut, "M5", 8.0, 4.7),  # ISO 4032 Table 1
        (ISO4032Nut, "M10", 16.0, 8.4),
        (ISO4035Nut, "M8", 13.0, 4.0),  # ISO 4035
        (ISO4035Nut, "M12", 18.0, 6.0),
    ],
)
def test_iso_hex_nuts(cls, size, s, m):
    nut = cls(size, with_thread=False)
    assert (nut.width_across_flats, nut.thickness) == (s, m)
    assert nut.thread_pitch == thread(size).pitch
    lo, hi = bbox(nut)
    e = s / math.cos(math.radians(30))  # across corners
    assert hi[0] - lo[0] == pytest.approx(e, abs=1e-6)
    assert hi[2] - lo[2] == pytest.approx(m)
    # Both faces chamfered: two 30° ring cuts.
    assert sum(op.cut.value for op in _ops(nut, "Lathe")) == 2


@pytest.mark.parametrize(
    "size,series,h,s", [("M6", "ISO 7040", 8.0, 10.0), ("M10", "ISO 7040", 11.9, 16.0), ("M8", "ISO 10511", 8.0, 13.0)]
)
def test_nylon_insert_nut(size, series, h, s):
    nut = NylonInsertNut(size, series, with_thread=False)
    assert (nut.thickness, nut.width_across_flats) == (h, s)
    assert nut.insert_bore == pytest.approx(thread(size).minor_internal)  # D1
    bores = [op for op in _ops(nut, "Extrusion") if op.cut.value]
    radii = sorted(op.shape[0].radius.value for op in bores)
    assert radii == pytest.approx(sorted([thread(size).major / 2, thread(size).minor_internal / 2]))
    lo, hi = bbox(nut)
    assert hi[2] == pytest.approx(h)


def test_cap_nut_dome_and_blind_thread():
    nut = CapNut("M6", with_thread=False)  # DIN 1587: s 10, h 12, m 5, dk 9.5
    lo, hi = bbox(nut)
    assert hi[2] == pytest.approx(12.0)
    sphere = _ops(nut, "Sphere")[0]
    assert sphere.radius.value == pytest.approx(4.75)
    bore = [op for op in _ops(nut, "Extrusion") if op.cut.value][0]
    assert bore.end.value == pytest.approx(8.0)
    assert bore.end.value < 12.0  # blind


def test_flange_nut_flange():
    nut = FlangeNut("M8", with_thread=False)  # DIN 6923: dc 17.9, c 1.2, m 8
    lo, hi = bbox(nut)
    assert hi[0] - lo[0] == pytest.approx(17.9)
    assert hi[2] == pytest.approx(8.0)
    flange = [op for op in _ops(nut, "Lathe") if not op.cut.value][0]
    assert (17.9 / 2, 1.2) in [tuple(round(v, 6) for v in p) for p in _profile(flange)]


def test_nut_on_a_bolt_hole_connects():
    from cadbuildr.stdlib.standards import clearance_hole

    plate = _plate(10.0)
    clearance_hole(plate.anchor("h"), "M8", 10)
    asm = Assembly()
    asm.ground(plate)
    nut = FlangeNut("M8", with_thread=False)
    asm.connect(nut, plate.interface("h"))
    assert _world(nut.anchor("bottom"), asm) == pytest.approx([5.0, 0.0, 10.0])


# --------------------------------------------------------------------------- #
# Washers
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "cls,size,d1,d2,h",
    [
        (DIN433Washer, "M3", 3.2, 6.0, 0.5),  # ISO 7092
        (DIN433Washer, "M8", 8.4, 15.0, 1.6),
        (ISO7090Washer, "M8", 8.4, 16.0, 1.6),  # ISO 7090
    ],
)
def test_plain_washers(cls, size, d1, d2, h):
    w = cls(size)
    full = math.pi / 4 * (d2**2 - d1**2) * h
    vol = lathe_volume(w)
    if cls is ISO7090Washer:
        cz = 0.375 * h
        cr = cz / math.tan(math.radians(30))
        ring = math.pi * cr * cz * (d2 / 2 - cr / 3)  # Pappus of the chamfer triangle
        assert vol == pytest.approx(full - ring, rel=1e-9)
        assert vol < full
    else:
        assert vol == pytest.approx(full, rel=1e-9)
    lo, hi = bbox(w)
    assert hi[0] - lo[0] == pytest.approx(d2) and hi[2] == pytest.approx(h)


@pytest.mark.parametrize("size,form,teeth", [("M4", "A", 9), ("M8", "A", 11), ("M6", "J", 9)])
def test_tooth_lock_washer(size, form, teeth):
    w = ToothLockWasher(size, form)
    notches = [op for op in _ops(w, "Extrusion") if op.cut.value]
    assert len(notches) == teeth == w.teeth
    span = w.outer_radius - w.inner_radius
    if form == "A":
        assert w.root_radius == pytest.approx(w.outer_radius - 0.45 * span)
    else:
        assert w.root_radius == pytest.approx(w.inner_radius + 0.45 * span)


# --------------------------------------------------------------------------- #
# Pins
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("d,tol,mean", [("6", "m6", 6.008), ("8", "h8", 8 - 0.011)])
def test_parallel_pin_tolerance_and_volume(d, tol, mean):
    pin = ParallelPin(d, 24, tol)
    assert pin.diameter == pytest.approx(mean, abs=1e-6)  # ISO 286 zone middle
    r, c, L = mean / 2, pin.chamfer, 24.0
    # Cylinder minus two chamfer rings (Pappus of the 45° triangles).
    ring = math.pi * c * c * (2 * r - 2 * c / 3)
    assert lathe_volume(pin) == pytest.approx(math.pi * r * r * L - ring, rel=1e-9)
    assert pin.hole_fit == ("H7" if tol == "m6" else "H8")


def test_parallel_pin_in_its_hole():
    plate = _plate()
    pin = ParallelPin("6", 24)
    f = pin_hole(plate.anchor("h"), pin, 12)
    assert f.spec.designation == "H7" and f.diameter == pytest.approx(6.006)
    asm = Assembly()
    asm.ground(plate)
    asm.connect(pin.interface("end_a"), plate.interface("h"))
    show = asm.check()
    assert not [i for i in show if i["severity"] == "error"]


@pytest.mark.parametrize("d,d1,s", [("3", 3.4, 0.6), ("5", 5.5, 1.0), ("8", 8.65, 1.5)])
def test_spring_pin_is_a_slotted_tube(d, d1, s):
    pin = SpringPin(d, 24)
    assert pin.diameter == pytest.approx(d1) and pin.wall == s
    tube = [op for op in _ops(pin, "Lathe")][0]
    radii = {round(x, 6) for x, _ in _profile(tube)}
    assert round(d1 / 2 - s, 6) in radii and round(d1 / 2, 6) in radii
    assert pin.slot_width == pytest.approx(math.pi * (d1 - float(d)) + 0.1 * s)
    assert pin.hole_fit == "H12"


@pytest.mark.parametrize("d", ["3", "5", "8"])
def test_coiled_pin_spiral_section(d):
    pin = CoiledPin(d, 24)
    s = pin.strip
    outer, _ = CoiledPin.spiral(pin.diameter / 2, s, 2.25)
    strip_length = sum(math.dist(a, b) for a, b in zip(outer, outer[1:]))
    # Area of a strip of thickness s ~ s x mid-line length.
    assert pin.section_area == pytest.approx(s * (strip_length - math.pi * 2.25 * s), rel=0.03)
    lo, hi = bbox(pin)
    assert hi[0] == pytest.approx(pin.diameter / 2)  # the spiral starts on +X
    assert hi[2] == pytest.approx(24.0)
    assert pin.hole_fit == "H10"


def test_cotter_pin_iso_1234():
    p = CotterPin("3.2", 25)  # d 2.9, b 6.4, c 5.8
    assert p.wire_diameter == 2.9 and p.long_leg == pytest.approx(25 + 6.4)
    legs = sorted(op.end.value for op in _ops(p, "Extrusion"))
    assert legs == pytest.approx([25.0, 31.4])
    assert p.suits(12.0) and not p.suits(16.0)  # 11 < d <= 14
    assert p.eye_bottom < 0


def test_clevis_pin_with_split_pin_and_r_clip():
    pin = ClevisPin("8", 30, "B")  # ISO 2341: dk 14, k 3, d1 2, le 3.5
    assert (pin.head_diameter, pin.head_height, pin.split_pin_hole) == (14.0, 3.0, 2.0)
    assert pin.SPLIT_PIN == "2"
    lo, hi = bbox(pin)
    assert hi[2] == pytest.approx(33.0) and hi[0] - lo[0] == pytest.approx(14.0)
    cross = [op for op in _ops(pin, "Extrusion") if op.cut.value][0]
    assert cross.shape[0].radius.value == pytest.approx(1.0)
    asm = Assembly()
    asm.ground(pin)
    cotter = CotterPin("2", 16)
    asm.connect(cotter, pin.interface("split_pin"))
    assert _world(cotter.anchor("axis"), asm)[2] == pytest.approx(3.5)
    assert ClevisPin("10", 40, "A").split_pin_hole is None


def test_r_clip_din_11024():
    clip = RClip("4")  # d2 14..20, d3 3.6, l 64
    assert clip.wire_diameter == 3.6 and clip.length == 64
    assert clip.suits(16) and not clip.suits(25)
    assert len(_ops(clip, "Sweep")) == 1 and len(_ops(clip, "Lathe")) == 2


# --------------------------------------------------------------------------- #
# Rivets
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("d,dk,k,dm,hole", [("3.2", 6.7, 1.3, 2.0, 3.3), ("4.8", 10.1, 2.0, 2.95, 4.9)])
def test_blind_rivet_iso_15977(d, dk, k, dm, hole):
    r = BlindRivet(d, 12)
    assert (r.head_diameter, r.head_height, r.mandrel_diameter, r.drill_diameter) == (dk, k, dm, hole)
    sleeve, mandrel = _ops(r, "Lathe")
    sp = _profile(sleeve)
    assert max(x for x, _ in sp) == pytest.approx(dk / 2)
    assert max(z for _, z in sp) == pytest.approx(12 + k)
    assert min(x for x, _ in sp) == pytest.approx(dm / 2 + 0.05)  # hollow sleeve
    assert max(z for _, z in _profile(mandrel)) == pytest.approx(12 + k + r.mandrel_protrusion)
    lo, hi = r.grip_range
    assert codes(BlindRivet(d, 12, grip=(lo + hi) / 2)) == set()
    assert "rivet.grip" in codes(BlindRivet(d, 12, grip=hi + 1))


def test_blind_rivet_sets_in_its_hole():
    plate = _plate(4.0)
    rivet = BlindRivet("4", 10)
    f = rivet_hole(plate.anchor("h"), rivet, 4.0)
    assert f.diameter == 4.1
    asm = Assembly()
    asm.ground(plate)
    asm.connect(rivet, plate.interface("h"))
    assert _world(rivet.anchor("head_seat"), asm) == pytest.approx([5.0, 0.0, 4.0])


@pytest.mark.parametrize("head,dk,k", [("round", 7.0, 2.4), ("countersunk", 7.0, 2.0)])
def test_solid_rivet_heads(head, dk, k):
    r = SolidRivet("4", 12, head)
    pts = _profile(_ops(r, "Lathe")[0])
    assert max(x for x, _ in pts) == pytest.approx(dk / 2)
    if head == "round":
        assert max(z for _, z in pts) == pytest.approx(12 + k)
    else:  # flush 75° countersunk: (dk - d) / 2k = tan 37.5°
        assert max(z for _, z in pts) == pytest.approx(12)
        assert (dk - 4) / (2 * k) == pytest.approx(math.tan(math.radians(37.5)), rel=0.03)
    assert r.drill_diameter == 4.3


# --------------------------------------------------------------------------- #
# Inserts, studs, rod
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("size,length", [("M4", "1.5d"), ("M6", "1.5d"), ("M8", "2d")])
def test_wire_thread_insert(size, length):
    ins = WireThreadInsert(size, length)
    t = thread(size)
    k = float(length[:-1])
    assert ins.length == pytest.approx(k * t.major)
    assert ins.inner_diameter == pytest.approx(t.minor_internal)
    assert ins.outer_diameter == pytest.approx(t.major + 1.299038 * t.pitch, abs=1e-5)
    assert ins.outer_diameter > ins.drill_diameter > t.major
    coil = helices(ins)[0]
    assert coil.pitch.value == t.pitch and coil.height.value == pytest.approx(ins.length - t.pitch)
    assert coil.radius.value == pytest.approx((ins.inner_diameter + ins.outer_diameter) / 4)


def test_wire_thread_insert_hole_and_connect():
    plate = _plate()
    f = wire_thread_insert_hole(plate.anchor("h"), "M6", "1.5d")
    assert f.diameter == 6.3
    asm = Assembly()
    asm.ground(plate)
    ins = WireThreadInsert("M6", "1.5d")
    asm.connect(ins, plate.interface("h"))
    assert _world(ins.anchor("seat"), asm) == pytest.approx([5.0, 0.0, 20.0])


@pytest.mark.parametrize("size,series,bm", [("M8", "DIN 938", 8.0), ("M10", "DIN 939", 12.5)])
def test_studs(size, series, bm):
    st = StudBolt(size, 40, series)
    d = thread(size).major
    assert st.metal_end_length == pytest.approx(bm)
    assert st.nut_thread_length == pytest.approx(2 * d + 6)
    assert st.total_length == pytest.approx(bm + 40)
    sections = helices(st)
    assert [round(s.center.z.value, 6) for s in sections] == pytest.approx(
        [thread(size).pitch / 2, bm + 40 - (2 * d + 6) + thread(size).pitch / 2]
    )


@pytest.mark.parametrize("size", ["M6", "M10", "M16"])
def test_din976_rod_chamfered_to_the_root(size):
    rod = DIN976Rod(size, 200, with_thread=False)
    t = thread(size)
    assert rod.chamfer == pytest.approx((t.major - t.minor_external) / 2)
    r = t.major / 2
    c = rod.chamfer
    ring = math.pi * c * c * (2 * r - 2 * c / 3)
    assert lathe_volume(rod) == pytest.approx(math.pi * r * r * 200 - ring, rel=1e-9)


# --------------------------------------------------------------------------- #
# Knobs, handles, feet
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("d1,h1,t", [("16", 15.0, 7.0), ("25", 22.5, 11.0), ("40", 37.0, 18.0)])
def test_ball_knob_din_319(d1, h1, t):
    k = BallKnob(d1, with_thread=False)
    lo, hi = bbox(k)
    assert hi[2] == pytest.approx(h1)
    assert hi[0] - lo[0] == pytest.approx(float(d1))
    R = float(d1) / 2
    assert k.base_diameter == pytest.approx(2 * math.sqrt(R**2 - (h1 - R) ** 2))
    assert k.thread_depth == t


@pytest.mark.parametrize("d1", ["16", "25", "32"])
def test_fixed_handle_mass_matches_catalogue(d1):
    h = FixedHandle(d1, with_thread=False)
    grams = material("c45").mass_kg(lathe_volume(h)) * 1000
    assert grams == pytest.approx(h.catalogue_mass_g, rel=0.15)
    lo, hi = bbox(h)
    assert hi[2] == pytest.approx(h.length, abs=1e-6)
    assert lo[2] == pytest.approx(-h.pin_length)


@pytest.mark.parametrize("base,d1,af", [("32-M10", 32.0, 15.0), ("60-M16", 60.0, 24.0)])
def test_levelling_foot(base, d1, af):
    f = LevellingFoot(base, 80, with_thread=False)
    lo, hi = bbox(f)
    assert hi[0] - lo[0] == pytest.approx(d1)
    assert hi[2] == pytest.approx(f.base_height + 80)
    hexes = [op for op in _ops(f, "Extrusion")]
    assert len(hexes) == 1 and f.width_across_flats == af


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ISO4032Nut("M7"),
        lambda: NylonInsertNut("M8", "ISO 7041"),
        lambda: ParallelPin("7"),
        lambda: ToothLockWasher("M6", "V"),
        lambda: BlindRivet("5"),
        lambda: WireThreadInsert("M6", "4d"),
        lambda: StudBolt("M9"),
        lambda: BallKnob("30"),
        lambda: LevellingFoot("70-M20"),
        lambda: ClevisPin("8", 200),
    ],
)
def test_bad_inputs_raise_named_errors(factory):
    with pytest.raises(ValueError):
        factory()
