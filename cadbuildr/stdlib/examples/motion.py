"""Worked examples: driven motion with joint relations and slider joints.

* :func:`rack_and_pinion` — a spur gear pinion on a revolute joint drives a
  gear rack through ``mesh_rack`` (a ``RackPinionRelation``): turning the
  pinion slides the rack by ``pitch_radius x angle``.
* :func:`rail_slide` — an MGN12 rail bolted to a base plate with DIN 912
  screws, its carriage on a slider joint, a plate screwed on the carriage.

Both return ``(assembly, parts, joints)`` builders and plain-assembly
wrappers, like :mod:`cadbuildr.stdlib.examples.basics`.
"""

from __future__ import annotations

import math

from cadbuildr.foundation import (
    Assembly,
    BoolParameter,
    FloatParameter,
    RevoluteJoint,
)

from cadbuildr.stdlib.examples.basics import _plate
from cadbuildr.stdlib.fasteners import DIN912Screw, connect_with_screw
from cadbuildr.stdlib.linear_motion.rails import (
    LinearRail,
    RailCarriage,
    mount_carriage,
)
from cadbuildr.stdlib.power_transmission.gears import GearRack, SpurGear, mesh_rack


def build_rack_and_pinion(angle: float = 0.0):
    """m1 20-tooth pinion over a 200 mm m1 rack, pinion turned to ``angle`` rad.

    Returns ``(assembly, parts, joints)`` with joints ``spin`` (the pinion's
    ``RevoluteJoint``) and ``slide`` (the rack's ``SliderJoint``).
    """
    frame = _plate(60.0, 20.0, 4.0, color="#6b7480")
    pinion = SpurGear(module=1, teeth=20, face_width=6, bore=5)
    rack = GearRack(module=1, length=200, face_width=6, height=8)
    assembly = Assembly()
    assembly.add_component(frame)
    spin = RevoluteJoint(
        parent_anchor=frame.anchor("hole").offset([0.0, 0.0, 10.0], name="axle"),
        child_anchor=pinion.anchor("axis"),
        angle=FloatParameter(value=float(angle)),
        flip=BoolParameter(value=False),
    )
    assembly.add_joint(spin)
    slide, _ = mesh_rack(assembly, pinion, rack, spin)
    return (
        assembly,
        {"frame": frame, "pinion": pinion, "rack": rack},
        {
            "spin": spin,
            "slide": slide,
        },
    )


def rack_and_pinion(angle: float = 0.0) -> Assembly:
    """See :func:`build_rack_and_pinion`."""
    return build_rack_and_pinion(angle)[0]


def build_rail_slide(at: float = 150.0, with_thread: bool = False):
    """MGN12 x 300 rail screwed to a base plate, MGN12H carriage at ``at`` mm,
    a 40 x 40 plate on the carriage.

    Every part is placed by anchors and joints: the rail's mounting holes take
    DIN 912 M3 screws through ``connect_with_screw`` (screw heads in the
    counterbores, holes drilled into the base), the carriage rides a
    ``SliderJoint`` from ``mount_carriage``, the top plate sits on the
    carriage's ``top`` face.
    """
    from cadbuildr.foundation import RigidJoint

    base = _plate(80.0, 340.0, 6.0, color="#6b7480")
    rail = LinearRail("MGN12", 300)
    carriage = RailCarriage("MGN12", "H")
    top = _plate(40.0, 40.0, 5.0)
    assembly = Assembly()
    assembly.add_component(base)
    # Rail bottom face on the base top, rail running along the base's +Y.
    rail_line = base.anchor("hole").rotated(
        math.pi / 2, axis=[0.0, 0.0, 1.0], name="rail_line"
    )
    assembly.add_joint(
        RigidJoint(parent_anchor=rail_line, child_anchor=rail.anchor("bottom"))
    )
    # One M3 x 8 cap screw per rail hole, threaded into a tapped base hole
    # right under it (rail_line X runs along the rail).
    screws = []
    for i in range(rail.hole_count):
        screw = DIN912Screw(rail.bolt, 8, with_thread=with_thread)
        along = rail.end_distance + i * rail.hole_pitch - rail.length / 2
        tap = rail_line.offset([along, 0.0, 0.0], name=f"rail_tap_{i}")
        connect_with_screw(
            assembly,
            screw,
            rail.anchor(f"mount_hole_{i}"),
            drill=False,
            into=tap,
            into_depth=screw.body_height - rail.hole_grip + 0.5,
        )
        screws.append(screw)
    slide = mount_carriage(assembly, rail, carriage, at=at)
    assembly.add_joint(
        RigidJoint(
            parent_anchor=carriage.anchor("top"), child_anchor=top.anchor("bottom")
        )
    )
    parts = {"base": base, "rail": rail, "carriage": carriage, "top": top}
    return assembly, {**parts, "screws": screws}, {"slide": slide}


def rail_slide(at: float = 150.0) -> Assembly:
    """See :func:`build_rail_slide`."""
    return build_rail_slide(at)[0]
