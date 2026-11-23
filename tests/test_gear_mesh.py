"""Gears placed by mesh_gears() do not interpenetrate while they roll.

foundation's check_interference() compares bounding volumes and treats jointed
pairs as intended contacts, so it cannot see tooth overlap. This test checks
the actual 2D tooth outlines (the extruded profile) in the mesh frame used by
mesh_gears(): driven gear at the centre distance r1 + r2, phased by
mesh_phase(), then both rolled through one pinion tooth pitch.
"""

import math
from types import SimpleNamespace

import pytest

from cadbuildr.stdlib.power_transmission.gears import SpurGear, mesh_gears
from cadbuildr.stdlib.power_transmission.gears.connections import (
    center_distance,
    mesh_phase,
)
from cadbuildr.stdlib.power_transmission.gears.spur_gear_part import (
    spur_gear_outline,
)


def _place(points, angle, dx=0.0):
    c, s = math.cos(angle), math.sin(angle)
    return [(x * c - y * s + dx, x * s + y * c) for x, y in points]


def _inside(pt, poly):
    """Even-odd ray cast; points on the boundary may go either way."""
    x, y = pt
    hit = False
    j = len(poly) - 1
    for i, (xi, yi) in enumerate(poly):
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _segments_cross(p1, p2, q1, q2, eps=1e-9):
    """Proper crossing (strict; touching does not count)."""
    d1, d2 = _cross(q1, q2, p1), _cross(q1, q2, p2)
    d3, d4 = _cross(p1, p2, q1), _cross(p1, p2, q2)
    return d1 * d2 < -eps and d3 * d4 < -eps


def _near(poly, centre, radius):
    """Edges with an endpoint within ``radius`` of ``centre``."""
    cx, cy = centre
    r2 = radius * radius
    out = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        if (
            min(
                (a[0] - cx) ** 2 + (a[1] - cy) ** 2, (b[0] - cx) ** 2 + (b[1] - cy) ** 2
            )
            <= r2
        ):
            out.append((a, b))
    return out


def _gear(module, teeth):
    # What mesh_gears() reads off a SpurGear (building big gears is slow).
    return SimpleNamespace(module=module, teeth=teeth, pitch_radius=module * teeth / 2)


def _overlaps(module, z1, z2, steps=24):
    g1, g2 = _gear(module, z1), _gear(module, z2)
    cd = center_distance(g1, g2)
    phase = mesh_phase(g1, g2)
    o1 = spur_gear_outline(module, z1)
    o2 = spur_gear_outline(module, z2)
    contact = (g1.pitch_radius, 0.0)  # pitch point on the line of centres
    zone = 4 * module
    for k in range(steps):
        theta = 2 * math.pi / z1 * k / steps
        a = _place(o1, theta)
        b = _place(o2, phase - theta * z1 / z2, cd)
        ea, eb = _near(a, contact, zone), _near(b, contact, zone)
        if any(_inside(p, b) for p, _ in ea) or any(_inside(p, a) for p, _ in eb):
            return theta
        for p1, p2 in ea:
            for q1, q2 in eb:
                if _segments_cross(p1, p2, q1, q2):
                    return theta
    return None


@pytest.mark.parametrize(
    "module,z1,z2",
    [(1, 12, 30), (1, 20, 20), (0.5, 8, 60), (3, 8, 60), (1, 13, 31), (2, 60, 60)],
)
def test_meshed_gears_do_not_overlap(module, z1, z2):
    assert _overlaps(module, z1, z2) is None


def test_overlap_detector_sees_a_bad_phase():
    """Sanity: rotating the driven gear half a tooth puts tooth on tooth."""
    g1, g2 = _gear(1, 12), _gear(1, 30)
    cd = center_distance(g1, g2)
    bad = mesh_phase(g1, g2) + math.pi / 30
    a = _place(spur_gear_outline(1, 12), 0.0)
    b = _place(spur_gear_outline(1, 30), bad, cd)
    assert any(_inside(p, b) for p in a)


def test_outline_is_closed_and_ccw():
    pts = spur_gear_outline(1, 20)
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    assert area > 0
    assert pts[0] != pts[-1]


def test_mesh_gears_still_places_at_pitch_sum():
    from cadbuildr.foundation import Assembly

    g1, g2 = SpurGear(teeth=12), SpurGear(teeth=30)
    asm = Assembly()
    asm.add_component(g1)
    joint = mesh_gears(asm, g1, g2)
    assert center_distance(g1, g2) == pytest.approx(21.0)
    assert joint.angle.value == pytest.approx(mesh_phase(g1, g2))
