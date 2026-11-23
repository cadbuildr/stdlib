"""Tube joinery one-liners: cope-cut + place in a single call.

Like the wood joinery library, a tube junction both **positions** the tubes
and **shapes** them — here the branch tube end gets a cope (saddle) cut so it
hugs the main tube::

    tube_tee(assembly, branch, main, at=400)

Planned (same Connection pattern): mitred corner (both ends cut 45°),
crossing with notches.
"""

from __future__ import annotations

import math
from typing import Any, Optional

from cadbuildr.foundation import (
    Circle,
    Connection,
    Extrusion,
    PartModifier,
    RigidJoint,
    Sketch,
    anchor_plane,
)


def tube_tee(
    assembly: Any,
    branch: Any,
    main: Any,
    at: Optional[float] = None,
    angle: float = 0.0,
    end: str = "b",
    sink: Optional[float] = None,
    fit: float = 0.3,
) -> Connection:
    """Join ``branch``'s end onto ``main``'s side at a right angle (tee).

    The branch end is cope-cut (a cylinder of the main tube's diameter is
    removed) and sunk ``sink`` millimeters so the saddle wraps the main tube.

    Args:
        at: millimeters along the main tube (default: mid-length).
        angle: roll of the branch around the main tube, radians.
        end: which branch end joins (``a``/``b``).
        sink: saddle engagement depth (default: the sagitta of the branch
            width on the main tube — the natural wrap depth).
        fit: clearance added to the cope radius.
    """
    if at is None:
        at = main.length / 2.0
    if sink is None:
        # Sagitta of the branch tube's chord on the main tube surface.
        r_main, r_branch = main.outer_radius, branch.outer_radius
        chord = min(r_branch, r_main * 0.99)
        sink = r_main - math.sqrt(r_main**2 - chord**2)

    branch_end = branch.anchor(f"end_{end}")
    seat = main.radial_anchor(at, angle, name=f"tee_{at:g}_{angle:g}").offset(
        [0.0, 0.0, -sink], name="tee_seat"
    )

    # Cope cut: remove a cylinder around the main tube axis from the branch
    # end. In branch-end coordinates the main axis runs along the anchor X at
    # height (main radius - sink) past the end plane.
    cope_center = branch_end.offset(
        [0.0, 0.0, main.outer_radius - sink], name="cope_center"
    )
    cope_axis = cope_center.rotated(
        math.pi / 2.0, axis=[0.0, 1.0, 0.0], name="cope_axis"
    )
    cope_sketch = Sketch(anchor_plane(cope_axis))
    cope_circle = Circle(cope_sketch.origin, main.outer_radius + fit)
    span = branch.outer_diameter
    cope = Extrusion(cope_circle, span, -span, cut=True)

    connection = Connection(
        joint=RigidJoint(parent_anchor=seat, child_anchor=branch_end),
        modifiers=[PartModifier(anchor=branch_end, operations=[cope])],
    )
    assembly.add_connection(connection)
    return connection
