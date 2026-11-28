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
    driver_joint: Any = None,
) -> Any:
    """Place ``driven`` in mesh with the already-placed ``driver``.

    ``angle`` (rad) is the direction of the line of centres, measured about
    the driver axis from the driver's +X. Gears must share a module. Returns
    the driven gear's ``RevoluteJoint``.

    With ``driver_joint`` (the ``RevoluteJoint`` that spins the driver on
    its axle, child anchor ``axis`` or ``pitch_plane``) the driven gear gets
    its own axle in the same fixed frame and a ``GearRelation`` couples them:
    ``driver_joint.set_angle(a)`` turns the driven gear by ``-a * z1 / z2``,
    tooth-in-gap at every angle — a gear train that animates. Without it
    (legacy) the driven gear hangs off the driver's ``pitch_plane`` and the
    placement is static.
    """
    if not math.isclose(float(driver.module), float(driven.module)):
        raise ValueError(
            f"Gears must share a module to mesh ({driver.module} vs {driven.module})."
        )
    cd = center_distance(driver, driven, backlash)
    tag = f"mesh_{len(assembly.joints)}"
    if driver_joint is not None:
        return _mesh_on_axles(assembly, driver, driven, driver_joint, angle, cd, tag)
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


def _axle_mid_offset(gear: Any, joint: Any, who: str) -> float:
    """z of ``gear``'s mid face width in the frame of ``joint.parent_anchor``."""
    child = joint.child_anchor.name.value
    if child not in _PINION_ANCHOR_Z:
        raise ValueError(
            f"{who}: the joint must place the gear by 'axis' or 'pitch_plane' "
            f"(got '{child}')."
        )
    sign = -1.0 if bool(joint.flip.value) else 1.0
    return (0.5 - _PINION_ANCHOR_Z[child]) * float(gear.face_width) * sign


def _mesh_on_axles(assembly, driver, driven, driver_joint, angle, cd, tag):
    from cadbuildr.foundation import GearRelation

    mid = _axle_mid_offset(driver, driver_joint, "mesh_gears")
    parent = driver_joint.parent_anchor.rotated(float(angle), name=f"{tag}_dir").offset(
        [cd, 0.0, mid], name=f"{tag}_center"
    )
    ratio = int(driver.teeth) / int(driven.teeth)
    phase = mesh_phase(driver, driven, angle)
    joint = RevoluteJoint(
        parent_anchor=parent,
        child_anchor=driven.anchor("pitch_plane"),
        angle=FloatParameter(value=phase - ratio * float(driver_joint.angle.value)),
        flip=BoolParameter(value=False),
    )
    assembly.add_joint(joint)
    assembly.add_relation(
        GearRelation(
            driver=driver_joint,
            driven=joint,
            ratio=FloatParameter(value=ratio),
            reverse=BoolParameter(value=True),
            offset=FloatParameter(value=phase),
        )
    )
    return joint


# Where each supported pinion child anchor sits along the gear axis, as a
# fraction of the face width.
_PINION_ANCHOR_Z = {"axis": 0.0, "pitch_plane": 0.5}


def rack_phase(pinion: Any, angle: float = 0.0) -> float:
    """Rack offset (mm) at pinion angle 0 that puts a rack gap on a pinion
    tooth at the contact point (the line of contact at ``angle`` from the
    axle frame's -Y)."""
    step = 2 * math.pi / int(pinion.teeth)
    return float(pinion.pitch_radius) * ((math.pi / 2 - float(angle)) % step)


def mesh_rack(
    assembly: Any,
    pinion: Any,
    rack: Any,
    pinion_joint: Any,
    angle: float = 0.0,
) -> tuple[Any, Any]:
    """Mesh ``rack`` under ``pinion`` and couple them.

    ``pinion_joint`` is the ``RevoluteJoint`` (already added) that spins the
    pinion on its axle, with the pinion's ``axis`` or ``pitch_plane`` as
    child anchor. The rack goes on a ``SliderJoint`` from the same axle
    frame, its pitch line tangent to the pitch circle on the axle's -Y side
    (turned by ``angle`` rad about the axle), mid face widths aligned, and a
    ``RackPinionRelation`` makes ``pinion_joint.set_angle(a)`` slide the rack
    by ``pitch_radius * a`` (and ``slide.set_offset(x)`` turn the pinion).
    Tooth phase: a rack gap faces a pinion tooth at every angle.

    Returns ``(slide_joint, relation)``. Raises ``ValueError`` when the
    modules differ or the pinion joint uses another child anchor.
    """
    from cadbuildr.foundation import RackPinionRelation, SliderJoint

    if not math.isclose(float(pinion.module), float(rack.module)):
        raise ValueError(
            f"mesh_rack: pinion module {pinion.module} != rack module {rack.module}."
        )
    child = pinion_joint.child_anchor.name.value
    if child not in _PINION_ANCHOR_Z:
        raise ValueError(
            f"mesh_rack: the pinion joint must place the pinion by 'axis' or "
            f"'pitch_plane' (got '{child}')."
        )
    flipped = bool(pinion_joint.flip.value)
    fw = float(pinion.face_width)
    mid = (0.5 - _PINION_ANCHOR_Z[child]) * fw * (-1.0 if flipped else 1.0)
    r = float(pinion.pitch_radius)
    tag = f"rack_{len(assembly.joints)}"
    parent = (
        pinion_joint.parent_anchor.rotated(float(angle), name=f"{tag}_dir")
        .offset([0.0, -r, mid], name=f"{tag}_pitch")
        .rotated(math.pi / 2, axis=[0.0, 1.0, 0.0], name=f"{tag}_slide")
    )
    phase = rack_phase(pinion, angle)
    slide = SliderJoint(
        parent_anchor=parent,
        child_anchor=rack.anchor("slide"),
        offset=FloatParameter(value=r * float(pinion_joint.angle.value) + phase),
        flip=BoolParameter(value=False),
    )
    assembly.add_joint(slide)
    relation = RackPinionRelation(
        pinion=pinion_joint,
        rack=slide,
        pitch_radius=FloatParameter(value=r),
        offset=FloatParameter(value=phase),
    )
    assembly.add_relation(relation)
    return slide, relation
