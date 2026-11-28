"""Worked examples: small anchor-driven assemblies, the reference for placing
stdlib parts. No transform math anywhere — every part is placed by mating
named anchors, joints and the connection helpers::

    from cadbuildr.foundation import show
    from cadbuildr.stdlib.examples import bolted_plate, rack_and_pinion
    show(rack_and_pinion(angle=0.5))

Each ``<name>()`` returns the assembly; ``build_<name>()`` also returns the
part handles (and joints) to query anchors or drive DOFs afterwards.

| Example | Shows |
|---|---|
| ``bolted_plate`` | ``connect_with_bolt_and_nut`` through a plate, washers both sides |
| ``motor_leadscrew_stack`` | NEMA 17 -> clamp coupling -> T8 lead screw + nut by ``RigidJoint`` |
| ``gear_pair`` | two spur gears placed by ``mesh_gears`` |
| ``rack_and_pinion`` | ``mesh_rack``: a ``RackPinionRelation`` couples pinion angle and rack travel |
| ``rail_slide`` | MGN12 rail screwed into tapped base holes, carriage on a ``SliderJoint`` |
| ``pcb_on_standoffs`` | heat-set inserts, male-female standoffs and pan head screws holding a PCB |
"""

from cadbuildr.stdlib.examples.basics import (  # noqa: F401  (_plate: kept importable)
    _plate,
    bolted_plate,
    build_bolted_plate,
    build_gear_pair,
    build_motor_leadscrew_stack,
    gear_pair,
    motor_leadscrew_stack,
)
from cadbuildr.stdlib.examples.electronics import (
    build_pcb_on_standoffs,
    pcb_on_standoffs,
)
from cadbuildr.stdlib.examples.motion import (
    build_rack_and_pinion,
    build_rail_slide,
    rack_and_pinion,
    rail_slide,
)

__all__ = [
    "bolted_plate",
    "build_bolted_plate",
    "build_gear_pair",
    "build_motor_leadscrew_stack",
    "build_pcb_on_standoffs",
    "build_rack_and_pinion",
    "build_rail_slide",
    "gear_pair",
    "motor_leadscrew_stack",
    "pcb_on_standoffs",
    "rack_and_pinion",
    "rail_slide",
]
