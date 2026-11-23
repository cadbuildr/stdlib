"""Gear meshing on foundation joints.

    mesh_gears(assembly, pinion, wheel)            # wheel meshes on pinion's +X
    mesh_gears(assembly, pinion, idler, angle=pi)  # on the opposite side

The driven gear is placed by a ``RevoluteJoint`` about its own axis, located on
the driver's ``pitch_plane`` at the centre distance ``r1 + r2`` (pitch radii),
and phased so a tooth of one sits in a gap of the other.
"""

from __future__ import annotations

import math
from typing import Any

from cadbuildr.foundation import BoolParameter, FloatParameter, RevoluteJoint


def center_distance(driver: Any, driven: Any, backlash: float = 0.0) -> float:
    """Operating centre distance of two spur gears: sum of pitch radii (+ backlash)."""
    return float(driver.pitch_radius) + float(driven.pitch_radius) + float(backlash)


def mesh_phase(driver: Any, driven: Any, angle: float = 0.0) -> float:
    """Rotation of ``driven`` (about its axis, in the mesh frame) that puts a
    gap of ``driven`` against a tooth of ``driver`` on the line of centres.

    Both gears have tooth 0 on their +X. With the line of centres at ``angle``
    in the driver frame, rolling contact turns the driven gear by
    ``angle * z1 / z2``; a driven gear with an even tooth count needs an extra
    half tooth so a gap (not a tooth) faces the driver.
    """
    z1, z2 = int(driver.teeth), int(driven.teeth)
    base = 0.0 if z2 % 2 else math.pi / z2
    return base + angle * z1 / z2


def mesh_gears(
    assembly: Any,
    driver: Any,
    driven: Any,
    angle: float = 0.0,
    backlash: float = 0.0,
) -> Any:
    """Place ``driven`` in mesh with the already-placed ``driver``.

    ``angle`` (rad) is the direction of the line of centres, measured about
    the driver axis from the driver's +X. Gears must share a module. Returns
    the ``RevoluteJoint`` (its angle is the mesh phase; the placement is
    static, so re-phase with :func:`mesh_phase` if you change ``angle``).
    """
    if not math.isclose(float(driver.module), float(driven.module)):
        raise ValueError(
            f"Gears must share a module to mesh ({driver.module} vs {driven.module})."
        )
    cd = center_distance(driver, driven, backlash)
    tag = f"mesh_{len(assembly.joints)}"
    parent = (
        driver.anchor("pitch_plane")
        .rotated(float(angle), name=f"{tag}_dir")
        .offset([cd, 0.0, 0.0], name=f"{tag}_center")
    )
    joint = RevoluteJoint(
        parent_anchor=parent,
        child_anchor=driven.anchor("pitch_plane"),
        angle=FloatParameter(value=mesh_phase(driver, driven, angle)),
        flip=BoolParameter(value=False),
    )
    assembly.add_joint(joint)
    return joint
