"""Helical wire geometry shared by the springs: coils are swept circles.

Each coil section is a foundation ``Thread`` (a circular wire profile swept
along a ``Helix3D``): the kernel places the profile's x=0 on the helix
radius, so a circle centred on the sketch origin becomes a round wire whose
centre line runs at ``radius``. A helix starts at angle 0 (+X) and turns
right-handed about +Z; sections that each span whole turns therefore join
end to end at +X.
"""

from __future__ import annotations

from cadbuildr.foundation import Circle, Point, Point3D, Sketch, Thread

__all__ = ["add_coil"]


def add_coil(part, *, d: float, D: float, pitch: float, z0: float, turns: float):
    """Sweep ``turns`` coils of round wire ``d`` on mean diameter ``D`` with
    ``pitch`` from wire-centre height ``z0``; returns the ``Thread`` op."""
    s = Sketch(part.xz())
    op = Thread(
        profile=Circle(Point(s, 0.0, 0.0), d / 2.0),
        pitch=pitch,
        height=pitch * turns,
        radius=D / 2.0,
        center=Point3D(0.0, 0.0, z0),
        dir=Point3D(0.0, 0.0, 1.0),
    )
    part.add_operation(op)
    return op
