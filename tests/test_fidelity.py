"""Geometry fidelity checks against published values (fidelity review):
T8 trapezoidal lead screw, GT2 pulley hub, gear / rack root fillets."""

from __future__ import annotations

import math

import pytest

from cadbuildr.foundation import Assembly
from cadbuildr.foundation.compute_functions import component_frames
from cadbuildr.foundation.math_utils import tf_relative_to_frame

from cadbuildr.stdlib.common import trapezoidal_thread_geometry
from cadbuildr.stdlib.fasteners import SetScrew, connect_with_screw
from cadbuildr.stdlib.linear_motion.lead_screws.lead_screw_part import (
    LeadScrewNutT8,
    LeadScrewT8,
)
from cadbuildr.stdlib.power_transmission.gears import SpurGear
from cadbuildr.stdlib.power_transmission.gears.rack_part import rack_outline
from cadbuildr.stdlib.power_transmission.gears.spur_gear_part import (
    ADDENDUM,
    DEDENDUM,
    spur_gear_outline,
)
from cadbuildr.stdlib.power_transmission.pulleys import GT2Pulley

# --------------------------------------------------------------------------- #
# T8 lead screw
# --------------------------------------------------------------------------- #


def test_din103_tr8x2_dimensions():
    g = trapezoidal_thread_geometry(8.0, 2.0)
    # DIN 103-4 Tr 8x2 (screw d3, pitch d2, nut D1 / D4, depth h3, clearance ac)
    assert g["d3"] == pytest.approx(5.5)
    assert g["d2"] == pytest.approx(7.0)
    assert g["D1"] == pytest.approx(6.0)
    assert g["D4"] == pytest.approx(8.5)
    assert g["h3"] == pytest.approx(1.25)
    assert g["ac"] == pytest.approx(0.25)
    # Crest flat 0.366 P (30° flanks, P/2 thick on the pitch line).
    crest = 2 * (2.0 / 4 - (8.0 / 2 - g["d2"] / 2) * math.tan(math.radians(15)))
    assert crest == pytest.approx(0.366 * 2.0, abs=1e-3)


@pytest.mark.parametrize("lead,starts", [("8", 4), ("2", 1)])
def test_t8_lead_and_starts(lead, starts):
    screw = LeadScrewT8(length=100, lead=lead)
    nut = LeadScrewNutT8(lead=lead)
    assert screw.lead == nut.lead == float(lead)
    assert screw.starts == nut.starts == starts
    assert screw.pitch == 2.0  # tooth spacing; lead is what a ScrewRelation uses


def test_t8_default_is_the_printer_tr8x8():
    assert LeadScrewT8(length=100).lead == 8.0
    with pytest.raises(ValueError, match="choose from"):
        LeadScrewT8(length=100, lead="4")


# --------------------------------------------------------------------------- #
# GT2 pulley hub
# --------------------------------------------------------------------------- #


def _world(anchor, assembly):
    return tf_relative_to_frame(anchor.frame, component_frames(assembly))


def test_gt2_pulley_hub_and_set_screws():
    p = GT2Pulley(teeth=20, bore=5)
    assert p.hub_length == 7 and p.hub_diameter == pytest.approx(2 * p.pitch_radius + 3)
    # 1 + 6 + 1 (flanges + belt) + 7 hub = the ~16 mm of a stock 20T pulley
    assert p.height == pytest.approx(15.0)
    names = {a.name.value for a in p.anchors}
    assert {"set_screw_0", "set_screw_1"} <= names
    plain = GT2Pulley(teeth=20, bore=5, hub=False)
    assert plain.height == pytest.approx(8.0) and plain.hub_length == 0


def test_set_screw_drops_into_the_pulley_hub():
    p = GT2Pulley(teeth=20, bore=5)
    grub = SetScrew("M3", 4, "cup", with_thread=False)
    assembly = Assembly()
    assembly.add_component(p)
    connect_with_screw(assembly, grub, p.anchor("set_screw_0"), drill=False)
    tip, _ = _world(grub.anchor("tip"), assembly)
    # Flush in the hub, 4 mm deep: the cup point stops on the 5 mm bore.
    assert tip[0] == pytest.approx(p.hub_diameter / 2 - 4)
    assert tip[0] >= 2.5 - 1e-9


# --------------------------------------------------------------------------- #
# Gear and rack profiles
# --------------------------------------------------------------------------- #


def _angles_increase(pts):
    angles = [math.atan2(y, x) % (2 * math.pi) for x, y in pts]
    start = angles.index(min(angles))
    seq = angles[start:] + [a + 2 * math.pi for a in angles[:start]]
    return all(b >= a - 1e-12 for a, b in zip(seq, seq[1:]))


@pytest.mark.parametrize("teeth", [8, 12, 17, 30, 60])
def test_gear_outline_is_star_shaped_with_root_fillets(teeth):
    m = 1.0
    pts = spur_gear_outline(m, teeth)
    rp = m * teeth / 2
    rf, ra = rp - DEDENDUM * m, rp + ADDENDUM * m
    radii = [math.hypot(x, y) for x, y in pts]
    assert min(radii) == pytest.approx(rf, abs=1e-9)
    assert max(radii) == pytest.approx(ra, abs=1e-9)
    assert _angles_increase(pts), "outline folds back on itself"
    # Fillet: points strictly between the root circle and the flank start.
    assert sum(1 for r in radii if rf + 1e-6 < r < rf + 0.3 * m) >= teeth * 2
    assert len(pts) >= teeth * 30  # 13 flank points per side + fillets


def test_rack_outline_has_root_fillets_and_runs_left_to_right():
    m = 1.5
    pts = rack_outline(m, 10, 10)
    xs = [x for x, _ in pts[1:-1]]
    assert all(b >= a - 1e-9 for a, b in zip(xs, xs[1:]))
    ded = DEDENDUM * m
    # Fillet points lift off the root line by up to ~rho (1 - sin 20°).
    lifted = [y for _, y in pts if -ded + 1e-6 < y < -ded + 0.38 * m]
    assert len(lifted) >= 10 * 2 * 3


def test_gear_hub_and_its_limits():
    g = SpurGear(module=1, teeth=30, bore=8, hub_length=8)
    assert g.hub_diameter == pytest.approx(1.6 * 8 + 4)
    names = {a.name.value for a in g.anchors}
    assert {"hub_end", "set_screw"} <= names
    with pytest.raises(ValueError, match="no room for a hub"):
        SpurGear(module=0.5, teeth=12, bore=4, hub_length=5)


# --------------------------------------------------------------------------- #
# Countersunk heads (ISO 10642 socket, ISO 2009 slotted)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "cls_name", ["CountersunkSocketScrew", "CountersunkSlottedScrew"]
)
def test_countersunk_heads_follow_the_iso_tables(cls_name):
    from cadbuildr.stdlib import fasteners
    from cadbuildr.stdlib.common import countersunk_head_profile, nominal_diameter

    cls = getattr(fasteners, cls_name)
    for size, row in cls.TABLE.items():
        d = nominal_diameter(size)
        # 90° head: k = (dk_theoretical - d) / 2, as tabulated.
        assert row["k"] == pytest.approx((row["dk"] - d) / 2, abs=0.011), size
        assert row["dka"] < row["dk"]
        pts = countersunk_head_profile(d / 2 - 0.1, 20.0, d, row["dk"], row["dka"])
        (r0, z0), (r1, z1) = pts[3], pts[4]
        assert r1 - r0 == pytest.approx(z1 - z0)  # 45° flank
        # Extended to the top face the cone reaches dk: flush in a dk countersink.
        assert r0 + (20.0 - z0) == pytest.approx(row["dk"] / 2)
        assert pts[5] == pytest.approx((row["dka"] / 2, 20.0))
    screw = cls("M6", 20, with_thread=False)
    assert screw.head_radius == pytest.approx(cls.TABLE["M6"]["dk"] / 2)
